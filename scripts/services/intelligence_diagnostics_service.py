"""Structured diagnostics for the 5ibr intelligence system."""

from __future__ import annotations

from dataclasses import dataclass, field

from scripts.rule_check import validate_rule_config
from scripts.services.analyzer_service import load_analyzer_config
from scripts.services.intelligence_summary_service import (
    validate_decision_engine,
    validate_explain_engine,
)
from scripts.services.knowledge_service import (
    knowledge_integrity_report,
    load_knowledge_entries,
)


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class ComponentDiagnostic:
    name: str
    status: str
    checks: list[DiagnosticCheck] = field(default_factory=list)


@dataclass(frozen=True)
class IntelligenceDiagnostics:
    status: str
    components: list[ComponentDiagnostic] = field(default_factory=list)


def _status(ok: bool) -> str:
    return "Healthy" if ok else "Warning"


def knowledge_diagnostic() -> ComponentDiagnostic:
    entries = load_knowledge_entries()
    ok, errors = knowledge_integrity_report()

    checks = [
        DiagnosticCheck(
            name="entries-loaded",
            ok=bool(entries),
            detail=f"{len(entries)} knowledge entries loaded",
        ),
        DiagnosticCheck(
            name="schema-valid",
            ok=ok,
            detail=(
                "all required knowledge fields are valid"
                if ok
                else "; ".join(errors)
            ),
        ),
    ]

    component_ok = all(check.ok for check in checks)

    return ComponentDiagnostic(
        name="Knowledge Base",
        status=_status(component_ok),
        checks=checks,
    )


def rule_diagnostic() -> ComponentDiagnostic:
    config = load_analyzer_config()
    ok, errors = validate_rule_config(config)

    vendor_groups = len(config.get("vendor_patterns", {}))
    category_groups = len(config.get("category_keywords", {}))
    filter_mappings = len(config.get("filter_map", {}))

    checks = [
        DiagnosticCheck(
            name="vendor-groups",
            ok=vendor_groups > 0,
            detail=f"{vendor_groups} vendor groups loaded",
        ),
        DiagnosticCheck(
            name="category-groups",
            ok=category_groups > 0,
            detail=f"{category_groups} category groups loaded",
        ),
        DiagnosticCheck(
            name="filter-mappings",
            ok=filter_mappings > 0,
            detail=f"{filter_mappings} filter mappings loaded",
        ),
        DiagnosticCheck(
            name="config-valid",
            ok=ok,
            detail=(
                "analyzer rule configuration is valid"
                if ok
                else "; ".join(errors)
            ),
        ),
    ]

    component_ok = all(check.ok for check in checks)

    return ComponentDiagnostic(
        name="Rule Engine",
        status=_status(component_ok),
        checks=checks,
    )


def decision_diagnostic() -> ComponentDiagnostic:
    ok, errors = validate_decision_engine()

    checks = [
        DiagnosticCheck(
            name="decision-api",
            ok=ok,
            detail=(
                "decision construction and confidence calculation operational"
                if ok
                else "; ".join(errors)
            ),
        ),
        DiagnosticCheck(
            name="recommendation-thresholds",
            ok=ok,
            detail=(
                "recommendation threshold behavior validated"
                if ok
                else "recommendation threshold validation failed"
            ),
        ),
    ]

    return ComponentDiagnostic(
        name="Decision Engine",
        status=_status(all(check.ok for check in checks)),
        checks=checks,
    )


def explain_diagnostic() -> ComponentDiagnostic:
    ok, errors = validate_explain_engine()

    checks = [
        DiagnosticCheck(
            name="explanation-api",
            ok=ok,
            detail=(
                "explanation creation operational"
                if ok
                else "; ".join(errors)
            ),
        ),
        DiagnosticCheck(
            name="reason-generation",
            ok=ok,
            detail=(
                "reason generation operational"
                if ok
                else "reason generation validation failed"
            ),
        ),
    ]

    return ComponentDiagnostic(
        name="Explain Engine",
        status=_status(all(check.ok for check in checks)),
        checks=checks,
    )


def build_intelligence_diagnostics() -> IntelligenceDiagnostics:
    components = [
        knowledge_diagnostic(),
        rule_diagnostic(),
        decision_diagnostic(),
        explain_diagnostic(),
    ]

    healthy = all(component.status == "Healthy" for component in components)

    return IntelligenceDiagnostics(
        status=_status(healthy),
        components=components,
    )
