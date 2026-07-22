from pathlib import Path

from web.i18n import TRANSLATIONS


def test_stage66a_dashboard_keys_exist_in_both_languages():
    required = {
        "guardrail_readiness", "progress_toward_ready",
        "readiness_diagnostics", "readiness_decision_engine",
        "manual_approval_gate", "audit_decision_archive",
        "readiness_history_trends", "visibility_only",
    }
    assert required <= TRANSLATIONS["en"].keys()
    assert required <= TRANSLATIONS["ar"].keys()


def test_stage66a_dashboard_uses_translation_calls():
    source = Path("web/templates/dashboard.html").read_text(encoding="utf-8")
    assert "{{ t('guardrail_readiness') }}" in source
    assert "{{ t('progress_toward_ready') }}" in source
    assert "{{ t('readiness_diagnostics') }}" in source
    assert "{{ t('visibility_only') }}" in source
