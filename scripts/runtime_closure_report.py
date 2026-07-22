"""CLI report for runtime architecture closure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.runtime_architecture_closure import (
    evaluate_runtime_architecture,
)


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="runtime-closure-report",
    )

    parser.add_argument(
        "--wheel",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "reports/release/"
            "stage61f5-runtime-closure.json"
        ),
    )

    args = parser.parse_args(argv)

    result = evaluate_runtime_architecture(
        wheel_path=args.wheel
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            result.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("Runtime Architecture Closure")
    print("============================")
    print(
        "Decision         :",
        result.decision,
    )
    print(
        "Accepted         :",
        result.accepted,
    )
    print(
        "Checks passed    :",
        result.checks_passed,
    )
    print(
        "Checks failed    :",
        result.checks_failed,
    )
    print(
        "Blocking reasons:",
        len(result.blocking_reasons),
    )

    for reason in result.blocking_reasons:
        print(" -", reason)

    print()
    print("Report:", args.output)

    return 0 if result.accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
