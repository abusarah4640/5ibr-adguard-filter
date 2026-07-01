#!/usr/bin/env python3

"""
5ibr Report Generator
"""

import csv
from collections import Counter
from pathlib import Path

from scripts.cli import parse_no_args
from scripts.services.report_service import category_report, status_report, vendor_report

ROOT = Path(__file__).resolve().parent.parent

REPORT_DIR = ROOT / "reports"

NEW_CSV = REPORT_DIR / "new_candidates.csv"

SUMMARY_MD = REPORT_DIR / "summary.md"

VENDORS_CSV = REPORT_DIR / "vendors.csv"

CATEGORIES_CSV = REPORT_DIR / "categories.csv"
STATUS_CSV = REPORT_DIR / "status.csv"
DATABASE_SUMMARY_MD = REPORT_DIR / "database-summary.md"


def load_candidates() -> list[dict[str, str]]:
    """Load analyzer candidate rows if present."""

    rows = []

    if not NEW_CSV.exists():
        return rows

    with open(NEW_CSV, newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:
            rows.append(row)

    return rows



def write_database_reports() -> None:
    """Write database-level vendor/category/status reports."""

    with VENDORS_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Vendor", "Count"])
        for vendor, count in vendor_report().most_common():
            writer.writerow([vendor, count])

    with CATEGORIES_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Category", "Count"])
        for category, count in category_report().most_common():
            writer.writerow([category, count])

    statuses = status_report()
    with STATUS_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Status", "Count"])
        for status, count in statuses.most_common():
            writer.writerow([status, count])

    with DATABASE_SUMMARY_MD.open("w", encoding="utf-8") as file:
        file.write("# 5ibr Database Summary\n\n")
        file.write("## Status\n\n")
        for status, count in statuses.most_common():
            file.write(f"- {status}: {count}\n")
        file.write("\n## Top Vendors\n\n")
        for vendor, count in vendor_report().most_common(20):
            file.write(f"- {vendor}: {count}\n")
        file.write("\n## Categories\n\n")
        for category, count in category_report().most_common():
            file.write(f"- {category}: {count}\n")


def write_summary(rows: list[dict[str, str]]) -> None:
    """Write the Markdown summary report."""

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


def write_vendor_csv(rows: list[dict[str, str]]) -> None:
    """Write vendor frequency statistics."""

    counter = Counter()

    for row in rows:
        counter[row["Vendor"]] += 1

    with open(VENDORS_CSV, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow(["Vendor", "Count"])

        for vendor, count in counter.most_common():

            writer.writerow([vendor, count])


def write_category_csv(rows: list[dict[str, str]]) -> None:
    """Write category frequency statistics."""

    counter = Counter()

    for row in rows:
        counter[row["Category"]] += 1

    with open(CATEGORIES_CSV, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow(["Category", "Count"])

        for category, count in counter.most_common():

            writer.writerow([category, count])


def main(argv: list[str] | None = None) -> int:
    """Generate report files from query-log analysis candidates."""

    parse_no_args(
        prog="fivebr report",
        description="Generate project report",
        argv=argv,
    )

    REPORT_DIR.mkdir(exist_ok=True)

    rows = load_candidates()

    write_summary(rows)

    write_vendor_csv(rows)

    write_category_csv(rows)

    write_database_reports()

    print()

    print("===================================")
    print("5ibr Report Generator")
    print("===================================")

    print()

    print(f"Candidates : {len(rows)}")

    print(f"Generated  : {SUMMARY_MD.name}")
    print(f"Generated  : {VENDORS_CSV.name}")
    print(f"Generated  : {CATEGORIES_CSV.name}")
    print(f"Generated  : {STATUS_CSV.name}")
    print(f"Generated  : {DATABASE_SUMMARY_MD.name}")

    print()

    return 0


if __name__ == "__main__":

    raise SystemExit(main())
