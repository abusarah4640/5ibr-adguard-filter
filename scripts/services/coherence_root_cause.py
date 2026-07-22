"""Root-cause attribution for cross-field coherence failures.

This module is diagnostic-only. It never modifies Analyzer output,
resolver decisions, confidence, recommendations, or production data.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from scripts.services.semantic_filter_mapping import (
    normalize_mapping_value,
)


ROOT_CAUSES = {
    "legacy-mapping-leakage",
    "direct-evidence-conflict",
    "category-derived-conflict",
    "possible-taxonomy-dimension-collision",
    "ambiguous-resolution",
    "unresolved-evidence",
    "cross-field-incoherence",
}


PLATFORM_FILTERS = {
    "mobile",
    "smart tv",
    "gaming",
    "streaming",
}

BEHAVIORAL_CATEGORIES = {
    "ads",
    "telemetry",
    "privacy",
    "crash reporting",
    "connectivity",
}


@dataclass(frozen=True)
class RootCauseAttribution:
    domain: str
    category: str
    actual_filter: str
    expected_filter: str
    root_cause: str
    severity: str
    filter_sources: tuple[str, ...] = field(
        default_factory=tuple
    )
    filter_score: int = 0
    conflict: bool = False
    ambiguous: bool = False
    requires_review: bool = True
    reasons: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.root_cause not in ROOT_CAUSES:
            raise ValueError(
                f"unsupported root cause: {self.root_cause}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "category": self.category,
            "actual_filter": self.actual_filter,
            "expected_filter": self.expected_filter,
            "root_cause": self.root_cause,
            "severity": self.severity,
            "filter_sources": list(
                self.filter_sources
            ),
            "filter_score": self.filter_score,
            "conflict": self.conflict,
            "ambiguous": self.ambiguous,
            "requires_review": self.requires_review,
            "reasons": list(self.reasons),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RootCauseSummary:
    domains_inspected: int
    domains_attributed: int
    causes: dict[str, int]
    severities: dict[str, int]
    attributions: tuple[RootCauseAttribution, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "domains_inspected": self.domains_inspected,
            "domains_attributed": self.domains_attributed,
            "causes": dict(self.causes),
            "severities": dict(self.severities),
            "attributions": [
                attribution.to_dict()
                for attribution in self.attributions
            ],
        }


def normalize_domain(value: object) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .strip(".")
    )


def normalize_sources(
    value: object,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()

    return tuple(
        sorted(
            {
                str(item).strip().lower()
                for item in value
                if str(item).strip()
            }
        )
    )


def load_json_object(
    path: Path,
) -> dict[str, Any]:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"expected JSON object: {path}"
        )

    return data


def load_json_list(
    path: Path,
) -> list[dict[str, Any]]:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, list):
        raise ValueError(
            f"expected JSON list: {path}"
        )

    return [
        item
        for item in data
        if isinstance(item, dict)
    ]


def index_comparisons(
    comparisons: Iterable[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        normalize_domain(
            comparison.get("domain")
        ): comparison
        for comparison in comparisons
        if normalize_domain(
            comparison.get("domain")
        )
    }


def legacy_filter_for_category(
    category: str,
    configured_map: dict[str, str],
) -> str:
    normalized_category = normalize_mapping_value(
        category
    )

    for key, value in configured_map.items():
        if (
            normalize_mapping_value(str(key))
            == normalized_category
        ):
            return str(value or "").strip()

    return ""


def is_taxonomy_dimension_collision(
    category: str,
    actual_filter: str,
) -> bool:
    normalized_category = normalize_mapping_value(
        category
    )

    normalized_filter = normalize_mapping_value(
        actual_filter
    )

    return (
        normalized_category
        in BEHAVIORAL_CATEGORIES
        and normalized_filter
        in PLATFORM_FILTERS
    )


def determine_severity(
    *,
    root_cause: str,
    conflict: bool,
    ambiguous: bool,
) -> str:
    if ambiguous:
        return "critical"

    if root_cause in {
        "direct-evidence-conflict",
        "possible-taxonomy-dimension-collision",
    } and conflict:
        return "high"

    if root_cause in {
        "legacy-mapping-leakage",
        "category-derived-conflict",
        "cross-field-incoherence",
    }:
        return "medium"

    if root_cause == "unresolved-evidence":
        return "low"

    return "high" if conflict else "medium"


def attribute_root_cause(
    coherence: dict[str, Any],
    *,
    comparison: dict[str, Any] | None = None,
    configured_filter_map: dict[str, str] | None = None,
) -> RootCauseAttribution:
    """Attribute one coherence assessment to a probable cause."""

    configured_map = configured_filter_map or {}

    domain = normalize_domain(
        coherence.get("domain")
    )

    category = str(
        coherence.get("category", "")
        or ""
    ).strip()

    actual_filter = str(
        coherence.get("filter", "")
        or ""
    ).strip()

    expected_filter = str(
        coherence.get(
            "expected_filter",
            "",
        )
        or ""
    ).strip()

    status = str(
        coherence.get("status", "")
        or ""
    ).strip().lower()

    conflict = bool(
        coherence.get(
            "category_conflict",
            False,
        )
        or coherence.get(
            "filter_conflict",
            False,
        )
    )

    ambiguous = bool(
        coherence.get(
            "category_ambiguous",
            False,
        )
        or coherence.get(
            "filter_ambiguous",
            False,
        )
    )

    fields = (
        comparison.get("fields", {})
        if isinstance(comparison, dict)
        else {}
    )

    if not isinstance(fields, dict):
        fields = {}

    filter_field = fields.get("filter", {})

    if not isinstance(filter_field, dict):
        filter_field = {}

    filter_sources = normalize_sources(
        filter_field.get(
            "preview_sources",
            [],
        )
    )

    filter_score = int(
        filter_field.get(
            "preview_score",
            0,
        )
        or 0
    )

    legacy_filter = legacy_filter_for_category(
        category,
        configured_map,
    )

    reasons: list[str] = []

    if status == "unresolved":
        root_cause = "unresolved-evidence"
        reasons.append(
            "category or filter was not resolved"
        )

    elif ambiguous:
        root_cause = "ambiguous-resolution"
        reasons.append(
            "resolver winner is tied or insufficiently separated"
        )

    elif (
        actual_filter
        and legacy_filter
        and normalize_mapping_value(
            actual_filter
        )
        == normalize_mapping_value(
            legacy_filter
        )
        and normalize_mapping_value(
            legacy_filter
        )
        != normalize_mapping_value(
            expected_filter
        )
        and set(filter_sources).issubset(
            {"rule"}
        )
    ):
        root_cause = "legacy-mapping-leakage"
        reasons.append(
            "winning filter matches legacy analyzer mapping"
        )
        reasons.append(
            "winning evidence is rule-derived"
        )

    elif is_taxonomy_dimension_collision(
        category,
        actual_filter,
    ):
        root_cause = (
            "possible-taxonomy-dimension-collision"
        )
        reasons.append(
            "behavioral category is paired with a platform-oriented filter"
        )

    elif any(
        source in {
            "knowledge",
            "database",
        }
        for source in filter_sources
    ):
        root_cause = "direct-evidence-conflict"
        reasons.append(
            "incoherent filter is supported by direct knowledge or database evidence"
        )

    elif filter_sources == ("rule",):
        root_cause = "category-derived-conflict"
        reasons.append(
            "incoherent filter is supported only by rule evidence"
        )

    else:
        root_cause = "cross-field-incoherence"
        reasons.append(
            "category and filter disagree without a more specific attribution"
        )

    if conflict:
        reasons.append(
            "competing evidence is present"
        )

    if ambiguous:
        reasons.append(
            "resolution is ambiguous"
        )

    severity = determine_severity(
        root_cause=root_cause,
        conflict=conflict,
        ambiguous=ambiguous,
    )

    return RootCauseAttribution(
        domain=domain,
        category=category,
        actual_filter=actual_filter,
        expected_filter=expected_filter,
        root_cause=root_cause,
        severity=severity,
        filter_sources=filter_sources,
        filter_score=filter_score,
        conflict=conflict,
        ambiguous=ambiguous,
        requires_review=bool(
            coherence.get(
                "requires_review",
                True,
            )
        ),
        reasons=tuple(reasons),
        metadata={
            "coherence_status": status,
            "legacy_filter": legacy_filter,
        },
    )


def attribute_root_causes(
    coherence_assessments: Iterable[
        dict[str, Any]
    ],
    *,
    comparisons: Iterable[
        dict[str, Any]
    ] = (),
    configured_filter_map: dict[
        str,
        str
    ] | None = None,
    incoherent_only: bool = True,
) -> RootCauseSummary:
    items = tuple(coherence_assessments)

    comparison_index = index_comparisons(
        comparisons
    )

    selected = [
        item
        for item in items
        if (
            str(
                item.get("status", "")
                or ""
            ).strip().lower()
            == "incoherent"
            if incoherent_only
            else True
        )
    ]

    attributions = tuple(
        attribute_root_cause(
            item,
            comparison=comparison_index.get(
                normalize_domain(
                    item.get("domain")
                )
            ),
            configured_filter_map=(
                configured_filter_map
            ),
        )
        for item in selected
    )

    cause_counts = Counter(
        item.root_cause
        for item in attributions
    )

    severity_counts = Counter(
        item.severity
        for item in attributions
    )

    return RootCauseSummary(
        domains_inspected=len(selected),
        domains_attributed=len(
            attributions
        ),
        causes=dict(cause_counts),
        severities=dict(
            severity_counts
        ),
        attributions=attributions,
    )


def build_root_cause_report(
    summary: RootCauseSummary,
) -> str:
    lines = [
        "5ibr Coherence Root-Cause Attribution",
        "=====================================",
        "",
        (
            "Domains inspected   : "
            f"{summary.domains_inspected}"
        ),
        (
            "Domains attributed  : "
            f"{summary.domains_attributed}"
        ),
        "",
        "Root causes:",
    ]

    if summary.causes:
        for cause, count in sorted(
            summary.causes.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        ):
            lines.append(
                f"  {cause:<40}: {count}"
            )
    else:
        lines.append("  None")

    lines.extend(
        [
            "",
            "Severity:",
        ]
    )

    if summary.severities:
        for severity, count in sorted(
            summary.severities.items()
        ):
            lines.append(
                f"  {severity:<12}: {count}"
            )
    else:
        lines.append("  None")

    lines.extend(
        [
            "",
            "Domain attribution:",
            "",
        ]
    )

    if not summary.attributions:
        lines.append("  None")
        return "\n".join(lines)

    for item in summary.attributions:
        lines.append(
            f"  {item.domain}"
        )
        lines.append(
            f"    category        : "
            f"{item.category or 'Unresolved'}"
        )
        lines.append(
            f"    actual filter   : "
            f"{item.actual_filter or 'Unresolved'}"
        )
        lines.append(
            f"    expected filter : "
            f"{item.expected_filter or 'Unmapped'}"
        )
        lines.append(
            f"    root cause      : "
            f"{item.root_cause}"
        )
        lines.append(
            f"    severity        : "
            f"{item.severity}"
        )
        lines.append(
            f"    sources         : "
            f"{','.join(item.filter_sources) or '-'}"
        )
        lines.append(
            f"    score           : "
            f"{item.filter_score}"
        )
        lines.append(
            f"    conflict        : "
            f"{item.conflict}"
        )
        lines.append(
            f"    ambiguous       : "
            f"{item.ambiguous}"
        )

        for reason in item.reasons:
            lines.append(
                f"    reason          : "
                f"{reason}"
            )

        lines.append("")

    return "\n".join(lines).rstrip()
