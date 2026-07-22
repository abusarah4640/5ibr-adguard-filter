"""Manual readiness review gate.

This service records an operator acknowledgement of a readiness decision. It is
intentionally incapable of activating enforcement or changing approvals.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from scripts.runtime.paths import get_runtime_paths
from scripts.services.readiness_decision_service import ReadinessDecision

CONFIRMATION_PHRASE = "APPROVE READINESS REVIEW"


@dataclass(frozen=True, slots=True)
class ReadinessApprovalRecord:
    timestamp: str
    reviewer: str
    note: str
    decision_status: str
    decision_fingerprint: str
    observed_snapshots: int
    window_size: int
    ready_snapshots: int
    regressions: int
    acknowledgement: str = "manual-review-approved"
    enforcement_activated: bool = False


def default_approval_path() -> Path:
    return get_runtime_paths().reports / "guardrails" / "readiness-approvals.jsonl"


def decision_fingerprint(decision: ReadinessDecision) -> str:
    payload = {
        "status": decision.status,
        "eligible_for_manual_review": decision.eligible_for_manual_review,
        "stable": decision.stable,
        "window_size": decision.window_size,
        "observed_snapshots": decision.observed_snapshots,
        "ready_snapshots": decision.ready_snapshots,
        "regressions": decision.regressions,
        "rules": [
            {"name": rule.name, "passed": rule.passed, "detail": rule.detail}
            for rule in decision.rules
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def record_manual_readiness_approval(
    decision: ReadinessDecision,
    *,
    reviewer: str,
    confirmation: str,
    note: str = "",
    path: Path | None = None,
    timestamp: str | None = None,
) -> ReadinessApprovalRecord:
    """Record manual review approval after conservative server-side checks."""

    reviewer = reviewer.strip()
    note = note.strip()

    if not decision.eligible_for_manual_review:
        raise ValueError("Readiness decision is not eligible for manual review.")
    if confirmation.strip() != CONFIRMATION_PHRASE:
        raise ValueError("Confirmation phrase does not match.")
    if not reviewer:
        raise ValueError("Reviewer name is required.")
    if len(reviewer) > 120:
        raise ValueError("Reviewer name is too long.")
    if len(note) > 1000:
        raise ValueError("Review note is too long.")

    record = ReadinessApprovalRecord(
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        reviewer=reviewer,
        note=note,
        decision_status=decision.status,
        decision_fingerprint=decision_fingerprint(decision),
        observed_snapshots=decision.observed_snapshots,
        window_size=decision.window_size,
        ready_snapshots=decision.ready_snapshots,
        regressions=decision.regressions,
    )

    target = path or default_approval_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
    return record


def load_readiness_approvals(
    path: Path | None = None,
) -> tuple[ReadinessApprovalRecord, ...]:
    target = path or default_approval_path()
    if not target.exists():
        return ()

    records: list[ReadinessApprovalRecord] = []
    with target.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(ReadinessApprovalRecord(**json.loads(line)))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(
                    f"Invalid readiness approval record at line {line_number}."
                ) from exc
    return tuple(records)


def latest_matching_approval(
    decision: ReadinessDecision,
    path: Path | None = None,
) -> ReadinessApprovalRecord | None:
    fingerprint = decision_fingerprint(decision)
    for record in reversed(load_readiness_approvals(path)):
        if record.decision_fingerprint == fingerprint:
            return record
    return None
