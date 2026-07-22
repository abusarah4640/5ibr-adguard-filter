"""CLI for Stage 53 scoped policy shadow execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.scoped_policy_shadow import (
    build_scoped_policy_shadow_report,
    run_scoped_policy_shadow,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scoped-policy-shadow-report",
        description=(
            "Run persistent scoped-promotion "
            "policies in non-destructive shadow mode"
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
        default=Path(
            "config/"
            "scoped-promotion-policies.json"
        ),
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
            "stage53-scoped-policy-shadow"
        ),
    )

    args = parser.parse_args(argv)

    summary = run_scoped_policy_shadow(
        suggestions_path=args.suggestions,
        gate_path=args.candidate_gate,
        policy_path=args.policies,
        analyzer_config_path=args.config,
        limit=args.limit,
    )

    report = (
        build_scoped_policy_shadow_report(
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
