#!/usr/bin/env python3

"""
5ibr Report Generator
"""

import csv
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent

REPORT_DIR = ROOT / "reports"

NEW_CSV = REPORT_DIR / "new_candidates.csv"

SUMMARY_MD = REPORT_DIR / "summary.md"

VENDORS_CSV = REPORT_DIR / "vendors.csv"

CATEGORIES_CSV = REPORT_DIR / "categories.csv"


def load_candidates():

    rows = []

    if not NEW_CSV.exists():
        return rows

    with open(NEW_CSV, newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:
            rows.append(row)

    return rows


def write_summary(rows):

    vendors = Counter()
    categories = Counter()

    for row in rows:

        vendors[row["Vendor"]] += 1
        categories[row["Category"]] += 1

    with open(SUMMARY_MD, "w", encoding="utf-8") as f:

        f.write("# 5ibr Analysis Report\n\n")

        f.write(f"Total Suggestions: **{len(rows)}**\n\n")

        f.write("## Vendors\n\n")

        for vendor, count in vendors.most_common():

            f.write(f"- {vendor}: {count}\n")

        f.write("\n## Categories\n\n")

        for category, count in categories.most_common():

            f.write(f"- {category}: {count}\n")


def write_vendor_csv(rows):

    counter = Counter()

    for row in rows:
        counter[row["Vendor"]] += 1

    with open(VENDORS_CSV, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow(["Vendor", "Count"])

        for vendor, count in counter.most_common():

            writer.writerow([vendor, count])


def write_category_csv(rows):

    counter = Counter()

    for row in rows:
        counter[row["Category"]] += 1

    with open(CATEGORIES_CSV, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow(["Category", "Count"])

        for category, count in counter.most_common():

            writer.writerow([category, count])


def main():

    REPORT_DIR.mkdir(exist_ok=True)

    rows = load_candidates()

    write_summary(rows)

    write_vendor_csv(rows)

    write_category_csv(rows)

    print()

    print("===================================")
    print("5ibr Report Generator")
    print("===================================")

    print()

    print(f"Candidates : {len(rows)}")

    print(f"Generated  : {SUMMARY_MD.name}")
    print(f"Generated  : {VENDORS_CSV.name}")
    print(f"Generated  : {CATEGORIES_CSV.name}")

    print()


if __name__ == "__main__":

    main()