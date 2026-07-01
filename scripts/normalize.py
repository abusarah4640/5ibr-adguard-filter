#!/usr/bin/env python3
"""5ibr Normalize Command."""

from __future__ import annotations

import argparse

from scripts.database import load_database, save_database, sort_database

VENDOR_ALIASES = {
    "google": "Google",
    "google ads": "Google",
    "meta": "Meta",
    "facebook": "Meta",
    "microsoft": "Microsoft",
    "riot": "Riot Games",
    "riot games": "Riot Games",
    "huawei": "Huawei",
    "xiaomi": "Xiaomi",
    "oppo": "OPPO",
    "lg": "LG",
    "adult": "Adult",
}

CATEGORY_ALIASES = {
    "ads": "Ads",
    "advertising": "Ads",
    "adult": "Adult",
    "gaming": "Gaming",
    "privacy": "Privacy",
    "social": "Social",
    "telemetry": "Telemetry",
    "smart tv": "Smart TV",
    "smart-tv": "Smart TV",
}

STATUS_ALIASES = {
    "approved": "Approved",
    "pending": "Pending",
    "review": "Review",
    "rejected": "Rejected",
}


def _canonical(value: str, aliases: dict[str, str]) -> str:
    stripped = value.strip()
    return aliases.get(stripped.lower(), stripped)


def main(argv: list[str] | None = None) -> int:
    """Normalize common vendor/category/status casing and whitespace."""

    parser = argparse.ArgumentParser(
        prog="fivebr normalize",
        description="Normalize database values",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    rows = load_database()
    changes = 0

    for row in rows:
        before = row.copy()
        row["Domain"] = row.get("Domain", "").strip().lower()
        row["Vendor"] = _canonical(row.get("Vendor", ""), VENDOR_ALIASES)
        row["Category"] = _canonical(row.get("Category", ""), CATEGORY_ALIASES)
        row["Filter"] = row.get("Filter", "").strip().lower()
        row["Status"] = _canonical(row.get("Status", ""), STATUS_ALIASES)
        row["Confidence"] = row.get("Confidence", "").strip()
        if row != before:
            changes += 1

    print(f"Rows normalized: {changes}")

    if args.dry_run:
        print("Dry run: database was not changed.")
        return 0

    save_database(sort_database(rows))
    print("Database normalized successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
