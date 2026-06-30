#!/usr/bin/env python3

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RELEASES_CONFIG = ROOT / "config" / "releases.json"
FILTERS = ROOT / "filters"


def load_release_filters():

    with open(RELEASES_CONFIG, encoding="utf-8") as f:
        data = json.load(f)

    names = set()

    for release in data.values():
        names.update(release.get("filters", []))

    return sorted(names)


def load_filter_files():

    files = {path.stem: path for path in FILTERS.glob("*.txt")}

    for name in load_release_filters():
        files.setdefault(name, FILTERS / f"{name}.txt")

    return dict(sorted(files.items()))


def main():

    print()
    print("==========================================")
    print("5ibr Filter Validator")
    print("==========================================")
    print()

    has_errors = False

    global_rules = {}

    total_rules = 0

    for name, path in load_filter_files().items():

        filename = path.name

        print(f"Checking {filename}")

        if not path.exists():

            print("  ERROR : File not found")

            has_errors = True

            continue

        rules = set()

        with open(path, encoding="utf-8", errors="ignore") as f:

            for number, line in enumerate(f, start=1):

                line = line.strip()

                if not line:
                    continue

                if line.startswith("!"):
                    continue

                total_rules += 1

                if line in rules:

                    print(
                        f"  Duplicate in file : line {number}"
                    )

                    has_errors = True

                rules.add(line)

                if line in global_rules:

                    other = global_rules[line]

                    print(
                        f"  Duplicate across files : {filename} ↔ {other}"
                    )

                    has_errors = True

                else:

                    global_rules[line] = filename

        print(f"  OK ({len(rules)} rules)")
        print()

    print("------------------------------------------")
    print(f"Total unique rules : {len(global_rules)}")
    print(f"Total rules        : {total_rules}")
    print("------------------------------------------")

    if has_errors:

        print()
        print("Validation FAILED")

        return 1

    print()
    print("Validation PASSED")

    return 0


if __name__ == "__main__":
    sys.exit(main())
