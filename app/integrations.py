"""Bounded provider adapters. Never include provider response bodies in errors."""

import time

import httpx
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from domain.charge_rules import COLLECTIONS, FIELDS, SCOPE, EvidenceError, canonical

from .store import PolicyError


class ProviderError(RuntimeError):
    pass


ISSUE_FIELDS = (
    "id identifier title description updatedAt url team { id } state { id name type } "
    "labels { nodes { name } }"
)


class Linear:
    def __init__(self, token, transport=None):
        self.client = httpx.Client(
            base_url="https://api.linear.app",
            headers={"Authorization": token},
            timeout=10,
            transport=transport,
        )

    def query(self, query, variables, *, mutation=False):
        for attempt in range(1 if mutation else 2):
            try:
                response = self.client.post(
                    "/graphql", json={"query": query, "variables": variables}
                )
                response.raise_for_status()
                data = response.json()
                if data.get("errors") or not isinstance(data.get("data"), dict):
                    raise ProviderError("Linear returned an unsuccessful response")
                return data["data"]
            except (httpx.HTTPError, ValueError) as exc:
                if not mutation and attempt == 0:
                    time.sleep(0.2)
                    continue
                raise ProviderError(
                    "Linear request failed; mutation outcome may be unknown"
                ) from exc

    def issue(self, issue_id):
        result = self.query(
            "query($id:String!){issue(id:$id){" + ISSUE_FIELDS + "}}", {"id": issue_id}
        )
        if not result.get("issue"):
            raise ProviderError("Linear issue not found")
        return result["issue"]

    def create_issue(self, team_id, title, description):
        result = self.query(
            "mutation($input:IssueCreateInput!){issueCreate(input:$input)"
            "{success issue{" + ISSUE_FIELDS + "}}}",
            {"input": {"teamId": team_id, "title": title, "description": description}},
            mutation=True,
        )["issueCreate"]
        if not result["success"]:
            raise ProviderError("Linear issue creation unsuccessful")
        return result["issue"]

    def open_issues(self, team_id):
        result = self.query(
            "query($teamId:ID!){issues(first:100,filter:{team:{id:{eq:$teamId}},"
            "state:{type:{nin:[\"completed\",\"canceled\"]}}}){nodes{"
            + ISSUE_FIELDS
            + "} pageInfo{hasNextPage}}}",
            {"teamId": team_id},
        )["issues"]
        if result["pageInfo"]["hasNextPage"]:
            raise ProviderError("Open Linear issue list exceeds the 100-ticket safety bound")
        return result["nodes"]

    def verify_team(self, team_id):
        result = self.query(
            "query{teams(first:100){nodes{id name key} pageInfo{hasNextPage}}}", {}
        )["teams"]
        if result["pageInfo"]["hasNextPage"]:
            raise ProviderError("Linear team lookup exceeded its result bound")
        teams = result["nodes"]
        match = next((team for team in teams if team["id"] == team_id), None)
        if match:
            return match
        if len(teams) == 1:
            return teams[0]
        raise ProviderError("Set LINEAR_TEAM_ID to an accessible team UUID")

    def post_comment(self, issue_id, text):
        result = self.query(
            "mutation($input:CommentCreateInput!){commentCreate(input:$input)"
            "{success comment{id body url issue{id}}}}",
            {"input": {"issueId": issue_id, "body": text}},
            mutation=True,
        )["commentCreate"]
        if not result["success"]:
            raise ProviderError("Linear comment creation unsuccessful")
        return result["comment"]

    def comment(self, comment_id):
        return self.query(
            "query($id:String!){comment(id:$id){id body url issue{id}}}", {"id": comment_id}
        )["comment"]

    def comments(self, issue_id):
        result = self.query(
            "query($id:String!){issue(id:$id){comments(first:100)"
            "{nodes{id body url issue{id}} pageInfo{hasNextPage}}}}",
            {"id": issue_id},
        )["issue"]["comments"]
        if result["pageInfo"]["hasNextPage"]:
            raise ProviderError("Comment reconciliation exceeded its result bound")
        return result["nodes"]


