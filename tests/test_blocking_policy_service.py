from scripts.services.blocking_policy_service import (
    BlockingPolicy,
    BlockingPolicyDecision,
    blocking_policy_value,
    classify_blocking_policy,
    normalize_category,
)


def test_ads_are_safe_to_block():
    decision = classify_blocking_policy(
        "Ads"
    )

    assert isinstance(
        decision,
        BlockingPolicyDecision,
    )

    assert (
        decision.policy
        == BlockingPolicy.SAFE_TO_BLOCK
    )

    assert decision.source == "category-policy"
    assert "Advertising" in decision.reason


def test_telemetry_needs_testing():
    decision = classify_blocking_policy(
        "Telemetry"
    )

    assert (
        decision.policy
        == BlockingPolicy.NEEDS_TESTING
    )

    assert "test" in decision.reason.lower()


def test_streaming_must_not_be_blocked():
    decision = classify_blocking_policy(
        "Streaming"
    )

    assert (
        decision.policy
        == BlockingPolicy.DO_NOT_BLOCK
    )

    assert "Streaming" in decision.reason


def test_gaming_must_not_be_blocked():
    decision = classify_blocking_policy(
        "Gaming"
    )

    assert (
        decision.policy
        == BlockingPolicy.DO_NOT_BLOCK
    )


def test_connectivity_must_not_be_blocked():
    decision = classify_blocking_policy(
        "Connectivity"
    )

    assert (
        decision.policy
        == BlockingPolicy.DO_NOT_BLOCK
    )


def test_unknown_category_has_safe_fallback():
    decision = classify_blocking_policy(
        "Experimental Category"
    )

    assert (
        decision.policy
        == BlockingPolicy.UNKNOWN
    )

    assert decision.source == "fallback"
    assert "Experimental Category" in decision.reason


def test_missing_category_is_unknown():
    for category in (
        None,
        "",
        "   ",
    ):
        decision = classify_blocking_policy(
            category
        )

        assert (
            decision.policy
            == BlockingPolicy.UNKNOWN
        )


def test_category_normalization():
    assert (
        normalize_category(
            "  Smart-TV  "
        )
        == "smart tv"
    )

    assert (
        normalize_category(
            "CRASH_REPORTING"
        )
        == "crash reporting"
    )


def test_serialized_policy_value():
    assert (
        blocking_policy_value("Ads")
        == "safe-to-block"
    )

    assert (
        blocking_policy_value(
            "Telemetry"
        )
        == "needs-testing"
    )

    assert (
        blocking_policy_value(
            "Streaming"
        )
        == "do-not-block"
    )


def test_policy_decision_is_immutable():
    decision = classify_blocking_policy(
        "Ads"
    )

    try:
        decision.reason = "changed"
    except AttributeError:
        pass
    else:
        raise AssertionError(
            "BlockingPolicyDecision must "
            "remain immutable."
        )
