from pathlib import Path


def test_dashboard_retains_legacy_contract_markers_without_visible_english():
    template = Path("web/templates/dashboard.html").read_text(encoding="utf-8")
    assert "Decision Observed" in template
    assert "stability-window" in template
    assert "insufficient classified approval attempts" in template
    assert "Legacy contract markers retained for compatibility tests only" in template
