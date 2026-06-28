#!/usr/bin/env python3

"""
5ibr AdGuard Filter
Smart Query Log Analyzer v3
"""

import csv
import json
from collections import Counter
from pathlib import Path

from filter_loader import load_existing_rules
from classifier import DomainClassifier

ROOT = Path(__file__).resolve().parent.parent

QUERY_LOG = ROOT / "querylog.json"

REPORT_DIR = ROOT / "reports"

TOP_CSV = REPORT_DIR / "top_domains.csv"
NEW_CSV = REPORT_DIR / "new_candidates.csv"


def extract_domain(entry):
    return entry.get("QH", "").strip().lower()


def load_querylog():

    counter = Counter()

    if not QUERY_LOG.exists():
        raise FileNotFoundError(
            f"Missing file: {QUERY_LOG}"
        )

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

            domain = extract_domain(obj)

            if domain:
                counter[domain] += 1

    return counter


def is_already_blocked(domain, rules):

    patterns = (
        f"||{domain}^",
        f"@@||{domain}^",
        f"|{domain}^",
        domain,
    )

    return any(pattern in rules for pattern in patterns)


def save_top(counter):

    with open(
        TOP_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as csvfile:

        writer = csv.writer(csvfile)

        writer.writerow([
            "Rank",
            "Requests",
            "Domain"
        ])

        for rank, (domain, count) in enumerate(
            counter.most_common(),
            start=1
        ):

            writer.writerow([
                rank,
                count,
                domain
            ])


def save_candidates(counter, rules):

    classifier = DomainClassifier()

    with open(
        NEW_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as csvfile:

        writer = csv.writer(csvfile)

        writer.writerow([
            "Rank",
            "Requests",
            "Domain",
            "Category",
            "Confidence",
            "Suggested Rule"
        ])

        rank = 1

        for domain, count in counter.most_common():

            if is_already_blocked(domain, rules):
                continue

            result = classifier.classify(domain)

            writer.writerow([
                rank,
                count,
                domain,
                result["category"],
                result["confidence"],
                f"||{domain}^"
            ])

            rank += 1


def print_summary(counter, rules):

    print()
    print("========================================")
    print("5ibr Query Log Analyzer")
    print("========================================")
    print()

    print(f"Unique Domains : {len(counter)}")
    print(f"Existing Rules : {len(rules)}")
    print()

    print(f"Generated : {TOP_CSV.name}")
    print(f"Generated : {NEW_CSV.name}")
    print()


def main():

    REPORT_DIR.mkdir(exist_ok=True)

    counter = load_querylog()

    rules = load_existing_rules()

    save_top(counter)

    save_candidates(counter, rules)

    print_summary(counter, rules)


if __name__ == "__main__":
    main()