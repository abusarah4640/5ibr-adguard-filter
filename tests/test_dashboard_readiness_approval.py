from types import SimpleNamespace


def readiness():
    return SimpleNamespace(
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


def history():
    return SimpleNamespace(
        entries=(),
        trend=SimpleNamespace(
            direction="insufficient-data", percent_delta=0.0,
            checks_delta=0, coverage_delta=0.0,
        ),
    )


def decision(eligible=True):
    return SimpleNamespace(
        status="ready-for-review" if eligible else "not-ready",
        eligible_for_manual_review=eligible,
        stable=False,
        window_size=7,
        observed_snapshots=3,
        ready_snapshots=3,
        regressions=0,
        rules=(),
    )


def configure(monkeypatch, web_app, *, eligible=True, approval=None):
    current = readiness()
    summary = history()
    result = decision(eligible)
    monkeypatch.setattr(web_app, "load_enforcement_readiness", lambda: current)
    monkeypatch.setattr(web_app, "append_readiness_snapshot", lambda value: False)
    monkeypatch.setattr(web_app, "load_readiness_history_summary", lambda: summary)
    monkeypatch.setattr(web_app, "evaluate_readiness_decision", lambda value, entries: result)
    monkeypatch.setattr(web_app, "latest_matching_approval", lambda value: approval)
    return result


def test_dashboard_shows_available_manual_gate(monkeypatch, tmp_path):
    import web.app as web_app

    configure(monkeypatch, web_app)
    app = web_app.create_app({"TESTING": True, "USER_DATABASE": tmp_path / "users.sqlite3"})
    app.extensions["fivebr_users"].create_user("gate-admin", "gate-admin-password", role="admin")
    client = app.test_client()
    client.post("/login", data={"username": "gate-admin", "password": "gate-admin-password"})
    html = client.get("/").get_data(as_text=True)

    assert "Manual Approval Gate" in html
    assert "AVAILABLE" in html
    assert "APPROVE READINESS REVIEW" in html
    assert "Record Manual Review" in html
    assert "cannot enable enforcement" in html


def test_dashboard_shows_locked_gate(monkeypatch):
    import web.app as web_app

    configure(monkeypatch, web_app, eligible=False)
    app = web_app.create_app()
    app.config["TESTING"] = True
    html = app.test_client().get("/").get_data(as_text=True)

    assert "Manual Approval Gate" in html
    assert "LOCKED" in html
    assert "Record Manual Review" not in html


def test_post_recomputes_and_records_manual_review(monkeypatch):
    import web.app as web_app

    result = configure(monkeypatch, web_app)
    captured = {}

    def record(value, **kwargs):
        captured["decision"] = value
        captured.update(kwargs)

    monkeypatch.setattr(web_app, "record_manual_readiness_approval", record)
    monkeypatch.setattr(web_app, "log_event", lambda *args: None)

    app = web_app.create_app()
    app.config["TESTING"] = True
    response = app.test_client().post(
        "/readiness/manual-approval",
        data={
            "reviewer": "Ibrahim",
            "confirmation": "APPROVE READINESS REVIEW",
            "note": "Reviewed manually.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert captured["decision"] is result
    assert captured["reviewer"] == "Ibrahim"
    assert captured["note"] == "Reviewed manually."
