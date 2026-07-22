from scripts.services.evidence_quality import (
    EvidenceAssessment,
    EvidenceQuality,
    assess_domain_evidence,
    conflict_evidence,
    quality_score,
)


def test_quality_score_mapping():
    assert quality_score(EvidenceQuality.EXACT) == 50
    assert quality_score(EvidenceQuality.STRONG) == 35
    assert quality_score(EvidenceQuality.MODERATE) == 20
    assert quality_score(EvidenceQuality.WEAK) == 10
    assert quality_score(EvidenceQuality.CONFLICT) == 0


def test_exact_domain_evidence():
    assessment = assess_domain_evidence(
        "netflix.com",
        "netflix.com",
    )

    assert isinstance(assessment, EvidenceAssessment)
    assert assessment.quality == EvidenceQuality.EXACT
    assert assessment.score == 50
    assert "exact domain match" in assessment.reason


def test_strong_suffix_evidence():
    assessment = assess_domain_evidence(
        "nrdp.nccp.netflix.com",
        "netflix.com",
    )

    assert assessment.quality == EvidenceQuality.STRONG
    assert assessment.score == 35
    assert "trusted domain suffix match" in assessment.reason


def test_moderate_keyword_evidence():
    assessment = assess_domain_evidence(
        "event.api.example.com",
        "event",
    )

    assert assessment.quality == EvidenceQuality.MODERATE
    assert assessment.score == 20
    assert "keyword match" in assessment.reason


def test_weak_evidence():
    assessment = assess_domain_evidence(
        "example.com",
        "missing",
    )

    assert assessment.quality == EvidenceQuality.WEAK
    assert assessment.score == 10


def test_conflict_evidence():
    assessment = conflict_evidence(
        rule_value="Telemetry",
        knowledge_value="Gaming",
        field_name="category",
    )

    assert assessment.quality == EvidenceQuality.CONFLICT
    assert assessment.score == 0
    assert (
        assessment.reason
        == "conflicting category evidence: "
        "rule=Telemetry, knowledge=Gaming"
    )
