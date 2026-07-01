#!/usr/bin/env python3

"""Update command for the 5ibr AdGuard Filter Toolkit."""

from __future__ import annotations

import argparse
import sys

from scripts.database import search_domain
from scripts.services.database_service import update_validated_domain


def _ask(prompt: str, current: str, value: str | None) -> str:
    """Return a provided value or ask interactively with a default."""

    if value is not None:
        return value.strip()

    sys.stdout.write(f"{prompt} [{current}]: ")
    sys.stdout.flush()
    answer = input().strip()

    if answer:
        return answer

    return current


def _resolve_value(
    *,
    prompt: str,
    current: str,
    value: str | None,
    interactive: bool,
) -> str:
    """Resolve an update value from CLI input, interaction or current data."""

    if interactive:
        return _ask(prompt, current, value)

    if value is not None:
        return value.strip()

    return current


def _parse_confidence(value: str) -> int | None:
    """Parse and validate a confidence value."""

    try:
        confidence = int(value)
    except ValueError:
        return None

    if confidence < 0 or confidence > 100:
        return None

    return confidence


def _ask_domain(value: str | None) -> str:
    """Return a provided domain or ask interactively."""

    if value:
        return value.strip()

    print("Domain:")
    return input().strip()


def main(argv: list[str] | None = None) -> int:
    """Update an existing domain in the database."""

    parser = argparse.ArgumentParser(
        prog="fivebr update",
        description="Update an existing domain in the database",
    )

    parser.add_argument("--domain")
    parser.add_argument("--vendor")
    parser.add_argument("--category")
    parser.add_argument("--filter")
    parser.add_argument("--confidence")

    args = parser.parse_args(argv)

    print()
    print("===================================")
    print("5ibr Update Domain")
    print("===================================")
    print()

    interactive = args.domain is None

    domain = _ask_domain(args.domain)

    if not domain:
        print("ERROR: Domain is required.")
        return 1

    row = search_domain(domain)

    if row is None:
        print("ERROR: Domain not found.")
        return 1

    print()
    print("Current values")
    print()
    print(f"Vendor      : {row['Vendor']}")
    print(f"Category    : {row['Category']}")
    print(f"Filter      : {row['Filter']}")
    print(f"Confidence  : {row['Confidence']}")
    print()

    vendor = _resolve_value(
        prompt="Vendor",
        current=row["Vendor"],
        value=args.vendor,
        interactive=interactive,
    )
    category = _resolve_value(
        prompt="Category",
        current=row["Category"],
        value=args.category,
        interactive=interactive,
    )
    filter_name = _resolve_value(
        prompt="Filter",
        current=row["Filter"],
        value=args.filter,
        interactive=interactive,
    )
    confidence_value = _resolve_value(
        prompt="Confidence",
        current=row["Confidence"],
        value=args.confidence,
        interactive=interactive,
    )

    confidence = _parse_confidence(confidence_value)

    if confidence is None:
        print("ERROR: Confidence must be between 0 and 100.")
        return 1

    updated, errors = update_validated_domain(
        domain=domain,
        vendor=vendor,
        category=category,
        filter_name=filter_name,
        confidence=confidence,
    )
    if not updated:
        print("ERROR: Unable to update domain.")
        for error in errors:
            print(f"- {error}")
        return 1

    print()
    print("Domain updated successfully.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
