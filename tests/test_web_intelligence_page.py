from pathlib import Path


def test_intelligence_page_route_exists():
    source = Path("web/app.py").read_text(encoding="utf-8")

    assert '@app.route("/intelligence")' in source
    assert "def intelligence_report_page()" in source
    assert '"intelligence.html"' in source


def test_intelligence_page_template_contains_summary_sections():
    source = Path("web/templates/intelligence.html").read_text(
        encoding="utf-8"
    )

    assert "intelligence.knowledge_entries" in source
    assert "intelligence.vendor_groups" in source
    assert "intelligence.category_groups" in source
    assert "intelligence.filter_mappings" in source
    assert 't("decision_engine")' in source
    assert 't("explain_engine")' in source


def test_dashboard_links_to_intelligence_page():
    source = Path("web/templates/dashboard.html").read_text(
        encoding="utf-8"
    )

    assert "url_for('intelligence_report_page')" in source
