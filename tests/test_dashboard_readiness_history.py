from types import SimpleNamespace


def test_dashboard_shows_readiness_history(monkeypatch):
    import web.app as web_app

    readiness = SimpleNamespace(
        ready=False,
        status="NOT READY",
        reasons=(),
        summary=SimpleNamespace(
            guardrail_coverage_rate=82.5,
            classified_approval_attempts=150,
            unclassified_approval_attempts=0,
            shadow_rows=25,
            enforce_rows=0,
        ),
        progress=SimpleNamespace(
            percent=50.0, passed_checks=3, total_checks=6,
            classified_approvals_remaining=50, coverage_gap=10.0,
            unclassified_approvals_excess=0,
            classified_block_rate_excess=0.0,
            shadow_rows_remaining=0, enforce_rows_excess=0,
        ),
        diagnostics=(),
    )
    history = SimpleNamespace(
        trend=SimpleNamespace(
            direction="improving", percent_delta=5.0,
            checks_delta=1, coverage_delta=2.5,
        ),
        entries=(SimpleNamespace(
            timestamp="2026-07-17T02:45:00+00:00",
            passed_checks=3, total_checks=6,
            percent=50.0, coverage_rate=82.5, status="NOT READY",
        ),),
    )

    decision = SimpleNamespace(
        status="not-ready",
        eligible_for_manual_review=False,
        stable=False,
        window_size=7,
        observed_snapshots=1,
        ready_snapshots=0,
        regressions=0,
        rules=(SimpleNamespace(
            name="current-readiness",
            passed=False,
            detail="Current readiness is not ready.",
        ),),
    )

    monkeypatch.setattr(web_app, "load_enforcement_readiness", lambda: readiness)
    monkeypatch.setattr(web_app, "append_readiness_snapshot", lambda value: False)
    monkeypatch.setattr(web_app, "load_readiness_history_summary", lambda: history)
    monkeypatch.setattr(
        web_app,
        "evaluate_readiness_decision",
        lambda current, entries: decision,
    )

    app = web_app.create_app()
    app.config["TESTING"] = True
    response = app.test_client().get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Readiness History &amp; Trends" in html
    assert "Improving" in html
    assert "2026-07-17T02:45:00+00:00" in html
    assert "Readiness Decision Engine" in html
    assert "NOT READY" in html
