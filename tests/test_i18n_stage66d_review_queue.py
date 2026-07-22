from pathlib import Path

from web.app import create_app
from web.i18n import TRANSLATIONS


TEMPLATE = Path("web/templates/review_queue.html")


def test_stage66d_review_queue_translation_catalog_is_complete():
    required = {
        "needs_review",
        "approved_candidates",
        "search_domain",
        "filter_results",
        "reset",
        "guardrail_shadow",
        "blocking_policy_reason",
        "blocking_policy_source",
        "would_block",
        "allowed",
        "requirement",
        "approval_evidence",
        "reason",
        "document_approval_reason",
        "impact_testing_confirmed",
        "blocking_policy_override_confirmed",
        "manual_review_confirmed",
        "shadow_mode_approval_note",
        "no_suggestions_found",
    }
    assert required <= TRANSLATIONS["en"].keys()
    assert required <= TRANSLATIONS["ar"].keys()
    assert all(TRANSLATIONS["en"][key] != TRANSLATIONS["ar"][key] for key in required)


def test_stage66d_review_queue_template_uses_translation_keys():
    source = TEMPLATE.read_text(encoding="utf-8")
    required_calls = {
        "t('needs_review')",
        "t('approved_candidates')",
        "t('search_domain')",
        "t('guardrail_shadow')",
        "t('approval_evidence')",
        "t('document_approval_reason')",
        "t('shadow_mode_approval_note')",
        "t('no_suggestions_found')",
    }
    assert required_calls <= {call for call in required_calls if call in source}
    assert "action='approved'" in source
    assert "action='rejected'" in source
    assert "action='ignored'" in source


def test_stage66d_arabic_review_queue_renders_localized_ui():
    app = create_app()
    app.testing = True
    client = app.test_client()
    client.set_cookie("fivebr_lang", "ar")

    response = client.get("/review-queue")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'dir="rtl"' in body
    assert "قائمة المراجعة" in body
    assert "مرشحون للاعتماد" in body
    assert "البحث عن دومين" in body
    assert "لم يتم العثور على اقتراحات." in body or "example" in body
    assert "Approved Candidates" not in body
