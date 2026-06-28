#!/usr/bin/env python3

"""
5ibr Build System
Build filters from the centralized domain database.
"""

from pathlib import Path
import csv
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent

DATABASE = ROOT / "database" / "domains.csv"
FILTERS = ROOT / "filters"

HEADER = """! Title: 5ibr Filter
! Homepage: https://github.com/abusarah4640/5ibr-adguard-filter
! License: GPL-3.0
! Generated automatically.
!
"""


def load_database():

    rows = []

    with open(DATABASE, newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:

            if row["Status"] != "Approved":
                continue

            rows.append(row)

    return rows


def build_filters(rows):

    groups = defaultdict(list)

    for row in rows:

        groups[row["Filter"]].append(
            "||" + row["Domain"] + "^"
        )

    FILTERS.mkdir(exist_ok=True)

    for name, rules in groups.items():

        rules = sorted(set(rules))

        output = FILTERS / f"{name}.txt"

        output.write_text(

            HEADER +
            "\n".join(rules) +
            "\n",

            encoding="utf-8"

        )

        print(f"Generated {output.name} ({len(rules)} rules)")


def main():

    rows = load_database()

    build_filters(rows)

    print()
    print("==============================")
    print("Build completed successfully.")
    print("==============================")
    print()


if __name__ == "__main__":
    main()