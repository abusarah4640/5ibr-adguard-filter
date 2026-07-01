#!/usr/bin/env python3

"""Command router for the 5ibr AdGuard Filter Toolkit."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from scripts.add import main as add_main
from scripts.doctor import main as doctor_main
from scripts.export_cmd import main as export_main
from scripts.import_cmd import main as import_main
from scripts.list_cmd import main as list_main
from scripts.normalize import main as normalize_main
from scripts.build import main as build_main
from scripts.remove import main as remove_main
from scripts.review import main as review_main
from scripts.report import main as report_main
from scripts.search import main as search_main
from scripts.stats import main as stats_main
from scripts.update import main as update_main
from scripts.validate import main as validate_main

CommandHandler = Callable[[list[str] | None], int]

COMMANDS: dict[str, CommandHandler] = {
    "build": build_main,
    "validate": validate_main,
    "report": report_main,
    "stats": stats_main,
    "search": search_main,
    "add": add_main,
    "remove": remove_main,
    "review": review_main,
    "list": list_main,
    "doctor": doctor_main,
    "normalize": normalize_main,
    "export": export_main,
    "import": import_main,
    "update": update_main,
}

COMMAND_HELP: dict[str, str] = {
    "build": "Build filters, configs and releases",
    "validate": "Validate generated filters",
    "report": "Generate project report",
    "stats": "Show database statistics",
    "search": "Search for a domain",
    "add": "Add a domain",
    "remove": "Remove a domain",
    "review": "Manage review workflow",
    "list": "List domains with filters",
    "doctor": "Check project health",
    "normalize": "Normalize database values",
    "export": "Export database",
    "import": "Import domains",
    "update": "Update a domain",
}


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level router parser."""

    parser = argparse.ArgumentParser(
        prog="fivebr",
        description="5ibr AdGuard Filter Toolkit",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    for name in COMMANDS:
        subparsers.add_parser(
            name,
            help=COMMAND_HELP[name],
            add_help=False,
        )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Route a command name to its command module."""

    parser = build_parser()
    args, command_argv = parser.parse_known_args(argv)

    command = COMMANDS[args.command]

    return command(command_argv)


if __name__ == "__main__":
    raise SystemExit(main())
