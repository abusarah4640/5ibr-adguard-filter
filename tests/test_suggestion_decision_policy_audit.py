from __future__ import annotations

import csv
from pathlib import Path

from scripts.services import (
    suggestions_service as service,
)


POLICY_COLUMNS = (
    "Blocking Policy",
    "Blocking Policy Reason",
    "Blocking Policy Source",
)


def read_rows(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        fields = list(
            reader.fieldnames
            or []
        )

        rows = list(reader)

    return fields, rows


def sample_suggestion() -> dict[str, str]:
    return {
        "Domain": "youtubei.googleapis.com",
        "Root": "googleapis.com",
        "Suggested Vendor": "Google",
        "Suggested Category": "Streaming",
        "Suggested Filter": "streaming",
        "Confidence": "85",
        "Recommendation": "review",
        "Blocking Policy": "do-not-block",
        "Blocking Policy Reason": (
            "Streaming endpoints may be required "
            "for playback."
        ),
        "Blocking Policy Source": "category-policy",
        "Seen": "12",
    }


def test_append_decision_records_policy_fields(
    tmp_path: Path,
    monkeypatch,
):
    decisions = (
        tmp_path
        / "suggestion-decisions.csv"
    )

    monkeypatch.setattr(
        service,
        "get_decisions_csv",
        lambda: decisions,
    )

    service.append_decision(
        sample_suggestion(),
        "approved",
        "operator override",
    )

    fields, rows = read_rows(
        decisions
    )

    assert len(rows) == 1

    for column in POLICY_COLUMNS:
        assert column in fields

    row = rows[0]

    assert (
        row["Blocking Policy"]
        == "do-not-block"
    )

    assert (
        row["Blocking Policy Reason"]
        == "Streaming endpoints may be required "
        "for playback."
    )

    assert (
        row["Blocking Policy Source"]
        == "category-policy"
    )

    assert row["Action"] == "approved"
    assert row["Reason"] == "operator override"


def test_append_decision_supports_legacy_suggestion(
    tmp_path: Path,
    monkeypatch,
):
    decisions = (
        tmp_path
        / "suggestion-decisions.csv"
    )

    monkeypatch.setattr(
        service,
        "get_decisions_csv",
        lambda: decisions,
    )

    suggestion = sample_suggestion()

    for column in POLICY_COLUMNS:
        suggestion.pop(
            column,
            None,
        )

    service.append_decision(
        suggestion,
        "ignored",
        "legacy row",
    )

    _, rows = read_rows(
        decisions
    )

    row = rows[0]

    assert (
        row["Blocking Policy"]
        == "unknown"
    )

    assert (
        row["Blocking Policy Reason"]
        == ""
    )

    assert (
        row["Blocking Policy Source"]
        == "fallback"
    )


def test_old_decision_csv_is_migrated_without_data_loss(
    tmp_path: Path,
    monkeypatch,
):
    decisions = (
        tmp_path
        / "suggestion-decisions.csv"
    )

    decisions.write_text(
        "Time,Action,Domain,Root,"
        "Suggested Vendor,Suggested Category,"
        "Suggested Filter,Confidence,"
        "Recommendation,Seen,Actor,Reason\n"
        "2026-07-01T00:00:00+00:00,"
        "ignored,legacy.example,example,"
        "Legacy,Telemetry,telemetry,"
        "50,review,2,web-ui,old decision\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        service,
        "get_decisions_csv",
        lambda: decisions,
    )

    service.append_decision(
        sample_suggestion(),
        "approved",
        "new decision",
    )

    fields, rows = read_rows(
        decisions
    )

    assert len(rows) == 2

    for column in POLICY_COLUMNS:
        assert column in fields

    assert (
        rows[0]["Domain"]
        == "legacy.example"
    )

    assert (
        rows[0]["Reason"]
        == "old decision"
    )

    assert (
        rows[0]["Blocking Policy"]
        == ""
    )

    assert (
        rows[1]["Domain"]
        == "youtubei.googleapis.com"
    )

    assert (
        rows[1]["Blocking Policy"]
        == "do-not-block"
    )


def test_multiple_decisions_keep_single_schema(
    tmp_path: Path,
    monkeypatch,
):
    decisions = (
        tmp_path
        / "suggestion-decisions.csv"
    )

    monkeypatch.setattr(
        service,
        "get_decisions_csv",
        lambda: decisions,
    )

    suggestion = sample_suggestion()

    service.append_decision(
        suggestion,
        "ignored",
        "first",
    )

    service.append_decision(
        suggestion,
        "approved",
        "second",
    )

    fields, rows = read_rows(
        decisions
    )

    assert len(rows) == 2

    assert fields.count(
        "Blocking Policy"
    ) == 1

    assert rows[0]["Action"] == "ignored"
    assert rows[1]["Action"] == "approved"
