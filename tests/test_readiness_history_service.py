from __future__ import annotations

from datetime import UTC, datetime, timedelta

from scripts.services.guardrail_readiness_service import (
    EnforcementReadinessThresholds,
    evaluate_enforcement_readiness,
)
from scripts.services.guardrail_report_service import GuardrailDryRunSummary
from scripts.services.readiness_history_service import (
    append_readiness_snapshot,
    build_history_entry,
    calculate_readiness_trend,
    load_readiness_history,
    load_readiness_history_summary,
)


def _summary(*, classified: int, unclassified: int = 0, shadow: int = 1):
    approvals = classified + unclassified
    return GuardrailDryRunSummary(
        generated_at="2026-07-17T00:00:00+00:00",
        source_path="test.csv",
        total_decisions=approvals,
        approval_attempts=approvals,
        classified_approval_attempts=classified,
        unclassified_approval_attempts=unclassified,
        non_approval_decisions=0,
        shadow_rows=shadow,
        enforce_rows=0,
        legacy_rows=0,
        would_block=0,
        would_allow=classified,
        allowed_in_recorded_mode=approvals,
        denied_in_recorded_mode=0,
        requirements={},
        policies={},
        actions={},
    )


def _readiness(classified: int, unclassified: int = 0):
    return evaluate_enforcement_readiness(
        _summary(classified=classified, unclassified=unclassified),
        thresholds=EnforcementReadinessThresholds(),
    )


def test_build_history_entry_captures_readiness_state():
    observed = datetime(2026, 7, 17, 2, 45, tzinfo=UTC)
    entry = build_history_entry(_readiness(50, 10), timestamp=observed)

    assert entry.timestamp == "2026-07-17T02:45:00+00:00"
    assert entry.classified_approvals == 50
    assert entry.coverage_rate == 83.33
    assert entry.total_checks == 6
    assert entry.enforce_rows == 0


def test_append_snapshot_suppresses_identical_consecutive_state(tmp_path):
    path = tmp_path / "history.jsonl"
    readiness = _readiness(50, 10)

    assert append_readiness_snapshot(readiness, path) is True
    assert append_readiness_snapshot(readiness, path) is False
    assert len(load_readiness_history(path)) == 1


def test_append_snapshot_records_changed_state(tmp_path):
    path = tmp_path / "history.jsonl"

    assert append_readiness_snapshot(_readiness(50, 10), path) is True
    assert append_readiness_snapshot(_readiness(75, 5), path) is True
    assert len(load_readiness_history(path)) == 2


def test_load_history_ignores_malformed_lines(tmp_path):
    path = tmp_path / "history.jsonl"
    append_readiness_snapshot(_readiness(50, 10), path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")

    assert len(load_readiness_history(path)) == 1


def test_trend_reports_improving_and_regressing():
    first_time = datetime(2026, 7, 17, tzinfo=UTC)
    first = build_history_entry(_readiness(25, 15), timestamp=first_time)
    second = build_history_entry(
        _readiness(75, 5),
        timestamp=first_time + timedelta(hours=1),
    )

    improving = calculate_readiness_trend((first, second))
    regressing = calculate_readiness_trend((second, first))

    assert improving.direction == "improving"
    assert improving.percent_delta > 0
    assert improving.coverage_delta > 0
    assert regressing.direction == "regressing"


def test_history_summary_limits_rows_and_exposes_trend(tmp_path):
    path = tmp_path / "history.jsonl"
    for classified in (10, 20, 30):
        append_readiness_snapshot(_readiness(classified, 10), path)

    result = load_readiness_history_summary(path, limit=2)

    assert len(result.entries) == 2
    assert result.entries[0].classified_approvals == 20
    assert result.trend.direction == "improving"
