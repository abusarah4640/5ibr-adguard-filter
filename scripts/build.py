#!/usr/bin/env python3

"""
5ibr Build System
"""

from builders.database import load_database
from builders.filters import build_filters
from builders.config import build_config


def main():

    print("===================================")
    print("5ibr Filter Build System")
    print("===================================")
    print()

    print("Loading database...")

    rows = load_database()

    print(f"Loaded {len(rows)} approved domains.")
    print()

    print("Generating filter files...")
    build_filters(rows)
    print()

    print("Generating configuration files...")
    build_config(rows)
    print()

    print("===================================")
    print("Build completed successfully.")
    print("===================================")


if __name__ == "__main__":
    main()