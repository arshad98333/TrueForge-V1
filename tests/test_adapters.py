import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.azure_foundry import AzureFoundryBridge
from app.cli import agent_manifest
from app.config import Settings
from app.integrations import EvidenceRepository, Linear, ProviderError
from app.main import create_app
from domain.charge_rules import COLLECTIONS, SCOPE, EvidenceError


def test_azure_foundry_project_endpoint_drives_trueforge_model():
    settings = Settings(
        azure_endpoint="https://demo.services.ai.azure.com/api/projects/project-one",
        azure_llm_model="gpt-6-astra",
    )
    assert settings.azure_openai_base_url == "https://demo.services.ai.azure.com/openai/v1"
    assert settings.resolved_model_name == "openai/gpt-6-astra"
    assert agent_manifest(settings)["model"]["name"] == "openai/gpt-6-astra"


def test_non_azure_endpoint_is_rejected():
    settings = Settings(azure_endpoint="https://example.com/api/projects/project-one")
    with pytest.raises(ValueError, match="Azure Foundry"):
        _ = settings.azure_openai_base_url


def test_azure_bridge_falls_back_to_openai_and_rewrites_model():
    requests = []

    def azure_handler(request):
        requests.append(("azure", json.loads(request.content)))
        return httpx.Response(404, json={"error": "deployment missing"})

    def openai_handler(request):
        requests.append(("openai", json.loads(request.content)))
        return httpx.Response(200, json={"output_text": "OK"})

    bridge = AzureFoundryBridge(
        "https://demo.openai.azure.com/openai/v1",
        "azure-deployment",
        openai_api_key="test-openai-key",
        openai_model="gpt-6-luna",
        primary_transport=httpx.MockTransport(azure_handler),
        fallback_transport=httpx.MockTransport(openai_handler),
    )
    bridge.access_token = lambda: "test-azure-token"

    async def call():
        response = await bridge.responses(
            json.dumps({"model": "azure-deployment", "input": "hello"}).encode()
        )
        await response.body_iterator.aclose()
        return response

    response = asyncio.run(call())
    assert response.status_code == 200
    assert response.headers["x-resolver-model-provider"] == "openai-fallback"
    assert requests[0][1]["model"] == "azure-deployment"
    assert requests[1][1]["model"] == "gpt-6-luna"


def test_trueforge_chat_completions_route_is_forwarded(monkeypatch, service):
    calls = []

    class FakeBridge:
        def __init__(self, endpoint, model, **kwargs):
            calls.append((endpoint, model))

        async def chat_completions(self, body):
            from starlette.responses import JSONResponse

            calls.append(body)
            return JSONResponse({"forwarded": True})

    monkeypatch.setattr(main_module, "AzureFoundryBridge", FakeBridge)
    settings = Settings(
        mcp_token="test-only",
        azure_endpoint="https://demo.services.ai.azure.com/api/projects/project-one",
        azure_llm_model="gpt-6-astra",
    )
    app = create_app(settings, service)
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        response = client.post(
            "/azure-openai/v1/chat/completions",
            headers={"Authorization": "Bearer test-only"},
            json={"model": "gpt-6-astra", "messages": []},
        )

    assert response.status_code == 200
    assert response.json() == {"forwarded": True}
    assert calls[0] == (
        "https://demo.services.ai.azure.com/openai/v1",
        "gpt-6-astra",
    )
    assert json.loads(calls[1]) == {"model": "gpt-6-astra", "messages": []}


def test_mcp_requires_auth_and_only_exposes_six_scoped_tools(service):
    app = create_app(Settings(mcp_token="test-only"), service)
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        assert client.get("/health").json()["customer_delivery"] is False
        assert client.post("/mcp", json={}).status_code == 401
        response = client.post(
            "/mcp",
            headers={
                "Authorization": "Bearer test-only",
                "Accept": "application/json, text/event-stream",
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
        assert response.status_code == 200
        tools = response.json()["result"]["tools"]
        assert {t["name"] for t in tools} == {
            "read_issue",
            "read_evidence",
            "prepare_execution",
            "prepare_review",
            "post_correction",
            "approve_reply_draft",
        }
        evidence = next(t for t in tools if t["name"] == "read_evidence")
        assert set(evidence["inputSchema"]["properties"]) == {"run_id"}


def test_linear_mutation_never_retries_timeout():
    attempts = []

    def handler(request):
        attempts.append(json.loads(request.content))
        raise httpx.ReadTimeout("lost response")

    client = Linear("fake", httpx.MockTransport(handler))
    with pytest.raises(ProviderError):
        client.post_comment("bound-issue", "exact approved text")
    assert len(attempts) == 1
    assert attempts[0]["variables"]["input"]["issueId"] == "bound-issue"


def test_linear_open_issues_is_team_scoped_and_bounded():
    def handler(request):
        payload = json.loads(request.content)
        assert payload["variables"] == {"teamId": "team-1"}
        assert "first:100" in payload["query"]
        return httpx.Response(
            200,
            json={
                "data": {
                    "issues": {
                        "nodes": [{"id": "issue-1"}],
                        "pageInfo": {"hasNextPage": False},
                    }
                }
            },
        )

    client = Linear("fake", httpx.MockTransport(handler))
    assert client.open_issues("team-1") == [{"id": "issue-1"}]


def test_mongo_all_queries_scoped_and_sentinel_blocks_overflow(bundle):
    seen = []

    class Cursor:
        def __init__(self, rows):
            self.rows = rows

        def limit(self, value):
            assert value == 101
            return self

        def max_time_ms(self, value):
            assert value == 5000
            return self

        def __iter__(self):
            return iter(self.rows)

    class Collection:
        def __init__(self, name):
            self.name = name

        def find(self, query, projection):
            seen.append((self.name, query, projection))
            return Cursor(bundle["collections"][self.name])

    repository = object.__new__(EvidenceRepository)
    repository.db = {name: Collection(name) for name in COLLECTIONS}
    result = repository.fetch()
    assert result["complete"] is True
    for name, query, projection in seen:
        assert projection["_id"] == 0
        if name == "tariff_rules":
            assert query["network_partner"] == SCOPE["network_partner"]
        else:
            assert query["customer_id"] == SCOPE["customer_id"]
    bundle["collections"]["roaming_charge_records"] *= 51
    with pytest.raises(EvidenceError, match="100 records"):
        repository.fetch()
