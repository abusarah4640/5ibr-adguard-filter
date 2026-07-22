"""Explain Engine foundation for 5ibr Filter Toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Explanation:
    source: str
    message: str
    weight: int = 0
    metadata: dict[str, str] = field(default_factory=dict)


def normalize_explanation_text(value: str) -> str:
    return (value or "").strip()


def make_explanation(
    *,
    source: str,
    message: str,
    weight: int = 0,
    metadata: dict[str, str] | None = None,
) -> Explanation:
    return Explanation(
        source=normalize_explanation_text(source) or "unknown",
        message=normalize_explanation_text(message),
        weight=max(0, int(weight)),
        metadata=metadata or {},
    )


def explanation_to_reason(explanation: Explanation) -> str:
    return explanation.message


def explanations_to_reasons(explanations: list[Explanation]) -> list[str]:
    reasons: list[str] = []

    for explanation in explanations:
        reason = explanation_to_reason(explanation)
        if reason and reason not in reasons:
            reasons.append(reason)

    return reasons


def reasons_to_explanations(
    reasons: list[str],
    *,
    source: str = "legacy",
    weight: int = 0,
) -> list[Explanation]:
    return [
        make_explanation(source=source, message=reason, weight=weight)
        for reason in reasons
        if normalize_explanation_text(reason)
    ]


def total_explanation_weight(explanations: list[Explanation]) -> int:
    return sum(explanation.weight for explanation in explanations)


def group_explanations_by_source(
    explanations: list[Explanation],
) -> dict[str, list[Explanation]]:
    grouped: dict[str, list[Explanation]] = {}

    for explanation in explanations:
        grouped.setdefault(explanation.source, []).append(explanation)

    return grouped
