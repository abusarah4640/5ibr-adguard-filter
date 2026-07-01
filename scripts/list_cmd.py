#!/usr/bin/env python3
"""5ibr List Command."""

from __future__ import annotations

import argparse

from scripts.database import load_database

COLUMNS = ["Domain", "Vendor", "Category", "Filter", "Status", "Confidence"]


def _matches(row: dict, field: str, value: str | None) -> bool:
    if not value:
        return True
    return row.get(field, "").lower() == value.strip().lower()


def _print_table(rows: list[dict], columns: list[str]) -> None:
    if not rows:
        print("No matching domains found.")
        return

    widths = {
        column: max(len(column), *(len(str(row.get(column, ""))) for row in rows))
        for column in columns
    }
    header = "  ".join(column.ljust(widths[column]) for column in columns)
    line = "  ".join("-" * widths[column] for column in columns)
    print(header)
    print(line)
    for row in rows:
        print("  ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns))


def main(argv: list[str] | None = None) -> int:
    """List database rows with optional filters."""

    parser = argparse.ArgumentParser(
        prog="fivebr list",
        description="List domains from the database",
    )
    parser.add_argument("--vendor")
    parser.add_argument("--category")
    parser.add_argument("--filter")
    parser.add_argument("--status")
    parser.add_argument("--limit", type=int, default=0)

    args = parser.parse_args(argv)

    rows = [
        row
        for row in load_database()
        if _matches(row, "Vendor", args.vendor)
        and _matches(row, "Category", args.category)
        and _matches(row, "Filter", args.filter)
        and _matches(row, "Status", args.status)
    ]

    rows.sort(key=lambda row: (row.get("Vendor", "").lower(), row.get("Domain", "").lower()))

    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    _print_table(rows, COLUMNS)
    print()
    print(f"Rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
