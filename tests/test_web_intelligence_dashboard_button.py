from pathlib import Path


def test_dashboard_has_intelligence_check_button():
    source = Path("web/templates/dashboard.html").read_text(encoding="utf-8")

    assert "intelligence-check" in source
    assert 't("intelligence_check")' in source
    assert "url_for('action', action='intelligence-check')" in source
