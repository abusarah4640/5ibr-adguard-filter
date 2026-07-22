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


def test_empty_evidence_exposes_bounded_progress_and_remaining_work():
    result = evaluate_enforcement_readiness(
        build_guardrail_dry_run_summary([]),
        thresholds=EnforcementReadinessThresholds(),
    )

    progress = result.progress
    assert 0.0 <= progress.percent <= 100.0
    assert progress.passed_checks == 3
    assert progress.total_checks == 6
    assert progress.classified_approvals_remaining == 100
    assert progress.coverage_gap == 95.0
    assert progress.shadow_rows_remaining == 1
    assert progress.enforce_rows_excess == 0


def test_ready_evidence_reports_complete_progress():
    rows = [
        {
            "Action": "approved",
            "Guardrail Mode": "shadow",
            "Guardrail Would Block": "false",
        }
        for _ in range(100)
    ]
    result = evaluate_enforcement_readiness(
        build_guardrail_dry_run_summary(rows),
        thresholds=EnforcementReadinessThresholds(),
    )

    assert result.ready is True
    assert result.progress.percent == 100.0
    assert result.progress.passed_checks == 6
    assert result.progress.classified_approvals_remaining == 0
    assert result.progress.coverage_gap == 0.0


def test_dashboard_template_contains_readiness_progress():
    source = Path("web/templates/dashboard.html").read_text(encoding="utf-8")

    assert "t('progress_toward_ready')" in source
    assert "readiness.progress.percent" in source
    assert "t('approvals_remaining')" in source
    assert "t('coverage_gap')" in source
    assert "t('enforce_rows_to_remove')" in source


def test_dashboard_renders_readiness_progress(monkeypatch):
    import web.app as web_app

    result = evaluate_enforcement_readiness(
        build_guardrail_dry_run_summary([]),
        thresholds=EnforcementReadinessThresholds(),
    )
    monkeypatch.setattr(web_app, "load_enforcement_readiness", lambda: result)

    app = create_app()
    app.config["TESTING"] = True
    response = app.test_client().get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Progress Toward READY" in html
    assert "3 / 6 checks passed" in html
    assert "Approvals remaining" in html
    assert "Visibility only" in html
