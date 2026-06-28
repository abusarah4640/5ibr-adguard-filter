#!/usr/bin/env python3

"""
5ibr Build System
"""

from builders.database import load_database
from builders.filters import build_filters
from builders.config import build_config
from builders.releases import build_releases


def main():

    print("===================================")
    print("5ibr Filter Build System")
    print("===================================")
    print()

    print("Loading database...")

    rows = load_database()

    print(f"Loaded {len(rows)} approved domains.")
    print()

    print("Generating filters...")
    build_filters(rows)
    print()

    print("Generating config...")
    build_config(rows)
    print()

    print("Generating releases...")
    build_releases()
    print()

    print("===================================")
    print("Build completed successfully.")
    print("===================================")


if __name__ == "__main__":
    main()