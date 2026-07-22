from scripts.services.intelligence_summary_service import (
    IntelligenceSummary,
    build_intelligence_summary,
)


def test_build_intelligence_summary():
    summary = build_intelligence_summary()

    assert isinstance(summary, IntelligenceSummary)
    assert summary.knowledge_entries >= 1
    assert summary.vendor_groups >= 1
    assert summary.category_groups >= 1
    assert summary.filter_mappings >= 1
    assert summary.status == "Healthy"
