from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_analysis_translates_dynamic_recommendations():
    text = Path("web/templates/analysis.html").read_text(encoding="utf-8")
    assert "t('rec_' ~ r|replace('-', '_'))" in text
    assert "t('rec_' ~ row.get('Recommendation','unknown')|replace('-', '_'))" in text


def test_dashboard_translates_readiness_runtime_values():
    text = Path("web/templates/dashboard.html").read_text(encoding="utf-8")
    assert "readiness_status_" in text
    assert "readiness_check_" in text
    assert "readiness_guidance_" in text
    assert "decision_rule_" in text
    assert "decision_detail_" in text
    assert "event_" in text
    assert "trend_" in text


def test_action_pages_translate_exit_code_label():
    for name in ("analyze.html", "analyze_log.html", "output.html"):
        text = Path("web/templates", name).read_text(encoding="utf-8")
        assert "{{ t('exit_code') }}" in text
        assert "Exit code:" not in text


def test_stage67a_keys_exist_in_both_languages():
    text = Path("web/i18n.py").read_text(encoding="utf-8")
    required = {
        "exit_code", "readiness_status_not_ready", "readiness_status_ready_for_review",
        "readiness_check_guardrail_coverage", "readiness_guidance_guardrail_coverage",
        "decision_rule_current_readiness", "decision_detail_current_readiness",
        "event_decision_observed", "trend_improving", "no_results",
    }
    for key in required:
        assert text.count(repr(key) + ":") >= 2
