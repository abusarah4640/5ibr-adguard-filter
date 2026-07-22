from pathlib import Path


def test_dashboard_uses_intelligence_report_translation_key():
    source = Path("web/templates/dashboard.html").read_text(encoding="utf-8")

    assert 't("intelligence_report")' in source


def test_i18n_contains_intelligence_report_key():
    source = Path("web/i18n.py").read_text(encoding="utf-8")

    assert '"intelligence_report"' in source
