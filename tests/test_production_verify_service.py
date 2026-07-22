from scripts.services.production_status_service import (
    PRODUCTION_ACTIVE,
    PRODUCTION_DEGRADED,
    ProductionStatus,
)
from scripts.services.production_verify_service import (
    PRODUCTION_VERIFICATION_FAILED,
    PRODUCTION_VERIFIED,
    build_production_verify_report,
    verify_production_status,
)


def valid_status():
    return ProductionStatus(
        decision=PRODUCTION_ACTIVE,
        healthy=True,
        enforcement_enabled=True,
        authorized_domains=13,
        configured_policy_sha256=(
            "a" * 64
        ),
        actual_policy_sha256=(
            "a" * 64
        ),
        policy_sha_matches=True,
        readiness_decision=(
            "PROMOTION_READY"
        ),
        activation_decision=(
            "PERMANENT_ACTIVATION_SUCCEEDED"
        ),
        activation_completed_at_utc=(
            "2026-07-12T09:42:52+00:00"
        ),
        activation_rollback_performed=False,
        audit_integrity_decision=(
            "AUDIT_INTEGRITY_PASS"
        ),
        audit_invalid_events=0,
        issues=(),
    )


def test_valid_production_is_verified():
    result = verify_production_status(
        valid_status()
    )

    assert result.verified is True
    assert (
        result.decision
        == PRODUCTION_VERIFIED
    )
    assert result.checks_failed == 0
    assert not result.blocking_reasons


def test_disabled_enforcement_fails():
    status = valid_status()

    status = ProductionStatus(
        **{
            **status.to_dict(),
            "enforcement_enabled": False,
        }
    )

    result = verify_production_status(
        status
    )

    assert result.verified is False
    assert (
        result.decision
        == PRODUCTION_VERIFICATION_FAILED
    )


def test_wrong_domain_count_fails():
    status = valid_status()

    status = ProductionStatus(
        **{
            **status.to_dict(),
            "authorized_domains": 12,
        }
    )

    result = verify_production_status(
        status
    )

    assert result.verified is False
    assert result.checks_failed == 1


def test_audit_failure_blocks_verification():
    status = valid_status()

    status = ProductionStatus(
        **{
            **status.to_dict(),
            "decision": (
                PRODUCTION_DEGRADED
            ),
            "healthy": False,
            "audit_integrity_decision": (
                "AUDIT_INTEGRITY_FAIL"
            ),
            "audit_invalid_events": 1,
            "issues": [
                "audit-integrity-not-pass",
                "invalid-audit-events",
            ],
        }
    )

    result = verify_production_status(
        status
    )

    assert result.verified is False
    assert result.checks_failed >= 1


def test_report_contains_verified_decision():
    result = verify_production_status(
        valid_status()
    )

    report = (
        build_production_verify_report(
            result
        )
    )

    assert (
        "PRODUCTION_VERIFIED"
        in report
    )

    assert (
        "Blocking reasons          : 0"
        in report
    )
