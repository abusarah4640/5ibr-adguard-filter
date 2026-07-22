from scripts.services.evidence_quality import (
    EvidenceQuality,
)
from scripts.services.unified_evidence import (
    make_unified_evidence,
)
from scripts.services.unified_evidence_collector import (
    UnifiedEvidenceBundle,
    evidence_value_groups,
    normalize_evidence_value,
)


def make_evidence(
    *,
    source: str,
    field: str,
    value: str,
    quality: EvidenceQuality = EvidenceQuality.STRONG,
    score: int = 35,
):
    return make_unified_evidence(
        source=source,
        field=field,
        value=value,
        quality=quality,
        score=score,
        reason=f"{source} evidence for {value}",
    )


def test_normalize_evidence_value():
    assert (
        normalize_evidence_value(
            "  Sony   PlayStation "
        )
        == "sony playstation"
    )

    assert (
        normalize_evidence_value("SMART-TV")
        == "smart tv"
    )

    assert (
        normalize_evidence_value("smart_tv")
        == "smart tv"
    )


def test_equivalent_values_do_not_create_conflict():
    bundle = UnifiedEvidenceBundle(
        domain="example.test",
        evidence=[
            make_evidence(
                source="rule",
                field="vendor",
                value="Sony PlayStation",
            ),
            make_evidence(
                source="knowledge",
                field="vendor",
                value="sony  playstation",
                score=50,
            ),
            make_evidence(
                source="database",
                field="vendor",
                value="SONY-PLAYSTATION",
                score=20,
            ),
        ],
    )

    assert bundle.value_conflicts() == {}
    assert bundle.conflicting_fields() == []
    assert not bundle.has_conflicts()


def test_different_semantic_values_create_value_conflict():
    telemetry = make_evidence(
        source="rule",
        field="category",
        value="Telemetry",
        quality=EvidenceQuality.MODERATE,
        score=30,
    )

    gaming = make_evidence(
        source="knowledge",
        field="category",
        value="Gaming",
        score=50,
    )

    bundle = UnifiedEvidenceBundle(
        domain="event.api.example.test",
        evidence=[
            telemetry,
            gaming,
        ],
    )

    conflicts = bundle.value_conflicts()

    assert set(conflicts) == {
        "category",
    }

    assert set(conflicts["category"]) == {
        "telemetry",
        "gaming",
    }

    assert bundle.conflicting_fields() == [
        "category"
    ]

    assert bundle.has_conflicts()


def test_explicit_conflicts_are_separate_from_value_conflicts():
    explicit = make_evidence(
        source="analyzer",
        field="category",
        value="Gaming",
        quality=EvidenceQuality.CONFLICT,
        score=0,
    )

    supporting = make_evidence(
        source="knowledge",
        field="category",
        value="Gaming",
        score=50,
    )

    bundle = UnifiedEvidenceBundle(
        domain="example.test",
        evidence=[
            explicit,
            supporting,
        ],
    )

    assert bundle.explicit_conflicts() == [
        explicit
    ]

    assert bundle.value_conflicts() == {}

    assert bundle.conflicting_fields() == [
        "category"
    ]

    assert bundle.has_conflicts()


def test_evidence_value_groups_and_serialization():
    items = [
        make_evidence(
            source="rule",
            field="filter",
            value="Smart TV",
            score=35,
        ),
        make_evidence(
            source="knowledge",
            field="filter",
            value="smart-tv",
            score=50,
        ),
        make_evidence(
            source="database",
            field="filter",
            value="streaming",
            score=20,
        ),
    ]

    groups = evidence_value_groups(items)

    assert set(groups) == {
        "smart tv",
        "streaming",
    }

    bundle = UnifiedEvidenceBundle(
        domain="tv.example.test",
        evidence=items,
    )

    payload = bundle.to_dict()

    assert payload["has_conflicts"] is True
    assert payload["conflicting_fields"] == [
        "filter"
    ]
    assert payload["explicit_conflict_count"] == 0
    assert payload["value_conflicts"] == {
        "filter": [
            "smart tv",
            "streaming",
        ]
    }
