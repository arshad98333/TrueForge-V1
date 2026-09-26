"""Adapter for the inspected TrueForge 0.2.1 HTTP contract."""

import json
from urllib.parse import quote

import httpx

from .integrations import ProviderError
from .store import PolicyError


class TrueForge:
    def __init__(self, base_url, token="", transport=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.client = httpx.Client(
            base_url=base_url, headers=headers, timeout=10, transport=transport
        )

    def request(self, method, path, **kwargs):
        try:
            response = self.client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            error = ProviderError(
                f"TrueForge {method} {path} returned HTTP {exc.response.status_code}"
            )
            error.status_code = exc.response.status_code
            raise error from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError("TrueForge request failed; check runtime and contract") from exc

    def pages(self, path, limit=100):
        items, token = [], None
        for _ in range(10):
            params = {"limit": limit}
            if token:
                params["page_token"] = token
            body = self.request("GET", path, params=params)
            items.extend(body["data"])
            token = body.get("pagination", {}).get("next_page_token")
            if not token:
                return items
        raise PolicyError("TrueForge trace exceeds its verification bound")

    def snapshot(self, session_id):
        path = "/api/v1/sessions/" + quote(session_id, safe="")
        session = self.request("GET", path)["data"]
        turns = self.pages(path + "/turns", limit=25)
        events = self.pages(path + "/events")
        return {"session": session, "turns": turns, "events": events}


def tool_calls(snapshot):
    for item in snapshot["events"]:
        event = item["event"]
        if event.get("type") == "model.message" and event.get("thread_id") == "main":
            for call in event.get("tool_calls", []):
                try:
                    arguments = json.loads(call["function"]["arguments"])
                except (KeyError, ValueError, TypeError):
                    continue
                yield item["turn_id"], event, call, arguments


def native_approval(snapshot, *, session_id, tool_name, arguments):
    """Accept only a native per-call allow in the CURRENT running approval turn."""
    if snapshot["session"]["id"] != session_id:
        raise PolicyError("Wrong TrueForge session")
    turns = sorted(snapshot["turns"], key=lambda turn: turn["created_at"], reverse=True)
    if not turns or turns[0]["state"]["status"] != "running":
        raise PolicyError("No current native approval turn")
    current = turns[0]
    for _, source, call, supplied in tool_calls(snapshot):
        info = call.get("tool_info", {})
        if (
            info.get("type") != "mcp"
            or info.get("server_name") != "roaming-resolver"
            or info.get("name") != tool_name
            or supplied != arguments
        ):
            continue
        gates = [
            item
            for item in snapshot["events"]
            if item["event"].get("type") == "tool.approval_required"
            and item["event"].get("thread_id") == "main"
            and {"id": call["id"], "source_event_id": source["id"]}
            in item["event"].get("tool_calls", [])
        ]
        if not gates or current.get("previous_turn_id") not in {g["turn_id"] for g in gates}:
            continue
        decisions = [
            entry
            for entry in current.get("input", [])
            if entry.get("type") == "user.tool_approval"
            and entry.get("thread_id") == "main"
            and entry.get("tool_call_id") == call["id"]
        ]
        if len(decisions) != 1 or decisions[0].get("approval") != {"status": "allow"}:
            raise PolicyError("Native approval denied or missing")
        # A native tool result means this call was already executed; it is not a new approval.
        if any(
            item["event"].get("type") == "tool.response"
            and item["event"].get("tool_call_id") == call["id"]
            for item in snapshot["events"]
        ):
            raise PolicyError("Native approval was already used")
        return {
            "session_id": session_id,
            "approval_turn_id": current["id"],
            "tool_call_id": call["id"],
            "source_event_id": source["id"],
            "actor": snapshot["session"]["created_by_subject"],
        }
    raise PolicyError("A matching per-call TrueForge approval is required")


def sandbox_result(snapshot, spec):
    sandbox_ids = [
        item["event"]["sandbox_id"]
        for item in snapshot["events"]
        if item["event"].get("type") == "sandbox.created"
    ]
    if len(set(sandbox_ids)) != 1 or not sandbox_ids[0].startswith("v1:e2b:"):
        raise PolicyError("One bound E2B sandbox creation event is required")
    # An earlier arbitrary shell command could replace the interpreter or tamper with stdlib.
    # This v1 permits only the self-contained validated calculation command in the session.
    for _, _, call, arguments in tool_calls(snapshot):
        if call.get("tool_info") == {"type": "truefoundry-system", "name": "exec"}:
            if arguments.get("command") != spec["command"] or set(arguments) - {
                "command",
                "intent",
            }:
                raise PolicyError("Session contains an unapproved sandbox command")
    for turn_id, _, call, arguments in tool_calls(snapshot):
        if call.get("tool_info") != {"type": "truefoundry-system", "name": "exec"}:
            continue
        if arguments.get("command") != spec["command"] or set(arguments) - {"command", "intent"}:
            continue
        responses = [
            item["event"]
            for item in snapshot["events"]
            if item["turn_id"] == turn_id
            and item["event"].get("type") == "tool.response"
            and item["event"].get("tool_call_id") == call["id"]
        ]
        if len(responses) != 1:
            continue
        try:
            # TrueForge 0.2.1 persists the text from the native tool response.
            output = json.loads(responses[0]["content"])
            if output.get("success") is not True or output["response"]["exitCode"] != 0:
                raise PolicyError("Sandbox calculation did not succeed")
            text = output["response"]["result"]
            if len(text.encode()) > 65536:
                raise PolicyError("Sandbox output exceeded 64 KiB")
            result = json.loads(text)
        except (ValueError, KeyError, TypeError) as exc:
            raise PolicyError("Invalid native sandbox result") from exc
        if (
            result.get("evidence_hash") != spec["evidence_hash"]
            or result.get("library_version") != spec["library_version"]
            or result.get("classification") != "duplicate_charge"
            or result.get("calculation_status") != "success"
            or result.get("warnings") != []
        ):
            raise PolicyError("Sandbox result is not bound to this evidence and library")
        return result, {
            "turn_id": turn_id,
            "tool_call_id": call["id"],
            "sandbox_id": sandbox_ids[0],
        }
    raise PolicyError("No verified execution of the exact constrained command")
