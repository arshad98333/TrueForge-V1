import json
import secrets
from pathlib import Path

from domain.charge_rules import SCOPE, canonical, digest

from .integrations import ProviderError

TERMINAL_FAILURES = {"blocked", "not_reproducible", "rejected"}


def list_demo_tickets(service, settings):
    settings.require("linear_token", "linear_team_id")
    marker = "ROAMING_RESOLVER_SCOPE=" + canonical(SCOPE)
    return [
        {
            "id": issue["id"],
            "identifier": issue["identifier"],
            "title": issue["title"],
            "state": issue["state"]["name"],
            "url": issue.get("url"),
            "labels": [item["name"] for item in issue.get("labels", {}).get("nodes", [])],
            "eligible": marker in (issue.get("description") or ""),
        }
        for issue in service.linear.open_issues(settings.linear_team_id)
    ]


def hackathon_edge_cases():
    seed = json.loads(
        (Path(__file__).resolve().parents[1] / "Instructions" / "seed_data.json").read_text(
            encoding="utf-8-sig"
        )
    )
    safe_stop = {
        "missing_roaming_pack",
        "tariff_mismatch",
        "missing_tariff",
        "conflicting_evidence",
        "mongodb_timeout",
        "sandbox_failure",
        "prompt_injection",
    }
    return [
        {
            "ticket_id": item["ticket_id"],
            "title": item["title"],
            "scenario": item["scenario"],
            "expected": "Safe stop" if item["scenario"] in safe_stop else "Bounded handling",
        }
        for item in seed["linear_issue_snapshots"]
    ]


def create_random_demo_case(service, settings):
    settings.require("linear_token", "linear_team_id", "mongo_uri")
    nonce = secrets.token_hex(3).upper()
    amount = f"{secrets.choice((750, 900, 1100, 1200, 1500, 1800))}.00"
    generated = service.evidence.upsert_synthetic_case(amount, nonce)
    description = (
        f"Synthetic generated telecom fixture {generated['fixture']}. No real customer data.\n\n"
        f"Customer {SCOPE['customer_id']} disputes INR {generated['billed_amount']} for "
        f"{SCOPE['country']} roaming. Unit charge is hidden from the agent prompt.\n"
        f"Generation nonce: {nonce}. Investigate from tool evidence only.\n\n"
        "ROAMING_RESOLVER_SCOPE="
        + canonical(SCOPE)
    )
    issue = service.linear.create_issue(
        settings.linear_team_id,
        f"[Generated {generated['fixture']}] Unexpected Singapore roaming charge",
        description,
    )
    return {"issue": issue, "generated": generated}


def start_demo_workflow(service, settings, issue_id=None):
    settings.require("linear_team_id", "linear_token", "mongo_uri")
    issue_id = issue_id or settings.issue_id
    if not issue_id:
        raise ValueError("Select a Linear ticket before starting the workflow")
    run = service.store.create_run(issue_id, settings.linear_team_id)
    if run["status"] in TERMINAL_FAILURES | {"complete"}:
        return {
            "started": False,
            "run_id": run["id"],
            "session_id": run.get("session_id"),
            "message": f"Run is already {run['status'].replace('_', ' ')}.",
        }
    if run["status"] in {"awaiting_correction", "awaiting_reply_draft"}:
        return {
            "started": False,
            "run_id": run["id"],
            "session_id": run.get("session_id"),
            "message": "Human review is required in TrueForge.",
        }

    def create_session():
        session = service.trueforge.request(
            "POST",
            "/api/v1/sessions",
            json={
                "agent": {"name": settings.agent_name},
                "metadata": {"resolver_run_id": run["id"]},
            },
        )["data"]
        service.store.update_run(run["id"], session_id=session["id"])
        return session["id"]

    session_id = run.get("session_id")
    if not session_id:
        session_id = create_session()
    else:
        try:
            snapshot = service.trueforge.snapshot(session_id)
        except ProviderError as exc:
            if getattr(exc, "status_code", None) != 404:
                raise
            session_id = create_session()
            snapshot = None
        if (
            snapshot
            and snapshot["turns"]
            and snapshot["turns"][0]["state"]["status"] == "running"
        ):
            return {
                "started": False,
                "run_id": run["id"],
                "session_id": session_id,
                "message": "The TrueForge agent is already running.",
            }

    service.trueforge.request(
        "POST",
        f"/api/v1/sessions/{session_id}/turns",
        json={
            "stream": False,
            "input": [
                {
                    "type": "user.message",
                    "content": (
                        "Investigate the selected synthetic Linear issue using "
                        f"run_id={run['id']}. "
                        "Continue the saved workflow from its verified state."
                    ),
                }
            ],
        },
    )
    return {
        "started": True,
        "run_id": run["id"],
        "session_id": session_id,
        "message": "TrueForge workflow started.",
    }


def _sandbox_trace(service, run):
    trace = {
        "available": False,
        "sandbox_id": None,
        "exec_calls": 0,
        "tool_calls": 0,
        "turns": 0,
        "status": "Not started",
    }
    if not run.get("session_id"):
        return trace
    try:
        snapshot = service.trueforge.snapshot(run["session_id"])
    except Exception:
        return trace | {"status": "Trace unavailable"}
    trace["available"] = True
    trace["turns"] = len(snapshot["turns"])
    sandbox_ids = []
    latest_status = "Unknown"
    if snapshot["turns"]:
        latest_status = snapshot["turns"][0].get("state", {}).get("status", "Unknown")
    for item in snapshot["events"]:
        event = item.get("event", {})
        if event.get("type") == "sandbox.created":
            sandbox_ids.append(event.get("sandbox_id"))
        if event.get("type") != "model.message":
            continue
        for call in event.get("tool_calls", []):
            trace["tool_calls"] += 1
            if call.get("tool_info") == {"type": "truefoundry-system", "name": "exec"}:
                trace["exec_calls"] += 1
    trace["sandbox_id"] = next((value for value in reversed(sandbox_ids) if value), None)
    trace["status"] = latest_status.replace("_", " ").title()
    return trace


