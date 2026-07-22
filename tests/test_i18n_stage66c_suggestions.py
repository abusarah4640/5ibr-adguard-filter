from pathlib import Path

from web.app import create_app


def test_arabic_suggestions_page_translates_stage66c_labels():
    app = create_app()
    app.testing = True
    client = app.test_client()
    client.set_cookie("fivebr_lang", "ar")

    response = client.get("/reports/suggestions")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "سياسة الحجب" in body or "لا توجد اقتراحات" in body
    assert "Blocking Policy" not in body


def test_stage66c_templates_use_translation_keys_for_visible_labels():
    root = Path(__file__).resolve().parents[1]
    suggestions = (root / "web/templates/suggestions.html").read_text(encoding="utf-8")
    form = (root / "web/templates/suggestion_form.html").read_text(encoding="utf-8")

    assert "{{ t('blocking_policy') }}" in suggestions
    assert "{{ t('source') }}" in suggestions
    assert "{{ t('suggestion_guidance') }}" in form
    assert "{{ t('analyzer_explanation') }}" in form
    assert "normalize_unknown(item.get('Suggested Vendor') or item.get('Vendor'), t('needs_selection'))" in form


def test_stage66c_arabic_catalog_contains_suggestion_labels():
    from web.i18n import TRANSLATIONS

    expected = {
        "blocking_policy": "سياسة الحجب",
        "source": "المصدر",
        "suggestion_guidance": "إرشادات الاقتراح",
        "analyzer_explanation": "تفسير المحلل",
    }

    for key, value in expected.items():
        assert TRANSLATIONS["ar"][key] == value
        assert key in TRANSLATIONS["en"]
