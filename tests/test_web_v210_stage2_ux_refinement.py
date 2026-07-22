from pathlib import Path
import importlib
from types import SimpleNamespace

from web.app import create_app
from web.dashboard_analytics import (
    audit_operation_key,
    domain_analytics,
    format_display_datetime,
)


ROOT = Path(__file__).resolve().parents[1]


def test_confidence_and_status_distributions_are_derived_only():
    rows = [
        {"Confidence": "90", "Status": "Approved"},
        {"Confidence": "65", "Status": "Pending"},
        {"Confidence": "20", "Status": "Pending"},
    ]
    result = domain_analytics(rows)
    assert [item["count"] for item in result["confidence_distribution"]] == [1, 1, 1]
    assert [item["count"] for item in result["status_distribution"]] == [1, 2]


def test_dashboard_contains_accessible_readiness_sections_and_visual_summaries():
    source = (ROOT / "web/templates/dashboard.html").read_text(encoding="utf-8")
    for marker in ("readiness-overview", "readiness-checks", "readiness-decision", "readiness-log", "readiness-activity"):
        assert f'id="{marker}"' in source
    assert "confidence_distribution" in source and "status_distribution" in source
    assert 'role="progressbar"' in source


def test_review_queue_uses_collapsible_details_with_aria_contract():
    source = (ROOT / "web/templates/review_queue.html").read_text(encoding="utf-8")
    assert 'data-bs-toggle="collapse"' in source
    assert 'aria-expanded="false"' in source and 'aria-controls="explain-' in source
    assert "review_requirements" in source and "blocking_policy" in source


def test_unified_empty_states_exist_for_analysis_review_and_output():
    for template in ("analysis.html", "review_queue.html", "output.html"):
        source = (ROOT / "web/templates" / template).read_text(encoding="utf-8")
        assert "empty-state" in source
    assert "current_user.role in ['admin', 'editor']" in (ROOT / "web/templates/analysis.html").read_text(encoding="utf-8")


def test_output_page_has_summary_metadata_and_raw_output(monkeypatch, tmp_path):
    app_module = importlib.import_module("web.app")
    monkeypatch.setattr(app_module.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="technical line", stderr=""))
    monkeypatch.setattr(app_module, "log_event", lambda *args: None)
    app = create_app({"TESTING": True, "CSRF_ENABLED": False, "SECRET_KEY": "stage2", "USER_DATABASE": tmp_path / "users.sqlite3"})
    body = app.test_client().post("/actions/validate").get_data(as_text=True)
    assert "Operation summary" in body and "Exit code" in body
    assert "Executed at" in body and "Duration" in body and "technical line" in body


def test_output_empty_state_is_rendered_without_console_output(monkeypatch, tmp_path):
    app_module = importlib.import_module("web.app")
    monkeypatch.setattr(app_module.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(app_module, "log_event", lambda *args: None)
    app = create_app({"TESTING": True, "CSRF_ENABLED": False, "SECRET_KEY": "stage2", "USER_DATABASE": tmp_path / "users.sqlite3"})
    assert "No output returned" in app.test_client().post("/actions/doctor").get_data(as_text=True)


def test_audit_helpers_preserve_raw_values_and_format_display_time():
    assert audit_operation_key("action.intelligence-check") == "intelligence_check"
    assert audit_operation_key("domain.update") == ""
    assert format_display_datetime("2026-07-19T08:30:00+00:00", "Asia/Riyadh", "dd/mm/yyyy") == "19/07/2026 11:30"
    assert format_display_datetime("not-a-date") == "not-a-date"


def test_audit_template_keeps_technical_action_and_localizes_status():
    source = (ROOT / "web/templates/audit.html").read_text(encoding="utf-8")
    assert "audit_operation_key(event.Action)" in source
    assert "event.Action" in source and "format_display_datetime" in source
    assert "audit_status_" in source


def test_stage2_css_supports_focus_mobile_wrapping_and_output_scrolling():
    css = (ROOT / "web/static/css/components.css").read_text(encoding="utf-8")
    assert ":focus-visible" in css and "overflow-wrap: anywhere" in css
    assert ".operation-summary-grid" in css and ".operation-output" in css
    assert "@media (max-width: 575.98px)" in css


def test_stage2_copy_is_complete_in_english_and_arabic():
    from web.i18n import TRANSLATIONS
    keys = ("operation_summary", "technical_output", "confidence_distribution", "what_do_i_do_now", "review_queue_empty_title")
    for key in keys:
        assert TRANSLATIONS["en"][key] and TRANSLATIONS["ar"][key]


def test_security_and_route_contracts_remain_present():
    source = (ROOT / "web/app.py").read_text(encoding="utf-8")
    assert '@roles_required("admin", "editor")' in source
    assert 'allowed = {"doctor", "validate", "build", "intelligence-check", "intelligence-report"}' in source
    base = (ROOT / "web/templates/base.html").read_text(encoding="utf-8")
    assert "csrf_token" in base and "logout" in base


def test_runtime_version_is_stage2():
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "2.2.0"
