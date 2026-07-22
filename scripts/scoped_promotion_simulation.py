"""CLI for Stage 52 scoped promotion simulation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.scoped_promotion_policy import (
    build_scoped_promotion_report,
    run_scoped_promotion_simulation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scoped-promotion-simulation",
        description=(
            "Simulate explicitly scoped semantic "
            "promotion policies without modifying production"
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
            "stage52-scoped-promotion"
        ),
    )

    args = parser.parse_args(argv)

    summary = (
        run_scoped_promotion_simulation(
            suggestions_path=args.suggestions,
            gate_path=args.candidate_gate,
            config_path=args.config,
            limit=args.limit,
        )
    )

    report = build_scoped_promotion_report(
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
