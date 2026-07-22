from scripts.services.evidence_quality import EvidenceQuality
from scripts.services.knowledge_evidence_adapter import (
    knowledge_entry_to_unified_evidence,
    matched_knowledge_keywords,
)
from scripts.services.knowledge_service import KnowledgeEntry
from scripts.services.unified_evidence import (
    group_evidence_by_field,
)


def make_lg_entry() -> KnowledgeEntry:
    return KnowledgeEntry(
        name="LG Smart TV",
        kind="product",
        keywords=(
            "lgtvsdp.com",
            "lge.com",
            "lgsmartad.com",
        ),
        vendor="LG",
        category="Smart TV",
        filter_name="smart-tv",
        technologies=(
            "smart-tv",
            "telemetry",
        ),
    )


def test_matched_knowledge_keywords():
    entry = make_lg_entry()

    matched = matched_knowledge_keywords(
        "sa.rdx2.lgtvsdp.com",
        entry,
    )

    assert matched == ("lgtvsdp.com",)


def test_adapter_creates_vendor_category_and_filter_evidence():
    entry = make_lg_entry()

    evidence_items = knowledge_entry_to_unified_evidence(
        "sa.rdx2.lgtvsdp.com",
        entry,
    )

    assert len(evidence_items) == 3

    grouped = group_evidence_by_field(evidence_items)

    assert set(grouped) == {
        "vendor",
        "category",
        "filter",
    }

    assert grouped["vendor"][0].value == "LG"
    assert grouped["category"][0].value == "Smart TV"
    assert grouped["filter"][0].value == "smart-tv"


def test_adapter_preserves_knowledge_quality_and_score():
    entry = make_lg_entry()

    evidence_items = knowledge_entry_to_unified_evidence(
        "sa.rdx2.lgtvsdp.com",
        entry,
    )

    for evidence in evidence_items:
        assert evidence.source == "knowledge"
        assert evidence.quality == EvidenceQuality.STRONG
        assert evidence.score == 50
        assert "trusted domain suffix match" in evidence.reason
        assert evidence.metadata["entry_name"] == "LG Smart TV"
        assert evidence.metadata["matched_keywords"] == [
            "lgtvsdp.com"
        ]


def test_adapter_returns_empty_for_unmatched_entry():
    entry = make_lg_entry()

    evidence_items = knowledge_entry_to_unified_evidence(
        "unrelated.example.com",
        entry,
    )

    assert evidence_items == []


def test_adapter_skips_unknown_fields():
    entry = KnowledgeEntry(
        name="Partial Knowledge",
        kind="service",
        keywords=("partial.example.com",),
        vendor="Example",
        category="Unknown",
        filter_name="unknown",
    )

    evidence_items = knowledge_entry_to_unified_evidence(
        "api.partial.example.com",
        entry,
    )

    assert len(evidence_items) == 1
    assert evidence_items[0].field == "vendor"
    assert evidence_items[0].value == "Example"
