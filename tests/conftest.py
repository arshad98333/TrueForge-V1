import copy
import json
from datetime import UTC, datetime, timedelta

import pytest

from app.cli import primary_seed
from app.integrations import ProviderError
from app.sandbox import RUNNER, execution_spec
from app.service import Resolver
from app.store import Store
from domain.charge_rules import SCOPE, canonical, reconstruct


@pytest.fixture
def bundle():
    return {"scope": copy.deepcopy(SCOPE), "complete": True, "collections": primary_seed()}


def event_item(turn_id, event_type, **fields):
    return {
        "turn_id": turn_id,
        "event": {
            "type": event_type,
            "id": fields.pop("id", "event-" + event_type),
            "thread_id": "main",
            "created_at": "2026-09-26T00:00:00Z",
            **fields,
        },
    }


def calculation_trace(bundle, session_id="session-1"):
    spec = execution_spec(bundle, RUNNER)
    return {
        "session": {
            "id": session_id,
            "created_by_subject": {
                "subject_id": "local-operator",
                "subject_type": "user",
                "subject_display_name": "Local operator",
            },
        },
        "turns": [
            {
                "id": "calculation-turn",
                "created_at": "2026-09-26T00:00:00Z",
                "state": {"status": "running"},
                "input": [],
            }
        ],
        "events": [
            event_item("calculation-turn", "sandbox.created", sandbox_id="v1:e2b:demo"),
            event_item(
                "calculation-turn",
                "model.message",
                tool_calls=[
                    {
                        "id": "exec-1",
                        "tool_info": {"type": "truefoundry-system", "name": "exec"},
                        "function": {
                            "name": "sandbox__exec",
                            "arguments": json.dumps(
                                {
                                    "command": spec["command"],
                                    "intent": "Reconstruct the duplicate charge",
                                }
                            ),
                        },
                    }
                ],
            ),
            event_item(
                "calculation-turn",
                "tool.response",
                tool_call_id="exec-1",
                content=json.dumps(
                    {
                        "success": True,
                        "response": {"exitCode": 0, "result": json.dumps(reconstruct(bundle))},
                    }
                ),
            ),
        ],
    }


def add_approval(trace, tool, arguments, *, allow=True):
    previous = "gate-" + tool
    call_id = "call-" + tool
    source_id = "source-" + tool
    created = datetime.now(UTC)
    trace["turns"] = [
        {
            "id": previous,
            "created_at": (created - timedelta(seconds=1)).isoformat(),
            "state": {"status": "done"},
            "input": [],
        },
        {
            "id": "approval-" + tool,
            "created_at": created.isoformat(),
            "previous_turn_id": previous,
            "state": {"status": "running"},
            "input": [
                {
                    "type": "user.tool_approval",
                    "thread_id": "main",
                    "tool_call_id": call_id,
                    "approval": {"status": "allow" if allow else "deny"},
                }
            ],
        },
    ]
    trace["events"].extend(
        [
            event_item(
                previous,
                "model.message",
                id=source_id,
                tool_calls=[
                    {
                        "id": call_id,
                        "tool_info": {
                            "type": "mcp",
                            "name": tool,
                            "server_id": "server-1",
                            "server_name": "roaming-resolver",
                        },
                        "function": {
                            "name": "roaming-resolver__" + tool,
                            "arguments": json.dumps(arguments),
                        },
                    }
                ],
            ),
            event_item(
                previous,
                "tool.approval_required",
                tool_calls=[{"id": call_id, "source_event_id": source_id}],
            ),
        ]
    )


class FakeEvidence:
    def __init__(self, bundle):
        self.bundle = copy.deepcopy(bundle)
        self.calls = 0

    def fetch(self):
        self.calls += 1
        return copy.deepcopy(self.bundle)


class FakeLinear:
    def __init__(self):
        self.issue_data = {
            "id": "issue-1",
            "team": {"id": "team-1"},
            "identifier": "DEMO-7",
            "title": "Synthetic roaming issue",
            "state": {"id": "state-1", "name": "Open"},
            "updatedAt": "version1",
            "description": "ROAMING_RESOLVER_SCOPE=" + canonical(SCOPE),
            "url": "https://linear.app/demo/issue/DEMO-7",
        }
        self.posted = []
        self.fail_after_post = False

    def issue(self, issue_id):
        assert issue_id == "issue-1"
        return copy.deepcopy(self.issue_data)

    def post_comment(self, issue_id, text):
        assert issue_id == "issue-1"
        result = {
            "id": "comment-1",
            "body": text,
            "issue": {"id": issue_id},
            "url": "https://linear.app/demo/comment/comment-1",
        }
        self.posted.append(result)
        if self.fail_after_post:
            raise ProviderError("Simulated lost response")
        return result

    def comment(self, comment_id):
        return next(c for c in self.posted if c["id"] == comment_id)

    def comments(self, issue_id):
        assert issue_id == "issue-1"
        return copy.deepcopy(self.posted)


class FakeTrueForge:
    def __init__(self, bundle):
        self.trace = calculation_trace(bundle)

    def snapshot(self, session_id):
        assert session_id == self.trace["session"]["id"]
        return copy.deepcopy(self.trace)


@pytest.fixture
def service(tmp_path, bundle):
    store = Store(tmp_path / "state.sqlite")
    run = store.create_run("issue-1", "team-1")
    store.update_run(run["id"], session_id="session-1")
    resolver = Resolver(store, FakeLinear(), FakeEvidence(bundle), FakeTrueForge(bundle))
    resolver.read_issue(run["id"])
    resolver.read_evidence(run["id"])
    execution = resolver.prepare_execution(run["id"], RUNNER)
    review = resolver.prepare_review(
        run["id"],
        execution["execution_id"],
        "A duplicate charge was found. A correction is recommended.",
    )
    resolver.test_run_id = run["id"]
    resolver.test_review = review
    return resolver
