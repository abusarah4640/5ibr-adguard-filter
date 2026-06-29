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

FIELDNAMES = [
    "Domain",
    "Vendor",
    "Category",
    "Filter",
    "Confidence",
]


def load_database() -> list[dict]:
    """
    Load all records from the CSV database.
    """

    if not DATABASE.exists():
        return []

    with DATABASE.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def save_database(rows: list[dict]) -> None:
    """
    Save all records to the CSV database.
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


def sort_database(rows: list[dict]) -> list[dict]:
    """
    Sort records alphabetically by domain.
    """

    return sorted(
        rows,
        key=lambda row: row["Domain"].lower(),
    )


def search_domain(domain: str) -> dict | None:
    """
    Search for a domain.
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
    Add a new domain.
    """

    rows = load_database()

    if search_domain(domain):
        return False

    rows.append(
        {
            "Domain": domain.strip(),
            "Vendor": vendor.strip(),
            "Category": category.strip(),
            "Filter": filter_name.strip(),
            "Confidence": str(confidence),
        }
    )

    save_database(sort_database(rows))

    return True


def remove_domain(domain: str) -> bool:
    """
    Remove a domain.
    """

    rows = load_database()

    filtered = [
        row
        for row in rows
        if row["Domain"].lower() != domain.lower()
    ]

    if len(filtered) == len(rows):
        return False

    save_database(filtered)

    return True


def update_domain(
    domain: str,
    vendor: str,
    category: str,
    filter_name: str,
    confidence: int,
) -> bool:
    """
    Update an existing domain.
    """

    rows = load_database()

    updated = False

    for row in rows:

        if row["Domain"].lower() == domain.lower():

            row["Vendor"] = vendor
            row["Category"] = category
            row["Filter"] = filter_name
            row["Confidence"] = str(confidence)

            updated = True
            break

    if not updated:
        return False

    save_database(sort_database(rows))

    return True


def database_stats() -> dict:
    """
    Return database statistics.
    """

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
