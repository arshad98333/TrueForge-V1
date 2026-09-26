import hmac
import secrets
from contextlib import asynccontextmanager
from functools import partial

import anyio
from fastapi import FastAPI, Request
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

from domain.charge_rules import EvidenceError

from .azure_foundry import AzureFoundryBridge
from .config import ROOT, Settings
from .demo import (
    build_demo_state,
    create_random_demo_case,
    hackathon_edge_cases,
    list_demo_tickets,
    start_demo_workflow,
)
from .integrations import EvidenceRepository, Linear, ProviderError
from .service import Resolver
from .store import PolicyError, Store
from .trueforge import TrueForge


def build_service(settings):
    return Resolver(
        Store(settings.state_path),
        Linear(settings.linear_token),
        EvidenceRepository(settings.mongo_uri),
        TrueForge(settings.trueforge_url, settings.trueforge_token),
    )


def create_app(settings=None, service=None):
    settings = settings or Settings.load()
    settings.require("mcp_token")
    if service is None:
        settings.require("mongo_uri")
        service = build_service(settings)
    mcp = FastMCP(
        "roaming-resolver",
        stateless_http=True,
        json_response=True,
        max_request_body_size=65536,
        log_level="WARNING",
    )
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True)

    async def invoke(name, **kwargs):
        try:
            return await anyio.to_thread.run_sync(partial(getattr(service, name), **kwargs))
        except ProviderError as exc:
            return {"status": "blocked", "message": str(exc), "changed": None, "retryable": False}
        except (PolicyError, EvidenceError) as exc:
            return {"status": "blocked", "message": str(exc), "changed": False}
        except Exception:
            return {
                "status": "blocked",
                "message": "Internal resolver error; inspect local tests.",
                "changed": None,
            }

    @mcp.tool(annotations=read)
    async def read_issue(run_id: str) -> dict:
        """Read the one bound synthetic Linear issue. No writes. Two 10s attempts maximum."""
        return await invoke("read_issue", run_id=run_id)

    @mcp.tool(annotations=read)
    async def read_evidence(run_id: str) -> dict:
        """Read scoped Atlas evidence with IDs/completeness; max 100 per collection, 5s reads.

        No billing writes. Overflow, unknown run or missing scope blocks calculation.
        """
        return await invoke("read_evidence", run_id=run_id)

    @mcp.tool(annotations=read)
    async def prepare_execution(run_id: str, runner_source: str) -> dict:
        """Validate a constrained runner and return an exact TrueForge sandbox exec command.

        Local preparation only; does NOT execute code. Command has a 20s/64KiB calculation limit.
        """
        return await invoke("prepare_execution", run_id=run_id, runner_source=runner_source)

    @mcp.tool(annotations=read)
    async def prepare_review(run_id: str, execution_id: str, reply_draft: str) -> dict:
        """Verify native sandbox trace; freeze a 15-minute correction and reply preview.

        No external mutation. reply_draft max 4000 chars. Missing execution evidence blocks review.
        """
        return await invoke(
            "prepare_review", run_id=run_id, execution_id=execution_id, reply_draft=reply_draft
        )

    @mcp.tool(annotations=write)
    async def post_correction(
        approval_id: str,
        action_version: int,
        expires_at: str,
        plan_hash: str,
        idempotency_key: str,
        issue_id: str,
        text: str,
    ) -> dict:
        """APPROVAL REQUIRED: post exactly the displayed text to the bound Linear demo issue.

        Recommendation only, no refund/status change. Verifies native per-call approval and
        fresh evidence; one write attempt, 10s timeout. Uncertain delivery requires reconciliation.
        """
        return await invoke(
            "post_correction",
            approval_id=approval_id,
            action_version=action_version,
            expires_at=expires_at,
            plan_hash=plan_hash,
            idempotency_key=idempotency_key,
            issue_id=issue_id,
            text=text,
        )

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False)
    )
    async def approve_reply_draft(
        approval_id: str,
        action_version: int,
        expires_at: str,
        plan_hash: str,
        idempotency_key: str,
        issue_id: str,
        text: str,
    ) -> dict:
        """SEPARATE APPROVAL REQUIRED: mark this exact reply draft approved locally.

        No message is sent or posted. Requires verified correction and a new native approval.
        Returns approved draft text and sent=false. Provider verification reads are bounded.
        """
        return await invoke(
            "approve_reply_draft",
            approval_id=approval_id,
            action_version=action_version,
            expires_at=expires_at,
            plan_hash=plan_hash,
            idempotency_key=idempotency_key,
            issue_id=issue_id,
            text=text,
        )

    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app):
        async with mcp.session_manager.run():
            yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    demo_token = secrets.token_urlsafe(24)
    azure = (
        AzureFoundryBridge(
            settings.azure_openai_base_url,
            settings.azure_llm_model,
            openai_api_key=(settings.openai_api_key if settings.openai_fallback_ready else ""),
            openai_model=settings.resolved_fallback_model,
        )
        if settings.azure_endpoint and settings.azure_llm_model
        else None
    )

    @app.middleware("http")
    async def authenticate(request, call_next):
        public_demo = request.url.path == "/demo" or request.url.path.startswith(
            "/demo-assets/"
        )
        if request.url.path != "/health" and not public_demo:
            supplied = request.headers.get("authorization", "")
            if not hmac.compare_digest(supplied, "Bearer " + settings.mcp_token):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "mode": "synthetic-local-only",
            "customer_delivery": False,
            "model_primary": "azure" if azure else "openai",
            "openai_fallback": bool(azure and settings.openai_fallback_ready),
        }

    @app.get("/demo", include_in_schema=False)
    def demo():
        return FileResponse(ROOT / "app" / "static" / "index.html")

    @app.get("/demo-assets/state", include_in_schema=False)
    def demo_state(run_id: str | None = None):
        state = build_demo_state(service, run_id)
        state["demo_token"] = demo_token
        state["provider"] = {
            "primary": "Azure OpenAI" if azure else "OpenAI",
            "fallback": "OpenAI" if azure and settings.openai_fallback_ready else None,
        }
        return JSONResponse(
            state, headers={"Cache-Control": "no-store"}
        )

    @app.post("/demo-assets/start", include_in_schema=False)
    async def start_demo(request: Request):
        supplied = request.headers.get("x-demo-token", "")
        if not hmac.compare_digest(supplied, demo_token):
            return JSONResponse({"error": "Invalid demo token"}, status_code=403)
        try:
            try:
                payload = await request.json()
            except ValueError:
                payload = {}
            return start_demo_workflow(service, settings, payload.get("issue_id"))
        except (ValueError, ProviderError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=409)
        except Exception:
            return JSONResponse(
                {"error": "Workflow could not start. Check local runtime status."},
                status_code=500,
            )

    @app.get("/demo-assets/tickets", include_in_schema=False)
    def tickets():
        try:
            return {
                "tickets": list_demo_tickets(service, settings),
                "edge_cases": hackathon_edge_cases(),
            }
        except (ValueError, ProviderError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=409)

    @app.post("/demo-assets/tickets/random", include_in_schema=False)
    def random_ticket(request: Request):
        supplied = request.headers.get("x-demo-token", "")
        if not hmac.compare_digest(supplied, demo_token):
            return JSONResponse({"error": "Invalid demo token"}, status_code=403)
        try:
            return create_random_demo_case(service, settings)
        except (ValueError, ProviderError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=409)
        except Exception:
            return JSONResponse(
                {"error": "Synthetic case creation failed; no workflow was started."},
                status_code=500,
            )

    @app.post("/azure-openai/v1/responses")
    async def azure_responses(request: Request):
        """Local-only token-refresh bridge used by TrueForge's custom provider."""
        if azure is None:
            return JSONResponse({"error": "Azure Foundry is not configured"}, status_code=503)
        try:
            return await azure.responses(await request.body())
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=413)
        except Exception:
            return JSONResponse(
                {"error": "Azure Foundry request failed; credentials or connectivity unavailable"},
                status_code=502,
            )

    @app.post("/azure-openai/v1/chat/completions")
    async def azure_chat_completions(request: Request):
        """Compatibility route used by TrueForge's OpenAI chat provider."""
        if azure is None:
            return JSONResponse({"error": "Azure Foundry is not configured"}, status_code=503)
        try:
            return await azure.chat_completions(await request.body())
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=413)
        except Exception:
            return JSONResponse(
                {"error": "Azure Foundry request failed; credentials or connectivity unavailable"},
                status_code=502,
            )

    app.mount(
        "/demo-assets",
        StaticFiles(directory=ROOT / "app" / "static"),
        name="demo-assets",
    )
    app.mount("/", mcp_app)
    return app
