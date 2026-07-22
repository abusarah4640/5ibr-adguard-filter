import json

from scripts.services.guarded_reenable_service import (
    run_guarded_reenable,
)
from scripts.services.production_status_service import (
    PRODUCTION_INACTIVE,
)
from scripts.services.production_verify_service import (
    PRODUCTION_VERIFIED,
)


def write_json(path, payload):
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


class ValidInactiveStatus:
    decision = PRODUCTION_INACTIVE
    healthy = True
    policy_sha_matches = True
    authorized_domains = 13
    audit_integrity_decision = (
        "AUDIT_INTEGRITY_PASS"
    )
    audit_invalid_events = 0


class VerifiedResult:
    decision = PRODUCTION_VERIFIED


class FailedVerification:
    decision = (
        "PRODUCTION_VERIFICATION_FAILED"
    )


def test_reenable_changes_false_to_true(
    tmp_path,
):
    config = tmp_path / "config.json"
    receipt = tmp_path / "receipt.json"

    write_json(
        config,
        {
            "enabled": False,
            "policy_sha256": "a" * 64,
        },
    )

    result = run_guarded_reenable(
        config_path=config,
        receipt_path=receipt,
        status_loader=lambda: (
            ValidInactiveStatus()
        ),
        verifier=lambda: VerifiedResult(),
    )

    payload = json.loads(
        config.read_text(encoding="utf-8")
    )

    assert result.decision == (
        "PRODUCTION_REENABLE_SUCCEEDED"
    )
    assert result.enabled_before is False
    assert result.enabled_after is True
    assert (
        result.rollback_performed is False
    )
    assert payload["enabled"] is True
    assert not result.failures


def test_enabled_state_fails_preflight(
    tmp_path,
):
    config = tmp_path / "config.json"
    receipt = tmp_path / "receipt.json"

    write_json(
        config,
        {
            "enabled": True,
        },
    )

    result = run_guarded_reenable(
        config_path=config,
        receipt_path=receipt,
        status_loader=lambda: (
            ValidInactiveStatus()
        ),
        verifier=lambda: VerifiedResult(),
    )

    payload = json.loads(
        config.read_text(encoding="utf-8")
    )

    assert result.decision == (
        "PRODUCTION_REENABLE_ROLLED_BACK"
    )
    assert result.rollback_performed is True
    assert payload["enabled"] is True


def test_unhealthy_inactive_state_blocks(
    tmp_path,
):
    config = tmp_path / "config.json"
    receipt = tmp_path / "receipt.json"

    write_json(
        config,
        {
            "enabled": False,
        },
    )

    class UnhealthyStatus:
        decision = PRODUCTION_INACTIVE
        healthy = False
        policy_sha_matches = True
        authorized_domains = 13
        audit_integrity_decision = (
            "AUDIT_INTEGRITY_PASS"
        )
        audit_invalid_events = 0

    result = run_guarded_reenable(
        config_path=config,
        receipt_path=receipt,
        status_loader=lambda: (
            UnhealthyStatus()
        ),
        verifier=lambda: VerifiedResult(),
    )

    payload = json.loads(
        config.read_text(encoding="utf-8")
    )

    assert result.decision == (
        "PRODUCTION_REENABLE_ROLLED_BACK"
    )
    assert payload["enabled"] is False
    assert result.rollback_performed is True


def test_failed_post_verification_rolls_back(
    tmp_path,
):
    config = tmp_path / "config.json"
    receipt = tmp_path / "receipt.json"

    write_json(
        config,
        {
            "enabled": False,
        },
    )

    result = run_guarded_reenable(
        config_path=config,
        receipt_path=receipt,
        status_loader=lambda: (
            ValidInactiveStatus()
        ),
        verifier=lambda: (
            FailedVerification()
        ),
    )

    payload = json.loads(
        config.read_text(encoding="utf-8")
    )

    assert result.decision == (
        "PRODUCTION_REENABLE_ROLLED_BACK"
    )
    assert result.rollback_performed is True
    assert payload["enabled"] is False


def test_receipt_is_written(
    tmp_path,
):
    config = tmp_path / "config.json"
    receipt = tmp_path / "receipt.json"

    write_json(
        config,
        {
            "enabled": False,
        },
    )

    run_guarded_reenable(
        config_path=config,
        receipt_path=receipt,
        status_loader=lambda: (
            ValidInactiveStatus()
        ),
        verifier=lambda: VerifiedResult(),
    )

    payload = json.loads(
        receipt.read_text(encoding="utf-8")
    )

    assert payload["operation"] == (
        "guarded-reenable"
    )
    assert payload["decision"] == (
        "PRODUCTION_REENABLE_SUCCEEDED"
    )
    assert payload["enabled_before"] is False
    assert payload["enabled_after"] is True
    assert (
        payload["rollback_performed"]
        is False
    )
    assert payload["failures"] == []
