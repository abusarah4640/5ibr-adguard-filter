#!/usr/bin/env python3
"""AdGuard Home query log parsing and suggestion reporting service."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from scripts.runtime.paths import (
    get_runtime_paths,
)
from typing import Any, Iterable

from scripts.database import load_database
from scripts.services.analyzer_service import DomainAnalysis, analyze_domain, normalize_domain
from scripts.services.production_enforcement_hook import (
    apply_production_enforcement,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_default_reports_dir() -> Path:
    """Return the active runtime reports directory."""

    return get_runtime_paths().reports


DEFAULT_REPORTS_DIR = get_default_reports_dir()


@dataclass(slots=True)
class QueryLogSuggestion:
    """A domain suggestion produced from query-log analysis."""

    domain: str
    seen: int
    analysis: DomainAnalysis


@dataclass(slots=True)
class QueryLogAnalysis:
    """Summary returned by query-log analysis."""

    source: Path
    total_queries: int
    unique_domains: int
    known_domains: int
    unknown_domains: int
    suggestions: list[QueryLogSuggestion] = field(default_factory=list)
    csv_report: Path | None = None
    markdown_report: Path | None = None


def _iter_json_records(path: Path) -> Iterable[dict[str, Any]]:
    """Yield query records from common AdGuard JSON formats.

    Supported local formats:
    - A JSON array of records.
    - A JSON object containing a list under keys like data/queries/items.
    - Newline-delimited JSON records.
    """

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        for line in text.splitlines():
            line = line.strip().rstrip(",")
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record
        return

    if isinstance(payload, list):
        for record in payload:
            if isinstance(record, dict):
                yield record
        return

    if isinstance(payload, dict):
        for key in ("data", "queries", "items", "log"):
            value = payload.get(key)
            if isinstance(value, list):
                for record in value:
                    if isinstance(record, dict):
                        yield record
                return
        yield payload


def _extract_domain_from_record(record: dict[str, Any]) -> str | None:
    """Extract a queried domain from one AdGuard-like query-log record."""

    for key in ("QH", "domain", "host", "hostname", "query", "name"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_domain(value)

    question = record.get("question") or record.get("Question")
    if isinstance(question, dict):
        for key in ("host", "name", "domain", "QH"):
            value = question.get(key)
            if isinstance(value, str) and value.strip():
                return normalize_domain(value)

    return None


def extract_query_domains(path: str | Path) -> Counter[str]:
    """Extract normalized domain counts from an AdGuard query log."""

    source = Path(path)
    counts: Counter[str] = Counter()
    for record in _iter_json_records(source):
        domain = _extract_domain_from_record(record)
        if domain:
            counts[domain] += 1
    return counts


def known_database_domains(rows: list[dict] | None = None) -> set[str]:
    """Return normalized domains that already exist in the database."""

    database_rows = load_database() if rows is None else rows
    return {
        normalize_domain(row.get("Domain", ""))
        for row in database_rows
        if normalize_domain(row.get("Domain", ""))
    }


def analyze_query_log(
    path: str | Path,
    *,
    min_seen: int = 1,
    limit: int = 50,
    rows: list[dict] | None = None,
    reports_dir: str | Path | None = None,
    write_reports: bool = True,
    min_confidence: int = 0,
    recommendation: str | None = None,
    vendor: str | None = None,
    category: str | None = None,
    filter_name: str | None = None,
    sort_by: str = "seen",
) -> QueryLogAnalysis:
    """Analyze an AdGuard query log and produce ranked domain suggestions."""

    source = Path(path)
    counts = extract_query_domains(source)
    database_rows = load_database() if rows is None else rows
    known = known_database_domains(database_rows)

    unknown_counts = Counter(
        {
            domain: seen
            for domain, seen in counts.items()
            if domain not in known and seen >= min_seen
        }
    )

    suggestions: list[QueryLogSuggestion] = []
    for domain, seen in unknown_counts.most_common():
        analysis = analyze_domain(domain, rows=database_rows)
        analysis = apply_production_enforcement(analysis)
        if analysis.confidence < min_confidence:
            continue
        if recommendation and analysis.recommendation != recommendation:
            continue
        if vendor and analysis.suggested_vendor.lower() != vendor.lower():
            continue
        if category and analysis.suggested_category.lower() != category.lower():
            continue
        if filter_name and analysis.suggested_filter.lower() != filter_name.lower():
            continue
        suggestions.append(QueryLogSuggestion(domain=domain, seen=seen, analysis=analysis))

    if sort_by == "confidence":
        suggestions.sort(key=lambda item: (item.analysis.confidence, item.seen), reverse=True)
    elif sort_by == "domain":
        suggestions.sort(key=lambda item: item.domain)
    else:
        suggestions.sort(key=lambda item: item.seen, reverse=True)

    suggestions = suggestions[: max(0, limit)]

    result = QueryLogAnalysis(
        source=source,
        total_queries=sum(counts.values()),
        unique_domains=len(counts),
        known_domains=sum(1 for domain in counts if domain in known),
        unknown_domains=len([domain for domain in counts if domain not in known]),
        suggestions=suggestions,
    )

    if write_reports:
        output_dir = (
            Path(reports_dir)
            if reports_dir is not None
            else get_default_reports_dir()
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        result.csv_report = output_dir / "suggestions.csv"
        result.markdown_report = output_dir / "suggestions.md"
        write_suggestions_csv(result, result.csv_report)
        write_suggestions_markdown(result, result.markdown_report)

    return result


def write_suggestions_csv(result: QueryLogAnalysis, path: str | Path) -> None:
    """Write suggestions to CSV for later processing."""

    target = Path(path)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Domain",
                "Seen",
                "Root",
                "Suggested Vendor",
                "Suggested Category",
                "Suggested Filter",
                "Confidence",
                "Recommendation",
                "Blocking Policy",
                "Blocking Policy Reason",
                "Blocking Policy Source",
                "Reasons",
            ],
        )
        writer.writeheader()
        for suggestion in result.suggestions:
            analysis = suggestion.analysis
            writer.writerow(
                {
                    "Domain": suggestion.domain,
                    "Seen": suggestion.seen,
                    "Root": analysis.root_domain,
                    "Suggested Vendor": analysis.suggested_vendor,
                    "Suggested Category": analysis.suggested_category,
                    "Suggested Filter": analysis.suggested_filter,
                    "Confidence": analysis.confidence,
                    "Recommendation": analysis.recommendation,
                    "Blocking Policy": analysis.blocking_policy,
                    "Blocking Policy Reason": (
                        analysis.blocking_policy_reason
                    ),
                    "Blocking Policy Source": (
                        analysis.blocking_policy_source
                    ),
                    "Reasons": "; ".join(analysis.reasons),
                }
            )


def write_suggestions_markdown(result: QueryLogAnalysis, path: str | Path) -> None:
    """Write suggestions to Markdown for human review."""

    target = Path(path)
    lines = [
        "# 5ibr Query Log Suggestions",
        "",
        f"- Source: `{result.source}`",
        f"- Total Queries: {result.total_queries}",
        f"- Unique Domains: {result.unique_domains}",
        f"- Known Domains: {result.known_domains}",
        f"- Unknown Domains: {result.unknown_domains}",
        "",
        "## Top Suggestions",
        "",
    ]

    for index, suggestion in enumerate(result.suggestions, start=1):
        analysis = suggestion.analysis
        lines.extend(
            [
                f"### {index}. {suggestion.domain}",
                "",
                f"- Seen: {suggestion.seen}",
                f"- Root: `{analysis.root_domain}`",
                f"- Suggested Vendor: {analysis.suggested_vendor}",
                f"- Suggested Category: {analysis.suggested_category}",
                f"- Suggested Filter: {analysis.suggested_filter}",
                f"- Confidence: {analysis.confidence}",
                f"- Recommendation: {analysis.recommendation}",
                f"- Blocking Policy: {analysis.blocking_policy}",
                (
                    "- Blocking Policy Reason: "
                    f"{analysis.blocking_policy_reason}"
                ),
                (
                    "- Blocking Policy Source: "
                    f"{analysis.blocking_policy_source}"
                ),
                "- Reasons:",
            ]
        )
        lines.extend(f"  - {reason}" for reason in analysis.reasons)
        lines.append("")

    target.write_text("\n".join(lines), encoding="utf-8")
