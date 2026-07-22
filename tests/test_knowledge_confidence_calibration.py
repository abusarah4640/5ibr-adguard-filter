from scripts.services.analyzer_service import analyze_domain
from scripts.services.knowledge_engine import knowledge_match_score
from scripts.services.knowledge_service import KnowledgeEntry


def test_domain_suffix_knowledge_match_has_strong_weight():
    entry = KnowledgeEntry(
        name="LG Smart TV",
        kind="product",
        keywords=("lgtvsdp.com",),
        vendor="LG",
        category="Smart TV",
        filter_name="smart-tv",
    )

    assert knowledge_match_score("sa.rdx2.lgtvsdp.com", entry) == 50


def test_generic_keyword_knowledge_match_keeps_lower_weight():
    entry = KnowledgeEntry(
        name="Example Service",
        kind="service",
        keywords=("event",),
        vendor="Example",
        category="Telemetry",
        filter_name="telemetry",
    )

    assert knowledge_match_score("event.api.example.com", entry) == 20


def test_lg_smart_tv_reaches_review_confidence():
    result = analyze_domain(
        "sa.rdx2.lgtvsdp.com",
        rows=[],
    )

    assert result.suggested_vendor == "LG"
    assert result.suggested_category == "Smart TV"
    assert result.suggested_filter == "smart-tv"
    assert result.confidence >= 50
    assert result.recommendation == "review"
