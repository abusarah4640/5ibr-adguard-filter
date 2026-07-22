"""CLI for initializing a 5ibr runtime project."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.runtime.project_init import (
    initialize_project,
)


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="fivebr init",
    )

    parser.add_argument(
        "path",
        type=Path,
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    args = parser.parse_args(argv)

    result = initialize_project(
        args.path,
        force=args.force,
    )

    print(
        "Project root       :",
        result.root,
    )
    print(
        "Directories created:",
        len(result.created_directories),
    )
    print(
        "Files created      :",
        len(result.created_files),
    )
    print(
        "Files skipped      :",
        len(result.skipped_files),
    )

    return 0
