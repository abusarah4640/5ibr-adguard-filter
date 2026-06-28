#!/usr/bin/env python3

"""
5ibr Build System
"""

from builders.database import load_database
from builders.filters import build_filters


def main():

    print("Loading database...")

    rows = load_database()

    print(f"Loaded {len(rows)} domains")

    print()

    build_filters(rows)

    print()

    print("========================")
    print("5ibr Build Complete")
    print("========================")


if __name__ == "__main__":
    main()