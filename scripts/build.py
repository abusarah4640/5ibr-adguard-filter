#!/usr/bin/env python3

"""Build command for the 5ibr AdGuard Filter Toolkit."""

from __future__ import annotations

from scripts.builders.config import build_config
from scripts.builders.database import load_database
from scripts.builders.filters import build_filters
from scripts.builders.releases import build_releases
from scripts.cli import parse_no_args


def main(argv: list[str] | None = None) -> int:
    """Build filters, generated config files and release bundles."""

    parse_no_args(
        prog="fivebr build",
        description="Build filters, configs and releases",
        argv=argv,
    )

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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
