from scripts.services.cross_field_coherence import (
    assess_preview_values,
    build_coherence_report,
    summarize_coherence,
)


def test_coherent_streaming_filter():
    result = assess_preview_values(
        domain="video.example",
        category="Streaming",
        filter_value="streaming",
    )

    assert result.status == "coherent"
    assert result.is_coherent
    assert not result.requires_review
    assert result.expected_filter == "streaming"


def test_incoherent_streaming_filter_requires_review():
    result = assess_preview_values(
        domain="youtubei.googleapis.com",
        category="Streaming",
        filter_value="telemetry",
        filter_conflict=True,
    )

    assert result.status == "incoherent"
    assert result.is_incoherent
    assert result.requires_review
    assert result.expected_filter == "streaming"
    assert result.filter_conflict


def test_ambiguous_coherent_result_still_requires_review():
    result = assess_preview_values(
        domain="ambiguous.example",
        category="Ads",
        filter_value="ads",
        category_ambiguous=True,
    )

    assert result.status == "coherent"
    assert result.requires_review
    assert result.category_ambiguous


def test_unresolved_and_unmapped_results():
    unresolved = assess_preview_values(
        domain="partial.example",
        category="Gaming",
        filter_value="",
    )

    assert unresolved.status == "unresolved"
    assert unresolved.requires_review

    unmapped = assess_preview_values(
        domain="custom.example",
        category="Custom Category",
        filter_value="custom",
    )

    assert unmapped.status == "unmapped"
    assert unmapped.requires_review


def test_summary_and_report():
    assessments = [
        assess_preview_values(
            domain="good.example",
            category="Gaming",
            filter_value="gaming",
        ),
        assess_preview_values(
            domain="bad.example",
            category="Streaming",
            filter_value="social",
        ),
        assess_preview_values(
            domain="partial.example",
            category="",
            filter_value="",
        ),
    ]

    summary = summarize_coherence(
        assessments
    )

    assert summary.total == 3
    assert summary.statuses["coherent"] == 1
    assert summary.statuses["incoherent"] == 1
    assert summary.statuses["unresolved"] == 1
    assert summary.requiring_review == 1

    report = build_coherence_report(
        summary,
        review_only=True,
    )

    assert (
        "5ibr Cross-Field Coherence Report"
        in report
    )
    assert "bad.example" in report
    assert "good.example" not in report
