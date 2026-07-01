#!/usr/bin/env python3
"""5ibr Import Command."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from scripts.database import load_database, save_database, sort_database


def _read_rows(path: Path, fmt: str) -> list[dict]:
    if fmt == "json":
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise ValueError("JSON import must contain a list of objects")
        return [dict(item) for item in data]

    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def main(argv: list[str] | None = None) -> int:
    """Import database rows from CSV or JSON."""

    parser = argparse.ArgumentParser(prog="fivebr import", description="Import domains")
    parser.add_argument("path")
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--status", default="Pending", help="Default status for imported rows without Status")
    parser.add_argument("--replace", action="store_true", help="Replace existing rows with imported rows")
    args = parser.parse_args(argv)

    imported = _read_rows(Path(args.path), args.format)
    existing = load_database()
    by_domain = {row.get("Domain", "").strip().lower(): row for row in existing if row.get("Domain")}

    added = 0
    updated = 0
    for row in imported:
        domain = row.get("Domain", "").strip().lower()
        if not domain:
            continue
        row["Domain"] = domain
        row.setdefault("Status", args.status)
        if not row.get("Status"):
            row["Status"] = args.status
        if domain in by_domain:
            if args.replace:
                by_domain[domain].update(row)
                updated += 1
        else:
            by_domain[domain] = row
            added += 1

    save_database(sort_database(list(by_domain.values())))
    print(f"Imported rows added: {added}")
    print(f"Imported rows updated: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
