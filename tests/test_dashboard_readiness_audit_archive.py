from types import SimpleNamespace


def configure(monkeypatch, web_app):
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
    history = SimpleNamespace(
        entries=(),
        trend=SimpleNamespace(direction="stable", percent_delta=0.0, checks_delta=0, coverage_delta=0.0),
    )
    decision = SimpleNamespace(
        status="ready-for-review", eligible_for_manual_review=True, stable=False,
        window_size=7, observed_snapshots=3, ready_snapshots=3, regressions=0, rules=(),
    )
    entry = SimpleNamespace(
        timestamp="2026-07-17T05:40:00+00:00",
        event_type="decision-observed",
        decision_status="ready-for-review",
        reviewer="",
        decision_fingerprint="1234567890abcdef",
        enforcement_activated=False,
    )
    archive = SimpleNamespace(entries=(entry,), total_entries=1, decision_events=1, approval_events=0, latest_entry=entry)
    monkeypatch.setattr(web_app, "load_enforcement_readiness", lambda: readiness)
    monkeypatch.setattr(web_app, "append_readiness_snapshot", lambda value: False)
    monkeypatch.setattr(web_app, "load_readiness_history_summary", lambda: history)
    monkeypatch.setattr(web_app, "evaluate_readiness_decision", lambda value, entries: decision)
    monkeypatch.setattr(web_app, "latest_matching_approval", lambda value: None)
    monkeypatch.setattr(web_app, "archive_readiness_decision", lambda value: True)
    monkeypatch.setattr(web_app, "load_readiness_audit_archive_summary", lambda: archive)
    return decision


def test_dashboard_shows_audit_decision_archive(monkeypatch):
    import web.app as web_app
    configure(monkeypatch, web_app)
    app = web_app.create_app()
    app.config["TESTING"] = True
    response = app.test_client().get("/")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Audit &amp; Decision Archive" in html
    assert "APPEND-ONLY" in html
    assert "Decision observed" in html
    assert "DISABLED" in html


def test_manual_review_is_archived_after_recording(monkeypatch):
    import web.app as web_app
    decision = configure(monkeypatch, web_app)
    approval = SimpleNamespace(decision_fingerprint="fingerprint", enforcement_activated=False)
    captured = {}
    monkeypatch.setattr(web_app, "record_manual_readiness_approval", lambda *args, **kwargs: approval)
    monkeypatch.setattr(web_app, "archive_manual_readiness_approval", lambda current, record: captured.update(current=current, record=record))
    monkeypatch.setattr(web_app, "log_event", lambda *args: None)
    app = web_app.create_app()
    app.config["TESTING"] = True
    response = app.test_client().post(
        "/readiness/manual-approval",
        data={"reviewer": "Ibrahim", "confirmation": "APPROVE READINESS REVIEW", "note": "Reviewed"},
    )
    assert response.status_code == 302
    assert captured == {"current": decision, "record": approval}
