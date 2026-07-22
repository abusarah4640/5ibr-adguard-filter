from pathlib import Path


def test_web_still_allows_intelligence_report_cli_action():
    source = Path("web/app.py").read_text(encoding="utf-8")

    assert '"intelligence-report"' in source


def test_dashboard_links_to_intelligence_report_page():
    source = Path("web/templates/dashboard.html").read_text(encoding="utf-8")

    assert "url_for('intelligence_report_page')" in source
    assert 't("intelligence_report")' in source
