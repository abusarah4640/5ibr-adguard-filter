"""CLI report for production verification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.production_verify_service import (
    build_production_verify_report,
    verify_production,
)


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="production-verify",
    )

    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path(
            "reports/evaluation/"
            "stage60b-production-verify"
        ),
    )

    args = parser.parse_args(argv)

    result = verify_production()

    report = (
        build_production_verify_report(
            result
        )
    )

    text_path = (
        args.output_prefix.with_suffix(
            ".txt"
        )
    )

    json_path = (
        args.output_prefix.with_suffix(
            ".json"
        )
    )

    text_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    text_path.write_text(
        report + "\n",
        encoding="utf-8",
    )

    json_path.write_text(
        json.dumps(
            result.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(report)
    print()
    print(f"Text report : {text_path}")
    print(f"JSON report : {json_path}")

    return 0 if result.verified else 2


if __name__ == "__main__":
    raise SystemExit(main())
