#!/usr/bin/env python3

"""
Database utilities
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

DATABASE = ROOT / "database" / "domains.csv"


def load_database():

    rows = []

    with open(
        DATABASE,
        newline="",
        encoding="utf-8"
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            if row["Status"] != "Approved":
                continue

            rows.append(row)

    return rows