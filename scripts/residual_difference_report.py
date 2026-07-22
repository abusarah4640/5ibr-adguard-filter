"""CLI for residual shadow difference diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.residual_difference_diagnostics import (
    build_residual_diagnostic_report,
    diagnose_comparisons,
    load_comparisons,
    load_filter_map,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="residual-difference-report",
        description=(
            "Diagnose residual Shadow Comparison "
            "differences and cross-field coherence"
        ),
    )

    parser.add_argument(
        "comparisons",
        type=Path,
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "config/analyzer.json"
        ),
    )

    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path(
            "reports/evaluation/"
            "stage44-residual-diagnostics"
        ),
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Inspect all comparisons instead "
            "of different decisions only"
        ),
    )

    args = parser.parse_args(argv)

    comparisons = load_comparisons(
        args.comparisons
    )

    filter_map = load_filter_map(
        args.config
    )

    summary = diagnose_comparisons(
        comparisons,
        filter_map=filter_map,
        differences_only=not args.all,
    )

    report = build_residual_diagnostic_report(
        summary
    )

    text_path = args.output_prefix.with_suffix(
        ".txt"
    )

    json_path = args.output_prefix.with_suffix(
        ".json"
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
            summary.to_dict(),
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
