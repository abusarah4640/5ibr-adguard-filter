#!/usr/bin/env python3

"""Command router for the 5ibr AdGuard Filter Toolkit."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from scripts.add import main as add_main
from scripts.analyze import main as analyze_main
from scripts.analyze_log import main as analyze_log_main
from scripts.confidence_impact_report import main as confidence_impact_main
from scripts.conflict_impact_report import main as conflict_impact_main
from scripts.doctor import main as doctor_main
from scripts.export_cmd import main as export_main
from scripts.import_cmd import main as import_main
from scripts.init_project import main as init_main
from scripts.knowledge_check import main as knowledge_check_main
from scripts.list_cmd import main as list_main
from scripts.normalize import main as normalize_main
from scripts.build import main as build_main
from scripts.remove import main as remove_main
from scripts.review import main as review_main
from scripts.rule_check import main as rule_check_main
from scripts.intelligence_check import main as intelligence_check_main
from scripts.intelligence_diagnostics import main as intelligence_diagnostics_main
from scripts.intelligence_report import main as intelligence_report_main
from scripts.report import main as report_main
from scripts.project_status import main as project_status_main
from scripts.search import main as search_main
from scripts.stats import main as stats_main
from scripts.update import main as update_main
from scripts.validate import main as validate_main
from scripts.version import main as version_main

CommandHandler = Callable[[list[str] | None], int]

COMMANDS: dict[str, CommandHandler] = {
    "analyze": analyze_main,
    "analyze-log": analyze_log_main,
    "confidence-impact": confidence_impact_main,
    "conflict-impact": conflict_impact_main,
    "build": build_main,
    "validate": validate_main,
    "report": report_main,
    "project-status": project_status_main,
    "stats": stats_main,
    "search": search_main,
    "add": add_main,
    "remove": remove_main,
    "review": review_main,
    "rule-check": rule_check_main,
    "intelligence-check": intelligence_check_main,
    "intelligence-diagnostics": intelligence_diagnostics_main,
    "intelligence-report": intelligence_report_main,
    "list": list_main,
    "doctor": doctor_main,
    "normalize": normalize_main,
    "export": export_main,
    "import": import_main,
    "init": init_main,
    "knowledge-check": knowledge_check_main,
    "update": update_main,
    "version": version_main,
}

COMMAND_HELP: dict[str, str] = {
    "analyze": "Analyze a domain with local rules",
    "analyze-log": "Analyze an AdGuard Home query log",
    "confidence-impact": "Compare confidence between evaluation snapshots",
    "conflict-impact": "Compare results before and after conflict guardrails",
    "build": "Build filters, configs and releases",
    "validate": "Validate generated filters",
    "report": "Generate project report",
    "stats": "Show database statistics",
    "search": "Search for a domain",
    "add": "Add a domain",
    "remove": "Remove a domain",
    "review": "Manage review workflow",
    "rule-check": "Check analyzer rule configuration",
    "intelligence-check": "Run intelligence validation",
    "intelligence-diagnostics": "Run detailed intelligence diagnostics",
    "intelligence-report": "Generate intelligence report",
    "list": "List domains with filters",
    "doctor": "Check project health",
    "normalize": "Normalize database values",
    "export": "Export database",
    "import": "Import domains",
    "init": "Initialize a runtime project",
    "knowledge-check": "Check Knowledge Base integrity",
    "update": "Update a domain",
    "version": "Show version",
                                   "project-status": "Show runtime project status",
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
