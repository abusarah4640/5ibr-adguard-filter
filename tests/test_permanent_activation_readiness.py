from scripts.services.permanent_activation_readiness import (
    PERMANENT_ACTIVATION_BLOCKED,
    PERMANENT_ACTIVATION_READY,
    build_permanent_readiness_report,
    evaluate_permanent_activation_readiness,
)


SHA = "a" * 64


def valid_inputs():
    production = {
        "decision": "PROMOTION_READY",
        "checks_failed": 0,
        "blocking_reasons": [],
    }

    audit = {
        "decision": "AUDIT_INTEGRITY_PASS",
        "invalid_events": 0,
    }

    receipt = {
        "validation_passed": True,
        "target_domains": 13,
        "changed_domains": 13,
        "expected_changes": 13,
        "unexpected_changes": 0,
        "missed_targets": 0,
        "non_filter_changes": 0,
        "vendor_changes": 0,
        "category_changes": 0,
        "confidence_changes": 0,
        "recommendation_changes": 0,
    }

    regression = {
        "common_domains": 500,
        "changed_domains": 0,
    }

    config = {
        "policy_sha256": SHA,
        "enabled": False,
    }

    return (
        production,
        audit,
        receipt,
        regression,
        config,
    )


def test_ready_when_all_checks_pass():
    (
        production,
        audit,
        receipt,
        regression,
        config,
    ) = valid_inputs()

    result = (
        evaluate_permanent_activation_readiness(
            production_readiness=production,
            audit_integrity=audit,
            activation_receipt=receipt,
            regression=regression,
            enforcement_config=config,
            policy_sha256=SHA,
        )
    )

    assert result.ready
    assert (
        result.decision
        == PERMANENT_ACTIVATION_READY
    )
    assert result.checks_failed == 0


def test_blocked_on_invalid_audit():
    (
        production,
        audit,
        receipt,
        regression,
        config,
    ) = valid_inputs()

    audit["invalid_events"] = 1

    result = (
        evaluate_permanent_activation_readiness(
            production_readiness=production,
            audit_integrity=audit,
            activation_receipt=receipt,
            regression=regression,
            enforcement_config=config,
            policy_sha256=SHA,
        )
    )

    assert not result.ready
    assert (
        result.decision
        == PERMANENT_ACTIVATION_BLOCKED
    )


def test_blocked_on_policy_hash_mismatch():
    (
        production,
        audit,
        receipt,
        regression,
        config,
    ) = valid_inputs()

    result = (
        evaluate_permanent_activation_readiness(
            production_readiness=production,
            audit_integrity=audit,
            activation_receipt=receipt,
            regression=regression,
            enforcement_config=config,
            policy_sha256="b" * 64,
        )
    )

    assert not result.ready


def test_blocked_when_switch_already_enabled():
    (
        production,
        audit,
        receipt,
        regression,
        config,
    ) = valid_inputs()

    config["enabled"] = True

    result = (
        evaluate_permanent_activation_readiness(
            production_readiness=production,
            audit_integrity=audit,
            activation_receipt=receipt,
            regression=regression,
            enforcement_config=config,
            policy_sha256=SHA,
        )
    )

    assert not result.ready


def test_report_contains_decision():
    (
        production,
        audit,
        receipt,
        regression,
        config,
    ) = valid_inputs()

    result = (
        evaluate_permanent_activation_readiness(
            production_readiness=production,
            audit_integrity=audit,
            activation_receipt=receipt,
            regression=regression,
            enforcement_config=config,
            policy_sha256=SHA,
        )
    )

    report = (
        build_permanent_readiness_report(
            result
        )
    )

    assert (
        "PERMANENT_ACTIVATION_READY"
        in report
    )
    assert (
        "Blocking reasons          : 0"
        in report
    )
