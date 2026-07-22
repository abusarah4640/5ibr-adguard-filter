from pathlib import Path


def test_dashboard_groups_intelligence_actions():
    source = Path("web/templates/dashboard.html").read_text(encoding="utf-8")

    assert 't("intelligence")' in source
    assert 't("intelligence_check")' in source
    assert 't("intelligence_report")' in source


def test_i18n_contains_intelligence_group_key():
    source = Path("web/i18n.py").read_text(encoding="utf-8")

    assert '"intelligence"' in source
    assert '"الذكاء"' in source
