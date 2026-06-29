#!/usr/bin/env python3

"""
5ibr Database Search
"""

from __future__ import annotations

import argparse

from scripts.database import search_domain


def main() -> int:

    parser = argparse.ArgumentParser(
        prog="fivebr search",
        description="Search for a domain in the database",
    )

    parser.add_argument(
        "domain",
        help="Domain to search for",
    )

    args = parser.parse_args()

    result = search_domain(args.domain)

    print()
    print("===================================")
    print("5ibr Domain Search")
    print("===================================")
    print()

    if result is None:
        print("Domain not found.")
        return 1

    print(f"Domain      : {result['Domain']}")
    print(f"Vendor      : {result['Vendor']}")
    print(f"Category    : {result['Category']}")
    print(f"Filter      : {result['Filter']}")
    print(f"Confidence  : {result['Confidence']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
