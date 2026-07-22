from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.services.readiness_approval_service import (
    CONFIRMATION_PHRASE,
    record_manual_readiness_approval,
)
from scripts.services.readiness_audit_archive_service import (
    APPROVAL_EVENT,
    DECISION_EVENT,
    archive_manual_readiness_approval,
    archive_readiness_decision,
    load_readiness_audit_archive,
    load_readiness_audit_archive_summary,
)


def decision(*, status="ready-for-review"):
    return SimpleNamespace(
        status=status,
        eligible_for_manual_review=True,
        stable=False,
        window_size=7,
        observed_snapshots=3,
        ready_snapshots=3,
        regressions=0,
        rules=(SimpleNamespace(name="current-readiness", passed=True, detail="ok"),),
    )


def test_archives_decision_and_suppresses_consecutive_duplicate(tmp_path: Path):
    path = tmp_path / "archive.jsonl"
    assert archive_readiness_decision(decision(), path=path, timestamp="2026-07-17T05:30:00+00:00") is True
    assert archive_readiness_decision(decision(), path=path, timestamp="2026-07-17T05:31:00+00:00") is False
    entries = load_readiness_audit_archive(path)
    assert len(entries) == 1
    assert entries[0].event_type == DECISION_EVENT
    assert entries[0].enforcement_activated is False


def test_archives_manual_approval_with_reviewer_and_note(tmp_path: Path):
    approvals = tmp_path / "approvals.jsonl"
    archive = tmp_path / "archive.jsonl"
    current = decision()
    approval = record_manual_readiness_approval(
        current,
        reviewer="Ibrahim",
        confirmation=CONFIRMATION_PHRASE,
        note="Ticket GOV-8",
        path=approvals,
        timestamp="2026-07-17T05:32:00+00:00",
    )
    entry = archive_manual_readiness_approval(current, approval, path=archive)
    assert entry.event_type == APPROVAL_EVENT
    assert entry.reviewer == "Ibrahim"
    assert entry.note == "Ticket GOV-8"
    assert entry.enforcement_activated is False


def test_rejects_approval_for_different_decision(tmp_path: Path):
    first = decision()
    approval = record_manual_readiness_approval(
        first,
        reviewer="Ibrahim",
        confirmation=CONFIRMATION_PHRASE,
        path=tmp_path / "approvals.jsonl",
    )
    with pytest.raises(ValueError, match="does not match"):
        archive_manual_readiness_approval(
            decision(status="ready"), approval, path=tmp_path / "archive.jsonl"
        )


def test_summary_counts_archive_events(tmp_path: Path):
    path = tmp_path / "archive.jsonl"
    current = decision()
    archive_readiness_decision(current, path=path)
    approval = record_manual_readiness_approval(
        current,
        reviewer="Ibrahim",
        confirmation=CONFIRMATION_PHRASE,
        path=tmp_path / "approvals.jsonl",
    )
    archive_manual_readiness_approval(current, approval, path=path)
    summary = load_readiness_audit_archive_summary(path)
    assert summary.total_entries == 2
    assert summary.decision_events == 1
    assert summary.approval_events == 1
    assert summary.latest_entry.event_type == APPROVAL_EVENT


def test_summary_requires_positive_limit(tmp_path: Path):
    with pytest.raises(ValueError, match="at least 1"):
        load_readiness_audit_archive_summary(tmp_path / "missing", limit=0)
