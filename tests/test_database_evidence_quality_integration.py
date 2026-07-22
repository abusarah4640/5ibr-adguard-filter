from scripts.services.database_evidence_engine import (
    database_evidence_assessment,
    match_database_evidence,
)
from scripts.services.evidence_quality import EvidenceQuality


def test_exact_database_match_has_exact_quality():
    assessment = database_evidence_assessment(
        "api.netflix.com",
        "api.netflix.com",
    )

    assert assessment.quality == EvidenceQuality.EXACT
    assert assessment.score == 50


def test_shared_root_database_match_has_strong_quality():
    assessment = database_evidence_assessment(
        "nrdp.netflix.com",
        "api.netflix.com",
    )

    assert assessment.quality == EvidenceQuality.STRONG
    assert assessment.score == 35
    assert (
        assessment.reason
        == "shared database root match: netflix.com"
    )


def test_database_evidence_exposes_quality_metadata():
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

    # Preserve established analyzer score.
    assert evidence.score == 20

    assert evidence.vendor == "Netflix"
    assert evidence.category == "Streaming"
    assert evidence.filter_name == "streaming"

    assert evidence.evidence_quality == "STRONG"
    assert (
        evidence.evidence_reason
        == "shared database root match: netflix.com"
    )
