import json

from scripts.services.coherence_analytics import (
    analyze_coherence_patterns,
    build_coherence_analytics_report,
    load_seen_counts,
)


def assessment(
    *,
    domain: str,
    category: str,
    filter_value: str,
    expected_filter: str,
    status: str = "incoherent",
    conflict: bool = False,
    ambiguous: bool = False,
):
    return {
        "domain": domain,
        "status": status,
        "category": category,
        "filter": filter_value,
        "expected_filter": expected_filter,
        "category_conflict": conflict,
        "filter_conflict": conflict,
        "category_ambiguous": ambiguous,
        "filter_ambiguous": ambiguous,
        "requires_review": (
            status == "incoherent"
            or ambiguous
        ),
    }


def test_groups_semantic_mismatch_patterns():
    summary = analyze_coherence_patterns(
        [
            assessment(
                domain="a.example",
                category="Streaming",
                filter_value="social",
                expected_filter="streaming",
            ),
            assessment(
                domain="b.example",
                category="streaming",
                filter_value="SOCIAL",
                expected_filter="streaming",
            ),
        ],
        seen_counts={
            "a.example": 100,
            "b.example": 50,
        },
    )

    assert summary.incoherent_assessments == 2
    assert len(summary.patterns) == 1

    pattern = summary.patterns[0]

    assert pattern.count == 2
    assert pattern.total_seen == 150
    assert pattern.expected_filter == "streaming"


def test_pattern_severity():
    summary = analyze_coherence_patterns(
        [
            assessment(
                domain="critical.example",
                category="Streaming",
                filter_value="social",
                expected_filter="streaming",
                conflict=True,
                ambiguous=True,
            ),
            assessment(
                domain="medium.example",
                category="Telemetry",
                filter_value="mobile",
                expected_filter="telemetry",
            ),
        ]
    )

    severities = {
        pattern.pattern_key: pattern.severity
        for pattern in summary.patterns
    }

    assert (
        severities["Streaming -> social"]
        == "critical"
    )

    assert (
        severities["Telemetry -> mobile"]
        == "medium"
    )


def test_load_seen_counts(tmp_path):
    path = tmp_path / "suggestions.json"

    path.write_text(
        json.dumps(
            {
                "suggestions": [
                    {
                        "domain": "a.example",
                        "seen": 25,
                    },
                    {
                        "domain": "b.example",
                        "seen": 10,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    assert load_seen_counts(path) == {
        "a.example": 25,
        "b.example": 10,
    }


def test_analytics_report():
    summary = analyze_coherence_patterns(
        [
            assessment(
                domain="youtube.example",
                category="Streaming",
                filter_value="telemetry",
                expected_filter="streaming",
                conflict=True,
            )
        ],
        seen_counts={
            "youtube.example": 500,
        },
    )

    report = build_coherence_analytics_report(
        summary
    )

    assert (
        "5ibr Cross-Field Coherence Analytics"
        in report
    )
    assert "Streaming -> telemetry" in report
    assert "total seen      : 500" in report
    assert "severity        : high" in report


def test_resolved_assessments_can_be_excluded():
    summary = analyze_coherence_patterns(
        [
            assessment(
                domain="resolved.example",
                category="Gaming",
                filter_value="",
                expected_filter="gaming",
                status="unresolved",
            )
        ]
    )

    assert summary.analyzed_patterns == 0
    assert summary.incoherent_assessments == 0
