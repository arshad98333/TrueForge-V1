"""Read-only Linear connectivity/contract diagnostics. Never prints credentials."""

import json
from pathlib import Path

import httpx
from dotenv import dotenv_values

values = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
token = values.get("LINEAR_API_TOKEN", "")
query = "query { viewer { id } teams(first:100) { nodes { id key name } } }"
try:
    response = httpx.post(
        "https://api.linear.app/graphql",
        json={"query": query},
        headers={"Authorization": token},
        timeout=15,
    )
    body = response.json()
    report = {"http_status": response.status_code}
    if body.get("errors"):
        errors = [str(error.get("message", ""))[:500] for error in body["errors"][:3]]
        for name, value in values.items():
            if value and len(value) > 5:
                errors = [text.replace(value, "[REDACTED]") for text in errors]
        report["errors"] = errors
    else:
        teams = body["data"]["viewer"] is not None and body["data"]["teams"]["nodes"]
        report["authenticated"] = bool(teams)
        report["configured_team_found"] = any(
            t["id"] == values.get("LINEAR_TEAM_ID") for t in teams
        )
        report["team_names"] = [{"key": t["key"], "name": t["name"]} for t in teams]
    print(json.dumps(report, indent=2))
except Exception:
    print("Linear diagnostic failed before a usable response; check connectivity.")
