import pytest

from scripts.services.database_evidence_engine import (
    DatabaseEvidence,
)
from scripts.services.evidence_quality import (
    EvidenceQuality,
)
from scripts.services.knowledge_service import (
    KnowledgeEntry,
)
from scripts.services.rule_engine import (
    RuleMatch,
)
from scripts.services.unified_evidence import (
    make_unified_evidence,
)
from scripts.services.unified_evidence_collector import (
    UnifiedEvidenceBundle,
    collect_unified_evidence,
)


def make_sources():
    rule_matches = [
        RuleMatch(
            rule_type="category",
            value="Telemetry",
            score=30,
            reason="matched category keyword: event",
            metadata={
                "keyword": "event",
                "evidence_quality": "MODERATE",
                "evidence_reason": "keyword match: event",
            },
        )
    ]

    knowledge_entries = [
        KnowledgeEntry(
            name="PlayStation Network",
            kind="service",
            keywords=("playstation.net",),
            vendor="Sony PlayStation",
            category="Gaming",
            filter_name="gaming",
            technologies=("gaming",),
        )
    ]

    database_evidence = DatabaseEvidence(
        vendor="Sony PlayStation",
        category="Gaming",
        filter_name="gaming",
        score=20,
        reasons=[
            "matched existing database root: playstation.net"
        ],
        evidence_quality="STRONG",
        evidence_reason=(
            "shared database root match: playstation.net"
        ),
    )

    return (
        rule_matches,
        knowledge_entries,
        database_evidence,
    )


def test_collects_all_three_evidence_sources():
    (
        rule_matches,
        knowledge_entries,
        database_evidence,
    ) = make_sources()

    bundle = collect_unified_evidence(
        "event.api.playstation.net",
        rule_matches=rule_matches,
        knowledge_entries=knowledge_entries,
        database_evidence=database_evidence,
    )

    assert isinstance(
        bundle,
        UnifiedEvidenceBundle,
    )

    assert bundle.domain == (
        "event.api.playstation.net"
    )

    assert len(bundle.by_source("rule")) == 1
    assert len(bundle.by_source("knowledge")) == 3
    assert len(bundle.by_source("database")) == 3
    assert len(bundle.all()) == 7


def test_bundle_filters_and_groups_evidence():
    (
        rule_matches,
        knowledge_entries,
        database_evidence,
    ) = make_sources()

    bundle = collect_unified_evidence(
        "event.api.playstation.net",
        rule_matches=rule_matches,
        knowledge_entries=knowledge_entries,
        database_evidence=database_evidence,
    )

    grouped = bundle.grouped_by_field()

    assert set(grouped) == {
        "vendor",
        "category",
        "filter",
    }

    assert len(bundle.by_field("vendor")) == 2
    assert len(bundle.by_field("category")) == 3
    assert len(bundle.by_field("filter")) == 2


def test_bundle_detects_conflicting_field_values():
    (
        rule_matches,
        knowledge_entries,
        database_evidence,
    ) = make_sources()

    bundle = collect_unified_evidence(
        "event.api.playstation.net",
        rule_matches=rule_matches,
        knowledge_entries=knowledge_entries,
        database_evidence=database_evidence,
    )

    assert bundle.conflicting_fields() == [
        "category"
    ]


def test_bundle_selects_strongest_field_evidence():
    (
        rule_matches,
        knowledge_entries,
        database_evidence,
    ) = make_sources()

    bundle = collect_unified_evidence(
        "event.api.playstation.net",
        rule_matches=rule_matches,
        knowledge_entries=knowledge_entries,
        database_evidence=database_evidence,
    )

    strongest = bundle.strongest("category")

    assert strongest is not None
    assert strongest.source == "knowledge"
    assert strongest.value == "Gaming"
    assert strongest.quality == EvidenceQuality.STRONG
    assert strongest.score == 50


def test_bundle_exposes_explicit_conflict_evidence():
    conflict = make_unified_evidence(
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

    bundle = collect_unified_evidence(
        "event.api.playstation.net",
        additional_evidence=[conflict],
    )

    assert bundle.conflicts() == [conflict]
    assert not conflict.is_positive


def test_bundle_serialization_and_validation():
    (
        rule_matches,
        knowledge_entries,
        database_evidence,
    ) = make_sources()

    bundle = collect_unified_evidence(
        "EVENT.API.PLAYSTATION.NET.",
        rule_matches=rule_matches,
        knowledge_entries=knowledge_entries,
        database_evidence=database_evidence,
    )

    payload = bundle.to_dict()

    assert payload["domain"] == (
        "event.api.playstation.net"
    )
    assert payload["evidence_count"] == 7
    assert payload["conflicting_fields"] == [
        "category"
    ]
    assert len(payload["evidence"]) == 7

    with pytest.raises(
        ValueError,
        match="domain is required",
    ):
        collect_unified_evidence("")
