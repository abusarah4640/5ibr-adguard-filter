"""Compare analyzer confidence between two evaluation snapshots."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConfidenceImpact:
    total_common: int
    moved_to_review: int
    moved_to_approved: int
    decreased_below_review: int
    unchanged: int
    average_before: float
    average_after: float
    max_increase: int
    max_decrease: int


def load_rows(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        rows = data.get("suggestions", [])
    else:
        rows = data

    if not isinstance(rows, list):
        raise ValueError(f"Invalid suggestions format in {path}")

    return [row for row in rows if isinstance(row, dict)]


def confidence(row: dict) -> int:
    try:
        return int(float(row.get("confidence", 0) or 0))
    except (TypeError, ValueError):
        return 0


def analyze_impact(before_rows: list[dict], after_rows: list[dict]) -> tuple[ConfidenceImpact, list[dict]]:
    before_by_domain = {
        str(row.get("domain", "")): row
        for row in before_rows
        if row.get("domain")
    }

    after_by_domain = {
        str(row.get("domain", "")): row
        for row in after_rows
        if row.get("domain")
    }

    common_domains = sorted(set(before_by_domain) & set(after_by_domain))

    moved_to_review = 0
    moved_to_approved = 0
    decreased_below_review = 0
    unchanged = 0
    deltas: list[int] = []
    changed: list[dict] = []

    before_values: list[int] = []
    after_values: list[int] = []

    for domain in common_domains:
        before = before_by_domain[domain]
        after = after_by_domain[domain]

        before_conf = confidence(before)
        after_conf = confidence(after)

        before_values.append(before_conf)
        after_values.append(after_conf)

        delta = after_conf - before_conf
        deltas.append(delta)

        if before_conf < 50 <= after_conf < 90:
            moved_to_review += 1
        elif before_conf < 90 <= after_conf:
            moved_to_approved += 1
        elif before_conf >= 50 > after_conf:
            decreased_below_review += 1
        elif before_conf == after_conf:
            unchanged += 1

        if delta != 0:
            changed.append(
                {
                    "domain": domain,
                    "seen": int(after.get("seen", 0) or 0),
                    "before": before_conf,
                    "after": after_conf,
                    "delta": delta,
                    "vendor": after.get("vendor", "Unknown"),
                    "category": after.get("category", "Unknown"),
                    "filter": after.get("filter", "unknown"),
                }
            )

    changed.sort(
        key=lambda item: (abs(item["delta"]), item["seen"]),
        reverse=True,
    )

    total_common = len(common_domains)

    impact = ConfidenceImpact(
        total_common=total_common,
        moved_to_review=moved_to_review,
        moved_to_approved=moved_to_approved,
        decreased_below_review=decreased_below_review,
        unchanged=unchanged,
        average_before=(
            sum(before_values) / len(before_values)
            if before_values
            else 0.0
        ),
        average_after=(
            sum(after_values) / len(after_values)
            if after_values
            else 0.0
        ),
        max_increase=max(deltas, default=0),
        max_decrease=min(deltas, default=0),
    )

    return impact, changed


def build_report(before_path: Path, after_path: Path) -> str:
    before_rows = load_rows(before_path)
    after_rows = load_rows(after_path)

    impact, changed = analyze_impact(before_rows, after_rows)

    lines = [
        "5ibr Confidence Impact Report",
        "=============================",
        "",
        f"Before file          : {before_path}",
        f"After file           : {after_path}",
        f"Common domains       : {impact.total_common}",
        "",
        f"Average before       : {impact.average_before:.1f}",
        f"Average after        : {impact.average_after:.1f}",
        f"Average delta        : {impact.average_after - impact.average_before:+.1f}",
        "",
        f"Moved to review      : {impact.moved_to_review}",
        f"Moved to approved    : {impact.moved_to_approved}",
        f"Dropped below review : {impact.decreased_below_review}",
        f"Unchanged            : {impact.unchanged}",
        f"Max increase         : {impact.max_increase:+d}",
        f"Max decrease         : {impact.max_decrease:+d}",
        "",
        "Top changed domains:",
        "",
    ]

    for item in changed[:30]:
        lines.append(
            f"{item['seen']:>8}  "
            f"{item['domain']}  "
            f"{item['before']} -> {item['after']} "
            f"({item['delta']:+d})"
        )
        lines.append(
            f"          "
            f"{item['vendor']} | "
            f"{item['category']} | "
            f"{item['filter']}"
        )
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fivebr confidence-impact",
        description="Compare confidence between evaluation snapshots",
    )

    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)

    args = parser.parse_args(argv)

    print(build_report(args.before, args.after))
    return 0
