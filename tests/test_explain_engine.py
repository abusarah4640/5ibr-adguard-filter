from scripts.services.explain_engine import (
    Explanation,
    explanation_to_reason,
    explanations_to_reasons,
    group_explanations_by_source,
    make_explanation,
    normalize_explanation_text,
    reasons_to_explanations,
    total_explanation_weight,
)


def test_make_explanation():
    explanation = make_explanation(
        source="rule",
        message="matched category keyword: video",
        weight=30,
        metadata={"keyword": "video"},
    )

    assert isinstance(explanation, Explanation)
    assert explanation.source == "rule"
    assert explanation.message == "matched category keyword: video"
    assert explanation.weight == 30
    assert explanation.metadata["keyword"] == "video"


def test_normalize_explanation_text():
    assert normalize_explanation_text("  hello  ") == "hello"
    assert normalize_explanation_text("") == ""


def test_explanation_to_reason():
    explanation = make_explanation(
        source="knowledge",
        message="knowledge matched service: Netflix via keyword: nrdp",
        weight=20,
    )

    assert explanation_to_reason(explanation) == "knowledge matched service: Netflix via keyword: nrdp"


def test_explanations_to_reasons_deduplicates():
    explanations = [
        make_explanation(source="rule", message="same reason", weight=10),
        make_explanation(source="knowledge", message="same reason", weight=20),
        make_explanation(source="db", message="different reason", weight=30),
    ]

    assert explanations_to_reasons(explanations) == [
        "same reason",
        "different reason",
    ]


def test_reasons_to_explanations():
    explanations = reasons_to_explanations(
        ["reason one", "reason two"],
        source="legacy",
        weight=5,
    )

    assert len(explanations) == 2
    assert explanations[0].source == "legacy"
    assert explanations[0].weight == 5


def test_total_explanation_weight():
    explanations = [
        make_explanation(source="rule", message="a", weight=10),
        make_explanation(source="rule", message="b", weight=15),
    ]

    assert total_explanation_weight(explanations) == 25


def test_group_explanations_by_source():
    explanations = [
        make_explanation(source="rule", message="a", weight=10),
        make_explanation(source="knowledge", message="b", weight=20),
        make_explanation(source="rule", message="c", weight=5),
    ]

    grouped = group_explanations_by_source(explanations)

    assert len(grouped["rule"]) == 2
    assert len(grouped["knowledge"]) == 1
