from pathlib import Path

from web.app import create_app
from web.i18n import TRANSLATIONS


REQUIRED_KEYS = {
    "analysis_desc", "after_filter", "needs_human_review", "average_confidence",
    "high", "search_analysis_placeholder", "minimum", "shown",
    "needs_selection", "explain",
}


def test_analysis_translation_keys_exist_in_english_and_arabic():
    for language in ("en", "ar"):
        assert REQUIRED_KEYS <= TRANSLATIONS[language].keys()
        assert all(TRANSLATIONS[language][key].strip() for key in REQUIRED_KEYS)


def test_analysis_template_uses_translation_helper_for_visible_labels():
    source = Path("web/templates/analysis.html").read_text(encoding="utf-8")
    for key in REQUIRED_KEYS:
        assert f"t('{key}')" in source
    assert "t(..., count=" not in source


def test_arabic_analysis_page_renders_localized_ui():
    app = create_app()
    app.testing = True
    client = app.test_client()
    client.set_cookie("fivebr_lang", "ar")
    response = client.get("/analysis")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'dir="rtl"' in body
    assert "تحليل وتصفية الاقتراحات" in body
    assert "إجمالي الاقتراحات" in body
    assert "يحتاج مراجعة بشرية" in body
    assert "متوسط الثقة" in body
    assert "ابحث في الدومين أو المزود أو النص" in body
