#!/usr/bin/env python3
"""5ibr Export Command."""

from __future__ import annotations

import argparse
import csv
import json
import sys

from scripts.database import get_database_fieldnames, load_database


def _write_markdown(rows: list[dict], fields: list[str]) -> str:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Export the database to CSV, JSON or Markdown."""

    parser = argparse.ArgumentParser(prog="fivebr export", description="Export database")
    parser.add_argument("--format", choices=["csv", "json", "md", "markdown"], default="json")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    rows = load_database()
    fields = get_database_fieldnames(rows)

    if args.format == "json":
        data = json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    elif args.format in {"md", "markdown"}:
        data = _write_markdown(rows, fields)
    else:
        from io import StringIO
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        data = buffer.getvalue()

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as file:
            file.write(data)
        print(f"Exported {len(rows)} rows to {args.output}")
    else:
        sys.stdout.write(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
