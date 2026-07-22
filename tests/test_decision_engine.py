from scripts.services.decision_engine import (
    Decision,
    build_decision,
    clamp_confidence,
    decision_reasons,
    legacy_reason_explanation,
    recommendation_from_confidence,
)
from scripts.services.explain_engine import make_explanation


def test_clamp_confidence():
    assert clamp_confidence(-10) == 0
    assert clamp_confidence(50) == 50
    assert clamp_confidence(150) == 100


def test_recommendation_from_confidence():
    assert recommendation_from_confidence(95) == "approved-candidate"
    assert recommendation_from_confidence(50) == "review"
    assert recommendation_from_confidence(10) == "unknown"


def test_build_decision():
    explanations = [
        make_explanation(source="rule", message="matched vendor", weight=35),
        make_explanation(source="rule", message="matched category", weight=30),
    ]

    decision = build_decision(
        vendor="Netflix",
        category="Streaming",
        filter_name="streaming",
        explanations=explanations,
    )

    assert isinstance(decision, Decision)
    assert decision.vendor == "Netflix"
    assert decision.category == "Streaming"
    assert decision.filter_name == "streaming"
    assert decision.confidence == 65
    assert decision.recommendation == "review"


def test_build_decision_clamps_confidence():
    explanations = [
        make_explanation(source="rule", message="a", weight=80),
        make_explanation(source="db", message="b", weight=80),
    ]

    decision = build_decision(explanations=explanations)

    assert decision.confidence == 100
    assert decision.recommendation == "approved-candidate"


def test_decision_reasons():
    decision = build_decision(
        explanations=[
            make_explanation(source="rule", message="reason one", weight=10),
            make_explanation(source="rule", message="reason one", weight=10),
            make_explanation(source="db", message="reason two", weight=20),
        ]
    )

    assert decision_reasons(decision) == ["reason one", "reason two"]


def test_unknown_decision_has_default_reason():
    decision = build_decision()

    assert decision.recommendation == "unknown"
    assert decision_reasons(decision) == ["no local analyzer rules matched"]


def test_legacy_reason_explanation():
    explanation = legacy_reason_explanation(
        "matched existing database root: netflix.com",
        source="database",
        weight=20,
    )

    assert explanation.source == "database"
    assert explanation.message == "matched existing database root: netflix.com"
    assert explanation.weight == 20
