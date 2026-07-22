#!/usr/bin/env python3
"""Rule-based local domain analysis service."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from scripts.services.blocking_policy_service import (
    classify_blocking_policy,
)

from scripts.database import load_database
from scripts.runtime.paths import (
    get_runtime_paths,
)
from scripts.services.database_evidence_engine import match_database_evidence
from scripts.services.decision_engine import (
    apply_confidence_guardrails,
    build_decision,
    decision_reasons,
    legacy_reason_explanation,
)
from scripts.services.knowledge_engine import (
    explain_domain_match,
    first_domain_match,
    knowledge_match_score,
)
from scripts.services.rule_engine import (
    first_match,
    match_category_rules,
    match_vendor_rules,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "analyzer.json"


@dataclass(slots=True)
class DomainAnalysis:
    """Structured result returned by the analyzer service."""

    domain: str
    root_domain: str
    suggested_vendor: str = "Unknown"
    suggested_category: str = "Unknown"
    suggested_filter: str = "unknown"
    confidence: int = 0
    recommendation: str = "unknown"
    blocking_policy: str = "unknown"
    blocking_policy_reason: str = ""
    blocking_policy_source: str = "fallback"
    reasons: list[str] = field(default_factory=list)


def normalize_domain(domain: str) -> str:
    """Return a lowercase hostname without URL syntax."""

    value = domain.strip().lower()
    value = value.removeprefix("http://").removeprefix("https://")
    value = value.split("/", 1)[0].split(":", 1)[0].strip(".")
    return value


def root_domain(domain: str) -> str:
    """Return a simple registrable-domain approximation."""

    parts = [part for part in normalize_domain(domain).split(".") if part]
    if len(parts) <= 2:
        return ".".join(parts)
    return ".".join(parts[-2:])


def load_analyzer_config(path: Path | None = None) -> dict:
    """Load local analyzer rules."""

    if path is not None:
        config_path = path

    else:
        runtime_config_path = (
            get_runtime_paths().config
            / "analyzer.json"
        )

        if runtime_config_path.exists():
            config_path = (
                runtime_config_path
            )

        elif DEFAULT_CONFIG_PATH.exists():
            config_path = (
                DEFAULT_CONFIG_PATH
            )

        else:
            config_path = (
                Path.cwd()
                / "config"
                / "analyzer.json"
            )

    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)



def analyze_domain(
    domain: str,
    *,
    config_path: Path | None = None,
    rows: list[dict] | None = None,
) -> DomainAnalysis:
    """Analyze a domain using rule engine, knowledge engine, and database patterns."""

    normalized = normalize_domain(domain)
    config = load_analyzer_config(config_path)
    database_rows = load_database() if rows is None else rows

    reasons: list[str] = []
    score = 0
    suggested_vendor = "Unknown"
    suggested_category = "Unknown"
    suggested_filter = "unknown"
    conflicting_evidence = False

    vendor_matches = match_vendor_rules(
        normalized,
        config.get("vendor_patterns", {}),
    )
    vendor_match = first_match(vendor_matches, "vendor")

    if vendor_match:
        suggested_vendor = vendor_match.value
        reasons.append(vendor_match.reason)
        score += vendor_match.score

    category_matches = match_category_rules(
        normalized,
        config.get("category_keywords", {}),
    )
    category_match = first_match(category_matches, "category")

    if category_match:
        suggested_category = category_match.value
        reasons.append(category_match.reason)
        score += category_match.score

    # Knowledge Engine enrichment (v1.8.0-stage5+).
    entry = first_domain_match(normalized)

    if entry:
        for reason in explain_domain_match(normalized):
            if reason not in reasons:
                reasons.append(reason)

        if suggested_vendor == "Unknown" and entry.vendor != "Unknown":
            suggested_vendor = entry.vendor

        # Knowledge matches represent a specific known service and are
        # more precise than generic category keywords such as "event".
        if (
            suggested_category != "Unknown"
            and entry.category != "Unknown"
            and suggested_category != entry.category
        ):
            conflicting_evidence = True
            conflict_reason = (
                "conflicting category evidence: "
                f"rule={suggested_category}, "
                f"knowledge={entry.category}"
            )
            if conflict_reason not in reasons:
                reasons.append(conflict_reason)

        if entry.category != "Unknown":
            suggested_category = entry.category

        if (
            suggested_filter != "unknown"
            and entry.filter_name != "unknown"
            and suggested_filter != entry.filter_name
        ):
            conflicting_evidence = True
            conflict_reason = (
                "conflicting filter evidence: "
                f"current={suggested_filter}, "
                f"knowledge={entry.filter_name}"
            )
            if conflict_reason not in reasons:
                reasons.append(conflict_reason)

        if entry.filter_name != "unknown":
            suggested_filter = entry.filter_name

        score += knowledge_match_score(normalized, entry)

    database_evidence = match_database_evidence(normalized, database_rows)

    if database_evidence.reasons:
        reasons.extend(reason for reason in database_evidence.reasons if reason not in reasons)
        score += database_evidence.score

    if suggested_vendor == "Unknown" and database_evidence.vendor:
        suggested_vendor = database_evidence.vendor

    if suggested_category == "Unknown" and database_evidence.category:
        suggested_category = database_evidence.category

    # Database evidence may fill a missing filter, but must never
    # replace a more specific filter selected by Knowledge or Rule engines.
    if (
        suggested_filter == "unknown"
        and database_evidence.filter_name
    ):
        suggested_filter = database_evidence.filter_name

    if suggested_filter == "unknown" and suggested_category != "Unknown":
        suggested_filter = config.get("filter_map", {}).get(suggested_category, "unknown")

    explanations = [
        legacy_reason_explanation(reason, source="analyzer", weight=0)
        for reason in reasons
    ]

    if score:
        explanations.append(
            legacy_reason_explanation(
                "confidence score from analyzer evidence",
                source="analyzer-score",
                weight=score,
            )
        )

    decision = build_decision(
        vendor=suggested_vendor,
        category=suggested_category,
        filter_name=suggested_filter,
        explanations=explanations,
    )

    decision = apply_confidence_guardrails(
        decision,
        conflicting_evidence=conflicting_evidence,
    )

    final_reasons = [
        reason
        for reason in decision_reasons(decision)
        if reason != "confidence score from analyzer evidence"
    ]

    blocking_policy = (
        classify_blocking_policy(
            decision.category
        )
    )

    return DomainAnalysis(
        domain=normalized,
        root_domain=root_domain(normalized),
        suggested_vendor=decision.vendor,
        suggested_category=decision.category,
        suggested_filter=decision.filter_name,
        confidence=decision.confidence,
        recommendation=decision.recommendation,
        blocking_policy=(
            blocking_policy.policy.value
        ),
        blocking_policy_reason=(
            blocking_policy.reason
        ),
        blocking_policy_source=(
            blocking_policy.source
        ),
        reasons=final_reasons,
    )
