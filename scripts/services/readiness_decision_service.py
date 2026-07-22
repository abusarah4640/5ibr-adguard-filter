"""Read-only readiness decision engine.

The engine interprets current readiness together with recent history. It never
activates enforcement, changes approvals, or mutates guardrail evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from scripts.services.guardrail_readiness_service import EnforcementReadinessResult
from scripts.services.readiness_history_service import ReadinessHistoryEntry


NOT_READY = "not-ready"
READY_FOR_REVIEW = "ready-for-review"
READY = "ready"


@dataclass(frozen=True, slots=True)
class ReadinessDecisionRule:
    """One explainable decision rule."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class ReadinessDecision:
    """Conservative, dashboard-ready readiness decision."""

    status: str
    eligible_for_manual_review: bool
    stable: bool
    window_size: int
    observed_snapshots: int
    ready_snapshots: int
    regressions: int
    rules: tuple[ReadinessDecisionRule, ...]


def _count_regressions(entries: tuple[ReadinessHistoryEntry, ...]) -> int:
    regressions = 0
    for previous, current in zip(entries, entries[1:]):
        if (
            current.percent < previous.percent
            or current.passed_checks < previous.passed_checks
            or current.coverage_rate < previous.coverage_rate
        ):
            regressions += 1
    return regressions


def evaluate_readiness_decision(
    readiness: EnforcementReadinessResult,
    history: Iterable[ReadinessHistoryEntry],
    *,
    window_size: int = 7,
) -> ReadinessDecision:
    """Interpret current readiness and a trailing stability window.

    READY is deliberately strict: the current result must be ready, the full
    window must exist, every snapshot must be ready, and no regression may be
    present. A currently ready result with incomplete or unstable history is
    READY_FOR_REVIEW, never automatic activation.
    """

    if window_size < 2:
        raise ValueError("window_size must be at least 2")

    rows = tuple(history)[-window_size:]
    observed = len(rows)
    ready_snapshots = sum(1 for row in rows if row.ready)
    regressions = _count_regressions(rows)

    history_available = observed > 0
    full_window = observed == window_size
    all_ready = full_window and ready_snapshots == window_size
    no_regressions = regressions == 0
    stable = bool(readiness.ready and all_ready and no_regressions)

    rules = (
        ReadinessDecisionRule(
            "current-readiness",
            bool(readiness.ready),
            "Current readiness checks pass."
            if readiness.ready
            else "Current readiness checks do not yet pass.",
        ),
        ReadinessDecisionRule(
            "history-available",
            history_available,
            f"{observed} readiness snapshot(s) available.",
        ),
        ReadinessDecisionRule(
            "stability-window",
            full_window,
            f"{observed} of {window_size} required snapshots available.",
        ),
        ReadinessDecisionRule(
            "all-snapshots-ready",
            all_ready,
            f"{ready_snapshots} of {window_size} snapshots are ready.",
        ),
        ReadinessDecisionRule(
            "no-regressions",
            no_regressions,
            f"{regressions} regression(s) detected in the active window.",
        ),
    )

    if not readiness.ready:
        status = NOT_READY
    elif stable:
        status = READY
    else:
        status = READY_FOR_REVIEW

    return ReadinessDecision(
        status=status,
        eligible_for_manual_review=status in {READY_FOR_REVIEW, READY},
        stable=stable,
        window_size=window_size,
        observed_snapshots=observed,
        ready_snapshots=ready_snapshots,
        regressions=regressions,
        rules=rules,
    )
