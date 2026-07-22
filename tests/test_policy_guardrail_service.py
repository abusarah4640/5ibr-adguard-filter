from scripts.services.policy_guardrail_service import (
    GuardrailMode,
    GuardrailRequirement,
    evaluate_policy_guardrail,
)


def test_safe_to_block_allows_normal_approval():
    result = evaluate_policy_guardrail(
        "safe-to-block",
        "approved",
    )

    assert result.mode == GuardrailMode.SHADOW

    assert (
        result.requirement
        == GuardrailRequirement.ALLOW
    )

    assert result.would_block is False
    assert result.allowed is True


def test_do_not_block_would_require_override_in_shadow():
    result = evaluate_policy_guardrail(
        "do-not-block",
        "approved",
    )

    assert (
        result.requirement
        == GuardrailRequirement.REQUIRE_OVERRIDE
    )

    assert result.would_block is True

    # Shadow mode records the violation but
    # does not block the real approval.
    assert result.allowed is True


def test_do_not_block_override_satisfies_guardrail():
    result = evaluate_policy_guardrail(
        "do-not-block",
        "approved",
        reason_supplied=True,
        override_confirmed=True,
    )

    assert result.would_block is False
    assert result.allowed is True


def test_needs_testing_requires_reason_and_confirmation():
    missing = evaluate_policy_guardrail(
        "needs-testing",
        "approved",
        reason_supplied=True,
        test_confirmed=False,
    )

    complete = evaluate_policy_guardrail(
        "needs-testing",
        "approved",
        reason_supplied=True,
        test_confirmed=True,
    )

    assert (
        missing.requirement
        == GuardrailRequirement
        .REQUIRE_TEST_CONFIRMATION
    )

    assert missing.would_block is True
    assert complete.would_block is False


def test_enforce_mode_can_block_unsatisfied_approval():
    result = evaluate_policy_guardrail(
        "do-not-block",
        "approved",
        mode=GuardrailMode.ENFORCE,
    )

    assert result.would_block is True
    assert result.allowed is False


def test_reject_and_ignore_are_always_allowed():
    for action in (
        "rejected",
        "ignored",
    ):
        result = evaluate_policy_guardrail(
            "do-not-block",
            action,
            mode=GuardrailMode.ENFORCE,
        )

        assert (
            result.requirement
            == GuardrailRequirement.ALLOW
        )

        assert result.would_block is False
        assert result.allowed is True


def test_unknown_policy_requires_manual_review():
    result = evaluate_policy_guardrail(
        "unknown",
        "approved",
    )

    assert (
        result.requirement
        == GuardrailRequirement.MANUAL_REVIEW
    )

    assert result.would_block is True
    assert result.allowed is True
