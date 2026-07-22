import pytest

from scripts.services.evidence_quality import EvidenceQuality
from scripts.services.rule_engine import (
    RuleMatch,
    match_category_rules,
    match_vendor_rules,
)
from scripts.services.rule_evidence_adapter import (
    rule_match_to_unified_evidence,
    rule_matches_to_unified_evidence,
)
from scripts.services.unified_evidence import (
    group_evidence_by_field,
)


def test_vendor_rule_match_to_unified_evidence():
    matches = match_vendor_rules(
        "api.netflix.com",
        {
            "Netflix": ["netflix.com"],
        },
    )

    evidence = rule_match_to_unified_evidence(
        matches[0]
    )

    assert evidence.source == "rule"
    assert evidence.field == "vendor"
    assert evidence.value == "Netflix"
    assert evidence.quality == EvidenceQuality.STRONG
    assert evidence.score == 35
    assert (
        evidence.metadata["pattern"]
        == "netflix.com"
    )
    assert evidence.metadata["rule_type"] == "vendor"


def test_category_rule_match_to_unified_evidence():
    matches = match_category_rules(
        "event.api.example.com",
        {
            "Telemetry": ["event"],
        },
    )

    evidence = rule_match_to_unified_evidence(
        matches[0]
    )

    assert evidence.source == "rule"
    assert evidence.field == "category"
    assert evidence.value == "Telemetry"
    assert evidence.quality == EvidenceQuality.MODERATE
    assert evidence.score == 30
    assert evidence.metadata["keyword"] == "event"
    assert evidence.metadata["rule_type"] == "category"


def test_multiple_rule_matches_are_grouped_by_field():
    matches = [
        *match_vendor_rules(
            "event.api.netflix.com",
            {
                "Netflix": ["netflix.com"],
            },
        ),
        *match_category_rules(
            "event.api.netflix.com",
            {
                "Telemetry": ["event"],
            },
        ),
    ]

    evidence_items = (
        rule_matches_to_unified_evidence(matches)
    )

    assert len(evidence_items) == 2

    grouped = group_evidence_by_field(
        evidence_items
    )

    assert set(grouped) == {
        "vendor",
        "category",
    }

    assert grouped["vendor"][0].value == "Netflix"
    assert (
        grouped["category"][0].value
        == "Telemetry"
    )


def test_adapter_uses_match_reason_as_fallback():
    match = RuleMatch(
        rule_type="filter",
        value="privacy",
        score=10,
        reason="fallback filter rule",
        metadata={},
    )

    evidence = rule_match_to_unified_evidence(
        match
    )

    assert evidence.field == "filter"
    assert evidence.value == "privacy"
    assert evidence.quality == EvidenceQuality.MODERATE
    assert evidence.reason == "fallback filter rule"
    assert (
        evidence.metadata["original_reason"]
        == "fallback filter rule"
    )


def test_adapter_rejects_unknown_rule_type():
    match = RuleMatch(
        rule_type="unsupported",
        value="Example",
        score=10,
        reason="unsupported rule",
        metadata={},
    )

    with pytest.raises(
        ValueError,
        match="unsupported rule match type",
    ):
        rule_match_to_unified_evidence(match)
