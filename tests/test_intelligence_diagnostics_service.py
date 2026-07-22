from scripts.services.intelligence_diagnostics_service import (
    ComponentDiagnostic,
    DiagnosticCheck,
    IntelligenceDiagnostics,
    build_intelligence_diagnostics,
    decision_diagnostic,
    explain_diagnostic,
    knowledge_diagnostic,
    rule_diagnostic,
)


def test_knowledge_diagnostic():
    diagnostic = knowledge_diagnostic()

    assert isinstance(diagnostic, ComponentDiagnostic)
    assert diagnostic.name == "Knowledge Base"
    assert diagnostic.status == "Healthy"
    assert diagnostic.checks
    assert all(isinstance(check, DiagnosticCheck) for check in diagnostic.checks)
    assert all(check.ok for check in diagnostic.checks)


def test_rule_diagnostic():
    diagnostic = rule_diagnostic()

    assert diagnostic.name == "Rule Engine"
    assert diagnostic.status == "Healthy"
    assert any(check.name == "vendor-groups" for check in diagnostic.checks)
    assert any(check.name == "category-groups" for check in diagnostic.checks)
    assert any(check.name == "filter-mappings" for check in diagnostic.checks)


def test_decision_diagnostic():
    diagnostic = decision_diagnostic()

    assert diagnostic.name == "Decision Engine"
    assert diagnostic.status == "Healthy"
    assert all(check.ok for check in diagnostic.checks)


def test_explain_diagnostic():
    diagnostic = explain_diagnostic()

    assert diagnostic.name == "Explain Engine"
    assert diagnostic.status == "Healthy"
    assert all(check.ok for check in diagnostic.checks)


def test_build_intelligence_diagnostics():
    diagnostics = build_intelligence_diagnostics()

    assert isinstance(diagnostics, IntelligenceDiagnostics)
    assert diagnostics.status == "Healthy"
    assert len(diagnostics.components) == 4
    assert all(
        component.status == "Healthy"
        for component in diagnostics.components
    )
