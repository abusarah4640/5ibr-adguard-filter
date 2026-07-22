"""Dry-run reporting for blocking-policy guardrails."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from scripts.services import suggestions_service


APPROVAL_ACTIONS = {
    "approved",
    "approved-failed",
    "approved-build-failed",
}


@dataclass(frozen=True, slots=True)
class GuardrailDryRunSummary:
    """Aggregated guardrail impact from decision history."""

    generated_at: str
    source_path: str

    total_decisions: int
    approval_attempts: int
    classified_approval_attempts: int
    unclassified_approval_attempts: int
    non_approval_decisions: int

    shadow_rows: int
    enforce_rows: int
    legacy_rows: int

    would_block: int
    would_allow: int
    allowed_in_recorded_mode: int
    denied_in_recorded_mode: int

    requirements: dict[str, int]
    policies: dict[str, int]
    actions: dict[str, int]

    @property
    def approval_block_rate(self) -> float:
        """Return block percentage over all approval attempts."""

        if self.approval_attempts == 0:
            return 0.0

        return (
            self.would_block
            / self.approval_attempts
            * 100.0
        )

    @property
    def guardrail_coverage_rate(self) -> float:
        """Return approval attempts with usable guardrail data."""

        if self.approval_attempts == 0:
            return 0.0

        return (
            self.classified_approval_attempts
            / self.approval_attempts
            * 100.0
        )

    @property
    def classified_approval_block_rate(self) -> float:
        """Return block rate among classified approval attempts."""

        if self.classified_approval_attempts == 0:
            return 0.0

        return (
            self.would_block
            / self.classified_approval_attempts
            * 100.0
        )


def _normalize_bool(
    value: object,
) -> bool | None:
    """Convert CSV booleans to bool; return None when missing."""

    text = str(
        value or ""
    ).strip().lower()

    if text in {
        "true",
        "1",
        "yes",
        "on",
    }:
        return True

    if text in {
        "false",
        "0",
        "no",
        "off",
    }:
        return False

    return None


def load_guardrail_decisions(
    path: Path | str | None = None,
) -> tuple[Path, list[dict[str, str]]]:
    """Load decision history from an explicit or runtime path."""

    source = (
        Path(path)
        if path is not None
        else suggestions_service.get_decisions_csv()
    )

    if not source.is_file():
        return source, []

    with source.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    return source, rows


def build_guardrail_dry_run_summary(
    rows: Iterable[dict[str, str]],
    *,
    source_path: Path | str = "",
) -> GuardrailDryRunSummary:
    """Aggregate projected enforcement effects."""

    materialized = list(rows)

    action_counts: Counter[str] = Counter()
    requirement_counts: Counter[str] = Counter()
    policy_counts: Counter[str] = Counter()

    approval_attempts = 0
    classified_approval_attempts = 0
    unclassified_approval_attempts = 0
    non_approval_decisions = 0

    shadow_rows = 0
    enforce_rows = 0
    legacy_rows = 0

    would_block = 0
    would_allow = 0

    allowed_in_recorded_mode = 0
    denied_in_recorded_mode = 0

    for row in materialized:
        action = str(
            row.get(
                "Action",
                "unknown",
            )
            or "unknown"
        ).strip().lower()

        policy = str(
            row.get(
                "Blocking Policy",
                "unknown",
            )
            or "unknown"
        ).strip().lower()

        mode = str(
            row.get(
                "Guardrail Mode",
                "",
            )
            or ""
        ).strip().lower()

        requirement = str(
            row.get(
                "Guardrail Requirement",
                "",
            )
            or ""
        ).strip().lower()

        recorded_would_block = _normalize_bool(
            row.get(
                "Guardrail Would Block",
            )
        )

        recorded_allowed = _normalize_bool(
            row.get(
                "Guardrail Allowed",
            )
        )

        action_counts[action] += 1
        policy_counts[policy] += 1

        if requirement:
            requirement_counts[
                requirement
            ] += 1
        else:
            requirement_counts[
                "legacy-or-missing"
            ] += 1

        if action in APPROVAL_ACTIONS:
            approval_attempts += 1

            if recorded_would_block is True:
                classified_approval_attempts += 1
                would_block += 1

            elif recorded_would_block is False:
                classified_approval_attempts += 1
                would_allow += 1

            else:
                unclassified_approval_attempts += 1

        else:
            non_approval_decisions += 1

        if mode == "shadow":
            shadow_rows += 1

        elif mode == "enforce":
            enforce_rows += 1

        else:
            legacy_rows += 1

        if recorded_allowed is True:
            allowed_in_recorded_mode += 1

        elif recorded_allowed is False:
            denied_in_recorded_mode += 1

    return GuardrailDryRunSummary(
        generated_at=(
            datetime.now(UTC)
            .isoformat(timespec="seconds")
        ),
        source_path=str(source_path),
        total_decisions=len(materialized),
        approval_attempts=approval_attempts,
        classified_approval_attempts=(
            classified_approval_attempts
        ),
        unclassified_approval_attempts=(
            unclassified_approval_attempts
        ),
        non_approval_decisions=(
            non_approval_decisions
        ),
        shadow_rows=shadow_rows,
        enforce_rows=enforce_rows,
        legacy_rows=legacy_rows,
        would_block=would_block,
        would_allow=would_allow,
        allowed_in_recorded_mode=(
            allowed_in_recorded_mode
        ),
        denied_in_recorded_mode=(
            denied_in_recorded_mode
        ),
        requirements=dict(
            sorted(
                requirement_counts.items()
            )
        ),
        policies=dict(
            sorted(
                policy_counts.items()
            )
        ),
        actions=dict(
            sorted(
                action_counts.items()
            )
        ),
    )


def render_guardrail_dry_run_markdown(
    summary: GuardrailDryRunSummary,
) -> str:
    """Render a human-readable dry-run report."""

    lines = [
        "# 5ibr Guardrail Enforcement Dry Run",
        "",
        f"- Generated: {summary.generated_at}",
        f"- Source: `{summary.source_path}`",
        "",
        "## Impact Summary",
        "",
        (
            "- Total Decisions: "
            f"{summary.total_decisions}"
        ),
        (
            "- Approval Attempts: "
            f"{summary.approval_attempts}"
        ),
        (
            "- Classified Approval Attempts: "
            f"{summary.classified_approval_attempts}"
        ),
        (
            "- Unclassified Approval Attempts: "
            f"{summary.unclassified_approval_attempts}"
        ),
        (
            "- Guardrail Coverage Rate: "
            f"{summary.guardrail_coverage_rate:.2f}%"
        ),
        (
            "- Non-Approval Decisions: "
            f"{summary.non_approval_decisions}"
        ),
        (
            "- Would Block Under Enforcement: "
            f"{summary.would_block}"
        ),
        (
            "- Would Allow Under Enforcement: "
            f"{summary.would_allow}"
        ),
        (
            "- Projected Approval Block Rate "
            "Among Classified Attempts: "
            f"{summary.classified_approval_block_rate:.2f}%"
        ),
        "",
        "## Coverage Interpretation",
        "",
        (
            "- Coverage Status: "
            + (
                "complete"
                if summary.guardrail_coverage_rate == 100.0
                else "incomplete"
            )
        ),
        (
            "- Unclassified approval attempts are "
            "excluded from the classified block rate."
        ),
        (
            "- Do not enable enforcement using "
            "legacy or unclassified rows as evidence."
        ),
        "",
        "## Recorded Modes",
        "",
        f"- Shadow Rows: {summary.shadow_rows}",
        f"- Enforce Rows: {summary.enforce_rows}",
        f"- Legacy Rows: {summary.legacy_rows}",
        "",
        "## Recorded Outcomes",
        "",
        (
            "- Allowed in Recorded Mode: "
            f"{summary.allowed_in_recorded_mode}"
        ),
        (
            "- Denied in Recorded Mode: "
            f"{summary.denied_in_recorded_mode}"
        ),
        "",
        "## Requirements",
        "",
    ]

    if summary.requirements:
        for name, count in (
            summary.requirements.items()
        ):
            lines.append(
                f"- `{name}`: {count}"
            )
    else:
        lines.append(
            "- No requirement data."
        )

    lines.extend(
        [
            "",
            "## Blocking Policies",
            "",
        ]
    )

    if summary.policies:
        for name, count in (
            summary.policies.items()
        ):
            lines.append(
                f"- `{name}`: {count}"
            )
    else:
        lines.append(
            "- No policy data."
        )

    lines.extend(
        [
            "",
            "## Decision Actions",
            "",
        ]
    )

    if summary.actions:
        for name, count in (
            summary.actions.items()
        ):
            lines.append(
                f"- `{name}`: {count}"
            )
    else:
        lines.append(
            "- No decisions recorded."
        )

    lines.extend(
        [
            "",
            "## Enforcement Status",
            "",
            "- Application Enforcement: disabled",
            "- Report Mode: dry-run only",
            "- Approval Workflow: unchanged",
            "",
        ]
    )

    return "\n".join(lines)


def write_guardrail_dry_run_report(
    output_path: Path | str,
    *,
    decisions_path: Path | str | None = None,
) -> GuardrailDryRunSummary:
    """Build and write a guardrail dry-run report."""

    source, rows = load_guardrail_decisions(
        decisions_path
    )

    summary = build_guardrail_dry_run_summary(
        rows,
        source_path=source,
    )

    output = Path(
        output_path
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        render_guardrail_dry_run_markdown(
            summary
        ),
        encoding="utf-8",
    )

    return summary
