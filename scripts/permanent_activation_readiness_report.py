"""CLI for permanent activation readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.permanent_activation_readiness import (
    build_permanent_readiness_report,
    run_permanent_activation_readiness,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=(
            "permanent-activation-readiness"
        ),
    )

    parser.add_argument(
        "--production-readiness",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--audit-integrity",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--activation-receipt",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--regression",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--enforcement-config",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--policies",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path(
            "reports/evaluation/"
            "stage58c-permanent-readiness"
        ),
    )

    args = parser.parse_args(argv)

    result = (
        run_permanent_activation_readiness(
            production_readiness_path=(
                args.production_readiness
            ),
            audit_integrity_path=(
                args.audit_integrity
            ),
            activation_receipt_path=(
                args.activation_receipt
            ),
            regression_path=(
                args.regression
            ),
            enforcement_config_path=(
                args.enforcement_config
            ),
            policy_path=args.policies,
        )
    )

    report = (
        build_permanent_readiness_report(
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

    return 0 if result.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
