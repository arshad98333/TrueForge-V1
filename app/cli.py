"""Operator entry points. Setup mutations are never exposed as agent tools."""

import argparse
import json
import os
import secrets
import sys

import uvicorn
from dotenv import dotenv_values, set_key
from pymongo import MongoClient, UpdateOne

from domain.charge_rules import COLLECTIONS, FIELDS, SCOPE, canonical

from .config import ROOT, Settings
from .integrations import Linear, ProviderError, issue_binding
from .main import build_service
from .store import PolicyError, Store
from .trueforge import TrueForge

TOOLS = [
    "read_issue",
    "read_evidence",
    "prepare_execution",
    "prepare_review",
    "post_correction",
    "approve_reply_draft",
]
PROTECTED = ["post_correction", "approve_reply_draft"]


def init_env():
    path = ROOT / ".env"
    values = dotenv_values(path)
    defaults = {
        "MCP_AUTH_TOKEN": secrets.token_urlsafe(32),
        "LINEAR_API_TOKEN": "",
        "LINEAR_TEAM_ID": "",
        "DEMO_LINEAR_ISSUE_ID": "",
        "E2B_API_KEY": "",
        "E2B_TEMPLATE": "base",
        "MONGODB_SEED_URI": "",
        "TRUEFORGE_BASE_URL": "http://127.0.0.1:8790",
        "TRUEFORGE_MODEL_NAME": "openai/gpt-5-4-mini",
        "OPENAI_API_KEY": "",
        "OPENAI_FALLBACK_ENABLED": "true",
        "OPENAI_FALLBACK_MODEL": "gpt-6-luna",
    }
    for name, value in defaults.items():
        if name not in values or (name == "MCP_AUTH_TOKEN" and not values[name]):
            set_key(path, name, value)
    print("Environment placeholders added; credentials preserved. MCP secret generated locally.")


def primary_seed():
    seed = json.loads((ROOT / "Instructions" / "seed_data.json").read_text(encoding="utf-8-sig"))
    result = {}
    for name in COLLECTIONS:
        rows = seed[name]
        if name == "tariff_rules":
            rows = [row for row in rows if row["country"] == SCOPE["country"]]
        else:
            rows = [row for row in rows if row["customer_id"] == SCOPE["customer_id"]]
        result[name] = [{key: row[key] for key in FIELDS[name]} for row in rows]
    return result


def seed_database(settings):
    settings.require("mongo_seed_uri")
    client = MongoClient(
        settings.mongo_seed_uri,
        serverSelectionTimeoutMS=5000,
        socketTimeoutMS=5000,
        retryWrites=False,
    )
    db = client["roaming_resolver_demo"]
    identifiers = {
        "customer_plans": ("customer_id", "plan_id", "effective_from"),
        "roaming_packs": ("pack_id",),
        "tariff_rules": ("tariff_id",),
        "roaming_usage_events": ("event_id",),
        "roaming_charge_records": ("charge_id",),
    }
    with client:
        for name, rows in primary_seed().items():
            fields = identifiers[name]
            db[name].create_index([(key, 1) for key in fields], unique=True)
            operations = [
                UpdateOne({key: row[key] for key in fields}, {"$set": row}, upsert=True)
                for row in rows
            ]
            db[name].bulk_write(operations)
        db.roaming_usage_events.create_index([("customer_id", 1), ("occurred_at", 1)])
        db.roaming_charge_records.create_index([("customer_id", 1), ("charged_at", 1)])
        db.roaming_charge_records.create_index([("customer_id", 1), ("event_id", 1)])
        db.roaming_packs.create_index([("customer_id", 1), ("country", 1), ("activated_at", 1)])
        db.tariff_rules.create_index(
            [("country", 1), ("network_partner", 1), ("plan_id", 1), ("effective_from", 1)]
        )
    print("Upserted 6 primary-case records across 5 collections; no data deleted.")


