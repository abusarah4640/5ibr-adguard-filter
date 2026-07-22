"""Permanent audit archive for readiness decisions and manual reviews.

The archive is append-only and informational. It cannot activate enforcement or
change the readiness state.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.runtime.paths import get_runtime_paths
from scripts.services.readiness_approval_service import ReadinessApprovalRecord, decision_fingerprint
from scripts.services.readiness_decision_service import ReadinessDecision

DECISION_EVENT = "decision-observed"
APPROVAL_EVENT = "manual-review-recorded"


@dataclass(frozen=True, slots=True)
class ReadinessAuditArchiveEntry:
    timestamp: str
    event_type: str
    decision_status: str
    decision_fingerprint: str
    eligible_for_manual_review: bool
    stable: bool
    observed_snapshots: int
    window_size: int
    ready_snapshots: int
    regressions: int
    rules: tuple[dict[str, Any], ...]
    reviewer: str = ""
    note: str = ""
    acknowledgement: str = ""
    enforcement_activated: bool = False


@dataclass(frozen=True, slots=True)
class ReadinessAuditArchiveSummary:
    entries: tuple[ReadinessAuditArchiveEntry, ...]
    total_entries: int
    decision_events: int
    approval_events: int
    latest_entry: ReadinessAuditArchiveEntry | None


def default_archive_path() -> Path:
    return get_runtime_paths().reports / "guardrails" / "readiness-decision-archive.jsonl"


def _rules(decision: ReadinessDecision) -> tuple[dict[str, Any], ...]:
    return tuple(
        {"name": rule.name, "passed": bool(rule.passed), "detail": rule.detail}
        for rule in decision.rules
    )


def archive_readiness_decision(
    decision: ReadinessDecision,
    *,
    path: Path | None = None,
    timestamp: str | None = None,
    suppress_duplicate: bool = True,
) -> bool:
    """Append a decision observation, suppressing consecutive duplicates."""

    target = path or default_archive_path()
    fingerprint = decision_fingerprint(decision)
    if suppress_duplicate:
        existing = load_readiness_audit_archive(target)
        if existing:
            latest = existing[-1]
            if (
                latest.event_type == DECISION_EVENT
                and latest.decision_fingerprint == fingerprint
            ):
                return False

    entry = ReadinessAuditArchiveEntry(
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        event_type=DECISION_EVENT,
        decision_status=decision.status,
        decision_fingerprint=fingerprint,
        eligible_for_manual_review=decision.eligible_for_manual_review,
        stable=decision.stable,
        observed_snapshots=decision.observed_snapshots,
        window_size=decision.window_size,
        ready_snapshots=decision.ready_snapshots,
        regressions=decision.regressions,
        rules=_rules(decision),
    )
    _append_entry(entry, target)
    return True


def archive_manual_readiness_approval(
    decision: ReadinessDecision,
    approval: ReadinessApprovalRecord,
    *,
    path: Path | None = None,
) -> ReadinessAuditArchiveEntry:
    """Append a manual-review event linked to the exact decision fingerprint."""

    fingerprint = decision_fingerprint(decision)
    if approval.decision_fingerprint != fingerprint:
        raise ValueError("Approval does not match the current readiness decision.")
    if approval.enforcement_activated:
        raise ValueError("Enforcement activation cannot be archived as a readiness review.")

    entry = ReadinessAuditArchiveEntry(
        timestamp=approval.timestamp,
        event_type=APPROVAL_EVENT,
        decision_status=decision.status,
        decision_fingerprint=fingerprint,
        eligible_for_manual_review=decision.eligible_for_manual_review,
        stable=decision.stable,
        observed_snapshots=decision.observed_snapshots,
        window_size=decision.window_size,
        ready_snapshots=decision.ready_snapshots,
        regressions=decision.regressions,
        rules=_rules(decision),
        reviewer=approval.reviewer,
        note=approval.note,
        acknowledgement=approval.acknowledgement,
        enforcement_activated=False,
    )
    _append_entry(entry, path or default_archive_path())
    return entry


def _append_entry(entry: ReadinessAuditArchiveEntry, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(entry)
    payload["rules"] = list(entry.rules)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def load_readiness_audit_archive(
    path: Path | None = None,
) -> tuple[ReadinessAuditArchiveEntry, ...]:
    target = path or default_archive_path()
    if not target.exists():
        return ()

    entries: list[ReadinessAuditArchiveEntry] = []
    with target.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                payload["rules"] = tuple(payload.get("rules", ()))
                entries.append(ReadinessAuditArchiveEntry(**payload))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(
                    f"Invalid readiness audit archive entry at line {line_number}."
                ) from exc
    return tuple(entries)


def load_readiness_audit_archive_summary(
    path: Path | None = None,
    *,
    limit: int = 20,
) -> ReadinessAuditArchiveSummary:
    if limit < 1:
        raise ValueError("Archive summary limit must be at least 1.")
    all_entries = load_readiness_audit_archive(path)
    visible = all_entries[-limit:]
    return ReadinessAuditArchiveSummary(
        entries=visible,
        total_entries=len(all_entries),
        decision_events=sum(e.event_type == DECISION_EVENT for e in all_entries),
        approval_events=sum(e.event_type == APPROVAL_EVENT for e in all_entries),
        latest_entry=all_entries[-1] if all_entries else None,
    )
