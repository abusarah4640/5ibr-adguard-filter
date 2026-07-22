"""CLI for project runtime lifecycle status."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.project_status_service import (
    PROJECT_INVALID,
    evaluate_project_status,
)


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="fivebr project-status",
    )

    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
    )

    args = parser.parse_args(argv)

    result = evaluate_project_status(
        args.path
    )

    if args.as_json:
        print(
            json.dumps(
                result.to_dict(),
                ensure_ascii=False,
                indent=2,
            )
        )

    else:
        print("5ibr Project Status")
        print("===================")
        print(
            "Decision      :",
            result.decision,
        )
        print(
            "Valid         :",
            result.valid,
        )
        print(
            "Root          :",
            result.root,
        )
        print(
            "Database rows :",
            result.database_rows,
        )
        print(
            "Checks passed :",
            result.checks_passed,
        )
        print(
            "Checks failed :",
            result.checks_failed,
        )
        print(
            "Issues        :",
            len(result.issues),
        )

        for issue in result.issues:
            print(" -", issue)

    return (
        2
        if result.decision
        == PROJECT_INVALID
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
