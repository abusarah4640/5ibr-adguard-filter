#!/usr/bin/env python3

"""
5ibr Add Command
"""

from __future__ import annotations

import argparse
import sys

from scripts.database import search_domain
from scripts.services.database_service import add_validated_domain


def _ask(prompt: str, value: str | None) -> str:
    """Return a CLI value if provided, otherwise ask interactively."""

    if value:
        return value.strip()

    print(f"{prompt}:")

    return sys.stdin.readline().strip()


def main(argv: list[str] | None = None) -> int:
    """Add a domain to the database."""

    parser = argparse.ArgumentParser(
        prog="fivebr add",
        description="Add a new domain to the database",
    )

    parser.add_argument("--domain")
    parser.add_argument("--vendor")
    parser.add_argument("--category")
    parser.add_argument("--filter")
    parser.add_argument(
        "--confidence",
        type=int,
    )

    args = parser.parse_args(argv)

    print()
    print("===================================")
    print("5ibr Add Domain")
    print("===================================")
    print()

    domain = _ask("Domain", args.domain)

    if not domain:
        print("ERROR: Domain is required.")
        return 1

    if search_domain(domain):
        print("ERROR: Domain already exists.")
        return 1

    vendor = _ask("Vendor", args.vendor)

    category = _ask("Category", args.category)

    filter_name = _ask("Filter", args.filter)

    confidence = args.confidence

    if confidence is None:

        while True:

            print("Confidence:")
            value = sys.stdin.readline().strip()

            try:

                confidence = int(value)

                break

            except ValueError:

                print("Confidence must be a number.")

    if confidence < 0 or confidence > 100:

        print("ERROR: Confidence must be between 0 and 100.")

        return 1

    added, errors = add_validated_domain(
        domain=domain,
        vendor=vendor,
        category=category,
        filter_name=filter_name,
        confidence=confidence,
    )

    if not added:

        print("ERROR: Unable to add domain.")
        for error in errors:
            print(f"- {error}")

        return 1

    print()
    print("Domain added successfully.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
