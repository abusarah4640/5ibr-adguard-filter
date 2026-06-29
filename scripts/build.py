#!/usr/bin/env python3

"""
5ibr Build System
"""

from scripts.builders.database import load_database
from scripts.builders.filters import build_filters
from scripts.builders.config import build_config
from scripts.builders.releases import build_releases


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
