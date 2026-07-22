"""Read-only readiness history and trend reporting.

The service persists observation snapshots only. It never enables enforcement,
changes approval decisions, or mutates guardrail evidence.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from scripts.runtime.paths import get_runtime_paths
from scripts.services.guardrail_readiness_service import EnforcementReadinessResult


DEFAULT_HISTORY_PATH = (
    get_runtime_paths().reports
    / "guardrails"
    / "readiness-history.jsonl"
)


@dataclass(frozen=True, slots=True)
class ReadinessHistoryEntry:
    """One immutable readiness observation."""

    timestamp: str
    status: str
    ready: bool
    percent: float
    passed_checks: int
    total_checks: int
    classified_approvals: int
    coverage_rate: float
    unclassified_approvals: int
    classified_block_rate: float
    shadow_rows: int
    enforce_rows: int


@dataclass(frozen=True, slots=True)
class ReadinessTrend:
    """Direction between the two most recent observations."""

    direction: str
    percent_delta: float
    checks_delta: int
    coverage_delta: float


@dataclass(frozen=True, slots=True)
class ReadinessHistorySummary:
    """Dashboard-ready history view."""

    entries: tuple[ReadinessHistoryEntry, ...]
    trend: ReadinessTrend



def build_history_entry(
    readiness: EnforcementReadinessResult,
    *,
    timestamp: datetime | None = None,
) -> ReadinessHistoryEntry:
    """Build a serializable observation from a readiness result."""

    observed_at = timestamp or datetime.now(UTC)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)

    summary = readiness.summary
    progress = readiness.progress

    return ReadinessHistoryEntry(
        timestamp=observed_at.astimezone(UTC).isoformat(),
        status=readiness.status,
        ready=readiness.ready,
        percent=progress.percent,
        passed_checks=progress.passed_checks,
        total_checks=progress.total_checks,
        classified_approvals=summary.classified_approval_attempts,
        coverage_rate=round(summary.guardrail_coverage_rate, 2),
        unclassified_approvals=summary.unclassified_approval_attempts,
        classified_block_rate=round(summary.classified_approval_block_rate, 2),
        shadow_rows=summary.shadow_rows,
        enforce_rows=summary.enforce_rows,
    )



def _observation_signature(entry: ReadinessHistoryEntry) -> tuple[object, ...]:
    """Return the state fields used to suppress duplicate observations."""

    data = asdict(entry)
    data.pop("timestamp", None)
    return tuple(data.values())



def load_readiness_history(
    path: str | Path | None = None,
    *,
    limit: int | None = None,
) -> tuple[ReadinessHistoryEntry, ...]:
    """Load valid history rows, ignoring malformed lines safely."""

    history_path = Path(path) if path is not None else DEFAULT_HISTORY_PATH
    if not history_path.is_file():
        return ()

    entries: list[ReadinessHistoryEntry] = []
    for raw_line in history_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            entries.append(ReadinessHistoryEntry(**payload))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

    entries.sort(key=lambda item: item.timestamp)
    if limit is not None and limit >= 0:
        entries = entries[-limit:]
    return tuple(entries)



def append_readiness_snapshot(
    readiness: EnforcementReadinessResult,
    path: str | Path | None = None,
    *,
    timestamp: datetime | None = None,
) -> bool:
    """Append a changed observation; return False for an exact duplicate."""

    history_path = Path(path) if path is not None else DEFAULT_HISTORY_PATH
    entry = build_history_entry(readiness, timestamp=timestamp)
    previous = load_readiness_history(history_path, limit=1)

    if previous and _observation_signature(previous[-1]) == _observation_signature(entry):
        return False

    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(entry), sort_keys=True) + "\n")
    return True



def calculate_readiness_trend(
    entries: Iterable[ReadinessHistoryEntry],
) -> ReadinessTrend:
    """Calculate a deterministic improving/stable/regressing trend."""

    rows = tuple(entries)
    if len(rows) < 2:
        return ReadinessTrend("insufficient-data", 0.0, 0, 0.0)

    previous, current = rows[-2], rows[-1]
    percent_delta = round(current.percent - previous.percent, 2)
    checks_delta = current.passed_checks - previous.passed_checks
    coverage_delta = round(current.coverage_rate - previous.coverage_rate, 2)

    signals = (percent_delta, float(checks_delta), coverage_delta)
    if any(value < 0 for value in signals):
        direction = "regressing"
    elif any(value > 0 for value in signals):
        direction = "improving"
    else:
        direction = "stable"

    return ReadinessTrend(
        direction=direction,
        percent_delta=percent_delta,
        checks_delta=checks_delta,
        coverage_delta=coverage_delta,
    )



def load_readiness_history_summary(
    path: str | Path | None = None,
    *,
    limit: int = 8,
) -> ReadinessHistorySummary:
    """Load recent observations and their latest trend."""

    entries = load_readiness_history(path, limit=limit)
    return ReadinessHistorySummary(
        entries=entries,
        trend=calculate_readiness_trend(entries),
    )
