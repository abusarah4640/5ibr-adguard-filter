"""Aggregate and report Shadow Comparison results.

This module is evaluation-only. It does not modify Analyzer decisions,
confidence scores, recommendations, or production behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from scripts.services.shadow_comparison_service import (
    SUPPORTED_FIELDS,
    ShadowComparison,
)


@dataclass(frozen=True)
class ShadowFieldStatistics:
    """Aggregate comparison statistics for one field."""

    field: str
    matches: int = 0
    differences: int = 0
    unresolved: int = 0

    @property
    def compared(self) -> int:
        return self.matches + self.differences

    @property
    def total(self) -> int:
        return (
            self.matches
            + self.differences
            + self.unresolved
        )

    @property
    def agreement_rate(self) -> float:
        if self.compared == 0:
            return 0.0

        return (
            self.matches
            / self.compared
            * 100.0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "matches": self.matches,
            "differences": self.differences,
            "unresolved": self.unresolved,
            "compared": self.compared,
            "total": self.total,
            "agreement_rate": round(
                self.agreement_rate,
                2,
            ),
        }


@dataclass(frozen=True)
class ShadowEvaluationSummary:
    """Aggregate evaluation summary for shadow comparisons."""

    domains_compared: int
    full_matches: int
    partial_matches: int
    different_decisions: int
    preview_conflicts: int
    preview_ambiguities: int
    fields: dict[str, ShadowFieldStatistics]
    comparisons: tuple[ShadowComparison, ...] = field(
        default_factory=tuple
    )

    @property
    def full_match_rate(self) -> float:
        if self.domains_compared == 0:
            return 0.0

        return (
            self.full_matches
            / self.domains_compared
            * 100.0
        )

    @property
    def different_rate(self) -> float:
        if self.domains_compared == 0:
            return 0.0

        return (
            self.different_decisions
            / self.domains_compared
            * 100.0
        )

    @property
    def unresolved_totals(self) -> dict[str, int]:
        return {
            field_name: stats.unresolved
            for field_name, stats
            in self.fields.items()
        }

    @property
    def different_comparisons(
        self,
    ) -> tuple[ShadowComparison, ...]:
        return tuple(
            comparison
            for comparison in self.comparisons
            if comparison.overall_status
            == "different"
        )

    @property
    def partial_comparisons(
        self,
    ) -> tuple[ShadowComparison, ...]:
        return tuple(
            comparison
            for comparison in self.comparisons
            if comparison.overall_status
            == "partial"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "domains_compared": self.domains_compared,
            "full_matches": self.full_matches,
            "partial_matches": self.partial_matches,
            "different_decisions": (
                self.different_decisions
            ),
            "full_match_rate": round(
                self.full_match_rate,
                2,
            ),
            "different_rate": round(
                self.different_rate,
                2,
            ),
            "preview_conflicts": (
                self.preview_conflicts
            ),
            "preview_ambiguities": (
                self.preview_ambiguities
            ),
            "unresolved_totals": (
                self.unresolved_totals
            ),
            "fields": {
                field_name: stats.to_dict()
                for field_name, stats
                in self.fields.items()
            },
        }


def evaluate_shadow_comparisons(
    comparisons: Iterable[ShadowComparison],
) -> ShadowEvaluationSummary:
    """Aggregate multiple ShadowComparison objects."""

    items = tuple(comparisons)

    full_matches = sum(
        comparison.overall_status == "match"
        for comparison in items
    )

    partial_matches = sum(
        comparison.overall_status == "partial"
        for comparison in items
    )

    different_decisions = sum(
        comparison.overall_status == "different"
        for comparison in items
    )

    preview_conflicts = sum(
        comparison.preview_has_conflicts
        for comparison in items
    )

    preview_ambiguities = sum(
        comparison.preview_has_ambiguity
        for comparison in items
    )

    field_statistics: dict[
        str,
        ShadowFieldStatistics,
    ] = {}

    for field_name in SUPPORTED_FIELDS:
        matches = 0
        differences = 0
        unresolved = 0

        for comparison in items:
            result = comparison.get(field_name)

            if result is None:
                unresolved += 1
                continue

            if result.is_match:
                matches += 1
            elif result.is_different:
                differences += 1
            else:
                unresolved += 1

        field_statistics[field_name] = (
            ShadowFieldStatistics(
                field=field_name,
                matches=matches,
                differences=differences,
                unresolved=unresolved,
            )
        )

    return ShadowEvaluationSummary(
        domains_compared=len(items),
        full_matches=full_matches,
        partial_matches=partial_matches,
        different_decisions=different_decisions,
        preview_conflicts=preview_conflicts,
        preview_ambiguities=preview_ambiguities,
        fields=field_statistics,
        comparisons=items,
    )


def build_shadow_evaluation_report(
    summary: ShadowEvaluationSummary,
    *,
    top_differences: int = 20,
) -> str:
    """Build a human-readable Shadow Evaluation report."""

    lines = [
        "5ibr Shadow Evaluation Report",
        "=============================",
        "",
        (
            "Domains compared        : "
            f"{summary.domains_compared}"
        ),
        "",
        "Overall:",
        (
            "  Full matches          : "
            f"{summary.full_matches}"
        ),
        (
            "  Partial matches       : "
            f"{summary.partial_matches}"
        ),
        (
            "  Different decisions   : "
            f"{summary.different_decisions}"
        ),
        "",
        "Agreement:",
    ]

    for field_name in SUPPORTED_FIELDS:
        stats = summary.fields[field_name]

        lines.append(
            f"  {field_name.title():<20}: "
            f"{stats.agreement_rate:.2f}% "
            f"({stats.matches}/{stats.compared})"
        )

    lines.extend(
        [
            "",
            "Preview diagnostics:",
            (
                "  Conflicts             : "
                f"{summary.preview_conflicts}"
            ),
            (
                "  Ambiguities           : "
                f"{summary.preview_ambiguities}"
            ),
            "",
            "Unresolved fields:",
        ]
    )

    for field_name in SUPPORTED_FIELDS:
        stats = summary.fields[field_name]

        lines.append(
            f"  {field_name.title():<20}: "
            f"{stats.unresolved}"
        )

    differences = (
        summary.different_comparisons[
            :top_differences
        ]
    )

    lines.extend(
        [
            "",
            "Top differences:",
            "",
        ]
    )

    if not differences:
        lines.append("  None")
        return "\n".join(lines)

    for comparison in differences:
        lines.append(
            f"  {comparison.domain}"
        )

        for field_name in (
            comparison.different_fields
        ):
            result = comparison.get(
                field_name
            )

            if result is None:
                continue

            lines.append(
                f"    {field_name:<10}: "
                f"{result.current_value or 'Unknown'} "
                f"-> "
                f"{result.preview_value or 'Unresolved'}"
            )

            lines.append(
                f"               "
                f"score={result.preview_score}, "
                f"sources="
                f"{','.join(result.preview_sources) or '-'}, "
                f"conflict="
                f"{result.preview_has_conflict}, "
                f"ambiguous="
                f"{result.preview_ambiguous}"
            )

        lines.append("")

    return "\n".join(lines).rstrip()
