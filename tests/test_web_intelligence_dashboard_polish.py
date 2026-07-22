from pathlib import Path


def test_intelligence_card_contains_direct_actions():
    source = Path("web/templates/dashboard.html").read_text(encoding="utf-8")

    assert "btn btn-sm btn-outline-dark" in source
    assert "btn btn-sm btn-outline-secondary" in source
    assert "action='intelligence-check'" in source
    assert "url_for('intelligence_report_page')" in source
