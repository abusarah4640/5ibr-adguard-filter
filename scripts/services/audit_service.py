#!/usr/bin/env python3

"""Append-only audit log for Web UI administrative actions."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from scripts.runtime.paths import (
    get_runtime_paths,
)


FIELDNAMES = [
    "Timestamp",
    "Actor",
    "Action",
    "Target",
    "Result",
    "Details",
]


def get_audit_file() -> Path:
    """Return the active runtime Web audit file."""

    return (
        get_runtime_paths().data
        / "audit"
        / "web-audit.csv"
    )


# Compatibility constant for older imports/tests.
AUDIT_FILE = get_audit_file()


def utc_now() -> str:
    """Return the current UTC timestamp."""

    return (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def log_event(
    action: str,
    target: str = "",
    result: str = "ok",
    details: str = "",
    actor: str = "web-ui",
) -> None:
    """Append one event to the active runtime audit log."""

    audit_file = get_audit_file()

    audit_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    exists = audit_file.exists()

    with audit_file.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
        )

        if not exists:
            writer.writeheader()

        writer.writerow(
            {
                "Timestamp": utc_now(),
                "Actor": actor,
                "Action": action,
                "Target": target,
                "Result": result,
                "Details": details,
            }
        )


def recent_events(
    limit: int = 20,
) -> list[dict]:
    """Return the most recent runtime audit events."""

    audit_file = get_audit_file()

    if not audit_file.exists():
        return []

    with audit_file.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    return list(
        reversed(rows[-limit:])
    )
