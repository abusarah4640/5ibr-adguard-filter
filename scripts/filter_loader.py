#!/usr/bin/env python3

"""
5ibr AdGuard Filter
Filter Loader

Loads all existing rules from filters/*.txt
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILTERS_DIR = ROOT / "filters"


def load_existing_rules():
    """
    Load all blocking rules from every filter file.
    Returns:
        set[str]
    """

    rules = set()

    if not FILTERS_DIR.exists():
        return rules

    for file in sorted(FILTERS_DIR.glob("*.txt")):

        with open(file, "r", encoding="utf-8", errors="ignore") as f:

            for line in f:

                line = line.strip()

                if not line:
                    continue

                # Ignore comments
                if line.startswith("!"):
                    continue

                if line.startswith("#"):
                    continue

                # Ignore include directives
                if line.startswith("#!include"):
                    continue

                rules.add(line)

    return rules


def main():

    rules = load_existing_rules()

    print("====================================")
    print("5ibr Filter Loader")
    print("====================================")
    print()
    print(f"Loaded {len(rules)} rules.")
    print()


if __name__ == "__main__":
    main()