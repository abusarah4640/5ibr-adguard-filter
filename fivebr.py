#!/usr/bin/env python3

"""
5ibr Command Line Interface
"""

import argparse
import sys

from scripts.build import main as build_main
from scripts.validate import main as validate_main
from scripts.report import main as report_main
from scripts.stats import main as stats_main


def main():

    parser = argparse.ArgumentParser(
        prog="fivebr",
        description="5ibr AdGuard Filter Toolkit"
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True
    )

    sub.add_parser(
        "build",
        help="Build filters, configs and releases"
    )

    sub.add_parser(
        "validate",
        help="Validate generated filters"
    )

    sub.add_parser(
        "report",
        help="Generate project report"
    )

    sub.add_parser(
        "stats",
        help="Show database statistics"
    )

    args = parser.parse_args()

    if args.command == "build":
        build_main()

    elif args.command == "validate":
        sys.exit(validate_main())

    elif args.command == "report":
        report_main()

    elif args.command == "stats":
        stats_main()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
