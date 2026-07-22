from pathlib import Path


def test_dashboard_contains_intelligence_card():
    source = Path("web/templates/dashboard.html").read_text(encoding="utf-8")

    assert "intelligence.knowledge_entries" in source
    assert "intelligence.vendor_groups" in source
    assert "intelligence.category_groups" in source
    assert "intelligence.filter_mappings" in source


def test_dashboard_receives_intelligence_summary():
    source = Path("web/app.py").read_text(encoding="utf-8")

    assert "build_intelligence_summary()" in source
    assert "intelligence=intelligence" in source
