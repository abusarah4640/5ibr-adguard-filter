from types import SimpleNamespace


def test_dashboard_shows_readiness_decision_engine(monkeypatch):
    import web.app as web_app

    readiness = SimpleNamespace(
        ready=True,
        status="ready",
        reasons=(),
        summary=SimpleNamespace(
            guardrail_coverage_rate=100.0,
            classified_approval_attempts=150,
            unclassified_approval_attempts=0,
            classified_approval_block_rate=0.0,
            shadow_rows=25,
            enforce_rows=0,
        ),
        progress=SimpleNamespace(
            percent=100.0, passed_checks=6, total_checks=6,
            classified_approvals_remaining=0, coverage_gap=0.0,
            unclassified_approvals_excess=0,
            classified_block_rate_excess=0.0,
            shadow_rows_remaining=0, enforce_rows_excess=0,
        ),
        diagnostics=(),
    )
    history = SimpleNamespace(entries=(), trend=SimpleNamespace(
        direction="insufficient-data", percent_delta=0.0,
        checks_delta=0, coverage_delta=0.0,
    ))
    decision = SimpleNamespace(
        status="ready-for-review",
        eligible_for_manual_review=True,
        stable=False,
        window_size=7,
        observed_snapshots=2,
        ready_snapshots=2,
        regressions=0,
        rules=(SimpleNamespace(
            name="stability-window",
            passed=False,
            detail="2 of 7 required snapshots available.",
        ),),
    )

    monkeypatch.setattr(web_app, "load_enforcement_readiness", lambda: readiness)
    monkeypatch.setattr(web_app, "append_readiness_snapshot", lambda value: False)
    monkeypatch.setattr(web_app, "load_readiness_history_summary", lambda: history)
    monkeypatch.setattr(web_app, "evaluate_readiness_decision", lambda current, entries: decision)

    app = web_app.create_app()
    app.config["TESTING"] = True
    response = app.test_client().get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Readiness Decision Engine" in html
    assert "READY FOR REVIEW" in html
    assert "2 / 7" in html
    assert "Stability window" in html
    assert "no enforcement is activated automatically" in html
