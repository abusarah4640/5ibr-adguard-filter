from types import SimpleNamespace

from scripts.services.evidence_quality import (
    EvidenceQuality,
)
from scripts.services.shadow_comparison_service import (
    ShadowComparison,
    compare_analyzer_result,
    compare_analyzer_with_resolution,
    compare_shadow_field,
)
from scripts.services.unified_evidence import (
    make_unified_evidence,
)
from scripts.services.unified_evidence_collector import (
    UnifiedEvidenceBundle,
)
from scripts.services.unified_evidence_resolver import (
    resolve_unified_evidence,
)


def evidence(
    *,
    source: str,
    field: str,
    value: str,
    score: int,
    quality: EvidenceQuality = EvidenceQuality.STRONG,
):
    return make_unified_evidence(
        source=source,
        field=field,
        value=value,
        score=score,
        quality=quality,
        reason=f"{source} supports {value}",
    )


def make_resolution():
    bundle = UnifiedEvidenceBundle(
        domain="event.api.playstation.net",
        evidence=[
            evidence(
                source="rule",
                field="vendor",
                value="Sony",
                score=35,
            ),
            evidence(
                source="knowledge",
                field="vendor",
                value="Sony PlayStation",
                score=50,
            ),
            evidence(
                source="knowledge",
                field="category",
                value="Gaming",
                score=50,
            ),
            evidence(
                source="database",
                field="category",
                value="Gaming",
                score=20,
            ),
            evidence(
                source="rule",
                field="category",
                value="Telemetry",
                score=30,
                quality=EvidenceQuality.MODERATE,
            ),
            evidence(
                source="knowledge",
                field="filter",
                value="gaming",
                score=50,
            ),
        ],
    )

    return resolve_unified_evidence(bundle)


def test_shadow_field_matches_canonical_vendor_identity():
    resolution = make_resolution()

    comparison = compare_shadow_field(
        field_name="vendor",
        current_value="Sony",
        preview=resolution.get("vendor"),
    )

    assert comparison.status == "match"
    assert comparison.is_match
    assert comparison.current_identity == (
        "sony-playstation"
    )
    assert comparison.preview_identity == (
        "sony-playstation"
    )
    assert comparison.preview_value == (
        "Sony PlayStation"
    )


def test_shadow_field_detects_difference():
    resolution = make_resolution()

    comparison = compare_shadow_field(
        field_name="category",
        current_value="Telemetry",
        preview=resolution.get("category"),
    )

    assert comparison.status == "different"
    assert comparison.is_different
    assert comparison.preview_value == "Gaming"
    assert comparison.preview_has_conflict


def test_shadow_field_detects_unresolved_preview():
    comparison = compare_shadow_field(
        field_name="filter",
        current_value="gaming",
        preview=None,
    )

    assert comparison.status == "unresolved"
    assert comparison.is_unresolved


def test_full_shadow_comparison_matches_current_decision():
    resolution = make_resolution()

    comparison = compare_analyzer_with_resolution(
        domain="event.api.playstation.net",
        current_vendor="Sony PlayStation",
        current_category="Gaming",
        current_filter="gaming",
        current_confidence=89,
        current_recommendation="review",
        resolution=resolution,
    )

    assert isinstance(
        comparison,
        ShadowComparison,
    )

    assert comparison.overall_status == "match"
    assert comparison.matching_fields == (
        "vendor",
        "category",
        "filter",
    )
    assert comparison.different_fields == ()
    assert comparison.unresolved_fields == ()
    assert comparison.preview_has_conflicts
    assert not comparison.preview_has_ambiguity


def test_partial_and_different_shadow_statuses():
    partial_bundle = UnifiedEvidenceBundle(
        domain="partial.example.test",
        evidence=[
            evidence(
                source="knowledge",
                field="vendor",
                value="Example",
                score=50,
            )
        ],
    )

    partial_resolution = resolve_unified_evidence(
        partial_bundle
    )

    partial = compare_analyzer_with_resolution(
        domain="partial.example.test",
        current_vendor="Example",
        current_category="Unknown",
        current_filter="unknown",
        current_confidence=50,
        current_recommendation="review",
        resolution=partial_resolution,
    )

    assert partial.overall_status == "partial"
    assert partial.matching_fields == (
        "vendor",
    )
    assert partial.unresolved_fields == (
        "category",
        "filter",
    )

    different = compare_analyzer_with_resolution(
        domain="partial.example.test",
        current_vendor="Other Vendor",
        current_category="Unknown",
        current_filter="unknown",
        current_confidence=20,
        current_recommendation="unknown",
        resolution=partial_resolution,
    )

    assert different.overall_status == "different"
    assert different.different_fields == (
        "vendor",
    )


def test_compare_analyzer_result_and_serialization():
    resolution = make_resolution()

    result = SimpleNamespace(
        domain="event.api.playstation.net",
        suggested_vendor="Sony PlayStation",
        suggested_category="Gaming",
        suggested_filter="gaming",
        confidence=89,
        recommendation="review",
    )

    comparison = compare_analyzer_result(
        result,
        resolution,
    )

    payload = comparison.to_dict()

    assert payload["overall_status"] == "match"
    assert payload["matching_fields"] == [
        "vendor",
        "category",
        "filter",
    ]
    assert payload["different_fields"] == []
    assert payload["unresolved_fields"] == []
    assert payload["current_confidence"] == 89
    assert (
        payload["current_recommendation"]
        == "review"
    )
    assert (
        payload["fields"]["vendor"][
            "preview_value"
        ]
        == "Sony PlayStation"
    )
