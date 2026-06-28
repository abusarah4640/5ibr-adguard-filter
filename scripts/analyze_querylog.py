#!/usr/bin/env python3

import json
import csv
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent

QUERY_LOG = ROOT / "querylog.json"
REPORT_DIR = ROOT / "reports"

TOP_CSV = REPORT_DIR / "top_domains.csv"


def extract_domain(entry):
    return entry.get("QH", "").strip().lower()


def load_querylog():

    domains = Counter()

    with open(QUERY_LOG, encoding="utf-8", errors="ignore") as f:

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
                domains[domain] += 1

    return domains


def save_csv(counter):

    REPORT_DIR.mkdir(exist_ok=True)

    with open(TOP_CSV, "w", newline="", encoding="utf-8") as csvfile:

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


def main():

    print()
    print("====================================")
    print("5ibr Query Log Analyzer")
    print("====================================")
    print()

    counter = load_querylog()

    save_csv(counter)

    print(f"Unique Domains : {len(counter)}")
    print(f"CSV Report     : {TOP_CSV}")
    print()


if __name__ == "__main__":
    main()