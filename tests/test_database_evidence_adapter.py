from scripts.services.database_evidence_adapter import (
    database_evidence_to_unified_evidence,
)
from scripts.services.database_evidence_engine import (
    DatabaseEvidence,
    match_database_evidence,
)
from scripts.services.evidence_quality import (
    EvidenceQuality,
)
from scripts.services.unified_evidence import (
    group_evidence_by_field,
)


def test_database_evidence_creates_three_unified_items():
    evidence = match_database_evidence(
        "nrdp.netflix.com",
        [
            {
                "Domain": "api.netflix.com",
                "Vendor": "Netflix",
                "Category": "Streaming",
                "Filter": "streaming",
            }
        ],
    )

    evidence_items = (
        database_evidence_to_unified_evidence(
            evidence
        )
    )

    assert len(evidence_items) == 3

    grouped = group_evidence_by_field(
        evidence_items
    )

    assert set(grouped) == {
        "vendor",
        "category",
        "filter",
    }

    assert grouped["vendor"][0].value == "Netflix"
    assert (
        grouped["category"][0].value
        == "Streaming"
    )
    assert (
        grouped["filter"][0].value
        == "streaming"
    )


def test_database_adapter_preserves_quality_and_score():
    evidence = match_database_evidence(
        "nrdp.netflix.com",
        [
            {
                "Domain": "api.netflix.com",
                "Vendor": "Netflix",
                "Category": "Streaming",
                "Filter": "streaming",
            }
        ],
    )

    evidence_items = (
        database_evidence_to_unified_evidence(
            evidence
        )
    )

    for item in evidence_items:
        assert item.source == "database"
        assert item.quality == EvidenceQuality.STRONG
        assert item.score == 20
        assert (
            item.reason
            == "shared database root match: netflix.com"
        )
        assert (
            item.metadata["database_score"]
            == 20
        )
        assert (
            item.metadata["evidence_quality"]
            == "STRONG"
        )


def test_exact_database_evidence_preserves_exact_quality():
    evidence = match_database_evidence(
        "api.netflix.com",
        [
            {
                "Domain": "api.netflix.com",
                "Vendor": "Netflix",
                "Category": "Streaming",
                "Filter": "streaming",
            }
        ],
    )

    evidence_items = (
        database_evidence_to_unified_evidence(
            evidence
        )
    )

    assert len(evidence_items) == 3

    for item in evidence_items:
        assert item.quality == EvidenceQuality.EXACT
        assert item.score == 35


def test_database_adapter_skips_unknown_values():
    evidence = DatabaseEvidence(
        vendor="Unknown",
        category="Unknown",
        filter_name="unknown",
        score=20,
        reasons=["database root match"],
        evidence_quality="STRONG",
        evidence_reason="shared database root match",
    )

    assert (
        database_evidence_to_unified_evidence(
            evidence
        )
        == []
    )


def test_database_adapter_returns_empty_without_score():
    evidence = DatabaseEvidence(
        vendor="Netflix",
        category="Streaming",
        filter_name="streaming",
        score=0,
        reasons=[],
        evidence_quality="",
        evidence_reason="",
    )

    assert (
        database_evidence_to_unified_evidence(
            evidence
        )
        == []
    )
