from pathlib import Path


def test_intelligence_template_uses_dynamic_component_statuses():
    source = Path("web/templates/intelligence.html").read_text(
        encoding="utf-8"
    )

    assert "intelligence.knowledge_status" in source
    assert "intelligence.rule_status" in source
    assert "intelligence.decision_status" in source
    assert "intelligence.explain_status" in source


def test_intelligence_template_has_no_fixed_core_ok_badges():
    source = Path("web/templates/intelligence.html").read_text(
        encoding="utf-8"
    )

    assert '<span class="badge text-bg-success">OK</span>' not in source
