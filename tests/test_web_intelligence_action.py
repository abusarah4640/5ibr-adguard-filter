from pathlib import Path


def test_web_actions_allow_intelligence_check():
    source = Path("web/app.py").read_text(encoding="utf-8")

    assert '"intelligence-check"' in source
    assert '"intelligence-report"' in source
    assert 'allowed = {"doctor", "validate", "build", "intelligence-check", "intelligence-report"}' in source
