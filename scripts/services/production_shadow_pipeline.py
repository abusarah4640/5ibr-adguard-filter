"""Run the unified evidence pipeline in production shadow mode."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.services.database_evidence_engine import (
    match_database_evidence,
)
from scripts.services.database_service import load_database
from scripts.services.knowledge_engine import first_domain_match
from scripts.services.rule_engine import (
    RuleMatch,
    match_category_rules,
    match_vendor_rules,
)
from scripts.services.shadow_comparison_service import (
    ShadowComparison,
    compare_analyzer_with_resolution,
)
from scripts.services.shadow_evaluation_service import (
    ShadowEvaluationSummary,
    build_shadow_evaluation_report,
    evaluate_shadow_comparisons,
)
from scripts.services.unified_evidence_collector import (
    collect_unified_evidence,
)
from scripts.services.unified_evidence_resolver import (
    resolve_unified_evidence,
)


DEFAULT_CONFIG_PATH = Path("config/analyzer.json")


@dataclass(frozen=True)
class ProductionShadowResult:
    summary: ShadowEvaluationSummary
    comparisons: tuple[ShadowComparison, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "comparisons": [
                comparison.to_dict()
                for comparison in self.comparisons
            ],
        }


def load_analyzer_config(
    path: Path = DEFAULT_CONFIG_PATH,
) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(
            f"invalid analyzer configuration: {path}"
        )

    return data


def load_suggestion_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        rows = data.get("suggestions", [])
    else:
        rows = data

    if not isinstance(rows, list):
        raise ValueError(
            f"invalid suggestions format: {path}"
        )

    return [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("domain", "")).strip()
    ]


def category_filter_matches(
    category_matches: list[RuleMatch],
    filter_map: dict[str, str],
) -> list[RuleMatch]:
    """Create filter evidence derived from matched categories."""

    matches: list[RuleMatch] = []

    for category_match in category_matches:
        filter_name = str(
            filter_map.get(category_match.value, "")
            or ""
        ).strip()

        if not filter_name:
            continue

        metadata = {
            **dict(category_match.metadata),
            "derived_from": "category",
            "derived_category": category_match.value,
        }

        matches.append(
            RuleMatch(
                rule_type="filter",
                value=filter_name,
                score=category_match.score,
                reason=(
                    "derived filter from matched category: "
                    f"{category_match.value} -> {filter_name}"
                ),
                metadata=metadata,
            )
        )

    return matches


def build_shadow_comparison(
    row: dict[str, Any],
    *,
    config: dict[str, Any],
    database_rows: list[dict],
) -> ShadowComparison:
    domain = str(row.get("domain", "")).strip().lower()

    vendor_matches = match_vendor_rules(
        domain,
        config.get("vendor_patterns", {}),
    )

    category_matches = match_category_rules(
        domain,
        config.get("category_keywords", {}),
    )

    filter_matches = category_filter_matches(
        category_matches,
        config.get("filter_map", {}),
    )

    knowledge_entry = first_domain_match(domain)

    database_evidence = match_database_evidence(
        domain,
        database_rows,
    )

    bundle = collect_unified_evidence(
        domain,
        rule_matches=[
            *vendor_matches,
            *category_matches,
            *filter_matches,
        ],
        knowledge_entries=(
            [knowledge_entry]
            if knowledge_entry is not None
            else []
        ),
        database_evidence=database_evidence,
    )

    resolution = resolve_unified_evidence(bundle)

    return compare_analyzer_with_resolution(
        domain=domain,
        current_vendor=str(
            row.get("vendor", "Unknown")
        ),
        current_category=str(
            row.get("category", "Unknown")
        ),
        current_filter=str(
            row.get("filter", "unknown")
        ),
        current_confidence=int(
            float(row.get("confidence", 0) or 0)
        ),
        current_recommendation=str(
            row.get("recommendation", "unknown")
        ),
        resolution=resolution,
    )


def run_production_shadow_evaluation(
    suggestions_path: Path,
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    database_rows: list[dict] | None = None,
    limit: int | None = None,
) -> ProductionShadowResult:
    config = load_analyzer_config(config_path)

    rows = load_suggestion_rows(suggestions_path)

    if limit is not None:
        rows = rows[: max(limit, 0)]

    effective_database_rows = (
        load_database()
        if database_rows is None
        else database_rows
    )

    comparisons = tuple(
        build_shadow_comparison(
            row,
            config=config,
            database_rows=effective_database_rows,
        )
        for row in rows
    )

    summary = evaluate_shadow_comparisons(
        comparisons
    )

    return ProductionShadowResult(
        summary=summary,
        comparisons=comparisons,
    )


def write_production_shadow_reports(
    result: ProductionShadowResult,
    *,
    text_path: Path,
    json_path: Path,
    comparisons_path: Path,
) -> None:
    text_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = build_shadow_evaluation_report(
        result.summary,
        top_differences=50,
    )

    text_path.write_text(
        report + "\n",
        encoding="utf-8",
    )

    json_path.write_text(
        json.dumps(
            result.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    comparisons_path.write_text(
        json.dumps(
            [
                comparison.to_dict()
                for comparison in result.comparisons
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
