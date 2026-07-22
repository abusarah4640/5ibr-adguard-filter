from __future__ import annotations

import csv
from pathlib import Path

from scripts.services import (
    suggestions_service as service,
)


GUARDRAIL_COLUMNS = (
    "Guardrail Mode",
    "Guardrail Requirement",
    "Guardrail Would Block",
    "Guardrail Allowed",
    "Guardrail Reason",
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


def suggestion(
    policy: str,
) -> dict[str, str]:
    return {
        "Domain": "example.test",
        "Root": "example.test",
        "Suggested Vendor": "Example",
        "Suggested Category": "Streaming",
        "Suggested Filter": "streaming",
        "Confidence": "85",
        "Recommendation": "review",
        "Blocking Policy": policy,
        "Blocking Policy Reason": (
            "Policy test reason."
        ),
        "Blocking Policy Source": (
            "category-policy"
        ),
        "Seen": "5",
    }


def configure_decisions(
    tmp_path: Path,
    monkeypatch,
) -> Path:
    path = (
        tmp_path
        / "suggestion-decisions.csv"
    )

    monkeypatch.setattr(
        service,
        "get_decisions_csv",
        lambda: path,
    )

    return path


def test_do_not_block_approval_records_shadow_violation(
    tmp_path: Path,
    monkeypatch,
):
    decisions = configure_decisions(
        tmp_path,
        monkeypatch,
    )

    service.append_decision(
        suggestion("do-not-block"),
        "approved",
        "",
    )

    fields, rows = read_rows(
        decisions
    )

    for column in GUARDRAIL_COLUMNS:
        assert column in fields

    row = rows[0]

    assert row["Guardrail Mode"] == "shadow"

    assert (
        row["Guardrail Requirement"]
        == "require-override"
    )

    assert (
        row["Guardrail Would Block"]
        == "true"
    )

    # Shadow mode never blocks the real action.
    assert (
        row["Guardrail Allowed"]
        == "true"
    )

    assert row["Guardrail Reason"]


def test_safe_to_block_records_normal_allow(
    tmp_path: Path,
    monkeypatch,
):
    decisions = configure_decisions(
        tmp_path,
        monkeypatch,
    )

    service.append_decision(
        suggestion("safe-to-block"),
        "approved",
        "",
    )

    _, rows = read_rows(
        decisions
    )

    row = rows[0]

    assert (
        row["Guardrail Requirement"]
        == "allow"
    )

    assert (
        row["Guardrail Would Block"]
        == "false"
    )

    assert (
        row["Guardrail Allowed"]
        == "true"
    )


def test_non_approval_action_is_always_allowed(
    tmp_path: Path,
    monkeypatch,
):
    decisions = configure_decisions(
        tmp_path,
        monkeypatch,
    )

    service.append_decision(
        suggestion("do-not-block"),
        "ignored",
        "",
    )

    _, rows = read_rows(
        decisions
    )

    row = rows[0]

    assert (
        row["Guardrail Requirement"]
        == "allow"
    )

    assert (
        row["Guardrail Would Block"]
        == "false"
    )

    assert (
        row["Guardrail Allowed"]
        == "true"
    )


def test_needs_testing_without_confirmation_is_shadowed(
    tmp_path: Path,
    monkeypatch,
):
    decisions = configure_decisions(
        tmp_path,
        monkeypatch,
    )

    service.append_decision(
        suggestion("needs-testing"),
        "approved",
        "Reviewed manually",
    )

    _, rows = read_rows(
        decisions
    )

    row = rows[0]

    assert (
        row["Guardrail Requirement"]
        == "require-test-confirmation"
    )

    assert (
        row["Guardrail Would Block"]
        == "true"
    )

    assert (
        row["Guardrail Allowed"]
        == "true"
    )


def test_old_decision_csv_migrates_guardrail_columns(
    tmp_path: Path,
    monkeypatch,
):
    decisions = configure_decisions(
        tmp_path,
        monkeypatch,
    )

    decisions.write_text(
        "Time,Action,Domain,Root,"
        "Suggested Vendor,Suggested Category,"
        "Suggested Filter,Confidence,"
        "Recommendation,Blocking Policy,"
        "Blocking Policy Reason,"
        "Blocking Policy Source,"
        "Seen,Actor,Reason\n"
        "2026-07-01T00:00:00+00:00,"
        "ignored,legacy.example,example,"
        "Legacy,Telemetry,telemetry,"
        "50,review,unknown,,fallback,"
        "2,web-ui,old decision\n",
        encoding="utf-8",
    )

    service.append_decision(
        suggestion("safe-to-block"),
        "approved",
        "new decision",
    )

    fields, rows = read_rows(
        decisions
    )

    assert len(rows) == 2

    for column in GUARDRAIL_COLUMNS:
        assert column in fields

    assert (
        rows[0]["Domain"]
        == "legacy.example"
    )

    assert (
        rows[0]["Guardrail Mode"]
        == ""
    )

    assert (
        rows[1]["Guardrail Mode"]
        == "shadow"
    )
