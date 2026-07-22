from scripts.services.intelligence_summary_service import (
    build_intelligence_summary,
    validate_decision_engine,
    validate_explain_engine,
)


def test_decision_engine_dynamic_health():
    ok, errors = validate_decision_engine()

    assert ok
    assert errors == []


def test_explain_engine_dynamic_health():
    ok, errors = validate_explain_engine()

    assert ok
    assert errors == []


def test_intelligence_summary_has_independent_statuses():
    summary = build_intelligence_summary()

    assert summary.knowledge_status == "Healthy"
    assert summary.rule_status == "Healthy"
    assert summary.decision_status == "Healthy"
    assert summary.explain_status == "Healthy"
    assert summary.status == "Healthy"
