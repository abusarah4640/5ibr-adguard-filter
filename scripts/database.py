#!/usr/bin/env python3

"""
5ibr Database Manager
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "database" / "domains.csv"


def load_database() -> list[dict]:
    if not DATABASE.exists():
        return []

    with DATABASE.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def search_domain(domain: str) -> dict | None:
    domain = domain.lower()

    for row in load_database():
        if row["Domain"].lower() == domain:
            return row

    return None


def database_stats() -> dict:

    rows = load_database()

    vendors = Counter()
    categories = Counter()

    for row in rows:
        vendors[row["Vendor"]] += 1
        categories[row["Category"]] += 1

    return {
        "domains": len(rows),
        "vendors": len(vendors),
        "categories": len(categories),
        "top_vendors": vendors.most_common(10),
        "top_categories": categories.most_common(10),
    }
