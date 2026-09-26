import copy
from decimal import Decimal

import pytest

from app.sandbox import RUNNER, execution_spec, validate_runner
from app.store import PolicyError, Store
from domain.charge_rules import EvidenceError, money, reconstruct, validate_evidence


def test_duplicate_amounts_and_identity(bundle):
    result = reconstruct(bundle)
    assert result["classification"] == "duplicate_charge"
    assert (result["billed_amount"], result["expected_amount"], result["difference"]) == (
        "2400.00",
        "1200.00",
        "1200.00",
    )
    assert result["duplicate_charge_ids"] == ["CHG-SG-2001", "CHG-SG-2002"]
    assert "EVT-SG-1001" in result["evidence_ids"]


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1E9999", 1.2, "bad"])
def test_bad_money(value):
    with pytest.raises(EvidenceError):
        money(value)


def test_rounding():
    assert money("1.005") == Decimal("1.01")
    assert money("0.104") == Decimal("0.10")


def test_store_supports_idempotent_runs_for_multiple_synthetic_tickets(tmp_path):
    store = Store(tmp_path / "state.sqlite")
    first = store.create_run("issue-1", "team-1")
    assert store.create_run("issue-1", "team-1")["id"] == first["id"]
    second = store.create_run("issue-2", "team-1")
    assert second["id"] != first["id"]
    assert second["issue_id"] == "issue-2"


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c["roaming_charge_records"][1].update(currency="USD"),
        lambda c: c["roaming_charge_records"][1].update(event_id="OTHER-EVENT"),
        lambda c: c["roaming_charge_records"][1].update(session_id="OTHER-SESSION"),
        lambda c: c["roaming_charge_records"][1].update(charge_id="CHG-SG-2001"),
        lambda c: c["roaming_charge_records"][1].update(customer_id="CUST-OTHER"),
        lambda c: c["roaming_charge_records"].pop(),
        lambda c: c["tariff_rules"].clear(),
        lambda c: c["tariff_rules"].append(copy.deepcopy(c["tariff_rules"][0])),
        lambda c: c["roaming_usage_events"].append(copy.deepcopy(c["roaming_usage_events"][0])),
        lambda c: c["roaming_packs"][0].update(expires_at="2026-09-12T10:15:00Z"),
        lambda c: c["tariff_rules"][0].update(effective_to="2026-09-12T10:15:00Z"),
        lambda c: c["roaming_charge_records"][0].update(charged_at="2026-09-15T00:00:00Z"),
        lambda c: c["roaming_usage_events"][0].update(units=True),
        lambda c: c["roaming_packs"][0].update(price="1100.00"),
    ],
)
def test_unsupported_or_conflicting_evidence(bundle, change):
    change(bundle["collections"])
    with pytest.raises(EvidenceError):
        reconstruct(bundle)


def test_boundaries_and_complete_flag(bundle):
    bundle["complete"] = False
    with pytest.raises(EvidenceError):
        validate_evidence(bundle)
    bundle["complete"] = True
    bundle["collections"]["roaming_charge_records"] *= 51
    with pytest.raises(EvidenceError):
        validate_evidence(bundle)


@pytest.mark.parametrize(
    "source",
    [
        "import os; os.system('whoami')",
        RUNNER + "\nopen('/tmp/file','w')",
        RUNNER.replace("reconstruct(evidence)", "{'difference': '9000.00'}"),
        RUNNER + "\nimport socket",
        RUNNER + "\nprint(__import__('os').environ)",
    ],
)
def test_generated_runner_cannot_escape_contract(source):
    with pytest.raises(PolicyError):
        validate_runner(source)


def test_execution_command_is_self_contained_and_no_host_execution(bundle):
    spec = execution_spec(bundle, "# Written by the agent\n" + RUNNER)
    assert spec["command"].startswith("env -i PATH=")
    assert "timeout 20s python3 -I -S" in spec["command"]
    assert len(spec["library_hash"]) == 64
    assert spec["runner_source"].startswith("# Written by")
