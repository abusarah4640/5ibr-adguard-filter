"""CLI for Stage 54 production promotion readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.production_readiness_gate import (
    build_readiness_report,
    run_production_readiness_gate,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="production-readiness-report",
        description=(
            "Validate promotion artifacts and "
            "produce a final readiness decision"
        ),
    )

    parser.add_argument(
        "--candidate-gate",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--scoped-simulation",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--shadow-execution",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--policies",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--policy-sha256",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--before-snapshot",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--after-snapshot",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path(
            "reports/evaluation/"
            "stage54-production-readiness"
        ),
    )

    args = parser.parse_args(argv)

    summary = run_production_readiness_gate(
        candidate_gate_path=(
            args.candidate_gate
        ),
        scoped_simulation_path=(
            args.scoped_simulation
        ),
        shadow_execution_path=(
            args.shadow_execution
        ),
        policy_path=args.policies,
        recorded_sha256_path=(
            args.policy_sha256
        ),
        before_snapshot_path=(
            args.before_snapshot
        ),
        after_snapshot_path=(
            args.after_snapshot
        ),
    )

    report = build_readiness_report(
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

    return 0 if summary.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
