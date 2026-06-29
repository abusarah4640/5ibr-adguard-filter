#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = ROOT / "config" / "categories.json"
FILTER_DIR = ROOT / "filters"


def load_config():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def clean_file(path):

    comments = []
    rules = set()

    with open(path, encoding="utf-8", errors="ignore") as f:

        for line in f:

            line = line.rstrip()

            if not line:
                continue

            if line.startswith("!"):
                comments.append(line)
                continue

            rules.add(line.strip())

    with open(path, "w", encoding="utf-8") as f:

        for line in comments:
            f.write(line + "\n")

        if comments:
            f.write("\n")

        for rule in sorted(rules):
            f.write(rule + "\n")

    return len(rules)


def main():

    load_config()

    print()
    print("======================================")
    print("5ibr Auto Fix")
    print("======================================")
    print()

    total = 0

    for path in sorted(FILTER_DIR.glob("*.txt")):

        count = clean_file(path)

        total += count

        print(f"[FIXED] {path.stem:<20} {count:>6} rules")

    print()
    print("--------------------------------------")
    print(f"Total Rules : {total}")
    print("--------------------------------------")
    print()


if __name__ == "__main__":
    main()
