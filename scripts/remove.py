#!/usr/bin/env python3

"""
5ibr Remove Command
"""

from __future__ import annotations

import argparse

from scripts.database import (
    remove_domain,
    search_domain,
)


def main(argv: list[str] | None = None) -> int:
    """Remove a domain from the database."""

    parser = argparse.ArgumentParser(
        prog="fivebr remove",
        description="Remove a domain from the database",
    )

    parser.add_argument(
        "domain",
        nargs="?",
        help="Domain to remove",
    )

    args = parser.parse_args(argv)

    print()
    print("===================================")
    print("5ibr Remove Domain")
    print("===================================")
    print()

    domain = args.domain

    if not domain:
        print("Domain:")
        domain = input().strip()

    if not domain:
        print("ERROR: Domain is required.")
        return 1

    row = search_domain(domain)

    if not row:
        print("ERROR: Domain not found.")
        return 1

    print(f"Domain      : {row['Domain']}")
    print(f"Vendor      : {row['Vendor']}")
    print(f"Category    : {row['Category']}")
    print(f"Filter      : {row['Filter']}")
    print(f"Confidence  : {row['Confidence']}")
    print()

    print("Remove this domain? [y/N]:")
    answer = input().strip().lower()

    if answer not in ("y", "yes"):
        print("Operation cancelled.")
        return 0

    if not remove_domain(domain):
        print("ERROR: Unable to remove domain.")
        return 1

    print()
    print("Domain removed successfully.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
