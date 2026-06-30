#!/usr/bin/env python3

"""Database statistics command."""

from __future__ import annotations

from scripts.cli import parse_no_args
from scripts.database import database_stats


def main(argv: list[str] | None = None) -> int:
    """Print database statistics."""

    parse_no_args(
        prog="fivebr stats",
        description="Show database statistics",
        argv=argv,
    )

    stats = database_stats()

    print()
    print("===================================")
    print("5ibr Database Statistics")
    print("===================================")
    print()

    print(f"Domains    : {stats['domains']}")
    print(f"Vendors    : {stats['vendors']}")
    print(f"Categories : {stats['categories']}")

    print()
    print("Top Vendors")
    print("-----------")

    for vendor, count in stats["top_vendors"]:
        print(f"{vendor:<20} {count}")

    print()
    print("Top Categories")
    print("----------------")

    for category, count in stats["top_categories"]:
        print(f"{category:<20} {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
