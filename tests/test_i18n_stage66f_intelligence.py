from pathlib import Path


def test_intelligence_engine_labels_are_localized_in_template():
    source = Path("web/templates/intelligence.html").read_text(encoding="utf-8")

    assert 't("decision_engine")' in source
    assert 't("explain_engine")' in source
    assert "<span>Decision Engine</span>" not in source
    assert "<span>Explain Engine</span>" not in source


def test_intelligence_engine_translation_keys_exist_for_supported_languages():
    source = Path("web/i18n.py").read_text(encoding="utf-8")

    assert '"decision_engine": "Decision Engine"' in source
    assert '"explain_engine": "Explain Engine"' in source
    assert '"decision_engine": "محرك القرار"' in source
    assert '"explain_engine": "محرك التفسير"' in source
