from scripts.services.residual_difference_diagnostics import (
    build_residual_diagnostic_report,
    diagnose_comparison,
    diagnose_comparisons,
    expected_filter_for_category,
)


FILTER_MAP = {
    "Ads": "ads",
    "Streaming": "streaming",
    "Telemetry": "telemetry",
}


def comparison(
    *,
    domain: str,
    current_category: str,
    current_filter: str,
    preview_category: str,
    preview_filter: str,
    ambiguous: bool = False,
):
    return {
        "domain": domain,
        "overall_status": "different",
        "fields": {
            "vendor": {
                "status": "match",
                "current_value": "Example",
                "preview_value": "Example",
                "preview_has_conflict": False,
                "preview_ambiguous": False,
            },
            "category": {
                "status": (
                    "match"
                    if current_category
                    == preview_category
                    else "different"
                ),
                "current_value": current_category,
                "preview_value": preview_category,
                "preview_score": 30,
                "preview_sources": ["rule"],
                "preview_has_conflict": True,
                "preview_ambiguous": ambiguous,
            },
            "filter": {
                "status": (
                    "match"
                    if current_filter
                    == preview_filter
                    else "different"
                ),
                "current_value": current_filter,
                "preview_value": preview_filter,
                "preview_score": 30,
                "preview_sources": ["rule"],
                "preview_has_conflict": True,
                "preview_ambiguous": ambiguous,
            },
        },
    }


def test_expected_filter_for_category():
    assert (
        expected_filter_for_category(
            "Streaming",
            FILTER_MAP,
        )
        == "streaming"
    )

    assert (
        expected_filter_for_category(
            "streaming",
            FILTER_MAP,
        )
        == "streaming"
    )


def test_detects_preview_category_filter_incoherence():
    diagnostic = diagnose_comparison(
        comparison(
            domain="youtubei.googleapis.com",
            current_category="Streaming",
            current_filter="streaming",
            preview_category="Streaming",
            preview_filter="telemetry",
        ),
        filter_map=FILTER_MAP,
    )

    codes = {
        finding.code
        for finding in diagnostic.findings
    }

    assert (
        "preview-category-filter-incoherent"
        in codes
    )
    assert diagnostic.requires_review


def test_detects_ambiguous_residual_difference():
    diagnostic = diagnose_comparison(
        comparison(
            domain="adservetx.media.net",
            current_category="Ads",
            current_filter="ads",
            preview_category="Streaming",
            preview_filter="social",
            ambiguous=True,
        ),
        filter_map=FILTER_MAP,
    )

    codes = [
        finding.code
        for finding in diagnostic.findings
    ]

    assert (
        "preview-category-filter-incoherent"
        in codes
    )
    assert "preview-ambiguous" in codes
    assert codes.count(
        "shadow-field-difference"
    ) == 2


def test_summary_inspects_only_differences():
    match = comparison(
        domain="match.example",
        current_category="Ads",
        current_filter="ads",
        preview_category="Ads",
        preview_filter="ads",
    )
    match["overall_status"] = "match"

    different = comparison(
        domain="different.example",
        current_category="Streaming",
        current_filter="streaming",
        preview_category="Streaming",
        preview_filter="telemetry",
    )

    summary = diagnose_comparisons(
        [match, different],
        filter_map=FILTER_MAP,
    )

    assert summary.domains_inspected == 1
    assert (
        summary.domains_requiring_review
        == 1
    )


def test_build_report():
    summary = diagnose_comparisons(
        [
            comparison(
                domain="youtubei.googleapis.com",
                current_category="Streaming",
                current_filter="streaming",
                preview_category="Streaming",
                preview_filter="telemetry",
            )
        ],
        filter_map=FILTER_MAP,
    )

    report = build_residual_diagnostic_report(
        summary
    )

    assert (
        "5ibr Residual Difference Diagnostics"
        in report
    )
    assert "youtubei.googleapis.com" in report
    assert (
        "preview-category-filter-incoherent"
        in report
    )
