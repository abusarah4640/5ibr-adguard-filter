"""Decision Engine foundation for 5ibr Filter Toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field

from scripts.services.explain_engine import (
    Explanation,
    explanations_to_reasons,
    make_explanation,
    total_explanation_weight,
)


@dataclass(frozen=True)
class Decision:
    vendor: str = "Unknown"
    category: str = "Unknown"
    filter_name: str = "unknown"
    confidence: int = 0
    recommendation: str = "unknown"
    explanations: list[Explanation] = field(default_factory=list)


def clamp_confidence(value: int) -> int:
    return max(0, min(int(value), 100))


def recommendation_from_confidence(confidence: int) -> str:
    confidence = clamp_confidence(confidence)

    if confidence >= 90:
        return "approved-candidate"

    if confidence >= 50:
        return "review"

    return "unknown"


def build_decision(
    *,
    vendor: str = "Unknown",
    category: str = "Unknown",
    filter_name: str = "unknown",
    explanations: list[Explanation] | None = None,
) -> Decision:
    items = explanations or []
    confidence = clamp_confidence(total_explanation_weight(items))

    return Decision(
        vendor=vendor or "Unknown",
        category=category or "Unknown",
        filter_name=filter_name or "unknown",
        confidence=confidence,
        recommendation=recommendation_from_confidence(confidence),
        explanations=items,
    )


def decision_reasons(decision: Decision) -> list[str]:
    reasons = explanations_to_reasons(decision.explanations)

    if not reasons and decision.recommendation == "unknown":
        return ["no local analyzer rules matched"]

    return reasons


def legacy_reason_explanation(reason: str, *, source: str = "legacy", weight: int = 0) -> Explanation:
    return make_explanation(
        source=source,
        message=reason,
        weight=weight,
    )


def apply_confidence_guardrails(
    decision: Decision,
    *,
    conflicting_evidence: bool = False,
) -> Decision:
    """Apply conservative confidence caps to potentially conflicting evidence.

    A result with conflicting evidence may still be useful for review, but it
    must not become an automatically approved candidate.
    """

    if not conflicting_evidence:
        return decision

    guarded_confidence = min(decision.confidence, 89)

    return Decision(
        vendor=decision.vendor,
        category=decision.category,
        filter_name=decision.filter_name,
        confidence=guarded_confidence,
        recommendation=recommendation_from_confidence(
            guarded_confidence
        ),
        explanations=decision.explanations,
    )
