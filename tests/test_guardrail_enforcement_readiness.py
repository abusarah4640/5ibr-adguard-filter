from scripts.services.policy_guardrail_service import (
    GuardrailMode,
    GuardrailRequirement,
    evaluate_policy_guardrail,
)


def enforce(
    policy: str,
    **evidence,
):
    return evaluate_policy_guardrail(
        policy,
        "approved",
        mode=GuardrailMode.ENFORCE,
        **evidence,
    )


def test_safe_to_block_is_ready_without_extra_evidence():
    result = enforce(
        "safe-to-block"
    )

    assert (
        result.requirement
        == GuardrailRequirement.ALLOW
    )

    assert result.would_block is False
    assert result.allowed is True


def test_likely_safe_requires_documented_reason():
    missing = enforce(
        "likely-safe"
    )

    complete = enforce(
        "likely-safe",
        reason_supplied=True,
    )

    assert (
        missing.requirement
        == GuardrailRequirement.REQUIRE_REASON
    )

    assert missing.would_block is True
    assert missing.allowed is False

    assert complete.would_block is False
    assert complete.allowed is True


def test_needs_testing_reason_alone_is_not_enough():
    result = enforce(
        "needs-testing",
        reason_supplied=True,
        test_confirmed=False,
    )

    assert (
        result.requirement
        == GuardrailRequirement
        .REQUIRE_TEST_CONFIRMATION
    )

    assert result.would_block is True
    assert result.allowed is False


def test_needs_testing_requires_reason_and_test_confirmation():
    result = enforce(
        "needs-testing",
        reason_supplied=True,
        test_confirmed=True,
    )

    assert result.would_block is False
    assert result.allowed is True


def test_do_not_block_override_without_reason_is_not_enough():
    result = enforce(
        "do-not-block",
        override_confirmed=True,
        reason_supplied=False,
    )

    assert (
        result.requirement
        == GuardrailRequirement.REQUIRE_OVERRIDE
    )

    assert result.would_block is True
    assert result.allowed is False


def test_do_not_block_requires_reason_and_override():
    result = enforce(
        "do-not-block",
        reason_supplied=True,
        override_confirmed=True,
    )

    assert result.would_block is False
    assert result.allowed is True


def test_unknown_reason_without_manual_review_is_not_enough():
    result = enforce(
        "unknown",
        reason_supplied=True,
        manual_review_confirmed=False,
    )

    assert (
        result.requirement
        == GuardrailRequirement.MANUAL_REVIEW
    )

    assert result.would_block is True
    assert result.allowed is False


def test_unknown_requires_reason_and_manual_review_confirmation():
    result = enforce(
        "unknown",
        reason_supplied=True,
        manual_review_confirmed=True,
    )

    assert result.would_block is False
    assert result.allowed is True
