"""CLI for cross-field coherence analytics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.services.coherence_analytics import (
    analyze_coherence_patterns,
    build_coherence_analytics_report,
    load_coherence_assessments,
    load_seen_counts,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="coherence-analytics-report",
        description=(
            "Aggregate cross-field coherence "
            "patterns from shadow evaluation"
        ),
    )

    parser.add_argument(
        "coherence_report",
        type=Path,
    )

    parser.add_argument(
        "--suggestions",
        type=Path,
        default=None,
        help=(
            "Optional suggestions JSON used "
            "to attach query occurrence counts"
        ),
    )

    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path(
            "reports/evaluation/"
            "stage47-coherence-analytics"
        ),
    )

    parser.add_argument(
        "--all-statuses",
        action="store_true",
    )

    args = parser.parse_args(argv)

    assessments = load_coherence_assessments(
        args.coherence_report
    )

    seen_counts = load_seen_counts(
        args.suggestions
    )

    summary = analyze_coherence_patterns(
        assessments,
        seen_counts=seen_counts,
    )

    report = build_coherence_analytics_report(
        summary,
        incoherent_only=(
            not args.all_statuses
        ),
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
