import hashlib
import json

from scripts.services.production_status_service import (
    PRODUCTION_ACTIVE,
    PRODUCTION_DEGRADED,
    PRODUCTION_INACTIVE,
    get_production_status,
)


def write_json(path, payload):
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def make_artifacts(
    tmp_path,
    *,
    enabled=True,
    configured_sha=None,
    readiness_decision="PROMOTION_READY",
    activation_decision=(
        "PERMANENT_ACTIVATION_SUCCEEDED"
    ),
    rollback=False,
    audit_decision="AUDIT_INTEGRITY_PASS",
    invalid_events=0,
):
    policy = tmp_path / "policy.json"

    policy.write_text(
        '{"version": 1}',
        encoding="utf-8",
    )

    actual_sha = hashlib.sha256(
        policy.read_bytes()
    ).hexdigest()

    config = tmp_path / "config.json"

    write_json(
        config,
        {
            "version": 1,
            "enabled": enabled,
            "policy_sha256": (
                configured_sha
                if configured_sha is not None
                else actual_sha
            ),
            "authorized_domains": [
                "api3.shahid.net",
                "www.gstatic.com",
            ],
        },
    )

    readiness = (
        tmp_path / "readiness.json"
    )

    write_json(
        readiness,
        {
            "decision": readiness_decision,
        },
    )

    receipt = tmp_path / "receipt.json"

    write_json(
        receipt,
        {
            "decision": activation_decision,
            "completed_at_utc": (
                "2026-07-12T09:00:00+00:00"
            ),
            "rollback_performed": rollback,
        },
    )

    audit = tmp_path / "audit.json"

    write_json(
        audit,
        {
            "decision": audit_decision,
            "invalid_events": invalid_events,
        },
    )

    return {
        "enforcement_config_path": config,
        "policy_path": policy,
        "readiness_path": readiness,
        "activation_receipt_path": receipt,
        "audit_integrity_path": audit,
    }


def test_active_production_is_healthy(
    tmp_path,
):
    paths = make_artifacts(
        tmp_path,
        enabled=True,
    )

    result = get_production_status(
        **paths
    )

    assert (
        result.decision
        == PRODUCTION_ACTIVE
    )
    assert result.healthy is True
    assert (
        result.enforcement_enabled
        is True
    )
    assert result.authorized_domains == 2
    assert result.policy_sha_matches is True
    assert result.issues == ()


def test_inactive_but_valid_is_healthy(
    tmp_path,
):
    paths = make_artifacts(
        tmp_path,
        enabled=False,
    )

    result = get_production_status(
        **paths
    )

    assert (
        result.decision
        == PRODUCTION_INACTIVE
    )
    assert result.healthy is True
    assert (
        result.enforcement_enabled
        is False
    )


def test_policy_sha_mismatch_is_degraded(
    tmp_path,
):
    paths = make_artifacts(
        tmp_path,
        configured_sha="0" * 64,
    )

    result = get_production_status(
        **paths
    )

    assert (
        result.decision
        == PRODUCTION_DEGRADED
    )
    assert result.healthy is False
    assert result.policy_sha_matches is False
    assert (
        "policy-sha-mismatch"
        in result.issues
    )


def test_invalid_audit_is_degraded(
    tmp_path,
):
    paths = make_artifacts(
        tmp_path,
        audit_decision=(
            "AUDIT_INTEGRITY_FAIL"
        ),
        invalid_events=1,
    )

    result = get_production_status(
        **paths
    )

    assert (
        result.decision
        == PRODUCTION_DEGRADED
    )
    assert (
        "audit-integrity-not-pass"
        in result.issues
    )
    assert (
        "invalid-audit-events"
        in result.issues
    )


def test_rollback_receipt_is_degraded(
    tmp_path,
):
    paths = make_artifacts(
        tmp_path,
        activation_decision=(
            "PERMANENT_ACTIVATION_ROLLED_BACK"
        ),
        rollback=True,
    )

    result = get_production_status(
        **paths
    )

    assert (
        result.decision
        == PRODUCTION_DEGRADED
    )
    assert (
        "activation-not-succeeded"
        in result.issues
    )
    assert (
        "activation-rollback-recorded"
        in result.issues
    )


def test_unreadable_config_fails_closed(
    tmp_path,
):
    paths = make_artifacts(
        tmp_path
    )

    paths[
        "enforcement_config_path"
    ].write_text(
        "{broken",
        encoding="utf-8",
    )

    result = get_production_status(
        **paths
    )

    assert (
        result.decision
        == PRODUCTION_DEGRADED
    )
    assert result.healthy is False
    assert (
        result.enforcement_enabled
        is False
    )
    assert result.issues
