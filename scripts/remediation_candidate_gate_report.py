"""CLI for the Stage 50 remediation candidate safety gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.remediation_candidate_gate import (
    build_candidate_gate_report,
    load_remediation_proposals,
    run_candidate_safety_gate,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="remediation-candidate-gate-report",
        description=(
            "Apply a non-destructive second-stage "
            "safety gate to remediation candidates"
        ),
    )

    parser.add_argument(
        "remediation_report",
        type=Path,
    )

    parser.add_argument(
        "--minimum-family-support",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path(
            "reports/evaluation/"
            "stage50-candidate-safety-gate"
        ),
    )

    args = parser.parse_args(argv)

    proposals = load_remediation_proposals(
        args.remediation_report
    )

    summary = run_candidate_safety_gate(
        proposals,
        minimum_family_support=max(
            args.minimum_family_support,
            1,
        ),
    )

    report = build_candidate_gate_report(
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
