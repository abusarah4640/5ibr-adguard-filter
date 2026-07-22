from types import SimpleNamespace

import pytest

from scripts.services.readiness_decision_service import (
    NOT_READY,
    READY,
    READY_FOR_REVIEW,
    evaluate_readiness_decision,
)
from scripts.services.readiness_history_service import ReadinessHistoryEntry


def entry(index: int, *, ready: bool = True, percent: float = 100.0, coverage: float = 100.0):
    return ReadinessHistoryEntry(
        timestamp=f"2026-07-{index:02d}T00:00:00+00:00",
        status="ready" if ready else "not-ready",
        ready=ready,
        percent=percent,
        passed_checks=6 if ready else 5,
        total_checks=6,
        classified_approvals=150,
        coverage_rate=coverage,
        unclassified_approvals=0,
        classified_block_rate=0.0,
        shadow_rows=20,
        enforce_rows=0,
    )


def readiness(ready: bool):
    return SimpleNamespace(ready=ready)


def test_not_ready_when_current_checks_fail():
    result = evaluate_readiness_decision(
        readiness(False),
        [entry(1, ready=False)],
    )
    assert result.status == NOT_READY
    assert result.eligible_for_manual_review is False
    assert result.stable is False


def test_ready_for_review_when_current_ready_but_window_incomplete():
    result = evaluate_readiness_decision(
        readiness(True),
        [entry(1), entry(2)],
        window_size=7,
    )
    assert result.status == READY_FOR_REVIEW
    assert result.eligible_for_manual_review is True
    assert result.observed_snapshots == 2


def test_ready_after_full_stable_window():
    result = evaluate_readiness_decision(
        readiness(True),
        [entry(index) for index in range(1, 8)],
        window_size=7,
    )
    assert result.status == READY
    assert result.stable is True
    assert result.ready_snapshots == 7
    assert result.regressions == 0


def test_regression_prevents_ready_decision():
    rows = [entry(index, percent=100.0) for index in range(1, 7)]
    rows.append(entry(7, percent=90.0))
    result = evaluate_readiness_decision(readiness(True), rows, window_size=7)
    assert result.status == READY_FOR_REVIEW
    assert result.regressions == 1
    assert result.stable is False


def test_window_size_must_be_at_least_two():
    with pytest.raises(ValueError, match="at least 2"):
        evaluate_readiness_decision(readiness(True), (), window_size=1)
