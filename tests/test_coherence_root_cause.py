from scripts.services.coherence_root_cause import (
    attribute_root_cause,
    attribute_root_causes,
    build_root_cause_report,
)


LEGACY_MAP = {
    "Streaming": "social",
    "Connectivity": "privacy",
    "Telemetry": "telemetry",
}


def coherence(
    *,
    domain: str,
    category: str,
    actual_filter: str,
    expected_filter: str,
    conflict: bool = False,
    ambiguous: bool = False,
):
    return {
        "domain": domain,
        "status": "incoherent",
        "category": category,
        "filter": actual_filter,
        "expected_filter": expected_filter,
        "category_conflict": conflict,
        "filter_conflict": conflict,
        "category_ambiguous": ambiguous,
        "filter_ambiguous": ambiguous,
        "requires_review": True,
    }


def comparison(
    *,
    domain: str,
    sources: list[str],
    score: int = 30,
):
    return {
        "domain": domain,
        "fields": {
            "filter": {
                "preview_sources": sources,
                "preview_score": score,
            }
        },
    }


def test_attributes_legacy_mapping_leakage():
    result = attribute_root_cause(
        coherence(
            domain="api3.shahid.net",
            category="Streaming",
            actual_filter="social",
            expected_filter="streaming",
        ),
        comparison=comparison(
            domain="api3.shahid.net",
            sources=["rule"],
        ),
        configured_filter_map=LEGACY_MAP,
    )

    assert (
        result.root_cause
        == "legacy-mapping-leakage"
    )
    assert result.severity == "medium"


def test_attributes_direct_evidence_conflict():
    result = attribute_root_cause(
        coherence(
            domain="youtubei.googleapis.com",
            category="Streaming",
            actual_filter="telemetry",
            expected_filter="streaming",
            conflict=True,
        ),
        comparison=comparison(
            domain="youtubei.googleapis.com",
            sources=["database"],
            score=35,
        ),
        configured_filter_map=LEGACY_MAP,
    )

    assert (
        result.root_cause
        == "direct-evidence-conflict"
    )
    assert result.severity == "high"
    assert result.filter_sources == (
        "database",
    )


def test_attributes_taxonomy_dimension_collision():
    result = attribute_root_cause(
        coherence(
            domain="metrics2.data.hicloud.com",
            category="Telemetry",
            actual_filter="mobile",
            expected_filter="telemetry",
            conflict=True,
        ),
        comparison=comparison(
            domain="metrics2.data.hicloud.com",
            sources=["knowledge"],
        ),
        configured_filter_map=LEGACY_MAP,
    )

    assert result.root_cause == (
        "possible-taxonomy-dimension-collision"
    )
    assert result.severity == "high"


def test_ambiguous_resolution_has_priority():
    result = attribute_root_cause(
        coherence(
            domain="adservetx.media.net",
            category="Streaming",
            actual_filter="social",
            expected_filter="streaming",
            conflict=True,
            ambiguous=True,
        ),
        comparison=comparison(
            domain="adservetx.media.net",
            sources=["rule"],
        ),
        configured_filter_map=LEGACY_MAP,
    )

    assert (
        result.root_cause
        == "ambiguous-resolution"
    )
    assert result.severity == "critical"


def test_summary_and_report():
    assessments = [
        coherence(
            domain="legacy.example",
            category="Connectivity",
            actual_filter="privacy",
            expected_filter="connectivity",
        ),
        coherence(
            domain="direct.example",
            category="Streaming",
            actual_filter="telemetry",
            expected_filter="streaming",
            conflict=True,
        ),
    ]

    comparisons = [
        comparison(
            domain="legacy.example",
            sources=["rule"],
        ),
        comparison(
            domain="direct.example",
            sources=["database"],
        ),
    ]

    summary = attribute_root_causes(
        assessments,
        comparisons=comparisons,
        configured_filter_map=LEGACY_MAP,
    )

    assert summary.domains_inspected == 2
    assert summary.domains_attributed == 2

    assert summary.causes[
        "legacy-mapping-leakage"
    ] == 1

    assert summary.causes[
        "direct-evidence-conflict"
    ] == 1

    report = build_root_cause_report(
        summary
    )

    assert (
        "5ibr Coherence Root-Cause Attribution"
        in report
    )
    assert "legacy.example" in report
    assert "direct.example" in report
