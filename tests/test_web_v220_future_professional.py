from pathlib import Path

from web.app import create_app


ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def test_future_design_assets_are_local_and_bootstrap_only():
    base = read("web/templates/base.html")
    assert "future.css" in base and "animations.css" in base and "ui.js" in base
    assert "bootstrap@5.3.3" in base and "bootstrap-icons@1.11.3" in base
    for forbidden in ("react", "vue", "tailwind", "jquery"):
        assert forbidden not in base.lower()


def test_enterprise_header_and_footer_show_operational_context():
    base = read("web/templates/base.html")
    for marker in ("runtime_version", "runtime_environment", "runtime_commit", "notifications", "app-footer"):
        assert marker in base
    app = create_app({"TESTING": True, "SECRET_KEY": "v220"})
    body = app.test_client().get("/").get_data(as_text=True)
    assert "2.2.0" in body and "Enterprise Cyber Intelligence" in body


def test_dashboard_has_executive_summary_and_css_gauges():
    dashboard = read("web/templates/dashboard.html")
    assert "executive_summary" in dashboard and dashboard.count("cyber-gauge") >= 2
    assert "readiness.progress.percent" in dashboard and "domain_analytics.average_confidence" in dashboard


def test_analyzer_preserves_raw_report_behind_disclosure():
    for name in ("analyze.html", "analyze_log.html"):
        source = read(f"web/templates/{name}")
        assert "show_raw_report" in source and "operation-output" in source
        assert "<details" in source


def test_review_queue_uses_professional_workbench_without_route_changes():
    source = read("web/templates/review_queue.html")
    assert "review-workbench" in source and "data-bs-toggle=\"collapse\"" in source
    assert "review_queue_action" in source and 'method="post"' in source
    assert "inject_csrf_fields" in read("web/app.py")


def test_audit_has_client_side_search_filter_export_and_sort():
    source = read("web/templates/audit.html")
    for marker in ("data-table-search", "data-table-filter", "data-export-table", "data-sort-table"):
        assert marker in source
    assert "audit_log" in read("web/app.py")


def test_markdown_viewer_has_professional_tools():
    source = read("web/templates/markdown.html")
    for marker in ("data-copy-target", "data-download-target", "data-print", "data-fullscreen-target", "with-lines"):
        assert marker in source


def test_future_css_includes_dark_rtl_mobile_and_reduced_motion():
    css = read("web/static/css/future.css") + read("web/static/css/animations.css")
    assert '[data-bs-theme="dark"]' in css
    assert "max-width:767.98px" in css
    assert "prefers-reduced-motion" in css
    assert "inset-inline" in css


def test_security_contract_remains_fail_closed_and_csrf_enabled():
    source = read("web/app.py")
    assert "CSRF_ENABLED=True" in source
    assert "if not current_user.is_authenticated" in source
    assert "if not current_user.has_role(*roles)" in source
    assert "secrets.compare_digest" in source


def test_future_copy_exists_in_both_locales():
    from web.i18n import TRANSLATIONS
    keys = ("executive_summary", "operational_console", "show_raw_report", "advanced_search", "report_viewer")
    assert all(TRANSLATIONS[lang][key] for lang in ("en", "ar") for key in keys)


def test_runtime_version_is_v220_rc1():
    assert read("VERSION").strip() == "2.2.0rc1"
