#!/usr/bin/env python3
"""5ibr AdGuard Query Log Analyzer command."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from scripts.services.querylog_service import QueryLogAnalysis, analyze_query_log


def _suggestion_to_dict(suggestion) -> dict[str, object]:
    analysis = suggestion.analysis
    return {
        "domain": suggestion.domain,
        "seen": suggestion.seen,
        "root": analysis.root_domain,
        "vendor": analysis.suggested_vendor,
        "category": analysis.suggested_category,
        "filter": analysis.suggested_filter,
        "confidence": analysis.confidence,
        "recommendation": analysis.recommendation,
        "reasons": analysis.reasons,
    }


def _result_to_dict(result: QueryLogAnalysis) -> dict[str, object]:
    return {
        "source": str(result.source),
        "total_queries": result.total_queries,
        "unique_domains": result.unique_domains,
        "known_domains": result.known_domains,
        "unknown_domains": result.unknown_domains,
        "suggestions": [_suggestion_to_dict(item) for item in result.suggestions],
        "reports": {
            "csv": str(result.csv_report) if result.csv_report else None,
            "markdown": str(result.markdown_report) if result.markdown_report else None,
        },
    }


def _write_json(result: QueryLogAnalysis, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(_result_to_dict(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_filtered_csv(result: QueryLogAnalysis, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Domain",
                "Seen",
                "Root",
                "Vendor",
                "Category",
                "Filter",
                "Confidence",
                "Recommendation",
                "Reasons",
            ],
        )
        writer.writeheader()
        for suggestion in result.suggestions:
            row = _suggestion_to_dict(suggestion)
            writer.writerow(
                {
                    "Domain": row["domain"],
                    "Seen": row["seen"],
                    "Root": row["root"],
                    "Vendor": row["vendor"],
                    "Category": row["category"],
                    "Filter": row["filter"],
                    "Confidence": row["confidence"],
                    "Recommendation": row["recommendation"],
                    "Reasons": "; ".join(row["reasons"]),
                }
            )


def _print_text(result: QueryLogAnalysis) -> None:
    print()
    print("===================================")
    print("5ibr Query Log Analysis")
    print("===================================")
    print()
    print(f"Source          : {result.source}")
    print(f"Total Queries   : {result.total_queries}")
    print(f"Unique Domains  : {result.unique_domains}")
    print(f"Known Domains   : {result.known_domains}")
    print(f"Unknown Domains : {result.unknown_domains}")
    print()
    print("Top Suggestions")
    print("----------------------------------------")

    if not result.suggestions:
        print("No suggestions found.")
    else:
        for index, suggestion in enumerate(result.suggestions, start=1):
            analysis = suggestion.analysis
            print(f"{index}.")
            print(f"Domain         : {suggestion.domain}")
            print(f"Seen           : {suggestion.seen}")
            print(f"Vendor         : {analysis.suggested_vendor}")
            print(f"Category       : {analysis.suggested_category}")
            print(f"Filter         : {analysis.suggested_filter}")
            print(f"Confidence     : {analysis.confidence}")
            print(f"Recommendation : {analysis.recommendation}")
            print()

    if result.csv_report and result.markdown_report:
        print("Reports")
        print(f"CSV      : {result.csv_report}")
        print(f"Markdown : {result.markdown_report}")


def main(argv: list[str] | None = None) -> int:
    """Analyze an AdGuard Home querylog.json file and write suggestions."""

    parser = argparse.ArgumentParser(
        prog="fivebr analyze-log",
        description="Analyze an AdGuard Home query log using local rules",
    )
    parser.add_argument("path", help="Path to AdGuard Home querylog.json")
    parser.add_argument(
        "--min-seen",
        type=int,
        default=1,
        help="Only suggest domains seen at least this many times",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of suggestions to display and write",
    )
    parser.add_argument(
        "--min-confidence",
        type=int,
        default=0,
        help="Only keep suggestions with at least this confidence",
    )
    parser.add_argument(
        "--recommendation",
        choices=["approved-candidate", "review", "unknown", "safe-root"],
        help="Only keep suggestions with this recommendation",
    )
    parser.add_argument("--vendor", help="Only keep suggestions for this vendor")
    parser.add_argument("--category", help="Only keep suggestions for this category")
    parser.add_argument("--filter", dest="filter_name", help="Only keep suggestions for this filter")
    parser.add_argument(
        "--sort",
        choices=["seen", "confidence", "domain"],
        default="seen",
        help="Sort suggestions before limiting",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format printed to the terminal",
    )
    parser.add_argument(
        "--export",
        choices=["csv", "json"],
        help="Write the filtered result to reports/suggestions.filtered.<format>",
    )
    parser.add_argument(
        "--no-reports",
        action="store_true",
        help="Do not write the default suggestions.csv and suggestions.md reports",
    )
    args = parser.parse_args(argv)

    result = analyze_query_log(
        args.path,
        min_seen=args.min_seen,
        limit=args.limit,
        min_confidence=args.min_confidence,
        recommendation=args.recommendation,
        vendor=args.vendor,
        category=args.category,
        filter_name=args.filter_name,
        sort_by=args.sort,
        write_reports=not args.no_reports,
    )

    if args.export:
        export_path = Path("reports") / f"suggestions.filtered.{args.export}"
        if args.export == "json":
            _write_json(result, export_path)
        else:
            _write_filtered_csv(result, export_path)

    if args.format == "json":
        print(json.dumps(_result_to_dict(result), ensure_ascii=False, indent=2))
    else:
        _print_text(result)
        if args.export:
            print(f"Filtered export : {export_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
