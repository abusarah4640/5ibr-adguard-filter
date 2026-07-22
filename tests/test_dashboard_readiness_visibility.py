from __future__ import annotations

from pathlib import Path

from web.app import create_app


def test_dashboard_template_contains_readiness_card():
    source = Path("web/templates/dashboard.html").read_text(encoding="utf-8")

    assert "t('guardrail_readiness')" in source
    assert "readiness.summary.guardrail_coverage_rate" in source
    assert "readiness.summary.classified_approval_attempts" in source
    assert "t('visibility_only')" in source


def test_dashboard_receives_readiness_result(monkeypatch):
    import web.app as web_app

    class Summary:
        guardrail_coverage_rate = 0.0
        classified_approval_attempts = 0
        unclassified_approval_attempts = 1
        classified_approval_block_rate = 0.0
        shadow_rows = 0
        enforce_rows = 0

    class Progress:
        percent = 0.0
        passed_checks = 2
        total_checks = 6
        classified_approvals_remaining = 100
        coverage_gap = 95.0
        unclassified_approvals_excess = 0
        classified_block_rate_excess = 0.0
        shadow_rows_remaining = 1
        enforce_rows_excess = 0

    class Readiness:
        ready = False
        status = "not-ready"
        reasons = ("insufficient classified approval attempts",)
        summary = Summary()
        progress = Progress()
        diagnostics = ()

    monkeypatch.setattr(
        web_app,
        "load_enforcement_readiness",
        lambda: Readiness(),
    )

    app = create_app()
    app.config["TESTING"] = True
    response = app.test_client().get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Guardrail Readiness" in html
    assert "NOT READY" in html
    assert "Insufficient classified approval attempts." in html
    assert "Progress Toward READY" in html
    assert "2 / 6 checks passed" in html


def test_dashboard_stays_available_when_readiness_load_fails(monkeypatch):
    import web.app as web_app

    def fail():
        raise RuntimeError("readiness unavailable")

    monkeypatch.setattr(
        web_app,
        "load_enforcement_readiness",
        fail,
    )

    app = create_app()
    app.config["TESTING"] = True
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert "Guardrail Readiness" not in response.get_data(as_text=True)
