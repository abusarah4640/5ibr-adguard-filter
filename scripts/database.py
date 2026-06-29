#!/usr/bin/env python3

"""
5ibr Database Manager
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATABASE = ROOT / "database" / "domains.csv"


FIELDNAMES = [
    "Domain",
    "Vendor",
    "Category",
    "Filter",
    "Confidence",
]


def load_database() -> list[dict]:
    """
    Load all database records.
    """

    if not DATABASE.exists():
        return []

    with DATABASE.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        return list(reader)


def save_database(rows: list[dict]) -> None:
    """
    Save all records.
    """

    with DATABASE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
        )

        writer.writeheader()

        writer.writerows(rows)


def search_domain(domain: str) -> dict | None:
    """
    Find a domain.
    """

    domain = domain.lower()

    for row in load_database():

        if row["Domain"].lower() == domain:
            return row

    return None


def add_domain(
    domain: str,
    vendor: str,
    category: str,
    filter_name: str,
    confidence: int,
) -> bool:
    """
    Add new domain.
    """

    rows = load_database()

    if search_domain(domain):
        return False

    rows.append(
        {
            "Domain": domain,
            "Vendor": vendor,
            "Category": category,
            "Filter": filter_name,
            "Confidence": confidence,
        }
    )

    rows.sort(
        key=lambda item: item["Domain"].lower()
    )

    save_database(rows)

    return True


def remove_domain(domain: str) -> bool:
    """
    Remove domain.
    """

    rows = load_database()

    original = len(rows)

    rows = [
        row
        for row in rows
        if row["Domain"].lower() != domain.lower()
    ]

    if len(rows) == original:
        return False

    save_database(rows)

    return True


def database_stats() -> dict:

    rows = load_database()

    vendors = set()
    categories = set()

    for row in rows:

        vendors.add(row["Vendor"])

        categories.add(row["Category"])

    return {
        "domains": len(rows),
        "vendors": len(vendors),
        "categories": len(categories),
    }
