from scripts.services.evidence_quality import EvidenceQuality
from scripts.services.rule_engine import (
    match_category_rules,
    match_vendor_rules,
    rule_evidence_assessment,
)


def test_vendor_suffix_rule_has_strong_evidence():
    assessment = rule_evidence_assessment(
        "api.netflix.com",
        "netflix.com",
    )

    assert assessment.quality == EvidenceQuality.STRONG
    assert assessment.score == 35


def test_vendor_rule_includes_evidence_metadata():
    matches = match_vendor_rules(
        "api.netflix.com",
        {
            "Netflix": ["netflix.com"],
        },
    )

    assert len(matches) == 1

    match = matches[0]

    # Keep established analyzer score unchanged.
    assert match.score == 35
    assert match.metadata["pattern"] == "netflix.com"
    assert match.metadata["evidence_quality"] == "STRONG"
    assert "trusted domain suffix match" in match.metadata[
        "evidence_reason"
    ]


def test_category_rule_includes_moderate_evidence_metadata():
    matches = match_category_rules(
        "event.api.example.com",
        {
            "Telemetry": ["event"],
        },
    )

    assert len(matches) == 1

    match = matches[0]

    # Keep established category score unchanged.
    assert match.score == 30
    assert match.metadata["keyword"] == "event"
    assert match.metadata["evidence_quality"] == "MODERATE"
    assert "keyword match" in match.metadata["evidence_reason"]