def setup_issue(settings):
    settings.require("linear_token", "linear_team_id")
    linear = Linear(settings.linear_token)
    mapping = ROOT / ".state" / "issue-setup.json"
    if settings.issue_id:
        issue = linear.issue(settings.issue_id)
        issue_binding(issue, {"issue_id": settings.issue_id, "team_id": settings.linear_team_id})
        print("Existing demo issue verified:", issue["identifier"])
        return
    team = linear.verify_team(settings.linear_team_id)
    if team["id"] != settings.linear_team_id:
        settings.linear_team_id = team["id"]
        set_key(ROOT / ".env", "LINEAR_TEAM_ID", team["id"])
        print("Resolved the only accessible Linear team:", team["name"], team["key"])
    mapping.parent.mkdir(exist_ok=True)
    if mapping.exists():
        saved = json.loads(mapping.read_text())
        if saved.get("issue_id"):
            set_key(ROOT / ".env", "DEMO_LINEAR_ISSUE_ID", saved["issue_id"])
            print("Restored the existing issue mapping. Run setup-issue again to verify.")
            return
        raise PolicyError("An earlier issue creation is uncertain; inspect Linear before retrying")
    # Persist intent before the non-idempotent provider mutation.
    mapping.write_text(canonical({"status": "creating"}))
    description = (
        "Synthetic telecom hackathon fixture TEL-1042. No real customer data.\n\n"
        "Customer CUST-7781 disputes INR 2400.00 for Singapore roaming, "
        "10–14 September 2026. Investigate using evidence; do not assume an anomaly.\n\n"
        "ROAMING_RESOLVER_SCOPE=" + canonical(SCOPE)
    )
    issue = linear.create_issue(
        settings.linear_team_id, "[Demo TEL-1042] Unexpected Singapore roaming charge", description
    )
    mapping.write_text(canonical({"status": "created", "issue_id": issue["id"]}))
    set_key(ROOT / ".env", "DEMO_LINEAR_ISSUE_ID", issue["id"])
    print("Created synthetic issue and saved UUID mapping:", issue["identifier"])


def agent_manifest(settings):
    return {
        "model": {
            "name": settings.resolved_model_name,
            "params": {"max_tokens": 12000, "parallel_tool_calls": False},
        },
        "instructions": (ROOT / "agent" / "instructions.md").read_text(encoding="utf-8"),
        "mcp_servers": [
            {
                "name": "roaming-resolver",
                "enable_tools": TOOLS,
                "require_approval_for_tools": PROTECTED,
                "preload": True,
            }
        ],
        "config": {
            "iteration_limit": 15,
            "sandbox": {"enabled": True},
            "dynamic_sub_agents": {"enabled": False},
            "web_search": {"enabled": False},
        },
    }


