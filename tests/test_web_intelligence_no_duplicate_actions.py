from pathlib import Path


def test_intelligence_actions_exist_only_once():
    source = Path("web/templates/dashboard.html").read_text(encoding="utf-8")

    assert source.count("action='intelligence-check'") == 1
    assert source.count("url_for('intelligence_report_page')") == 1


def test_quick_actions_keep_general_admin_actions():
    source = Path("web/templates/dashboard.html").read_text(encoding="utf-8")

    assert "action='doctor'" in source
    assert "action='validate'" in source
    assert "action='build'" in source
    assert "url_for('domains')" in source
    assert "url_for('suggestions')" in source
