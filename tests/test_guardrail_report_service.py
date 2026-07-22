from __future__ import annotations

import csv
from pathlib import Path

from scripts.services import (
    guardrail_report_service as service,
)


def modern_row(
    *,
    action: str = "approved",
    policy: str = "do-not-block",
    requirement: str = "require-override",
    would_block: str = "true",
    allowed: str = "true",
    mode: str = "shadow",
) -> dict[str, str]:
    return {
        "Time": "2026-07-16T00:00:00+00:00",
        "Action": action,
        "Domain": "example.test",
        "Blocking Policy": policy,
        "Guardrail Mode": mode,
        "Guardrail Requirement": requirement,
        "Guardrail Would Block": would_block,
        "Guardrail Allowed": allowed,
    }


def test_empty_summary_is_safe():
    summary = (
        service
        .build_guardrail_dry_run_summary(
            [],
            source_path="/tmp/empty.csv",
        )
    )

    assert summary.total_decisions == 0
    assert summary.approval_attempts == 0
    assert summary.would_block == 0
    assert summary.approval_block_rate == 0.0


def test_summary_counts_projected_approval_blocks():
    rows = [
        modern_row(),
        modern_row(
            policy="safe-to-block",
            requirement="allow",
            would_block="false",
        ),
        modern_row(
            action="ignored",
            requirement="allow",
            would_block="false",
        ),
    ]

    summary = (
        service
        .build_guardrail_dry_run_summary(
            rows,
        )
    )

    assert summary.total_decisions == 3
    assert summary.approval_attempts == 2
    assert summary.non_approval_decisions == 1

    assert summary.would_block == 1
    assert summary.would_allow == 1

    assert (
        summary.approval_block_rate
        == 50.0
    )


def test_failed_approval_actions_count_as_attempts():
    rows = [
        modern_row(
            action="approved-failed",
        ),
        modern_row(
            action="approved-build-failed",
        ),
    ]

    summary = (
        service
        .build_guardrail_dry_run_summary(
            rows
        )
    )

    assert summary.approval_attempts == 2
    assert summary.would_block == 2


def test_legacy_rows_are_preserved_and_counted():
    rows = [
        {
            "Action": "ignored",
            "Domain": "legacy.test",
            "Blocking Policy": "unknown",
        }
    ]

    summary = (
        service
        .build_guardrail_dry_run_summary(
            rows
        )
    )

    assert summary.total_decisions == 1
    assert summary.legacy_rows == 1

    assert (
        summary.requirements[
            "legacy-or-missing"
        ]
        == 1
    )


def test_markdown_contains_key_sections():
    summary = (
        service
        .build_guardrail_dry_run_summary(
            [
                modern_row(),
            ],
            source_path="/tmp/decisions.csv",
        )
    )

    markdown = (
        service
        .render_guardrail_dry_run_markdown(
            summary
        )
    )

    required = (
        "Impact Summary",
        "Would Block Under Enforcement",
        "Projected Approval Block Rate",
        "Requirements",
        "Blocking Policies",
        "Application Enforcement: disabled",
    )

    for value in required:
        assert value in markdown


def test_report_writer_reads_csv_and_writes_markdown(
    tmp_path: Path,
):
    decisions = (
        tmp_path
        / "suggestion-decisions.csv"
    )

    output = (
        tmp_path
        / "guardrail-dry-run.md"
    )

    fieldnames = [
        "Time",
        "Action",
        "Domain",
        "Blocking Policy",
        "Guardrail Mode",
        "Guardrail Requirement",
        "Guardrail Would Block",
        "Guardrail Allowed",
    ]

    with decisions.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerow(
            modern_row()
        )

    summary = (
        service
        .write_guardrail_dry_run_report(
            output,
            decisions_path=decisions,
        )
    )

    assert output.is_file()
    assert summary.total_decisions == 1
    assert summary.would_block == 1

    markdown = output.read_text(
        encoding="utf-8"
    )

    assert (
        "Guardrail Enforcement Dry Run"
        in markdown
    )


def test_legacy_approval_is_unclassified():
    rows = [
        {
            "Action": "approved-failed",
            "Domain": "legacy.test",
            "Blocking Policy": "unknown",
        }
    ]

    summary = (
        service
        .build_guardrail_dry_run_summary(
            rows
        )
    )

    assert summary.approval_attempts == 1

    assert (
        summary.classified_approval_attempts
        == 0
    )

    assert (
        summary.unclassified_approval_attempts
        == 1
    )

    assert summary.guardrail_coverage_rate == 0.0

    assert (
        summary.classified_approval_block_rate
        == 0.0
    )


def test_coverage_rate_uses_all_approval_attempts():
    rows = [
        modern_row(
            would_block="true",
        ),
        {
            "Action": "approved",
            "Domain": "legacy.test",
            "Blocking Policy": "unknown",
        },
    ]

    summary = (
        service
        .build_guardrail_dry_run_summary(
            rows
        )
    )

    assert summary.approval_attempts == 2

    assert (
        summary.classified_approval_attempts
        == 1
    )

    assert (
        summary.unclassified_approval_attempts
        == 1
    )

    assert summary.guardrail_coverage_rate == 50.0


def test_classified_block_rate_excludes_legacy_rows():
    rows = [
        modern_row(
            would_block="true",
        ),
        modern_row(
            policy="safe-to-block",
            requirement="allow",
            would_block="false",
        ),
        {
            "Action": "approved",
            "Domain": "legacy.test",
            "Blocking Policy": "unknown",
        },
    ]

    summary = (
        service
        .build_guardrail_dry_run_summary(
            rows
        )
    )

    assert summary.approval_attempts == 3

    assert (
        summary.classified_approval_attempts
        == 2
    )

    assert (
        summary.classified_approval_block_rate
        == 50.0
    )

    # The old compatibility metric still uses
    # every approval attempt.
    assert round(
        summary.approval_block_rate,
        2,
    ) == 33.33


def test_markdown_explains_incomplete_coverage():
    summary = (
        service
        .build_guardrail_dry_run_summary(
            [
                {
                    "Action": "approved",
                    "Domain": "legacy.test",
                }
            ]
        )
    )

    markdown = (
        service
        .render_guardrail_dry_run_markdown(
            summary
        )
    )

    required = (
        "Classified Approval Attempts",
        "Unclassified Approval Attempts",
        "Guardrail Coverage Rate",
        (
            "Projected Approval Block Rate "
            "Among Classified Attempts"
        ),
        "Coverage Status: incomplete",
        (
            "Unclassified approval attempts are "
            "excluded"
        ),
    )

    for value in required:
        assert value in markdown