def configure(settings):
    settings.require("mcp_token")
    tf = TrueForge(settings.trueforge_url, settings.trueforge_token)
    tf.client.timeout = 60
    schema = tf.request("GET", "/api/v1/openapi.json")
    if "UserToolApprovalEvent" not in schema["components"]["schemas"]:
        raise PolicyError("Installed runtime lacks the required approval contract")
    configured = tf.request("GET", "/api/v1/settings/model-providers")["data"]
    azure_values = (settings.azure_endpoint, settings.azure_llm_model)
    if any(azure_values) and not all(azure_values):
        raise PolicyError(
            "AZURE_ENDPOINT and AZURE_LLM_MODEL must be set together"
        )
    if all(azure_values):
        tf.request(
            "PUT",
            "/api/v1/settings/model-providers",
            json={
                "manifest": {
                    "type": "openai",
                    "base_url": "http://127.0.0.1:8000/azure-openai/v1",
                    "auth": {"api_key": settings.mcp_token},
                    "models": [
                        {
                            "model_id": settings.azure_llm_model,
                            "name": settings.azure_llm_model,
                            "properties": {},
                        }
                    ],
                }
            },
        )
        print(
            "Azure Foundry provider configured for model",
            settings.azure_llm_model,
            "through the local DefaultAzureCredential bridge.",
        )
        if settings.openai_fallback_ready:
            print(
                "Optional OpenAI fallback enabled for",
                settings.resolved_fallback_model,
                "when Azure is unavailable.",
            )
    elif not any(p["manifest"]["type"] == "openai" for p in configured):
        catalog = tf.request("GET", "/api/v1/catalogs/model-providers")["data"]
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise PolicyError("OPENAI_API_KEY is required")
        provider = next(p for p in catalog if p["type"] == "openai")
        model = next(m for m in provider["models"] if m["name"] == "gpt-5-4-mini")
        tf.request(
            "POST",
            "/api/v1/settings/model-providers",
            json={"manifest": {"type": "openai", "auth": {"api_key": key}, "models": [model]}},
        )
        print("OpenAI provider configured using the shipped model catalog.")
    connector = {
        "type": "remote",
        "name": "roaming-resolver",
        "url": "http://127.0.0.1:8000/mcp",
        "description": "Scoped synthetic roaming resolver",
        "auth": {"type": "header", "headers": {"Authorization": "Bearer " + settings.mcp_token}},
    }
    # The pinned contract uses PUT on the collection for create-or-update, keyed by manifest.name.
    tf.request("PUT", "/api/v1/settings/mcp-servers", json={"manifest": connector})
    e2b_key = os.getenv("E2B_API_KEY") or os.getenv("E2B_SANDBOX")
    if e2b_key:
        tf.request(
            "PUT",
            "/api/v1/settings/sandbox-providers",
            json={
                "manifest": {
                    "type": "e2b",
                    "auth": {"api_key": e2b_key},
                    "template": os.getenv("E2B_TEMPLATE") or "base",
                    "exec_timeout_ms": 20000,
                    "lifetime_ms": 1800000,
                }
            },
        )
        print("E2B template configured; live native execution still requires verification.")
    else:
        raise PolicyError("E2B_API_KEY (or E2B_SANDBOX) is required")
    agents = tf.request("GET", "/api/v1/agents")["data"]
    existing = next((a for a in agents if a["name"] == settings.agent_name), None)
    body = {
        "description": "One synthetic duplicate-charge investigation with explicit approvals.",
        "manifest": agent_manifest(settings),
    }
    if existing:
        tf.request("PUT", "/api/v1/agents/" + existing["id"], json=body)
    else:
        tf.request("POST", "/api/v1/agents", json={"name": settings.agent_name, **body})
    print("Saved agent and per-call approval gates configured.")


def check(settings, live=False):
    checks = {
        name: bool(getattr(settings, name))
        for name in ("mongo_uri", "linear_token", "linear_team_id", "issue_id", "mcp_token")
    }
    checks["e2b_key"] = bool(os.getenv("E2B_API_KEY") or os.getenv("E2B_SANDBOX"))
    azure_values = (settings.azure_endpoint, settings.azure_llm_model)
    checks["azure_foundry_config"] = all(azure_values) if any(azure_values) else True
    checks["openai_fallback_config"] = (
        bool(settings.resolved_fallback_model) if settings.openai_fallback_ready else True
    )
    tf = TrueForge(settings.trueforge_url, settings.trueforge_token)
    try:
        schema = tf.request("GET", "/api/v1/openapi.json")
        checks["native_approval_contract"] = (
            "UserToolApprovalEvent" in schema["components"]["schemas"]
        )
        provider = tf.request("GET", "/api/v1/settings/sandbox-providers")["data"]
        checks["sandbox_ready"] = bool(
            provider and provider.get("status") == "ready" and provider["manifest"]["type"] == "e2b"
        )
    except ProviderError:
        checks["runtime_available"] = False
    if live and checks["mongo_uri"]:
        from domain.charge_rules import validate_evidence

        from .integrations import EvidenceRepository

        try:
            validate_evidence(EvidenceRepository(settings.mongo_uri).fetch())
            checks["live_evidence"] = True
        except Exception:
            checks["live_evidence"] = False
    if live and checks["azure_foundry_config"] and all(azure_values):
        from .azure_foundry import AzureFoundryBridge

        try:
            bridge = AzureFoundryBridge(
                settings.azure_openai_base_url, settings.azure_llm_model
            )
            checks["azure_identity"] = bool(bridge.access_token())
        except Exception:
            checks["azure_identity"] = False
    if live and all(checks[k] for k in ("linear_token", "linear_team_id", "issue_id")):
        try:
            issue_binding(
                Linear(settings.linear_token).issue(settings.issue_id),
                {"issue_id": settings.issue_id, "team_id": settings.linear_team_id},
            )
            checks["live_issue"] = True
        except Exception:
            checks["live_issue"] = False
    print(json.dumps(checks, indent=2))
    return all(checks.values())


