from scripts.services.evidence_quality import EvidenceQuality
from scripts.services.knowledge_engine import (
    knowledge_match_assessment,
    knowledge_match_score,
)
from scripts.services.knowledge_service import KnowledgeEntry


def test_knowledge_exact_match_uses_exact_quality():
    entry = KnowledgeEntry(
        name="Exact Service",
        kind="service",
        keywords=("service.example.com",),
        vendor="Example",
        category="Testing",
        filter_name="testing",
    )

    assessment = knowledge_match_assessment(
        "service.example.com",
        entry,
    )

    assert assessment.quality == EvidenceQuality.EXACT
    assert knowledge_match_score(
        "service.example.com",
        entry,
    ) == 50


def test_knowledge_suffix_match_uses_strong_quality_with_calibration():
    entry = KnowledgeEntry(
        name="LG Smart TV",
        kind="product",
        keywords=("lgtvsdp.com",),
        vendor="LG",
        category="Smart TV",
        filter_name="smart-tv",
    )

    assessment = knowledge_match_assessment(
        "sa.rdx2.lgtvsdp.com",
        entry,
    )

    assert assessment.quality == EvidenceQuality.STRONG
    assert assessment.score == 35
    assert knowledge_match_score(
        "sa.rdx2.lgtvsdp.com",
        entry,
    ) == 50


def test_knowledge_generic_keyword_uses_moderate_quality():
    entry = KnowledgeEntry(
        name="Generic Service",
        kind="service",
        keywords=("event",),
        vendor="Example",
        category="Telemetry",
        filter_name="telemetry",
    )

    assessment = knowledge_match_assessment(
        "event.api.example.com",
        entry,
    )

    assert assessment.quality == EvidenceQuality.MODERATE
    assert knowledge_match_score(
        "event.api.example.com",
        entry,
    ) == 20
