#!/usr/bin/env python3

"""
5ibr Query Log Analyzer v4
"""

import csv
import json
from collections import Counter
from pathlib import Path

from scripts.cli import parse_no_args
from scripts.classifier import DomainClassifier
from scripts.filter_loader import load_existing_rules

ROOT = Path(__file__).resolve().parent.parent

QUERY_LOG = ROOT / "querylog.json"
REPORT_DIR = ROOT / "reports"

TOP_CSV = REPORT_DIR / "top_domains.csv"
NEW_CSV = REPORT_DIR / "new_candidates.csv"


def load_querylog():

    counter = Counter()

    blocked = 0
    allowed = 0

    with open(
        QUERY_LOG,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            try:
                obj = json.loads(line)

            except Exception:
                continue

            domain = obj.get("QH", "").lower().strip()

            if not domain:
                continue

            result = obj.get("Result", {})

            if result.get("IsFiltered", False):
                blocked += 1
                continue

            allowed += 1
            counter[domain] += 1

    return counter, blocked, allowed


def is_existing(domain, rules):

    patterns = (
        f"||{domain}^",
        f"@@||{domain}^",
        domain,
    )

    return any(rule in rules for rule in patterns)


def write_reports(counter, rules):

    REPORT_DIR.mkdir(exist_ok=True)

    classifier = DomainClassifier()

    with open(
        TOP_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as top_file, open(
        NEW_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as new_file:

        top_writer = csv.writer(top_file)
        new_writer = csv.writer(new_file)

        top_writer.writerow(["Rank", "Requests", "Domain"])

        new_writer.writerow([
            "Rank",
            "Requests",
            "Domain",
            "Vendor",
            "Category",
            "Confidence",
            "Suggested Rule"
        ])

        rank = 1

        for domain, count in counter.most_common():

            top_writer.writerow([rank, count, domain])

            if not is_existing(domain, rules):

                info = classifier.classify(domain)

                new_writer.writerow([
                    rank,
                    count,
                    domain,
                    info["vendor"],
                    info["category"],
                    info["confidence"],
                    f"||{domain}^"
                ])

            rank += 1


def main(argv: list[str] | None = None) -> int:
    """Analyze an AdGuard query log and write candidate reports."""

    parse_no_args(
        prog="fivebr analyze-querylog",
        description="Analyze querylog.json",
        argv=argv,
    )

    rules = load_existing_rules()

    counter, blocked, allowed = load_querylog()

    write_reports(counter, rules)

    print()
    print("====================================")
    print("5ibr Query Analyzer")
    print("====================================")
    print()
    print(f"Allowed Queries : {allowed}")
    print(f"Blocked Queries : {blocked}")
    print(f"Unique Domains  : {len(counter)}")
    print(f"Existing Rules  : {len(rules)}")
    print()
    print("Reports generated successfully.")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