def start(settings):
    settings.require("issue_id", "linear_team_id", "linear_token", "mongo_uri")
    if not check(settings, live=True):
        raise PolicyError(
            "Complete the failed preflight checks before starting a live investigation"
        )
    store = Store(settings.state_path)
    run = store.create_run(settings.issue_id, settings.linear_team_id)
    tf = TrueForge(settings.trueforge_url, settings.trueforge_token)
    if run["session_id"]:
        print("Resume existing session in TrueForge:", run["session_id"])
        print("Run:", run["id"])
        return
    session = tf.request(
        "POST",
        "/api/v1/sessions",
        json={
            "agent": {"name": settings.agent_name},
            "metadata": {"resolver_run_id": run["id"]},
        },
    )["data"]
    store.update_run(run["id"], session_id=session["id"])
    print("Open TrueForge at", settings.trueforge_url, flush=True)
    print("Session:", session["id"], "Run:", run["id"], flush=True)
    tf.client.timeout = 180
    # The UI owns subsequent turns and approvals. Repeated start never resends this turn.
    tf.request(
        "POST",
        f"/api/v1/sessions/{session['id']}/turns",
        json={
            "stream": False,
            "input": [
                {
                    "type": "user.message",
                    "content": f"Investigate synthetic TEL-1042 using run_id={run['id']}. "
                    "Follow the saved workflow.",
                }
            ],
        },
    )
    print("Open TrueForge at", settings.trueforge_url)
    print("Session:", session["id"], "Run:", run["id"])


def main():
    parser = argparse.ArgumentParser(description="Synthetic roaming demo operator commands")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "seed", "setup-issue", "configure-runtime", "serve", "start"):
        commands.add_parser(name)
    check_parser = commands.add_parser("check")
    check_parser.add_argument("--live", action="store_true")
    status_parser = commands.add_parser("status")
    status_parser.add_argument("run_id")
    reconcile_parser = commands.add_parser("reconcile")
    reconcile_parser.add_argument("approval_id")
    args = parser.parse_args()
    try:
        if args.command == "init":
            init_env()
            return
        settings = Settings.load()
        if args.command == "seed":
            seed_database(settings)
        elif args.command == "setup-issue":
            setup_issue(settings)
        elif args.command == "configure-runtime":
            configure(settings)
        elif args.command == "check":
            sys.exit(0 if check(settings, args.live) else 1)
        elif args.command == "serve":
            uvicorn.run(
                "app.main:create_app",
                factory=True,
                host="127.0.0.1",
                port=8000,
                log_level="warning",
                access_log=False,
            )
        elif args.command == "start":
            start(settings)
        elif args.command == "reconcile":
            print(json.dumps(build_service(settings).reconcile(args.approval_id), indent=2))
        elif args.command == "status":
            service = build_service(settings)
            run = service.store.run(args.run_id)
            if run["session_id"]:
                service.sync_denials(args.run_id, service.trueforge.snapshot(run["session_id"]))
            run = service.store.run(args.run_id)
            print(json.dumps({key: run[key] for key in ("id", "session_id", "status")}, indent=2))
    except (ValueError, ProviderError) as exc:
        print("Blocked:", str(exc), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print(
            "Operation failed. No provider details printed; verify configuration/connectivity.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
