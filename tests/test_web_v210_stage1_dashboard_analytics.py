from types import SimpleNamespace

from web.dashboard_analytics import (
    domain_analytics,
    operational_activity,
    readiness_display_state,
)
from web.app import create_app


def dashboard_client(tmp_path, monkeypatch, *, rows=(), events=(), readiness=None, testing=True):
    monkeypatch.setattr("web.app.load_database", lambda: list(rows))
    monkeypatch.setattr("web.app.load_suggestions", lambda: [])
    monkeypatch.setattr("web.app.recent_events", lambda limit=20: list(events))
    monkeypatch.setattr("web.app.load_enforcement_readiness", lambda: readiness)
    app = create_app({
        "TESTING": testing,
        "SECRET_KEY": "v210-dashboard-secret",
        "USER_DATABASE": tmp_path / "dashboard-users.sqlite3",
    })
    return app, app.test_client()


def test_domain_analytics_calculates_real_summary_and_top_five():
    rows = [
        {"Domain": f"d{i}.test", "Vendor": f"V{i % 6}", "Category": f"C{i % 3}",
         "Filter": f"F{i % 2}", "Status": "Approved" if i < 5 else "Pending",
         "Confidence": str(40 + i)}
        for i in range(8)
    ]
    result = domain_analytics(rows)
    assert result["total"] == 8 and result["approved"] == 5 and result["pending"] == 3
    assert result["unique_vendors"] == 6
    assert result["unique_categories"] == 3 and result["unique_filters"] == 2
    assert result["average_confidence"] == 43.5 and result["low_confidence"] == 8
    assert len(result["top_vendors"]) == 5


def test_domain_analytics_uses_unknown_for_empty_distribution_values():
    result = domain_analytics([{"Vendor": "", "Category": None, "Filter": "", "Confidence": "80"}])
    assert result["top_vendors"][0]["name"] == "Unknown"
    assert result["top_categories"][0]["name"] == "Unknown"
    assert result["top_filters"][0]["name"] == "Unknown"


def test_operational_activity_filters_test_data_outside_tests():
    events = [
        {"Action": "action.build", "Target": "/tmp/pytest-x", "Result": "ok"},
        {"Action": "action.build", "Target": "example.test", "Result": "ok"},
        {"Action": "action.build", "Target": "build", "Result": "ok", "Timestamp": "real"},
    ]
    assert operational_activity(events)[0]["timestamp"] == "real"
    assert operational_activity(events[:2])[0]["status"] == "none"
    assert operational_activity(events[:1], testing=True)[0]["status"] == "success"


def test_readiness_display_state_distinguishes_evidence_and_failure():
    check = lambda key, passed: SimpleNamespace(key=key, passed=passed)
    insufficient = SimpleNamespace(ready=False, diagnostics=(check("classified-approvals", False),))
    failed = SimpleNamespace(ready=False, diagnostics=(check("enforce-rows", False),))
    ready = SimpleNamespace(ready=True, diagnostics=())
    assert readiness_display_state(None) == "insufficient_data"
    assert readiness_display_state(insufficient) == "insufficient_data"
    assert readiness_display_state(failed) == "failed"
    assert readiness_display_state(ready) == "ready"


def test_dashboard_is_read_only_for_guest_and_loads_for_signed_in_user(tmp_path, monkeypatch):
    app, guest = dashboard_client(tmp_path, monkeypatch)
    guest_body = guest.get("/").get_data(as_text=True)
    assert guest.get("/").status_code == 200
    assert 'action="/actions/build"' not in guest_body
    app.extensions["fivebr_users"].create_user("dash-user", "dashboard-password", role="viewer")
    signed_in = app.test_client()
    signed_in.post("/login", data={"username": "dash-user", "password": "dashboard-password"})
    assert signed_in.get("/").status_code == 200


def test_dashboard_renders_four_empty_operational_cards(tmp_path, monkeypatch):
    _, client = dashboard_client(tmp_path, monkeypatch, events=[])
    body = client.get("/").get_data(as_text=True)
    assert body.count("This operation has not been recorded yet.") == 4
    for name in ("Latest filter build", "Latest validation", "Latest system check", "Latest intelligence check"):
        assert name in body


def test_dashboard_renders_real_operation_metadata(tmp_path, monkeypatch):
    events = [{"Timestamp": "2026-07-19T01:00:00Z", "Action": "action.validate", "Target": "validate",
               "Result": "ok", "Details": "duration=1.2s; issues=2; exit code=0"}]
    _, client = dashboard_client(tmp_path, monkeypatch, events=events)
    body = client.get("/").get_data(as_text=True)
    assert "2026-07-19T01:00:00Z" in body and "1.2s" in body
    assert "Exit code" in body and ">0<" in body


def test_production_dashboard_hides_pytest_paths_and_known_test_domains(tmp_path, monkeypatch):
    events = [
        {"Timestamp": "x", "Action": "action.build", "Target": "/tmp/pytest-of-user/x", "Result": "ok", "Details": ""},
        {"Timestamp": "y", "Action": "domain.add", "Target": "example.test", "Result": "ok", "Details": ""},
    ]
    _, client = dashboard_client(tmp_path, monkeypatch, events=events, testing=False)
    body = client.get("/").get_data(as_text=True)
    assert "/tmp/pytest" not in body and "example.test" not in body


def test_dashboard_integration_shows_database_counts_and_top_five(tmp_path, monkeypatch):
    rows = [
        {"Domain": f"domain-{i}.invalid", "Vendor": f"Vendor {i % 6}", "Category": f"Category {i % 3}",
         "Filter": f"filter-{i % 2}", "Status": "Approved", "Confidence": "80"}
        for i in range(12)
    ]
    _, client = dashboard_client(tmp_path, monkeypatch, rows=rows)
    body = client.get("/").get_data(as_text=True)
    assert 'data-analytics-value="total_domains">12<' in body
    assert 'data-analytics-value="unique_vendors">6<' in body
    assert 'data-analytics-value="unique_categories">3<' in body
    assert 'data-analytics-value="unique_filters">2<' in body
    vendors_panel = body.split('data-distribution="vendors"', 1)[1].split("</section>", 1)[0]
    assert vendors_panel.count("distribution-item") == 5


def test_new_dashboard_copy_is_translated_and_rtl(tmp_path, monkeypatch):
    _, client = dashboard_client(tmp_path, monkeypatch)
    english = client.get("/?lang=en").get_data(as_text=True)
    arabic = client.get("/?lang=ar").get_data(as_text=True)
    assert "Latest operational status" in english and "Domain database distribution" in english
    assert "آخر حالة تشغيلية" in arabic and "توزيع قاعدة الدومينات" in arabic
    assert 'dir="rtl"' in arabic


def test_dashboard_unknown_distribution_is_localized_without_translating_technical_values(tmp_path, monkeypatch):
    rows = [{"Domain": "real.example", "Vendor": "", "Category": "", "Filter": "technical-filter", "Confidence": "90"}]
    _, client = dashboard_client(tmp_path, monkeypatch, rows=rows)
    body = client.get("/?lang=ar").get_data(as_text=True)
    assert "غير معروف" in body and "technical-filter" in body and "real.example" not in body
