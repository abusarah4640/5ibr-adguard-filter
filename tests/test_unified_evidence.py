import pytest

from scripts.services.evidence_quality import EvidenceQuality
from scripts.services.unified_evidence import (
    UnifiedEvidence,
    evidence_total,
    group_evidence_by_field,
    make_unified_evidence,
    strongest_evidence,
)


def test_create_unified_evidence():
    evidence = make_unified_evidence(
        source="knowledge",
        field="vendor",
        value="Netflix",
        quality=EvidenceQuality.STRONG,
        score=50,
        reason="trusted domain suffix match: netflix.com",
        metadata={
            "pattern": "netflix.com",
        },
    )

    assert isinstance(evidence, UnifiedEvidence)
    assert evidence.source == "knowledge"
    assert evidence.field == "vendor"
    assert evidence.value == "Netflix"
    assert evidence.quality == EvidenceQuality.STRONG
    assert evidence.score == 50
    assert evidence.is_positive
    assert not evidence.is_conflict


def test_unified_evidence_serialization():
    evidence = make_unified_evidence(
        source="rule",
        field="category",
        value="Telemetry",
        quality=EvidenceQuality.MODERATE,
        score=30,
        reason="matched category keyword: event",
    )

    assert evidence.to_dict() == {
        "source": "rule",
        "field": "category",
        "value": "Telemetry",
        "quality": "MODERATE",
        "score": 30,
        "reason": "matched category keyword: event",
        "metadata": {},
    }


def test_conflict_evidence_is_not_positive():
    evidence = make_unified_evidence(
        source="analyzer",
        field="category",
        value="Gaming",
        quality=EvidenceQuality.CONFLICT,
        score=0,
        reason=(
            "conflicting category evidence: "
            "rule=Telemetry, knowledge=Gaming"
        ),
    )

    assert evidence.is_conflict
    assert not evidence.is_positive


def test_evidence_total_ignores_conflicts_and_caps_at_100():
    evidence_items = [
        make_unified_evidence(
            source="knowledge",
            field="vendor",
            value="Netflix",
            quality=EvidenceQuality.STRONG,
            score=50,
            reason="knowledge match",
        ),
        make_unified_evidence(
            source="rule",
            field="category",
            value="Streaming",
            quality=EvidenceQuality.MODERATE,
            score=30,
            reason="category rule match",
        ),
        make_unified_evidence(
            source="database",
            field="filter",
            value="streaming",
            quality=EvidenceQuality.EXACT,
            score=35,
            reason="database exact match",
        ),
        make_unified_evidence(
            source="analyzer",
            field="category",
            value="Streaming",
            quality=EvidenceQuality.CONFLICT,
            score=0,
            reason="conflicting category evidence",
        ),
    ]

    assert evidence_total(evidence_items) == 100


def test_group_and_select_strongest_evidence():
    weak = make_unified_evidence(
        source="rule",
        field="vendor",
        value="Example",
        quality=EvidenceQuality.MODERATE,
        score=35,
        reason="rule match",
    )

    strong = make_unified_evidence(
        source="knowledge",
        field="vendor",
        value="Netflix",
        quality=EvidenceQuality.STRONG,
        score=50,
        reason="knowledge suffix match",
    )

    category = make_unified_evidence(
        source="rule",
        field="category",
        value="Streaming",
        quality=EvidenceQuality.MODERATE,
        score=30,
        reason="category rule match",
    )

    grouped = group_evidence_by_field(
        [weak, strong, category]
    )

    assert set(grouped) == {
        "vendor",
        "category",
    }

    assert grouped["vendor"] == [
        weak,
        strong,
    ]

    assert strongest_evidence(
        grouped["vendor"]
    ) == strong


def test_unified_evidence_rejects_invalid_data():
    with pytest.raises(
        ValueError,
        match="unsupported evidence source",
    ):
        make_unified_evidence(
            source="invalid",
            field="vendor",
            value="Example",
            quality=EvidenceQuality.WEAK,
            score=10,
            reason="invalid source",
        )

    with pytest.raises(
        ValueError,
        match="score must be between",
    ):
        make_unified_evidence(
            source="rule",
            field="vendor",
            value="Example",
            quality=EvidenceQuality.WEAK,
            score=101,
            reason="invalid score",
        )
