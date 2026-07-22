"""Compare analyzer results before and after conflict guardrails."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConflictImpact:
    common_domains: int
    lowered_domains: int
    raised_domains: int
    unchanged_domains: int
    approved_to_review: int
    lowered_with_conflict_reason: int
    lowered_without_conflict_reason: int
    max_drop: int
    max_raise: int


def load_rows(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))

    rows = data.get("suggestions", []) if isinstance(data, dict) else data

    if not isinstance(rows, list):
        raise ValueError(f"Invalid suggestions format in {path}")

    return [row for row in rows if isinstance(row, dict)]


def confidence(row: dict) -> int:
    try:
        return int(float(row.get("confidence", 0) or 0))
    except (TypeError, ValueError):
        return 0


def has_conflict_reason(row: dict) -> bool:
    reasons = row.get("reasons", [])

    if not isinstance(reasons, list):
        return False

    return any(
        "conflicting category evidence" in str(reason)
        or "conflicting filter evidence" in str(reason)
        for reason in reasons
    )


def analyze_conflict_impact(
    before_rows: list[dict],
    after_rows: list[dict],
) -> tuple[ConflictImpact, list[dict]]:
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

    lowered = 0
    raised = 0
    unchanged = 0
    approved_to_review = 0
    lowered_with_conflict = 0
    lowered_without_conflict = 0
    deltas: list[int] = []
    changed: list[dict] = []

    for domain in common_domains:
        before = before_by_domain[domain]
        after = after_by_domain[domain]

        before_conf = confidence(before)
        after_conf = confidence(after)
        delta = after_conf - before_conf
        deltas.append(delta)

        before_rec = str(before.get("recommendation", "unknown"))
        after_rec = str(after.get("recommendation", "unknown"))
        conflict = has_conflict_reason(after)

        if delta < 0:
            lowered += 1

            if conflict:
                lowered_with_conflict += 1
            else:
                lowered_without_conflict += 1

            if (
                before_rec == "approved-candidate"
                and after_rec == "review"
            ):
                approved_to_review += 1

        elif delta > 0:
            raised += 1
        else:
            unchanged += 1

        if delta != 0:
            changed.append(
                {
                    "domain": domain,
                    "seen": int(after.get("seen", 0) or 0),
                    "before_confidence": before_conf,
                    "after_confidence": after_conf,
                    "delta": delta,
                    "before_recommendation": before_rec,
                    "after_recommendation": after_rec,
                    "has_conflict_reason": conflict,
                    "vendor": after.get("vendor", "Unknown"),
                    "category": after.get("category", "Unknown"),
                    "filter": after.get("filter", "unknown"),
                }
            )

    changed.sort(
        key=lambda item: (abs(item["delta"]), item["seen"]),
        reverse=True,
    )

    impact = ConflictImpact(
        common_domains=len(common_domains),
        lowered_domains=lowered,
        raised_domains=raised,
        unchanged_domains=unchanged,
        approved_to_review=approved_to_review,
        lowered_with_conflict_reason=lowered_with_conflict,
        lowered_without_conflict_reason=lowered_without_conflict,
        max_drop=min(deltas, default=0),
        max_raise=max(deltas, default=0),
    )

    return impact, changed


def build_report(before_path: Path, after_path: Path) -> str:
    before_rows = load_rows(before_path)
    after_rows = load_rows(after_path)

    impact, changed = analyze_conflict_impact(
        before_rows,
        after_rows,
    )

    lines = [
        "5ibr Conflict Impact Report",
        "===========================",
        "",
        f"Before file                  : {before_path}",
        f"After file                   : {after_path}",
        f"Common domains               : {impact.common_domains}",
        "",
        f"Lowered domains              : {impact.lowered_domains}",
        f"Raised domains               : {impact.raised_domains}",
        f"Unchanged domains            : {impact.unchanged_domains}",
        f"Approved -> review           : {impact.approved_to_review}",
        f"Lowered with conflict reason : {impact.lowered_with_conflict_reason}",
        f"Lowered without conflict     : {impact.lowered_without_conflict_reason}",
        f"Maximum confidence drop      : {impact.max_drop:+d}",
        f"Maximum confidence raise     : {impact.max_raise:+d}",
        "",
        "Changed domains:",
        "",
    ]

    for item in changed[:30]:
        conflict_text = (
            "conflict=yes"
            if item["has_conflict_reason"]
            else "conflict=no"
        )

        lines.append(
            f"{item['seen']:>8}  "
            f"{item['domain']}  "
            f"{item['before_confidence']} -> "
            f"{item['after_confidence']} "
            f"({item['delta']:+d})  "
            f"{conflict_text}"
        )

        lines.append(
            f"          "
            f"{item['before_recommendation']} -> "
            f"{item['after_recommendation']} | "
            f"{item['vendor']} | "
            f"{item['category']} | "
            f"{item['filter']}"
        )

        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fivebr conflict-impact",
        description="Compare results before and after conflict guardrails",
    )

    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)

    args = parser.parse_args(argv)

    print(build_report(args.before, args.after))
    return 0
