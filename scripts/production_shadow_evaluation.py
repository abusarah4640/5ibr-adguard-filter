"""CLI for production shadow evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.services.production_shadow_pipeline import (
    run_production_shadow_evaluation,
    write_production_shadow_reports,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="production-shadow-evaluation",
        description=(
            "Compare current analyzer results with the "
            "unified resolver in shadow mode"
        ),
    )

    parser.add_argument(
        "suggestions",
        type=Path,
        help="Analyzer suggestions JSON file",
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/analyzer.json"),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path(
            "reports/evaluation/stage42-shadow-evaluation"
        ),
    )

    args = parser.parse_args(argv)

    result = run_production_shadow_evaluation(
        args.suggestions,
        config_path=args.config,
        limit=args.limit,
    )

    text_path = args.output_prefix.with_suffix(
        ".txt"
    )

    json_path = args.output_prefix.with_suffix(
        ".json"
    )

    comparisons_path = Path(
        str(args.output_prefix)
        + "-comparisons.json"
    )

    write_production_shadow_reports(
        result,
        text_path=text_path,
        json_path=json_path,
        comparisons_path=comparisons_path,
    )

    print(
        text_path.read_text(
            encoding="utf-8"
        ),
        end="",
    )

    print()
    print(f"Text report        : {text_path}")
    print(f"JSON report        : {json_path}")
    print(f"Comparisons report : {comparisons_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
