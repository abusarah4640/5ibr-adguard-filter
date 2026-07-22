from pathlib import Path

from web.i18n import TRANSLATIONS


TEMPLATE = Path("web/templates/releases.html")


def test_stage66e_releases_template_uses_translation_keys():
    source = TEMPLATE.read_text(encoding="utf-8")

    assert "{{ t('build_filters') }}" in source
    assert "{{ t('action') }}" in source
    assert "Build {{ t('filter') }}s" not in source
    assert "<th>Action</th>" not in source


def test_stage66e_releases_keys_exist_in_both_languages():
    required = {
        "releases",
        "build_filters",
        "file",
        "size",
        "last_modified",
        "action",
        "download",
        "no_releases",
    }

    for language in ("en", "ar"):
        assert required <= TRANSLATIONS[language].keys()


def test_stage66e_releases_arabic_labels_are_localized():
    ar = TRANSLATIONS["ar"]

    assert ar["releases"] == "الإصدارات"
    assert ar["build_filters"] == "بناء الفلاتر"
    assert ar["action"] == "الإجراء"
    assert ar["download"] == "فتح / تحميل"
    assert ar["no_releases"] == "لا توجد ملفات إصدار. شغّل البناء أولًا."
