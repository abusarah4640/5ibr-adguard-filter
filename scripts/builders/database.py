#!/usr/bin/env python3

"""Database utilities used by the build pipeline."""

import csv
from pathlib import Path

from scripts.runtime.paths import (
    get_runtime_paths,
)


def get_database_path() -> Path:
    """Return the active runtime database path."""

    return (
        get_runtime_paths().database
        / "domains.csv"
    )


DATABASE = get_database_path()


def load_database(
    path: str | Path | None = None,
) -> list[dict]:
    """Load approved domains from the runtime database."""

    database_path = (
        Path(path)
        if path is not None
        else get_database_path()
    )

    rows: list[dict] = []

    with database_path.open(
        newline="",
        encoding="utf-8",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            if row["Status"] != "Approved":
                continue

            rows.append(row)

    return rows
