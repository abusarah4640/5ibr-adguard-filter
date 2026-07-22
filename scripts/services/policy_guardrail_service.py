"""Shadow-mode policy guardrails for review decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GuardrailMode(StrEnum):
    """Supported policy enforcement modes."""

    SHADOW = "shadow"
    ENFORCE = "enforce"


class GuardrailRequirement(StrEnum):
    """Additional action required before approval."""

    ALLOW = "allow"
    REQUIRE_REASON = "require-reason"
    REQUIRE_TEST_CONFIRMATION = (
        "require-test-confirmation"
    )
    REQUIRE_OVERRIDE = "require-override"
    MANUAL_REVIEW = "manual-review"


@dataclass(frozen=True, slots=True)
class GuardrailEvaluation:
    """Result of evaluating one review action."""

    mode: GuardrailMode
    policy: str
    action: str
    requirement: GuardrailRequirement
    would_block: bool
    allowed: bool
    reason: str
    source: str = "blocking-policy-guardrail"


def evaluate_policy_guardrail(
    policy: str,
    action: str,
    *,
    mode: GuardrailMode | str = GuardrailMode.SHADOW,
    reason_supplied: bool = False,
    test_confirmed: bool = False,
    override_confirmed: bool = False,
    manual_review_confirmed: bool = False,
) -> GuardrailEvaluation:
    """Evaluate a review decision without changing application state."""

    resolved_mode = GuardrailMode(mode)

    normalized_policy = (
        str(policy or "unknown")
        .strip()
        .lower()
    )

    normalized_action = (
        str(action or "")
        .strip()
        .lower()
    )

    # Reject and ignore actions do not create blocking rules.
    if normalized_action != "approved":
        return GuardrailEvaluation(
            mode=resolved_mode,
            policy=normalized_policy,
            action=normalized_action,
            requirement=(
                GuardrailRequirement.ALLOW
            ),
            would_block=False,
            allowed=True,
            reason=(
                "Non-approval actions do not "
                "require blocking-policy approval."
            ),
        )

    if normalized_policy == "safe-to-block":
        requirement = GuardrailRequirement.ALLOW
        satisfied = True
        explanation = (
            "The blocking policy allows the "
            "normal approval path."
        )

    elif normalized_policy == "likely-safe":
        requirement = (
            GuardrailRequirement.REQUIRE_REASON
        )
        satisfied = reason_supplied
        explanation = (
            "Likely-safe approvals require "
            "a documented operator reason."
        )

    elif normalized_policy == "needs-testing":
        requirement = (
            GuardrailRequirement
            .REQUIRE_TEST_CONFIRMATION
        )
        satisfied = (
            reason_supplied
            and test_confirmed
        )
        explanation = (
            "This policy requires a documented "
            "reason and confirmed impact testing."
        )

    elif normalized_policy == "do-not-block":
        requirement = (
            GuardrailRequirement.REQUIRE_OVERRIDE
        )
        satisfied = (
            reason_supplied
            and override_confirmed
        )
        explanation = (
            "This policy requires an explicit "
            "override and documented reason."
        )

    else:
        requirement = (
            GuardrailRequirement.MANUAL_REVIEW
        )

        satisfied = (
            reason_supplied
            and manual_review_confirmed
        )

        explanation = (
            "Unknown blocking policy requires "
            "manual review confirmation and "
            "a documented reason."
        )

    would_block = not satisfied

    allowed = (
        True
        if resolved_mode == GuardrailMode.SHADOW
        else satisfied
    )

    return GuardrailEvaluation(
        mode=resolved_mode,
        policy=normalized_policy,
        action=normalized_action,
        requirement=requirement,
        would_block=would_block,
        allowed=allowed,
        reason=explanation,
    )
