"""CLI for Stage 51 controlled promotion simulation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.controlled_promotion_simulation import (
    build_controlled_promotion_report,
    run_controlled_promotion_simulation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="controlled-promotion-simulation",
        description=(
            "Simulate approved mapping changes "
            "without modifying production"
        ),
    )

    parser.add_argument(
        "suggestions",
        type=Path,
    )

    parser.add_argument(
        "candidate_gate",
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
        "--limit",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path(
            "reports/evaluation/"
            "stage51-controlled-promotion"
        ),
    )

    args = parser.parse_args(argv)

    summary = (
        run_controlled_promotion_simulation(
            suggestions_path=args.suggestions,
            gate_path=args.candidate_gate,
            config_path=args.config,
            limit=args.limit,
        )
    )

    report = (
        build_controlled_promotion_report(
            summary
        )
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
