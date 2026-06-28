#!/usr/bin/env python3

from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent

FILTER_DIR = ROOT / "filters"
RELEASE_DIR = ROOT / "releases"

OUTPUT_FILE = RELEASE_DIR / "home.txt"

VERSION = "1.0.0"

FILTERS = [
    "ads.txt",
    "telemetry.txt",
    "privacy.txt",
    "social.txt",
    "mobile.txt",
    "gaming.txt",
    "smart-tv.txt",
]

HEADER = f"""! Title: 5ibr Home Filter
! Description: Combined AdGuard Home filter.
! Author: 5ibr
! Homepage: https://github.com/abusarah4640/5ibr-adguard-filter
! License: GPL-3.0
! Version: {VERSION}
! Last modified: {date.today()}
! Expires: 7 days

"""


def read_rules(file_path):
    rules = []

    with open(file_path, encoding="utf-8", errors="ignore") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            if line.startswith("!"):
                continue

            rules.append(line)

    return rules


def build():

    all_rules = []

    duplicate_count = 0

    print()

    print("======================================")
    print("5ibr Filter Builder")
    print("======================================")

    for filename in FILTERS:

        path = FILTER_DIR / filename

        if not path.exists():
            print(f"[SKIP] {filename}")
            continue

        rules = read_rules(path)

        print(f"[OK] {filename:<20} {len(rules):>6} rules")

        all_rules.extend(rules)

    unique = sorted(set(all_rules))

    duplicate_count = len(all_rules) - len(unique)

    RELEASE_DIR.mkdir(exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:

        out.write(HEADER)

        for rule in unique:
            out.write(rule + "\n")

    print()
    print("--------------------------------------")
    print(f"Total Rules      : {len(all_rules)}")
    print(f"Duplicates       : {duplicate_count}")
    print(f"Final Rules      : {len(unique)}")
    print("--------------------------------------")
    print()
    print("Generated:")
    print(OUTPUT_FILE)
    print()


if __name__ == "__main__":
    build()