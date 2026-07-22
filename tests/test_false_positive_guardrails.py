import json

from scripts.services.analyzer_service import analyze_domain
from scripts.services.decision_engine import (
    apply_confidence_guardrails,
    build_decision,
)
from scripts.services.explain_engine import make_explanation


def test_conflicting_evidence_caps_approved_candidate():
    decision = build_decision(
        vendor="Example",
        category="Gaming",
        filter_name="gaming",
        explanations=[
            make_explanation(
                source="rule",
                message="rule evidence",
                weight=50,
            ),
            make_explanation(
                source="knowledge",
                message="knowledge evidence",
                weight=50,
            ),
        ],
    )

    guarded = apply_confidence_guardrails(
        decision,
        conflicting_evidence=True,
    )

    assert decision.confidence == 100
    assert decision.recommendation == "approved-candidate"

    assert guarded.confidence == 89
    assert guarded.recommendation == "review"


def test_non_conflicting_decision_is_unchanged():
    decision = build_decision(
        vendor="Example",
        category="Gaming",
        filter_name="gaming",
        explanations=[
            make_explanation(
                source="knowledge",
                message="knowledge evidence",
                weight=50,
            )
        ],
    )

    guarded = apply_confidence_guardrails(
        decision,
        conflicting_evidence=False,
    )

    assert guarded == decision
    assert guarded.confidence == 50
    assert guarded.recommendation == "review"


def test_generic_rule_conflict_cannot_auto_approve(tmp_path):
    config_path = tmp_path / "analyzer.json"
    config_path.write_text(
        json.dumps(
            {
                "vendor_patterns": {
                    "Sony PlayStation": [
                        "playstation.net"
                    ]
                },
                "category_keywords": {
                    "Telemetry": [
                        "event"
                    ]
                },
                "filter_map": {
                    "Telemetry": "telemetry",
                    "Gaming": "gaming"
                },
            }
        ),
        encoding="utf-8",
    )

    result = analyze_domain(
        "event.api.np.km.playstation.net",
        config_path=config_path,
        rows=[],
    )

    assert result.suggested_vendor == "Sony PlayStation"
    assert result.suggested_category == "Gaming"
    assert result.suggested_filter == "gaming"

    assert result.confidence == 89
    assert result.recommendation == "review"

    assert any(
        "conflicting category evidence" in reason
        for reason in result.reasons
    )
