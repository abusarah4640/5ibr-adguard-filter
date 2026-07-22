"""CLI for Stage 55 controlled enforcement validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.scoped_policy_enforcement import (
    build_enforcement_report,
    run_enforcement_simulation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scoped-policy-enforcement-report",
        description=(
            "Validate controlled scoped-policy "
            "enforcement with an explicit kill switch"
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
        "--policies",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--readiness",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--enforcement-config",
        type=Path,
        required=True,
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
            "stage55-controlled-enforcement"
        ),
    )

    args = parser.parse_args(argv)

    summary = run_enforcement_simulation(
        suggestions_path=args.suggestions,
        gate_path=args.candidate_gate,
        policy_path=args.policies,
        readiness_path=args.readiness,
        enforcement_config_path=(
            args.enforcement_config
        ),
        analyzer_config_path=args.config,
        limit=args.limit,
    )

    report = build_enforcement_report(
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
