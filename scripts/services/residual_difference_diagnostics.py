"""Diagnose residual Analyzer vs Resolver differences.

This module is diagnostic-only. It does not modify Analyzer output,
resolver decisions, confidence, recommendations, or production data.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.services.semantic_filter_mapping import (
    semantic_filter_for_category,
)


@dataclass(frozen=True)
class DiagnosticFinding:
    code: str
    severity: str
    message: str
    field_name: str = ""
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "field": self.field_name,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class DomainDiagnostic:
    domain: str
    overall_status: str
    findings: tuple[DiagnosticFinding, ...]

    @property
    def requires_review(self) -> bool:
        return any(
            finding.severity in {
                "warning",
                "critical",
            }
            for finding in self.findings
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "overall_status": self.overall_status,
            "requires_review": self.requires_review,
            "findings": [
                finding.to_dict()
                for finding in self.findings
            ],
        }


@dataclass(frozen=True)
class ResidualDiagnosticSummary:
    domains_inspected: int
    domains_requiring_review: int
    findings_by_code: dict[str, int]
    findings_by_severity: dict[str, int]
    diagnostics: tuple[DomainDiagnostic, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "domains_inspected": self.domains_inspected,
            "domains_requiring_review": (
                self.domains_requiring_review
            ),
            "findings_by_code": dict(
                self.findings_by_code
            ),
            "findings_by_severity": dict(
                self.findings_by_severity
            ),
            "diagnostics": [
                diagnostic.to_dict()
                for diagnostic in self.diagnostics
            ],
        }


def normalize_value(value: object) -> str:
    return str(value or "").strip()


def expected_filter_for_category(
    category: str,
    filter_map: dict[str, str] | None = None,
) -> str:
    """Return the canonical semantic filter for a category.

    filter_map remains accepted for API compatibility, but legacy
    Analyzer mappings are not used as semantic truth.
    """

    return semantic_filter_for_category(category)


def diagnose_comparison(
    comparison: dict[str, Any],
    *,
    filter_map: dict[str, str],
) -> DomainDiagnostic:
    """Diagnose one serialized ShadowComparison."""

    domain = normalize_value(
        comparison.get("domain")
    )

    overall_status = normalize_value(
        comparison.get("overall_status")
    ) or "unknown"

    fields = comparison.get("fields", {})

    if not isinstance(fields, dict):
        fields = {}

    findings: list[DiagnosticFinding] = []

    category = fields.get("category", {})
    filter_field = fields.get("filter", {})

    preview_category = normalize_value(
        category.get("preview_value")
        if isinstance(category, dict)
        else ""
    )

    preview_filter = normalize_value(
        filter_field.get("preview_value")
        if isinstance(filter_field, dict)
        else ""
    )

    current_category = normalize_value(
        category.get("current_value")
        if isinstance(category, dict)
        else ""
    )

    current_filter = normalize_value(
        filter_field.get("current_value")
        if isinstance(filter_field, dict)
        else ""
    )

    expected_preview_filter = (
        expected_filter_for_category(
            preview_category,
            filter_map,
        )
    )

    if (
        preview_category
        and preview_filter
        and expected_preview_filter
        and preview_filter.casefold()
        != expected_preview_filter.casefold()
    ):
        findings.append(
            DiagnosticFinding(
                code="preview-category-filter-incoherent",
                severity="critical",
                field_name="filter",
                message=(
                    "Resolver preview filter does not match "
                    "the configured filter for its preview category."
                ),
                metadata={
                    "preview_category": preview_category,
                    "preview_filter": preview_filter,
                    "expected_filter": (
                        expected_preview_filter
                    ),
                },
            )
        )

    expected_current_filter = (
        expected_filter_for_category(
            current_category,
            filter_map,
        )
    )

    if (
        current_category
        and current_filter
        and expected_current_filter
        and current_filter.casefold()
        != expected_current_filter.casefold()
    ):
        findings.append(
            DiagnosticFinding(
                code="current-category-filter-incoherent",
                severity="warning",
                field_name="filter",
                message=(
                    "Current Analyzer filter does not match "
                    "the configured filter for its category."
                ),
                metadata={
                    "current_category": current_category,
                    "current_filter": current_filter,
                    "expected_filter": (
                        expected_current_filter
                    ),
                },
            )
        )

    for field_name, field_data in fields.items():
        if not isinstance(field_data, dict):
            continue

        status = normalize_value(
            field_data.get("status")
        )

        if status == "different":
            findings.append(
                DiagnosticFinding(
                    code="shadow-field-difference",
                    severity="warning",
                    field_name=field_name,
                    message=(
                        "Current Analyzer and Resolver preview "
                        "selected different values."
                    ),
                    metadata={
                        "current": normalize_value(
                            field_data.get(
                                "current_value"
                            )
                        ),
                        "preview": normalize_value(
                            field_data.get(
                                "preview_value"
                            )
                        ),
                        "preview_score": int(
                            field_data.get(
                                "preview_score",
                                0,
                            )
                            or 0
                        ),
                        "preview_sources": list(
                            field_data.get(
                                "preview_sources",
                                [],
                            )
                            or []
                        ),
                    },
                )
            )

        if bool(
            field_data.get(
                "preview_ambiguous",
                False,
            )
        ):
            findings.append(
                DiagnosticFinding(
                    code="preview-ambiguous",
                    severity="critical",
                    field_name=field_name,
                    message=(
                        "Resolver preview could not clearly "
                        "separate the winning value from a competitor."
                    ),
                )
            )

        if bool(
            field_data.get(
                "preview_has_conflict",
                False,
            )
        ):
            findings.append(
                DiagnosticFinding(
                    code="preview-conflict",
                    severity="info",
                    field_name=field_name,
                    message=(
                        "Resolver preview contains competing "
                        "evidence for this field."
                    ),
                )
            )

        if status == "unresolved":
            findings.append(
                DiagnosticFinding(
                    code="preview-unresolved",
                    severity="info",
                    field_name=field_name,
                    message=(
                        "Resolver preview did not resolve this field."
                    ),
                )
            )

    return DomainDiagnostic(
        domain=domain,
        overall_status=overall_status,
        findings=tuple(findings),
    )


def diagnose_comparisons(
    comparisons: list[dict[str, Any]],
    *,
    filter_map: dict[str, str],
    differences_only: bool = True,
) -> ResidualDiagnosticSummary:
    """Diagnose serialized ShadowComparison records."""

    selected = comparisons

    if differences_only:
        selected = [
            comparison
            for comparison in comparisons
            if normalize_value(
                comparison.get("overall_status")
            )
            == "different"
        ]

    diagnostics = tuple(
        diagnose_comparison(
            comparison,
            filter_map=filter_map,
        )
        for comparison in selected
    )

    code_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()

    for diagnostic in diagnostics:
        for finding in diagnostic.findings:
            code_counts[finding.code] += 1
            severity_counts[finding.severity] += 1

    return ResidualDiagnosticSummary(
        domains_inspected=len(diagnostics),
        domains_requiring_review=sum(
            diagnostic.requires_review
            for diagnostic in diagnostics
        ),
        findings_by_code=dict(code_counts),
        findings_by_severity=dict(
            severity_counts
        ),
        diagnostics=diagnostics,
    )


def load_comparisons(
    path: Path,
) -> list[dict[str, Any]]:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, list):
        raise ValueError(
            f"invalid comparisons file: {path}"
        )

    return [
        item
        for item in data
        if isinstance(item, dict)
    ]


def load_filter_map(
    config_path: Path,
) -> dict[str, str]:
    data = json.loads(
        config_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"invalid analyzer config: {config_path}"
        )

    filter_map = data.get("filter_map", {})

    if not isinstance(filter_map, dict):
        raise ValueError(
            "analyzer filter_map must be an object"
        )

    return {
        str(key): str(value)
        for key, value in filter_map.items()
    }


def build_residual_diagnostic_report(
    summary: ResidualDiagnosticSummary,
) -> str:
    lines = [
        "5ibr Residual Difference Diagnostics",
        "====================================",
        "",
        (
            "Domains inspected         : "
            f"{summary.domains_inspected}"
        ),
        (
            "Domains requiring review  : "
            f"{summary.domains_requiring_review}"
        ),
        "",
        "Findings by severity:",
    ]

    if summary.findings_by_severity:
        for severity, count in sorted(
            summary.findings_by_severity.items()
        ):
            lines.append(
                f"  {severity:<12}: {count}"
            )
    else:
        lines.append("  None")

    lines.extend(
        [
            "",
            "Findings by code:",
        ]
    )

    if summary.findings_by_code:
        for code, count in sorted(
            summary.findings_by_code.items()
        ):
            lines.append(
                f"  {code:<38}: {count}"
            )
    else:
        lines.append("  None")

    lines.extend(
        [
            "",
            "Domain diagnostics:",
            "",
        ]
    )

    if not summary.diagnostics:
        lines.append("  None")
        return "\n".join(lines)

    for diagnostic in summary.diagnostics:
        lines.append(
            f"  {diagnostic.domain}"
        )
        lines.append(
            f"    overall status : "
            f"{diagnostic.overall_status}"
        )
        lines.append(
            f"    requires review: "
            f"{diagnostic.requires_review}"
        )

        for finding in diagnostic.findings:
            lines.append(
                f"    [{finding.severity.upper()}] "
                f"{finding.code}"
            )
            lines.append(
                f"      {finding.message}"
            )

            for key, value in (
                finding.metadata.items()
            ):
                lines.append(
                    f"      {key}: {value}"
                )

        lines.append("")

    return "\n".join(lines).rstrip()
