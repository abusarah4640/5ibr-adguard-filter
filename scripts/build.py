#!/usr/bin/env python3

import json
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent

FILTER_DIR = ROOT / "filters"
RELEASE_DIR = ROOT / "releases"
CONFIG_FILE = ROOT / "config" / "categories.json"

OUTPUT_FILE = RELEASE_DIR / "home.txt"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def read_rules(file_path):
    rules = []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if line.startswith("!"):
                continue

            rules.append(line)

    return rules


def build():

    config = load_config()

    version = config["version"]

    header = f"""! Title: 5ibr Home Filter
! Description: Combined AdGuard Home filter.
! Author: 5ibr
! Homepage: https://github.com/abusarah4640/5ibr-adguard-filter
! License: GPL-3.0
! Version: {version}
! Last modified: {date.today()}
! Expires: 7 days

"""

    all_rules = []

    print()
    print("======================================")
    print("5ibr Filter Builder")
    print("======================================")
    print()

    for item in config["filters"]:

        filename = item["file"]
        name = item["name"]

        path = FILTER_DIR / filename

        if not path.exists():
            print(f"[SKIP] {name}")
            continue

        rules = read_rules(path)

        print(f"[OK] {name:<20} {len(rules):>6} rules")

        all_rules.extend(rules)

    unique_rules = sorted(set(all_rules))

    duplicates = len(all_rules) - len(unique_rules)

    RELEASE_DIR.mkdir(exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

        f.write(header)

        for rule in unique_rules:
            f.write(rule + "\n")

    print()
    print("--------------------------------------")
    print(f"Total Rules      : {len(all_rules)}")
    print(f"Duplicates       : {duplicates}")
    print(f"Final Rules      : {len(unique_rules)}")
    print("--------------------------------------")
    print()
    print(f"Generated: {OUTPUT_FILE}")
    print()


if __name__ == "__main__":
    build()