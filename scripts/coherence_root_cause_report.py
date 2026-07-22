"""CLI for coherence root-cause attribution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.coherence_root_cause import (
    attribute_root_causes,
    build_root_cause_report,
    load_json_list,
    load_json_object,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="coherence-root-cause-report",
        description=(
            "Attribute cross-field coherence "
            "failures to probable root causes"
        ),
    )

    parser.add_argument(
        "coherence_report",
        type=Path,
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
            "stage48-root-cause-attribution"
        ),
    )

    parser.add_argument(
        "--all-statuses",
        action="store_true",
    )

    args = parser.parse_args(argv)

    coherence_payload = load_json_object(
        args.coherence_report
    )

    assessments = coherence_payload.get(
        "assessments",
        [],
    )

    if not isinstance(assessments, list):
        raise ValueError(
            "coherence assessments must be a list"
        )

    comparisons = load_json_list(
        args.comparisons
    )

    config = load_json_object(
        args.config
    )

    configured_filter_map = config.get(
        "filter_map",
        {},
    )

    if not isinstance(
        configured_filter_map,
        dict,
    ):
        configured_filter_map = {}

    summary = attribute_root_causes(
        assessments,
        comparisons=comparisons,
        configured_filter_map={
            str(key): str(value)
            for key, value
            in configured_filter_map.items()
        },
        incoherent_only=(
            not args.all_statuses
        ),
    )

    report = build_root_cause_report(
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
