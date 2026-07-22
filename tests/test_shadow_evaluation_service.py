from scripts.services.evidence_quality import (
    EvidenceQuality,
)
from scripts.services.shadow_comparison_service import (
    compare_analyzer_with_resolution,
)
from scripts.services.shadow_evaluation_service import (
    ShadowEvaluationSummary,
    ShadowFieldStatistics,
    build_shadow_evaluation_report,
    evaluate_shadow_comparisons,
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


def make_resolution(
    *,
    domain: str,
    vendor: str | None = None,
    category: str | None = None,
    filter_name: str | None = None,
):
    items = []

    if vendor is not None:
        items.append(
            evidence(
                source="knowledge",
                field="vendor",
                value=vendor,
                score=50,
            )
        )

    if category is not None:
        items.append(
            evidence(
                source="knowledge",
                field="category",
                value=category,
                score=50,
            )
        )

    if filter_name is not None:
        items.append(
            evidence(
                source="knowledge",
                field="filter",
                value=filter_name,
                score=50,
            )
        )

    return resolve_unified_evidence(
        UnifiedEvidenceBundle(
            domain=domain,
            evidence=items,
        )
    )


def make_comparison(
    *,
    domain: str,
    current_vendor: str,
    current_category: str,
    current_filter: str,
    preview_vendor: str | None,
    preview_category: str | None,
    preview_filter: str | None,
):
    resolution = make_resolution(
        domain=domain,
        vendor=preview_vendor,
        category=preview_category,
        filter_name=preview_filter,
    )

    return compare_analyzer_with_resolution(
        domain=domain,
        current_vendor=current_vendor,
        current_category=current_category,
        current_filter=current_filter,
        current_confidence=50,
        current_recommendation="review",
        resolution=resolution,
    )


def test_shadow_field_statistics_agreement_rate():
    stats = ShadowFieldStatistics(
        field="vendor",
        matches=8,
        differences=2,
        unresolved=3,
    )

    assert stats.compared == 10
    assert stats.total == 13
    assert stats.agreement_rate == 80.0


def test_evaluate_shadow_comparisons():
    match = make_comparison(
        domain="match.example",
        current_vendor="Google",
        current_category="Ads",
        current_filter="ads",
        preview_vendor="Google",
        preview_category="Ads",
        preview_filter="ads",
    )

    partial = make_comparison(
        domain="partial.example",
        current_vendor="Netflix",
        current_category="Streaming",
        current_filter="streaming",
        preview_vendor="Netflix",
        preview_category=None,
        preview_filter=None,
    )

    different = make_comparison(
        domain="different.example",
        current_vendor="Google",
        current_category="Telemetry",
        current_filter="telemetry",
        preview_vendor="Google",
        preview_category="Gaming",
        preview_filter="gaming",
    )

    summary = evaluate_shadow_comparisons(
        [
            match,
            partial,
            different,
        ]
    )

    assert isinstance(
        summary,
        ShadowEvaluationSummary,
    )

    assert summary.domains_compared == 3
    assert summary.full_matches == 1
    assert summary.partial_matches == 1
    assert summary.different_decisions == 1

    assert summary.fields["vendor"].matches == 3
    assert (
        summary.fields["vendor"].differences
        == 0
    )
    assert (
        summary.fields["vendor"].unresolved
        == 0
    )

    assert (
        summary.fields["category"].matches
        == 1
    )
    assert (
        summary.fields["category"].differences
        == 1
    )
    assert (
        summary.fields["category"].unresolved
        == 1
    )

    assert (
        summary.fields["filter"].matches
        == 1
    )
    assert (
        summary.fields["filter"].differences
        == 1
    )
    assert (
        summary.fields["filter"].unresolved
        == 1
    )


def test_empty_evaluation_is_safe():
    summary = evaluate_shadow_comparisons([])

    assert summary.domains_compared == 0
    assert summary.full_match_rate == 0.0
    assert summary.different_rate == 0.0

    for field_name in (
        "vendor",
        "category",
        "filter",
    ):
        stats = summary.fields[field_name]

        assert stats.agreement_rate == 0.0
        assert stats.total == 0


def test_evaluation_serialization():
    comparison = make_comparison(
        domain="example.test",
        current_vendor="Google",
        current_category="Ads",
        current_filter="ads",
        preview_vendor="Google",
        preview_category="Ads",
        preview_filter="ads",
    )

    summary = evaluate_shadow_comparisons(
        [comparison]
    )

    payload = summary.to_dict()

    assert payload["domains_compared"] == 1
    assert payload["full_matches"] == 1
    assert payload["partial_matches"] == 0
    assert payload["different_decisions"] == 0
    assert payload["full_match_rate"] == 100.0

    assert (
        payload["fields"]["vendor"][
            "agreement_rate"
        ]
        == 100.0
    )


def test_build_shadow_evaluation_report():
    match = make_comparison(
        domain="match.example",
        current_vendor="Google",
        current_category="Ads",
        current_filter="ads",
        preview_vendor="Google",
        preview_category="Ads",
        preview_filter="ads",
    )

    different = make_comparison(
        domain="different.example",
        current_vendor="Google",
        current_category="Telemetry",
        current_filter="telemetry",
        preview_vendor="Google",
        preview_category="Gaming",
        preview_filter="gaming",
    )

    summary = evaluate_shadow_comparisons(
        [
            match,
            different,
        ]
    )

    report = build_shadow_evaluation_report(
        summary
    )

    assert (
        "5ibr Shadow Evaluation Report"
        in report
    )
    assert "Domains compared        : 2" in report
    assert "Full matches          : 1" in report
    assert "Different decisions   : 1" in report
    assert "different.example" in report
    assert "Telemetry -> Gaming" in report
    assert "telemetry -> gaming" in report


def test_report_without_differences():
    comparison = make_comparison(
        domain="match.example",
        current_vendor="Google",
        current_category="Ads",
        current_filter="ads",
        preview_vendor="Google",
        preview_category="Ads",
        preview_filter="ads",
    )

    summary = evaluate_shadow_comparisons(
        [comparison]
    )

    report = build_shadow_evaluation_report(
        summary
    )

    assert "Top differences:" in report
    assert "None" in report
