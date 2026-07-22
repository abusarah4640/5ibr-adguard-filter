import json

from scripts.services.controlled_promotion_simulation import (
    SimulatedDecision,
)
from scripts.services.scoped_policy_enforcement import (
    EnforcementConfiguration,
    authorize_enforcement,
    enforce_scoped_decision,
    load_enforcement_configuration,
)
from scripts.services.scoped_promotion_policy import (
    ScopedPromotionPolicy,
)


SHA = "a" * 64


def test_load_enforcement_configuration(tmp_path):
    path = tmp_path / "enforcement.json"

    path.write_text(
        json.dumps(
            {
                "version": 1,
                "enabled": False,
                "required_readiness_decision": (
                    "PROMOTION_READY"
                ),
                "policy_sha256": SHA,
            }
        ),
        encoding="utf-8",
    )

    config = (
        load_enforcement_configuration(
            path
        )
    )

    assert not config.enabled
    assert config.policy_sha256 == SHA


def test_disabled_kill_switch_blocks_authorization(
    tmp_path,
):
    policy = tmp_path / "policy.json"
    policy.write_text(
        "policy",
        encoding="utf-8",
    )

    configuration = EnforcementConfiguration(
        enabled=False,
        required_readiness_decision=(
            "PROMOTION_READY"
        ),
        policy_sha256=(
            __import__("hashlib")
            .sha256(b"policy")
            .hexdigest()
        ),
    )

    authorization = authorize_enforcement(
        configuration=configuration,
        readiness_payload={
            "decision": "PROMOTION_READY",
            "checks_failed": 0,
            "blocking_reasons": [],
        },
        policy_path=policy,
    )

    assert not authorization.authorized
    assert (
        "enforcement kill switch is disabled"
        in authorization.reasons
    )


def test_enabled_valid_configuration_authorizes(
    tmp_path,
):
    policy = tmp_path / "policy.json"
    policy.write_text(
        "policy",
        encoding="utf-8",
    )

    actual_sha = (
        __import__("hashlib")
        .sha256(b"policy")
        .hexdigest()
    )

    configuration = EnforcementConfiguration(
        enabled=True,
        required_readiness_decision=(
            "PROMOTION_READY"
        ),
        policy_sha256=actual_sha,
    )

    authorization = authorize_enforcement(
        configuration=configuration,
        readiness_payload={
            "decision": "PROMOTION_READY",
            "checks_failed": 0,
            "blocking_reasons": [],
        },
        policy_path=policy,
    )

    assert authorization.authorized
    assert not authorization.reasons


def test_unauthorized_decision_is_unchanged():
    control = SimulatedDecision(
        vendor="Shahid",
        category="Streaming",
        filter_name="social",
        confidence=65,
        recommendation="review",
    )

    policy = ScopedPromotionPolicy(
        category="Streaming",
        current_filter="social",
        proposed_filter="streaming",
        authorized_suffixes=(
            "shahid.net",
        ),
    )

    from scripts.services.scoped_policy_enforcement import (
        EnforcementAuthorization,
    )

    result = enforce_scoped_decision(
        domain="api3.shahid.net",
        control=control,
        policies=[policy],
        authorization=EnforcementAuthorization(
            authorized=False,
            reasons=("disabled",),
            policy_sha256=SHA,
            configured_policy_sha256=SHA,
            readiness_decision=(
                "PROMOTION_READY"
            ),
            enabled=False,
        ),
    )

    assert not result.applied
    assert result.before == result.after
    assert result.changed_fields == ()


def test_authorized_scoped_decision_changes_filter_only():
    control = SimulatedDecision(
        vendor="Shahid",
        category="Streaming",
        filter_name="social",
        confidence=65,
        recommendation="review",
    )

    policy = ScopedPromotionPolicy(
        category="Streaming",
        current_filter="social",
        proposed_filter="streaming",
        authorized_suffixes=(
            "shahid.net",
        ),
    )

    from scripts.services.scoped_policy_enforcement import (
        EnforcementAuthorization,
    )

    result = enforce_scoped_decision(
        domain="api3.shahid.net",
        control=control,
        policies=[policy],
        authorization=EnforcementAuthorization(
            authorized=True,
            reasons=(),
            policy_sha256=SHA,
            configured_policy_sha256=SHA,
            readiness_decision=(
                "PROMOTION_READY"
            ),
            enabled=True,
        ),
    )

    assert result.applied
    assert result.changed_fields == (
        "filter",
    )
    assert (
        result.after.filter_name
        == "streaming"
    )
    assert (
        result.after.confidence
        == result.before.confidence
    )
    assert (
        result.after.recommendation
        == result.before.recommendation
    )
