"""Cross-field coherence guardrails for resolver preview results.

This module is governance-only. It never changes the selected category,
filter, Analyzer output, confidence, or recommendation.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable

from scripts.services.semantic_filter_mapping import (
    normalize_mapping_value,
    semantic_filter_for_category,
)
from scripts.services.unified_evidence_resolver import (
    UnifiedEvidenceResolution,
)


COHERENCE_STATUSES = {
    "coherent",
    "incoherent",
    "unresolved",
    "unmapped",
}


@dataclass(frozen=True)
class CoherenceAssessment:
    """Semantic relationship between resolved category and filter."""

    domain: str
    status: str
    category: str
    filter_value: str
    expected_filter: str
    category_conflict: bool = False
    filter_conflict: bool = False
    category_ambiguous: bool = False
    filter_ambiguous: bool = False
    requires_review: bool = False
    reasons: tuple[str, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        if self.status not in COHERENCE_STATUSES:
            raise ValueError(
                f"unsupported coherence status: {self.status}"
            )

    @property
    def is_coherent(self) -> bool:
        return self.status == "coherent"

    @property
    def is_incoherent(self) -> bool:
        return self.status == "incoherent"

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "status": self.status,
            "category": self.category,
            "filter": self.filter_value,
            "expected_filter": self.expected_filter,
            "category_conflict": self.category_conflict,
            "filter_conflict": self.filter_conflict,
            "category_ambiguous": self.category_ambiguous,
            "filter_ambiguous": self.filter_ambiguous,
            "requires_review": self.requires_review,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class CoherenceSummary:
    """Aggregate statistics for coherence assessments."""

    total: int
    statuses: dict[str, int]
    requiring_review: int
    ambiguous: int
    with_conflicts: int
    assessments: tuple[CoherenceAssessment, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "statuses": dict(self.statuses),
            "requiring_review": self.requiring_review,
            "ambiguous": self.ambiguous,
            "with_conflicts": self.with_conflicts,
            "assessments": [
                assessment.to_dict()
                for assessment in self.assessments
            ],
        }


def assess_preview_values(
    *,
    domain: str,
    category: str,
    filter_value: str,
    category_conflict: bool = False,
    filter_conflict: bool = False,
    category_ambiguous: bool = False,
    filter_ambiguous: bool = False,
) -> CoherenceAssessment:
    """Assess semantic coherence without changing either value."""

    normalized_category = (category or "").strip()
    normalized_filter = (filter_value or "").strip()

    reasons: list[str] = []

    if not normalized_category and not normalized_filter:
        return CoherenceAssessment(
            domain=domain,
            status="unresolved",
            category="",
            filter_value="",
            expected_filter="",
            requires_review=False,
            reasons=(
                "category and filter are both unresolved",
            ),
        )

    if not normalized_category or not normalized_filter:
        missing = (
            "category"
            if not normalized_category
            else "filter"
        )

        return CoherenceAssessment(
            domain=domain,
            status="unresolved",
            category=normalized_category,
            filter_value=normalized_filter,
            expected_filter=(
                semantic_filter_for_category(
                    normalized_category
                )
                if normalized_category
                else ""
            ),
            category_conflict=category_conflict,
            filter_conflict=filter_conflict,
            category_ambiguous=category_ambiguous,
            filter_ambiguous=filter_ambiguous,
            requires_review=True,
            reasons=(
                f"{missing} is unresolved",
            ),
        )

    expected_filter = semantic_filter_for_category(
        normalized_category
    )

    if not expected_filter:
        return CoherenceAssessment(
            domain=domain,
            status="unmapped",
            category=normalized_category,
            filter_value=normalized_filter,
            expected_filter="",
            category_conflict=category_conflict,
            filter_conflict=filter_conflict,
            category_ambiguous=category_ambiguous,
            filter_ambiguous=filter_ambiguous,
            requires_review=True,
            reasons=(
                "category has no semantic filter mapping",
            ),
        )

    coherent = (
        normalize_mapping_value(normalized_filter)
        == normalize_mapping_value(expected_filter)
    )

    if coherent:
        reasons.append(
            "resolved filter matches the semantic category mapping"
        )
    else:
        reasons.append(
            "resolved filter conflicts with the semantic category mapping"
        )

    if category_conflict:
        reasons.append(
            "category contains competing evidence"
        )

    if filter_conflict:
        reasons.append(
            "filter contains competing evidence"
        )

    if category_ambiguous:
        reasons.append(
            "category resolution is ambiguous"
        )

    if filter_ambiguous:
        reasons.append(
            "filter resolution is ambiguous"
        )

    ambiguous = (
        category_ambiguous
        or filter_ambiguous
    )

    return CoherenceAssessment(
        domain=domain,
        status=(
            "coherent"
            if coherent
            else "incoherent"
        ),
        category=normalized_category,
        filter_value=normalized_filter,
        expected_filter=expected_filter,
        category_conflict=category_conflict,
        filter_conflict=filter_conflict,
        category_ambiguous=category_ambiguous,
        filter_ambiguous=filter_ambiguous,
        requires_review=(
            not coherent
            or ambiguous
        ),
        reasons=tuple(reasons),
    )


def assess_resolution_coherence(
    resolution: UnifiedEvidenceResolution,
) -> CoherenceAssessment:
    """Assess category/filter coherence from a resolver result."""

    category = resolution.get("category")
    filter_result = resolution.get("filter")

    return assess_preview_values(
        domain=resolution.domain,
        category=(
            category.value
            if category is not None
            else ""
        ),
        filter_value=(
            filter_result.value
            if filter_result is not None
            else ""
        ),
        category_conflict=(
            category.has_conflict
            if category is not None
            else False
        ),
        filter_conflict=(
            filter_result.has_conflict
            if filter_result is not None
            else False
        ),
        category_ambiguous=(
            category.ambiguous
            if category is not None
            else False
        ),
        filter_ambiguous=(
            filter_result.ambiguous
            if filter_result is not None
            else False
        ),
    )


def assess_serialized_comparison(
    comparison: dict[str, Any],
) -> CoherenceAssessment:
    """Assess a serialized ShadowComparison record."""

    fields = comparison.get("fields", {})

    if not isinstance(fields, dict):
        fields = {}

    category = fields.get("category", {})
    filter_field = fields.get("filter", {})

    if not isinstance(category, dict):
        category = {}

    if not isinstance(filter_field, dict):
        filter_field = {}

    return assess_preview_values(
        domain=str(
            comparison.get("domain", "")
        ).strip(),
        category=str(
            category.get(
                "preview_value",
                "",
            )
            or ""
        ).strip(),
        filter_value=str(
            filter_field.get(
                "preview_value",
                "",
            )
            or ""
        ).strip(),
        category_conflict=bool(
            category.get(
                "preview_has_conflict",
                False,
            )
        ),
        filter_conflict=bool(
            filter_field.get(
                "preview_has_conflict",
                False,
            )
        ),
        category_ambiguous=bool(
            category.get(
                "preview_ambiguous",
                False,
            )
        ),
        filter_ambiguous=bool(
            filter_field.get(
                "preview_ambiguous",
                False,
            )
        ),
    )


def summarize_coherence(
    assessments: Iterable[CoherenceAssessment],
) -> CoherenceSummary:
    items = tuple(assessments)

    status_counts: Counter[str] = Counter(
        item.status
        for item in items
    )

    return CoherenceSummary(
        total=len(items),
        statuses={
            status: status_counts.get(
                status,
                0,
            )
            for status in sorted(
                COHERENCE_STATUSES
            )
        },
        requiring_review=sum(
            item.requires_review
            for item in items
        ),
        ambiguous=sum(
            (
                item.category_ambiguous
                or item.filter_ambiguous
            )
            for item in items
        ),
        with_conflicts=sum(
            (
                item.category_conflict
                or item.filter_conflict
            )
            for item in items
        ),
        assessments=items,
    )


def build_coherence_report(
    summary: CoherenceSummary,
    *,
    review_only: bool = False,
) -> str:
    lines = [
        "5ibr Cross-Field Coherence Report",
        "=================================",
        "",
        f"Assessments           : {summary.total}",
        f"Requires review       : {summary.requiring_review}",
        f"With conflicts        : {summary.with_conflicts}",
        f"Ambiguous             : {summary.ambiguous}",
        "",
        "Statuses:",
    ]

    for status, count in summary.statuses.items():
        lines.append(
            f"  {status:<12}: {count}"
        )

    lines.extend(
        [
            "",
            "Domain assessments:",
            "",
        ]
    )

    selected = [
        item
        for item in summary.assessments
        if (
            item.requires_review
            if review_only
            else True
        )
    ]

    if not selected:
        lines.append("  None")
        return "\n".join(lines)

    for item in selected:
        lines.append(
            f"  {item.domain}"
        )
        lines.append(
            f"    status          : {item.status}"
        )
        lines.append(
            f"    category        : {item.category or 'Unresolved'}"
        )
        lines.append(
            f"    filter          : {item.filter_value or 'Unresolved'}"
        )
        lines.append(
            f"    expected filter : {item.expected_filter or 'Unmapped'}"
        )
        lines.append(
            f"    requires review : {item.requires_review}"
        )
        lines.append(
            f"    conflict        : "
            f"{item.category_conflict or item.filter_conflict}"
        )
        lines.append(
            f"    ambiguous       : "
            f"{item.category_ambiguous or item.filter_ambiguous}"
        )

        for reason in item.reasons:
            lines.append(
                f"    reason          : {reason}"
            )

        lines.append("")

    return "\n".join(lines).rstrip()
