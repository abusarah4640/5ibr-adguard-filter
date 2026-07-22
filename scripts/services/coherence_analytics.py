"""Analytics for cross-field category/filter coherence assessments.

This module is reporting-only. It does not modify Analyzer output,
resolver decisions, confidence, recommendations, or production data.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from scripts.services.semantic_filter_mapping import (
    normalize_mapping_value,
)


@dataclass(frozen=True)
class CoherencePattern:
    """Aggregated category/filter coherence pattern."""

    category: str
    actual_filter: str
    expected_filter: str
    status: str
    count: int
    total_seen: int
    conflicts: int
    ambiguities: int
    requiring_review: int
    domains: tuple[str, ...] = field(
        default_factory=tuple
    )

    @property
    def pattern_key(self) -> str:
        return (
            f"{self.category} -> "
            f"{self.actual_filter or 'unresolved'}"
        )

    @property
    def severity(self) -> str:
        """Return an objective diagnostic severity."""

        if (
            self.status == "incoherent"
            and self.conflicts > 0
            and self.ambiguities > 0
        ):
            return "critical"

        if (
            self.status == "incoherent"
            and self.conflicts > 0
        ):
            return "high"

        if self.status == "incoherent":
            return "medium"

        if self.ambiguities > 0:
            return "low"

        return "info"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern_key,
            "category": self.category,
            "actual_filter": self.actual_filter,
            "expected_filter": self.expected_filter,
            "status": self.status,
            "severity": self.severity,
            "count": self.count,
            "total_seen": self.total_seen,
            "conflicts": self.conflicts,
            "ambiguities": self.ambiguities,
            "requiring_review": self.requiring_review,
            "domains": list(self.domains),
        }


@dataclass(frozen=True)
class CoherenceAnalyticsSummary:
    """Aggregate analytics over coherence assessments."""

    assessments: int
    analyzed_patterns: int
    incoherent_assessments: int
    requiring_review: int
    total_seen: int
    patterns_by_status: dict[str, int]
    patterns_by_severity: dict[str, int]
    patterns: tuple[CoherencePattern, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessments": self.assessments,
            "analyzed_patterns": self.analyzed_patterns,
            "incoherent_assessments": (
                self.incoherent_assessments
            ),
            "requiring_review": self.requiring_review,
            "total_seen": self.total_seen,
            "patterns_by_status": dict(
                self.patterns_by_status
            ),
            "patterns_by_severity": dict(
                self.patterns_by_severity
            ),
            "patterns": [
                pattern.to_dict()
                for pattern in self.patterns
            ],
        }


def normalize_domain(value: object) -> str:
    return str(value or "").strip().lower().strip(".")


def load_seen_counts(
    suggestions_path: Path | None,
) -> dict[str, int]:
    """Load domain occurrence counts from suggestions JSON."""

    if suggestions_path is None:
        return {}

    data = json.loads(
        suggestions_path.read_text(
            encoding="utf-8"
        )
    )

    if isinstance(data, dict):
        rows = data.get("suggestions", [])
    else:
        rows = data

    if not isinstance(rows, list):
        raise ValueError(
            f"invalid suggestions file: {suggestions_path}"
        )

    counts: dict[str, int] = {}

    for row in rows:
        if not isinstance(row, dict):
            continue

        domain = normalize_domain(
            row.get("domain")
        )

        if not domain:
            continue

        counts[domain] = int(
            row.get("seen", 0)
            or 0
        )

    return counts


def load_coherence_assessments(
    path: Path,
) -> list[dict[str, Any]]:
    """Load serialized Stage 46 coherence assessments."""

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"invalid coherence report: {path}"
        )

    assessments = data.get("assessments", [])

    if not isinstance(assessments, list):
        raise ValueError(
            "coherence assessments must be a list"
        )

    return [
        item
        for item in assessments
        if isinstance(item, dict)
    ]


def _normalized_pattern_key(
    assessment: dict[str, Any],
) -> tuple[str, str, str, str]:
    category = str(
        assessment.get("category", "")
        or ""
    ).strip()

    actual_filter = str(
        assessment.get("filter", "")
        or ""
    ).strip()

    expected_filter = str(
        assessment.get("expected_filter", "")
        or ""
    ).strip()

    status = str(
        assessment.get("status", "unknown")
        or "unknown"
    ).strip().lower()

    return (
        normalize_mapping_value(category),
        normalize_mapping_value(actual_filter),
        normalize_mapping_value(expected_filter),
        status,
    )


def analyze_coherence_patterns(
    assessments: Iterable[dict[str, Any]],
    *,
    seen_counts: dict[str, int] | None = None,
    include_statuses: set[str] | None = None,
) -> CoherenceAnalyticsSummary:
    """Aggregate coherence assessments by semantic mismatch pattern."""

    items = tuple(assessments)
    effective_seen = seen_counts or {}

    selected_statuses = (
        include_statuses
        if include_statuses is not None
        else {
            "incoherent",
            "coherent",
            "unmapped",
        }
    )

    grouped: dict[
        tuple[str, str, str, str],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for assessment in items:
        status = str(
            assessment.get("status", "")
            or ""
        ).strip().lower()

        if status not in selected_statuses:
            continue

        grouped[
            _normalized_pattern_key(
                assessment
            )
        ].append(assessment)

    patterns: list[CoherencePattern] = []

    for (
        _normalized_category,
        _normalized_actual,
        _normalized_expected,
        status,
    ), group in grouped.items():
        first = group[0]

        category = str(
            first.get("category", "")
            or ""
        ).strip()

        actual_filter = str(
            first.get("filter", "")
            or ""
        ).strip()

        expected_filter = str(
            first.get("expected_filter", "")
            or ""
        ).strip()

        domains = tuple(
            sorted(
                {
                    normalize_domain(
                        item.get("domain")
                    )
                    for item in group
                    if normalize_domain(
                        item.get("domain")
                    )
                },
                key=lambda domain: (
                    -effective_seen.get(
                        domain,
                        0,
                    ),
                    domain,
                ),
            )
        )

        conflicts = sum(
            bool(
                item.get(
                    "category_conflict",
                    False,
                )
                or item.get(
                    "filter_conflict",
                    False,
                )
            )
            for item in group
        )

        ambiguities = sum(
            bool(
                item.get(
                    "category_ambiguous",
                    False,
                )
                or item.get(
                    "filter_ambiguous",
                    False,
                )
            )
            for item in group
        )

        requiring_review = sum(
            bool(
                item.get(
                    "requires_review",
                    False,
                )
            )
            for item in group
        )

        total_seen = sum(
            effective_seen.get(
                domain,
                0,
            )
            for domain in domains
        )

        patterns.append(
            CoherencePattern(
                category=category,
                actual_filter=actual_filter,
                expected_filter=expected_filter,
                status=status,
                count=len(group),
                total_seen=total_seen,
                conflicts=conflicts,
                ambiguities=ambiguities,
                requiring_review=requiring_review,
                domains=domains,
            )
        )

    patterns.sort(
        key=lambda pattern: (
            pattern.status != "incoherent",
            -pattern.count,
            -pattern.total_seen,
            pattern.pattern_key.casefold(),
        )
    )

    status_counts = Counter(
        pattern.status
        for pattern in patterns
    )

    severity_counts = Counter(
        pattern.severity
        for pattern in patterns
    )

    incoherent_assessments = sum(
        pattern.count
        for pattern in patterns
        if pattern.status == "incoherent"
    )

    requiring_review = sum(
        pattern.requiring_review
        for pattern in patterns
    )

    return CoherenceAnalyticsSummary(
        assessments=len(items),
        analyzed_patterns=len(patterns),
        incoherent_assessments=(
            incoherent_assessments
        ),
        requiring_review=requiring_review,
        total_seen=sum(
            pattern.total_seen
            for pattern in patterns
        ),
        patterns_by_status=dict(
            status_counts
        ),
        patterns_by_severity=dict(
            severity_counts
        ),
        patterns=tuple(patterns),
    )


def build_coherence_analytics_report(
    summary: CoherenceAnalyticsSummary,
    *,
    incoherent_only: bool = True,
    top_domains: int = 10,
) -> str:
    """Build a human-readable coherence analytics report."""

    lines = [
        "5ibr Cross-Field Coherence Analytics",
        "====================================",
        "",
        (
            "Assessments loaded      : "
            f"{summary.assessments}"
        ),
        (
            "Patterns analyzed       : "
            f"{summary.analyzed_patterns}"
        ),
        (
            "Incoherent assessments  : "
            f"{summary.incoherent_assessments}"
        ),
        (
            "Requiring review        : "
            f"{summary.requiring_review}"
        ),
        (
            "Total query occurrences : "
            f"{summary.total_seen}"
        ),
        "",
        "Patterns by severity:",
    ]

    if summary.patterns_by_severity:
        for severity, count in sorted(
            summary.patterns_by_severity.items()
        ):
            lines.append(
                f"  {severity:<10}: {count}"
            )
    else:
        lines.append("  None")

    lines.extend(
        [
            "",
            "Pattern details:",
            "",
        ]
    )

    selected = [
        pattern
        for pattern in summary.patterns
        if (
            pattern.status == "incoherent"
            if incoherent_only
            else True
        )
    ]

    if not selected:
        lines.append("  None")
        return "\n".join(lines)

    for pattern in selected:
        lines.append(
            f"  {pattern.pattern_key}"
        )
        lines.append(
            f"    status          : {pattern.status}"
        )
        lines.append(
            f"    severity        : {pattern.severity}"
        )
        lines.append(
            f"    expected filter : "
            f"{pattern.expected_filter or 'Unmapped'}"
        )
        lines.append(
            f"    count           : {pattern.count}"
        )
        lines.append(
            f"    total seen      : {pattern.total_seen}"
        )
        lines.append(
            f"    conflicts       : {pattern.conflicts}"
        )
        lines.append(
            f"    ambiguities     : {pattern.ambiguities}"
        )
        lines.append(
            f"    requires review : "
            f"{pattern.requiring_review}"
        )

        lines.append(
            "    top domains:"
        )

        for domain in pattern.domains[
            : max(top_domains, 0)
        ]:
            lines.append(
                f"      {effective_seen_label(domain, pattern, summary)}"
            )

        if not pattern.domains:
            lines.append("      None")

        lines.append("")

    return "\n".join(lines).rstrip()


def effective_seen_label(
    domain: str,
    pattern: CoherencePattern,
    summary: CoherenceAnalyticsSummary,
) -> str:
    """Return a stable domain label for reports.

    Per-domain seen counts are intentionally not stored in CoherencePattern.
    The aggregate total remains authoritative in JSON output.
    """

    del pattern, summary
    return domain
