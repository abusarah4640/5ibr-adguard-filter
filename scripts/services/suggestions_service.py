#!/usr/bin/env python3

"""Suggestion and review-queue persistence services."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from scripts.services.policy_guardrail_service import (
    GuardrailMode,
    evaluate_policy_guardrail,
)

from scripts.runtime.paths import (
    get_runtime_paths,
)


SUGGESTION_FIELDNAMES = [
    "Domain",
    "Seen",
    "Root",
    "Suggested Vendor",
    "Suggested Category",
    "Suggested Filter",
    "Confidence",
    "Recommendation",
    "Reasons",
]

DECISION_FIELDNAMES = [
    "Time",
    "Action",
    "Domain",
    "Root",
    "Suggested Vendor",
    "Suggested Category",
    "Suggested Filter",
    "Confidence",
    "Recommendation",
    "Blocking Policy",
    "Blocking Policy Reason",
    "Blocking Policy Source",
    "Guardrail Mode",
    "Guardrail Requirement",
    "Guardrail Would Block",
    "Guardrail Allowed",
    "Guardrail Reason",
    "Test Confirmed",
    "Override Confirmed",
    "Manual Review Confirmed",
    "Seen",
    "Actor",
    "Reason",
]


def _runtime_suggestions_csv() -> Path:
    return (
        get_runtime_paths().reports
        / "suggestions.csv"
    )


def _runtime_rejected_csv() -> Path:
    return (
        get_runtime_paths().reports
        / "suggestions-rejected.csv"
    )


def _runtime_decisions_csv() -> Path:
    return (
        get_runtime_paths().reports
        / "suggestion-decisions.csv"
    )


_INITIAL_SUGGESTIONS_CSV = (
    _runtime_suggestions_csv()
)

_INITIAL_REJECTED_CSV = (
    _runtime_rejected_csv()
)

_INITIAL_DECISIONS_CSV = (
    _runtime_decisions_csv()
)


# Compatibility constants for existing imports/tests.
SUGGESTIONS_CSV = _INITIAL_SUGGESTIONS_CSV
REJECTED_CSV = _INITIAL_REJECTED_CSV
DECISIONS_CSV = _INITIAL_DECISIONS_CSV


def get_suggestions_csv() -> Path:
    """Return the active suggestions CSV.

    A monkeypatched compatibility constant takes
    priority. Otherwise resolve FIVEBR_HOME
    dynamically.
    """

    if (
        SUGGESTIONS_CSV
        != _INITIAL_SUGGESTIONS_CSV
    ):
        return Path(SUGGESTIONS_CSV)

    return _runtime_suggestions_csv()


def get_rejected_csv() -> Path:
    """Return the active rejected CSV."""

    if (
        REJECTED_CSV
        != _INITIAL_REJECTED_CSV
    ):
        return Path(REJECTED_CSV)

    return _runtime_rejected_csv()


def get_decisions_csv() -> Path:
    """Return the active review-decisions CSV."""

    if (
        DECISIONS_CSV
        != _INITIAL_DECISIONS_CSV
    ):
        return Path(DECISIONS_CSV)

    return _runtime_decisions_csv()


def load_suggestions() -> list[dict]:
    """Load current suggestions from the active runtime."""

    suggestions_csv = (
        get_suggestions_csv()
    )

    if not suggestions_csv.exists():
        return []

    with suggestions_csv.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def find_suggestion(
    domain: str,
) -> dict | None:
    """Find one suggestion by normalized domain."""

    target = (
        domain.strip().lower()
    )

    for row in load_suggestions():
        candidate = (
            row.get("Domain", "")
            .strip()
            .lower()
        )

        if candidate == target:
            return row

    return None


def append_rejected(
    row: dict,
    reason: str = "",
) -> None:
    """Append a rejected suggestion to runtime history."""

    rejected_csv = get_rejected_csv()

    rejected_csv.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = list(row.keys())

    if "Reason" not in fieldnames:
        fieldnames.append("Reason")

    exists = rejected_csv.exists()

    output = {
        name: row.get(name, "")
        for name in fieldnames
    }

    output["Reason"] = reason

    with rejected_csv.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        if not exists:
            writer.writeheader()

        writer.writerow(output)


def remove_suggestion(
    domain: str,
) -> bool:
    """Remove one suggestion from the runtime CSV."""

    suggestions_csv = (
        get_suggestions_csv()
    )

    if not suggestions_csv.exists():
        return False

    with suggestions_csv.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        fieldnames = (
            reader.fieldnames
            or SUGGESTION_FIELDNAMES
        )

        rows = list(reader)

    target = (
        domain.strip().lower()
    )

    filtered = [
        row
        for row in rows
        if (
            row.get("Domain", "")
            .strip()
            .lower()
            != target
        )
    ]

    if len(filtered) == len(rows):
        return False

    suggestions_csv.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = suggestions_csv.with_suffix(
        suggestions_csv.suffix
        + ".tmp"
    )

    with temporary.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(filtered)

    temporary.replace(
        suggestions_csv
    )

    return True


def load_decisions() -> list[dict]:
    """Load runtime review decisions."""

    decisions_csv = get_decisions_csv()

    if not decisions_csv.exists():
        return []

    with decisions_csv.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def latest_decision_map() -> dict[str, dict]:
    """Return the latest decision for each domain."""

    decisions: dict[str, dict] = {}

    for row in load_decisions():
        domain = (
            row.get("Domain", "")
            .strip()
            .lower()
        )

        if domain:
            decisions[domain] = row

    return decisions



def _ensure_decision_csv_schema(
    path: Path,
    fieldnames: list[str],
) -> None:
    """Upgrade an existing decision CSV without losing rows."""

    if not path.exists():
        return

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        current_fields = list(
            reader.fieldnames
            or []
        )

        rows = list(reader)

    if current_fields == fieldnames:
        return

    if not current_fields:
        return

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temporary.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    name: row.get(
                        name,
                        "",
                    )
                    for name in fieldnames
                }
            )

    temporary.replace(path)


def append_decision(
    row: dict,
    action: str,
    reason: str = "",
    actor: str = "web-ui",
    *,
    test_confirmed: bool = False,
    override_confirmed: bool = False,
    manual_review_confirmed: bool = False,
) -> None:
    """Append one runtime review decision."""

    decisions_csv = get_decisions_csv()

    decisions_csv.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _ensure_decision_csv_schema(
        decisions_csv,
        DECISION_FIELDNAMES,
    )

    exists = decisions_csv.exists()

    output = {
        name: row.get(name, "")
        for name in DECISION_FIELDNAMES
    }

    output["Blocking Policy"] = (
        row.get(
            "Blocking Policy",
            "unknown",
        )
        or "unknown"
    )

    output["Blocking Policy Reason"] = (
        row.get(
            "Blocking Policy Reason",
            "",
        )
        or ""
    )

    output["Blocking Policy Source"] = (
        row.get(
            "Blocking Policy Source",
            "fallback",
        )
        or "fallback"
    )

    output["Test Confirmed"] = (
        "true"
        if test_confirmed
        else "false"
    )

    output["Override Confirmed"] = (
        "true"
        if override_confirmed
        else "false"
    )

    output["Manual Review Confirmed"] = (
        "true"
        if manual_review_confirmed
        else "false"
    )

    guardrail = evaluate_policy_guardrail(
        output["Blocking Policy"],
        action,
        mode=GuardrailMode.SHADOW,
        reason_supplied=bool(
            str(reason or "").strip()
        ),
        test_confirmed=test_confirmed,
        override_confirmed=override_confirmed,
        manual_review_confirmed=(
            manual_review_confirmed
        ),
    )

    output["Guardrail Mode"] = (
        guardrail.mode.value
    )

    output["Guardrail Requirement"] = (
        guardrail.requirement.value
    )

    output["Guardrail Would Block"] = (
        "true"
        if guardrail.would_block
        else "false"
    )

    output["Guardrail Allowed"] = (
        "true"
        if guardrail.allowed
        else "false"
    )

    output["Guardrail Reason"] = (
        guardrail.reason
    )

    output["Time"] = (
        datetime.now(UTC)
        .isoformat(timespec="seconds")
    )

    output["Action"] = action
    output["Actor"] = actor
    output["Reason"] = reason

    with decisions_csv.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=DECISION_FIELDNAMES,
            extrasaction="ignore",
        )

        if not exists:
            writer.writeheader()

        writer.writerow(output)


def load_review_queue(
    include_decided: bool = False,
) -> list[dict]:
    """Load suggestions enriched with review decisions."""

    decisions = latest_decision_map()
    rows: list[dict] = []

    for row in load_suggestions():
        output = dict(row)

        domain = (
            output.get("Domain", "")
            .strip()
            .lower()
        )

        decision = decisions.get(domain)

        guardrail_preview = (
            evaluate_policy_guardrail(
                output.get(
                    "Blocking Policy",
                    "unknown",
                ),
                "approved",
                mode=GuardrailMode.SHADOW,
                reason_supplied=False,
            )
        )

        def decision_or_preview(
            field: str,
            preview: str,
        ) -> str:
            if decision:
                stored = str(
                    decision.get(
                        field,
                        "",
                    )
                    or ""
                ).strip()

                if stored:
                    return stored

            return preview

        output["Guardrail Preview"] = "true"

        output["Guardrail Mode"] = (
            decision_or_preview(
                "Guardrail Mode",
                guardrail_preview.mode.value,
            )
        )

        output["Guardrail Requirement"] = (
            decision_or_preview(
                "Guardrail Requirement",
                guardrail_preview.requirement.value,
            )
        )

        output["Guardrail Would Block"] = (
            decision_or_preview(
                "Guardrail Would Block",
                (
                    "true"
                    if guardrail_preview.would_block
                    else "false"
                ),
            )
        )

        output["Guardrail Allowed"] = (
            decision_or_preview(
                "Guardrail Allowed",
                (
                    "true"
                    if guardrail_preview.allowed
                    else "false"
                ),
            )
        )

        output["Guardrail Reason"] = (
            decision_or_preview(
                "Guardrail Reason",
                guardrail_preview.reason,
            )
        )

        output["Review Status"] = (
            decision.get(
                "Action",
                "pending",
            )
            if decision
            else "pending"
        )

        output["Review Reason"] = (
            decision.get(
                "Reason",
                "",
            )
            if decision
            else ""
        )

        output["Review Time"] = (
            decision.get(
                "Time",
                "",
            )
            if decision
            else ""
        )

        if (
            include_decided
            or output["Review Status"]
            == "pending"
        ):
            rows.append(output)

    return rows
