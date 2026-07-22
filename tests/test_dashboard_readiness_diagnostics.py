from __future__ import annotations

from pathlib import Path

from scripts.services.guardrail_readiness_service import (
    EnforcementReadinessThresholds,
    evaluate_enforcement_readiness,
)
from scripts.services.guardrail_report_service import (
    build_guardrail_dry_run_summary,
)
from web.app import create_app


def test_readiness_result_exposes_six_structured_diagnostics():
    result = evaluate_enforcement_readiness(
        build_guardrail_dry_run_summary([]),
        thresholds=EnforcementReadinessThresholds(),
    )

    assert len(result.diagnostics) == 6
    assert {check.key for check in result.diagnostics} == {
        "classified-approvals",
        "coverage",
        "unclassified-approvals",
        "classified-block-rate",
        "shadow-observations",
        "enforce-rows",
    }


def test_diagnostics_report_current_target_status_and_guidance():
    result = evaluate_enforcement_readiness(
        build_guardrail_dry_run_summary([]),
        thresholds=EnforcementReadinessThresholds(),
    )

    classified = result.diagnostics[0]
    assert classified.current == "0"
    assert classified.target == ">= 100"
    assert classified.passed is False
    assert "shadow mode" in classified.guidance


def test_dashboard_template_contains_diagnostics_table():
    source = Path("web/templates/dashboard.html").read_text(encoding="utf-8")

    assert "t('readiness_diagnostics')" in source
    assert "readiness.diagnostics" in source
    assert "t('needs_evidence')" in source
    assert "t('next_step')" in source


def test_dashboard_renders_readiness_diagnostics(monkeypatch):
    import web.app as web_app

    result = evaluate_enforcement_readiness(
        build_guardrail_dry_run_summary([]),
        thresholds=EnforcementReadinessThresholds(),
    )

    monkeypatch.setattr(
        web_app,
        "load_enforcement_readiness",
        lambda: result,
    )

    app = create_app()
    app.config["TESTING"] = True
    response = app.test_client().get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Readiness Diagnostics" in html
    assert "Classified approvals" in html
    assert "&gt;= 100" in html
    assert "NEEDS EVIDENCE" in html
    assert "application enforcement remains disabled" in html
