import json

import scripts.services.production_lifecycle_acceptance as service
from scripts.services.production_lifecycle_acceptance import (
    LIFECYCLE_ACCEPTED,
    LIFECYCLE_REJECTED,
    evaluate_lifecycle_acceptance,
)
from scripts.services.production_status_service import (
    PRODUCTION_ACTIVE,
)
from scripts.services.production_verify_service import (
    PRODUCTION_VERIFIED,
)


def write_json(path, payload):
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


class GoodStatus:
    decision = PRODUCTION_ACTIVE
    healthy = True
    enforcement_enabled = True
    authorized_domains = 13
    policy_sha_matches = True
    audit_integrity_decision = (
        "AUDIT_INTEGRITY_PASS"
    )
    audit_invalid_events = 0


class GoodVerification:
    decision = PRODUCTION_VERIFIED
    checks_failed = 0


def make_receipts(tmp_path):
    disable = tmp_path / "disable.json"
    reenable = tmp_path / "reenable.json"
    final_verify = tmp_path / "verify.json"

    write_json(
        disable,
        {
            "decision": (
                "PRODUCTION_DISABLE_SUCCEEDED"
            ),
            "enabled_before": True,
            "enabled_after": False,
            "failures": [],
        },
    )

    write_json(
        reenable,
        {
            "decision": (
                "PRODUCTION_REENABLE_SUCCEEDED"
            ),
            "enabled_before": False,
            "enabled_after": True,
            "rollback_performed": False,
            "failures": [],
        },
    )

    write_json(
        final_verify,
        {
            "decision": PRODUCTION_VERIFIED,
            "verified": True,
            "checks_failed": 0,
            "blocking_reasons": [],
        },
    )

    return disable, reenable, final_verify


def evaluate(
    tmp_path,
    monkeypatch,
):
    disable, reenable, final_verify = (
        make_receipts(tmp_path)
    )

    monkeypatch.setattr(
        service,
        "get_production_status",
        lambda: GoodStatus(),
    )

    monkeypatch.setattr(
        service,
        "verify_production",
        lambda: GoodVerification(),
    )

    return evaluate_lifecycle_acceptance(
        disable_receipt_path=disable,
        reenable_receipt_path=reenable,
        final_verify_path=final_verify,
    )


def test_valid_lifecycle_is_accepted(
    tmp_path,
    monkeypatch,
):
    result = evaluate(
        tmp_path,
        monkeypatch,
    )

    assert result.accepted is True
    assert (
        result.decision
        == LIFECYCLE_ACCEPTED
    )
    assert result.checks_failed == 0
    assert not result.blocking_reasons


def test_failed_reenable_is_rejected(
    tmp_path,
    monkeypatch,
):
    disable, reenable, final_verify = (
        make_receipts(tmp_path)
    )

    payload = json.loads(
        reenable.read_text(encoding="utf-8")
    )

    payload["decision"] = (
        "PRODUCTION_REENABLE_ROLLED_BACK"
    )

    write_json(
        reenable,
        payload,
    )

    monkeypatch.setattr(
        service,
        "get_production_status",
        lambda: GoodStatus(),
    )

    monkeypatch.setattr(
        service,
        "verify_production",
        lambda: GoodVerification(),
    )

    result = evaluate_lifecycle_acceptance(
        disable_receipt_path=disable,
        reenable_receipt_path=reenable,
        final_verify_path=final_verify,
    )

    assert result.accepted is False
    assert (
        result.decision
        == LIFECYCLE_REJECTED
    )
    assert result.checks_failed == 1


def test_missing_receipt_is_rejected(
    tmp_path,
    monkeypatch,
):
    disable, reenable, final_verify = (
        make_receipts(tmp_path)
    )

    reenable.unlink()

    monkeypatch.setattr(
        service,
        "get_production_status",
        lambda: GoodStatus(),
    )

    monkeypatch.setattr(
        service,
        "verify_production",
        lambda: GoodVerification(),
    )

    result = evaluate_lifecycle_acceptance(
        disable_receipt_path=disable,
        reenable_receipt_path=reenable,
        final_verify_path=final_verify,
    )

    assert result.accepted is False
    assert (
        result.decision
        == LIFECYCLE_REJECTED
    )
    assert result.checks_failed >= 1


def test_bad_live_status_is_rejected(
    tmp_path,
    monkeypatch,
):
    disable, reenable, final_verify = (
        make_receipts(tmp_path)
    )

    class BadStatus:
        decision = "PRODUCTION_DEGRADED"
        healthy = False
        enforcement_enabled = True
        authorized_domains = 13
        policy_sha_matches = True
        audit_integrity_decision = (
            "AUDIT_INTEGRITY_PASS"
        )
        audit_invalid_events = 0

    monkeypatch.setattr(
        service,
        "get_production_status",
        lambda: BadStatus(),
    )

    monkeypatch.setattr(
        service,
        "verify_production",
        lambda: GoodVerification(),
    )

    result = evaluate_lifecycle_acceptance(
        disable_receipt_path=disable,
        reenable_receipt_path=reenable,
        final_verify_path=final_verify,
    )

    assert result.accepted is False
    assert (
        result.decision
        == LIFECYCLE_REJECTED
    )
    assert result.checks_failed == 2
