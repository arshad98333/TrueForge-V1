"""Versioned, standard-library-only calculator. Production execution is sandbox-only."""

import hashlib
import json
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

VERSION = "1.0.0"
SCOPE = {
    "fixture": "TEL-1042",
    "customer_id": "CUST-7781",
    "country": "Singapore",
    "network_partner": "SG-PARTNER-01",
    "currency": "INR",
    "start_time": "2026-09-10T00:00:00Z",
    "end_time": "2026-09-15T00:00:00Z",
}
COLLECTIONS = (
    "customer_plans",
    "roaming_packs",
    "tariff_rules",
    "roaming_usage_events",
    "roaming_charge_records",
)
FIELDS = {
    "customer_plans": {
        "customer_id",
        "plan_id",
        "currency",
        "effective_from",
        "effective_to",
        "roaming_eligible",
    },
    "roaming_packs": {
        "pack_id",
        "customer_id",
        "country",
        "activated_at",
        "expires_at",
        "status",
        "price_rule",
        "price",
        "currency",
    },
    "tariff_rules": {
        "tariff_id",
        "country",
        "network_partner",
        "plan_id",
        "effective_from",
        "effective_to",
        "unit_price",
        "rounding",
        "currency",
        "version",
    },
    "roaming_usage_events": {
        "event_id",
        "session_id",
        "customer_id",
        "occurred_at",
        "country",
        "network_partner",
        "units",
    },
    "roaming_charge_records": {
        "charge_id",
        "event_id",
        "session_id",
        "customer_id",
        "invoice_id",
        "charged_at",
        "amount",
        "currency",
    },
}


class EvidenceError(ValueError):
    """Safe, non-sensitive error that may be shown to the operator."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def timestamp(value):
    if not isinstance(value, str):
        raise EvidenceError("Timestamp must be an ISO 8601 string")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("Invalid timestamp") from exc
    if result.tzinfo is None:
        raise EvidenceError("Timezone is required")
    return result


def money(value):
    if not isinstance(value, str) or len(value) > 24:
        raise EvidenceError("Money must be a bounded decimal string")
    try:
        number = Decimal(value)
        if not number.is_finite() or number < 0 or number > Decimal("1000000"):
            raise EvidenceError("Unsupported monetary value")
        return number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise EvidenceError("Invalid money") from exc


def validate_evidence(bundle):
    """Validate scope/identity/completeness without calculating any charge on the host."""
    if not isinstance(bundle, dict) or set(bundle) != {"scope", "complete", "collections"}:
        raise EvidenceError("Invalid evidence envelope")
    if bundle["scope"] != SCOPE or bundle["complete"] is not True:
        raise EvidenceError("Out-of-scope or incomplete evidence")
    records = bundle["collections"]
    if not isinstance(records, dict) or set(records) != set(COLLECTIONS):
        raise EvidenceError("Required evidence collections are missing")
    start, end = timestamp(SCOPE["start_time"]), timestamp(SCOPE["end_time"])
    for name, rows in records.items():
        if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
            raise EvidenceError("Missing or excessive evidence records")
        for row in rows:
            if not isinstance(row, dict) or set(row) != FIELDS[name]:
                raise EvidenceError("Evidence record fields do not match the contract")
            for field in ("customer_id", "country", "network_partner", "currency"):
                if field in row and row[field] != SCOPE[field]:
                    raise EvidenceError("Evidence scope or currency conflict")
            for field in ("occurred_at", "charged_at"):
                if field in row and not start <= timestamp(row[field]) < end:
                    raise EvidenceError("Evidence timestamp outside the supported window")
    if any(len(records[name]) != 1 for name in COLLECTIONS[:-1]):
        raise EvidenceError("Only one plan, pack, tariff, and usage event are supported")
    plan = records["customer_plans"][0]
    pack = records["roaming_packs"][0]
    tariff = records["tariff_rules"][0]
    usage = records["roaming_usage_events"][0]
    at = timestamp(usage["occurred_at"])
    if type(usage["units"]) is not int or usage["units"] != 1:
        raise EvidenceError("Only one flat-session billing unit is supported")
    if not usage["event_id"] or not usage["session_id"]:
        raise EvidenceError("Stable billing identity is required")
    for record in (plan, tariff):
        if not timestamp(record["effective_from"]) <= at < timestamp(record["effective_to"]):
            raise EvidenceError("No effective plan or tariff")
    if plan["roaming_eligible"] is not True or tariff["plan_id"] != plan["plan_id"]:
        raise EvidenceError("Plan and tariff conflict")
    if (
        pack["status"] != "active"
        or pack["price_rule"] != "flat_session"
        or not timestamp(pack["activated_at"]) <= at < timestamp(pack["expires_at"])
    ):
        raise EvidenceError("An active flat-session pack is required")
    if tariff["rounding"] != "0.01":
        raise EvidenceError("Unsupported rounding increment")
    charges = records["roaming_charge_records"]
    if len({row["charge_id"] for row in charges}) != len(charges):
        raise EvidenceError("Repeated records are not proof of repeated billing")
    for charge in charges:
        if (
            not charge["charge_id"]
            or charge["event_id"] != usage["event_id"]
            or charge["session_id"] != usage["session_id"]
        ):
            raise EvidenceError("Charge does not match the billable event/session")
    return bundle


def reconstruct(bundle):
    validate_evidence(bundle)
    records = bundle["collections"]
    pack, tariff = records["roaming_packs"][0], records["tariff_rules"][0]
    expected = money(pack["price"])
    if expected <= 0 or expected != money(tariff["unit_price"]):
        raise EvidenceError("Pack and tariff prices conflict")
    charges = records["roaming_charge_records"]
    if len(charges) < 2 or any(money(row["amount"]) != expected for row in charges):
        raise EvidenceError("This evidence does not prove the supported duplicate charge")
    billed = sum((money(row["amount"]) for row in charges), Decimal("0.00"))
    usage = records["roaming_usage_events"][0]
    return {
        "calculation_status": "success",
        "classification": "duplicate_charge",
        "expected_amount": str(expected),
        "billed_amount": str(billed),
        "difference": str(billed - expected),
        "currency": "INR",
        "duplicate_charge_ids": sorted(row["charge_id"] for row in charges),
        "evidence_ids": sorted(
            [
                usage["event_id"],
                usage["session_id"],
                pack["pack_id"],
                tariff["tariff_id"],
                *(row["charge_id"] for row in charges),
            ]
        ),
        "warnings": [],
        "evidence_hash": digest(bundle),
        "library_version": VERSION,
    }
