"""Build dashboard-ready intelligence summary."""

from __future__ import annotations

from dataclasses import dataclass

from scripts.rule_check import validate_rule_config
from scripts.services.analyzer_service import load_analyzer_config
from scripts.services.decision_engine import (
    build_decision,
    decision_reasons,
)
from scripts.services.explain_engine import make_explanation
from scripts.services.knowledge_service import (
    knowledge_integrity_report,
    load_knowledge_entries,
)


@dataclass(frozen=True)
class IntelligenceSummary:
    knowledge_entries: int
    vendor_groups: int
    category_groups: int
    filter_mappings: int
    knowledge_status: str
    rule_status: str
    decision_status: str
    explain_status: str
    status: str


def _status(ok: bool) -> str:
    return "Healthy" if ok else "Warning"


def validate_decision_engine() -> tuple[bool, list[str]]:
    """Run a small deterministic Decision Engine self-check."""

    errors: list[str] = []

    try:
        explanation = make_explanation(
            source="decision-self-check",
            message="decision engine self-check",
            weight=35,
        )

        decision = build_decision(
            vendor="SelfCheck",
            category="System",
            filter_name="system",
            explanations=[explanation],
        )

        if decision.vendor != "SelfCheck":
            errors.append("decision engine vendor check failed")

        if decision.confidence != 35:
            errors.append("decision engine confidence check failed")

        if decision.recommendation != "unknown":
            errors.append("decision engine recommendation check failed")

    except Exception as exc:
        errors.append(f"decision engine error: {exc}")

    return not errors, errors


def validate_explain_engine() -> tuple[bool, list[str]]:
    """Run a small deterministic Explain Engine self-check."""

    errors: list[str] = []

    try:
        explanation = make_explanation(
            source="explain-self-check",
            message="explain engine self-check",
            weight=10,
        )

        decision = build_decision(
            explanations=[explanation],
        )

        reasons = decision_reasons(decision)

        if reasons != ["explain engine self-check"]:
            errors.append("explain engine reason check failed")

    except Exception as exc:
        errors.append(f"explain engine error: {exc}")

    return not errors, errors


def build_intelligence_summary() -> IntelligenceSummary:
    entries = load_knowledge_entries()
    knowledge_ok, _ = knowledge_integrity_report()

    config = load_analyzer_config()
    rules_ok, _ = validate_rule_config(config)

    decision_ok, _ = validate_decision_engine()
    explain_ok, _ = validate_explain_engine()

    overall_ok = (
        knowledge_ok
        and rules_ok
        and decision_ok
        and explain_ok
    )

    return IntelligenceSummary(
        knowledge_entries=len(entries),
        vendor_groups=len(config.get("vendor_patterns", {})),
        category_groups=len(config.get("category_keywords", {})),
        filter_mappings=len(config.get("filter_map", {})),
        knowledge_status=_status(knowledge_ok),
        rule_status=_status(rules_ok),
        decision_status=_status(decision_ok),
        explain_status=_status(explain_ok),
        status=_status(overall_ok),
    )