def issue_binding(issue, run):
    if issue["id"] != run["issue_id"] or issue["team"]["id"] != run["team_id"]:
        raise PolicyError("Linear issue/team binding mismatch")
    description = issue.get("description") or ""
    marker = "ROAMING_RESOLVER_SCOPE=" + canonical(SCOPE)
    if marker not in description:
        raise PolicyError("Issue is missing its exact synthetic scope marker")
    if len(description) > 16000 or len(issue["title"]) > 1000:
        raise PolicyError("Ticket exceeds the supported text limit")
    return {key: issue[key] for key in ("id", "title", "description", "team", "state")}


class EvidenceRepository:
    def __init__(self, uri):
        self.client = MongoClient(
            uri,
            connect=False,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
            retryReads=False,
            retryWrites=False,
        )
        self.db = self.client["roaming_resolver_demo"]

    def _read(self, collection, query):
        projection = dict.fromkeys(FIELDS[collection], 1) | {"_id": 0}
        for attempt in range(2):
            try:
                rows = list(
                    self.db[collection].find(query, projection).limit(101).max_time_ms(5000)
                )
                if len(rows) > 100:
                    raise EvidenceError("Evidence exceeds 100 records; calculation is blocked")
                return sorted(rows, key=canonical)
            except PyMongoError as exc:
                if attempt == 0:
                    time.sleep(0.2)
                    continue
                raise ProviderError("MongoDB evidence unavailable after bounded retry") from exc

    def fetch(self):
        customer = {"customer_id": SCOPE["customer_id"]}
        window = {"$gte": SCOPE["start_time"], "$lt": SCOPE["end_time"]}
        # The demo importer stores canonical UTC ISO strings, not mixed BSON/string dates.
        queries = {
            "customer_plans": customer
            | {
                "effective_from": {"$lt": SCOPE["end_time"]},
                "effective_to": {"$gt": SCOPE["start_time"]},
            },
            "roaming_packs": customer
            | {
                "country": SCOPE["country"],
                "activated_at": {"$lt": SCOPE["end_time"]},
                "expires_at": {"$gt": SCOPE["start_time"]},
            },
            "roaming_usage_events": customer | {"occurred_at": window},
            "roaming_charge_records": customer | {"charged_at": window},
        }
        records = {name: self._read(name, query) for name, query in queries.items()}
        plans = records["customer_plans"]
        if len(plans) != 1:
            raise EvidenceError("Exactly one effective plan is required")
        records["tariff_rules"] = self._read(
            "tariff_rules",
            {
                "country": SCOPE["country"],
                "network_partner": SCOPE["network_partner"],
                "plan_id": plans[0]["plan_id"],
                "effective_from": {"$lt": SCOPE["end_time"]},
                "effective_to": {"$gt": SCOPE["start_time"]},
            },
        )
        return {
            "scope": SCOPE,
            "complete": True,
            "collections": {name: records[name] for name in COLLECTIONS},
        }

    def upsert_synthetic_case(self, amount, nonce):
        """Replace the bounded demo facts without widening the agent's read scope."""
        event_time = f"2026-09-12T10:{int(nonce[-2:], 16) % 50 + 5:02d}:00Z"
        invoice_id = "INV-RANDOM-" + nonce
        updates = {
            "roaming_packs": ({"pack_id": "PACK-SG-01"}, {"price": amount}),
            "tariff_rules": (
                {"tariff_id": "TARIFF-SG-STD-2026"},
                {"unit_price": amount, "version": "generated-" + nonce.lower()},
            ),
            "roaming_usage_events": (
                {"event_id": "EVT-SG-1001"},
                {"occurred_at": event_time},
            ),
        }
        for name, (query, values) in updates.items():
            self.db[name].update_one(query, {"$set": values})
        for charge_id, offset in (("CHG-SG-2001", 1), ("CHG-SG-2002", 2)):
            minute = int(event_time[14:16]) + offset
            self.db.roaming_charge_records.update_one(
                {"charge_id": charge_id},
                {
                    "$set": {
                        "amount": amount,
                        "invoice_id": invoice_id,
                        "charged_at": f"2026-09-12T10:{minute:02d}:00Z",
                    }
                },
            )
        return {
            "fixture": "TEL-GEN-" + nonce,
            "nonce": nonce,
            "unit_amount": amount,
            "billed_amount": f"{int(amount.split('.')[0]) * 2}.00",
            "event_time": event_time,
        }
