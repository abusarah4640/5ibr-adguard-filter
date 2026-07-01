#!/usr/bin/env python3
"""5ibr Doctor Command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.database import DATABASE, FIELDNAMES, load_database
from scripts.services.database_service import database_integrity_report

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
FILTERS = ROOT / "filters"
RELEASES = ROOT / "releases"


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _check(condition: bool, label: str, problems: list[str]) -> None:
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        problems.append(label)


def main(argv: list[str] | None = None) -> int:
    """Run a health check against database, config, filters and releases."""

    parser = argparse.ArgumentParser(
        prog="fivebr doctor",
        description="Check project health and consistency",
    )
    parser.parse_args(argv)

    print()
    print("==========================================")
    print("5ibr Project Doctor")
    print("==========================================")
    print()

    problems: list[str] = []

    _check(DATABASE.exists(), "Database file exists", problems)
    rows = load_database()
    _check(bool(rows), "Database has rows", problems)

    if rows:
        for field in FIELDNAMES:
            _check(field in rows[0], f"Database has required column: {field}", problems)

        integrity_ok, integrity_errors, integrity_warnings = database_integrity_report()
        _check(integrity_ok, "Central database integrity rules", problems)
        for warning in integrity_warnings:
            print(f"[WARN] {warning}")
        for error in integrity_errors:
            print(f"[FAIL] {error}")

    required_config = ["categories.json", "database.json", "releases.json", "signatures.json", "vendors.json"]
    for name in required_config:
        path = CONFIG / name
        _check(path.exists(), f"Config exists: {name}", problems)
        if path.exists():
            try:
                _load_json(path)
                _check(True, f"Config is valid JSON: {name}", problems)
            except json.JSONDecodeError:
                _check(False, f"Config is valid JSON: {name}", problems)

    release_filters: set[str] = set()
    releases_config = CONFIG / "releases.json"
    if releases_config.exists():
        try:
            releases = _load_json(releases_config)
            for release in releases.values():
                release_filters.update(release.get("filters", []))
        except json.JSONDecodeError:
            releases = {}
        for filter_name in sorted(release_filters):
            _check((FILTERS / f"{filter_name}.txt").exists(), f"Filter exists: {filter_name}.txt", problems)

    if rows:
        known_filters = {path.stem for path in FILTERS.glob("*.txt")}
        unknown_filters = sorted({row.get("Filter", "") for row in rows if row.get("Filter", "") not in known_filters})
        _check(not unknown_filters, "Database filters exist as files", problems)

    print()
    print("------------------------------------------")
    print(f"Rows checked     : {len(rows)}")
    print(f"Problems found   : {len(problems)}")
    print("------------------------------------------")

    if problems:
        print("Doctor FAILED")
        return 1

    print("Doctor PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
