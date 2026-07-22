"""CLI for root-cause remediation preview."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.root_cause_remediation import (
    build_remediation_preview,
    build_remediation_report,
    load_attributions,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="root-cause-remediation-report",
        description=(
            "Build non-destructive remediation "
            "proposals from root-cause attributions"
        ),
    )

    parser.add_argument(
        "attribution_report",
        type=Path,
    )

    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path(
            "reports/evaluation/"
            "stage49-remediation-preview"
        ),
    )

    args = parser.parse_args(argv)

    attributions = load_attributions(
        args.attribution_report
    )

    summary = build_remediation_preview(
        attributions
    )

    report = build_remediation_report(
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