def _calculation(actions):
    correction = next(
        (action for action in reversed(actions) if action["kind"] == "correction"), None
    )
    return correction.get("payload", {}).get("calculation") if correction else None


def _stage_state(complete, current, stopped):
    if complete:
        return "complete"
    if stopped:
        return "stopped"
    if current:
        return "current"
    return "waiting"


def build_demo_state(service, run_id=None):
    run = service.store.run(run_id) if run_id else service.store.latest_run()
    if not run:
        return {
            "available": False,
            "status": "Not started",
            "stages": [],
            "message": "Start one resolver run to populate the operator console.",
        }

    actions = service.store.actions_for_run(run["id"])
    audit = service.store.audit_for_run(run["id"])
    trace = _sandbox_trace(service, run)
    evidence = run.get("evidence") or {}
    collections = evidence.get("collections", {})
    calculation = _calculation(actions)
    correction = next((item for item in actions if item["kind"] == "correction"), None)
    reply = next((item for item in actions if item["kind"] == "reply_draft"), None)
    stopped = run["status"] in TERMINAL_FAILURES
    issue_ready = bool(run.get("issue_snapshot"))
    evidence_ready = bool(evidence)
    execution_ready = bool(trace["sandbox_id"] and trace["exec_calls"])
    decision_ready = bool(calculation)
    correction_done = bool(correction and correction["status"] == "succeeded")
    reply_done = bool(reply and reply["status"] == "succeeded")

    stages = [
        {
            "number": "01",
            "name": "Ticket bound",
            "system": "Linear",
            "state": _stage_state(issue_ready, not issue_ready, stopped),
            "detail": "Issue and team identity verified" if issue_ready else "Waiting for issue",
        },
        {
            "number": "02",
            "name": "Evidence scoped",
            "system": "MongoDB Atlas",
            "state": _stage_state(
                evidence_ready, issue_ready and not evidence_ready, stopped and issue_ready
            ),
            "detail": (
                f"{sum(len(rows) for rows in collections.values())} records across "
                f"{len(collections)} collections"
                if evidence_ready
                else "Waiting for complete evidence"
            ),
        },
        {
            "number": "03",
            "name": "Code executed",
            "system": "TrueForge and E2B",
            "state": _stage_state(
                execution_ready, evidence_ready and not execution_ready, stopped and evidence_ready
            ),
            "detail": (
                f"One verified native exec in {trace['sandbox_id']}"
                if execution_ready
                else "Waiting for a verified sandbox trace"
            ),
        },
        {
            "number": "04",
            "name": "Decision proven",
            "system": "Deterministic rules",
            "state": _stage_state(
                decision_ready, execution_ready and not decision_ready, stopped and execution_ready
            ),
            "detail": (
                "Duplicate charge reconstructed from stable billing IDs"
                if decision_ready
                else "No supported decision yet"
            ),
        },
        {
            "number": "05",
            "name": "Correction controlled",
            "system": "Human approval",
            "state": _stage_state(
                correction_done,
                bool(correction and correction["status"] == "pending"),
                bool(correction and correction["status"] in {"rejected", "revoked", "uncertain"}),
            ),
            "detail": (
                "Exact Linear recommendation verified"
                if correction_done
                else "Approval required before external write"
            ),
        },
        {
            "number": "06",
            "name": "Reply held",
            "system": "Draft only",
            "state": _stage_state(
                reply_done,
                correction_done and not reply_done,
                bool(reply and reply["status"] in {"rejected", "revoked", "uncertain"}),
            ),
            "detail": (
                "Approved locally and not sent"
                if reply_done
                else "No customer delivery tool is exposed"
            ),
        },
    ]

    issue = run.get("issue_snapshot") or {}
    issue_label = issue.get("identifier")
    if not issue_label and "TEL-1042" in issue.get("title", ""):
        issue_label = "TEL-1042"
    return {
        "available": True,
        "run_id": run["id"],
        "session_id": run.get("session_id"),
        "status": run["status"].replace("_", " ").title(),
        "issue": {
            "uuid": run["issue_id"],
            "id": issue_label or run["issue_id"],
            "title": issue.get("title", "Unexpected roaming charge in Singapore"),
            "state": (issue.get("state") or {}).get("name", "Unknown"),
        },
        "evidence": {
            "hash": digest(evidence) if evidence else None,
            "collections": {name: len(rows) for name, rows in collections.items()},
        },
        "calculation": calculation,
        "trace": trace,
        "stages": stages,
        "actions": [
            {"kind": item["kind"], "status": item["status"], "expires_at": item["expires_at"]}
            for item in actions
        ],
        "audit": [
            {"time": item["created_at"], "event": item["event"]} for item in audit[-8:]
        ],
        "proof": {
            "real_systems": issue_ready and evidence_ready,
            "executed_code": execution_ready,
            "safe_stop": run["status"] in TERMINAL_FAILURES
            or run["status"]
            in {"awaiting_correction", "awaiting_reply_draft", "complete"},
            "customer_message_sent": False,
        },
    }
