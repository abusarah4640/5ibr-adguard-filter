from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.services.readiness_approval_service import (
    CONFIRMATION_PHRASE,
    decision_fingerprint,
    latest_matching_approval,
    load_readiness_approvals,
    record_manual_readiness_approval,
)


def decision(*, eligible: bool = True):
    return SimpleNamespace(
        status="ready-for-review",
        eligible_for_manual_review=eligible,
        stable=False,
        window_size=7,
        observed_snapshots=3,
        ready_snapshots=3,
        regressions=0,
        rules=(SimpleNamespace(name="current-readiness", passed=True, detail="ok"),),
    )


def test_records_and_loads_manual_approval(tmp_path: Path):
    path = tmp_path / "approvals.jsonl"
    result = record_manual_readiness_approval(
        decision(),
        reviewer="Ibrahim",
        confirmation=CONFIRMATION_PHRASE,
        note="Reviewed safely.",
        path=path,
        timestamp="2026-07-17T05:00:00+00:00",
    )

    assert result.enforcement_activated is False
    assert result.reviewer == "Ibrahim"
    assert load_readiness_approvals(path) == (result,)
    assert latest_matching_approval(decision(), path) == result


def test_rejects_ineligible_decision(tmp_path: Path):
    with pytest.raises(ValueError, match="not eligible"):
        record_manual_readiness_approval(
            decision(eligible=False),
            reviewer="Ibrahim",
            confirmation=CONFIRMATION_PHRASE,
            path=tmp_path / "approvals.jsonl",
        )


def test_requires_exact_confirmation_and_reviewer(tmp_path: Path):
    with pytest.raises(ValueError, match="Confirmation"):
        record_manual_readiness_approval(
            decision(), reviewer="Ibrahim", confirmation="approve", path=tmp_path / "a"
        )
    with pytest.raises(ValueError, match="Reviewer"):
        record_manual_readiness_approval(
            decision(), reviewer="", confirmation=CONFIRMATION_PHRASE, path=tmp_path / "b"
        )


def test_fingerprint_changes_with_decision_state():
    first = decision()
    second = decision()
    second.status = "ready"
    assert decision_fingerprint(first) != decision_fingerprint(second)
