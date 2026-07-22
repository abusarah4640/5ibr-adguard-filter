from __future__ import annotations

from scripts.services.guardrail_readiness_service import (
    EnforcementReadinessThresholds,
    evaluate_enforcement_readiness,
    render_enforcement_readiness_markdown,
)

from scripts.services.guardrail_report_service import (
    build_guardrail_dry_run_summary,
)


def classified_row(
    *,
    would_block: bool = False,
    mode: str = "shadow",
) -> dict[str, str]:
    return {
        "Action": "approved",
        "Domain": "example.test",
        "Blocking Policy": (
            "do-not-block"
            if would_block
            else "safe-to-block"
        ),
        "Guardrail Mode": mode,
        "Guardrail Requirement": (
            "require-override"
            if would_block
            else "allow"
        ),
        "Guardrail Would Block": (
            "true"
            if would_block
            else "false"
        ),
        "Guardrail Allowed": "true",
    }


def evaluate(
    rows: list[dict[str, str]],
    **threshold_values,
):
    summary = build_guardrail_dry_run_summary(
        rows
    )

    thresholds = EnforcementReadinessThresholds(
        **threshold_values
    )

    return evaluate_enforcement_readiness(
        summary,
        thresholds=thresholds,
    )


def test_current_like_legacy_history_is_not_ready():
    result = evaluate(
        [
            {
                "Action": "approved-failed",
                "Domain": "legacy.test",
            }
        ],
        minimum_classified_approvals=1,
        minimum_coverage_rate=95.0,
    )

    assert result.ready is False
    assert result.status == "not-ready"

    assert any(
        "classified approval"
        in reason
        for reason in result.reasons
    )

    assert any(
        "coverage"
        in reason
        for reason in result.reasons
    )


def test_minimum_classified_count_is_required():
    result = evaluate(
        [
            classified_row(),
        ],
        minimum_classified_approvals=2,
        minimum_coverage_rate=0.0,
    )

    assert result.ready is False

    assert any(
        "insufficient classified"
        in reason
        for reason in result.reasons
    )


def test_minimum_coverage_is_required():
    result = evaluate(
        [
            classified_row(),
            {
                "Action": "approved",
                "Domain": "legacy.test",
            },
        ],
        minimum_classified_approvals=1,
        minimum_coverage_rate=75.0,
        maximum_unclassified_approvals=10,
    )

    assert result.ready is False

    assert any(
        "insufficient guardrail coverage"
        in reason
        for reason in result.reasons
    )


def test_unclassified_limit_is_enforced():
    result = evaluate(
        [
            classified_row(),
            {
                "Action": "approved",
                "Domain": "legacy-1.test",
            },
            {
                "Action": "approved",
                "Domain": "legacy-2.test",
            },
        ],
        minimum_classified_approvals=1,
        minimum_coverage_rate=0.0,
        maximum_unclassified_approvals=1,
    )

    assert result.ready is False

    assert any(
        "too many unclassified"
        in reason
        for reason in result.reasons
    )


def test_high_classified_block_rate_is_not_ready():
    result = evaluate(
        [
            classified_row(
                would_block=True
            ),
            classified_row(
                would_block=False
            ),
        ],
        minimum_classified_approvals=1,
        minimum_coverage_rate=100.0,
        maximum_classified_block_rate=25.0,
    )

    assert result.ready is False

    assert any(
        "block rate is too high"
        in reason
        for reason in result.reasons
    )


def test_enforce_rows_make_gate_not_ready():
    result = evaluate(
        [
            classified_row(
                mode="enforce"
            ),
        ],
        minimum_classified_approvals=1,
        minimum_coverage_rate=100.0,
        maximum_classified_block_rate=100.0,
    )

    assert result.ready is False

    assert any(
        "enforce-mode rows"
        in reason
        for reason in result.reasons
    )


def test_complete_safe_shadow_evidence_is_ready():
    rows = [
        classified_row(
            would_block=False
        )
        for _ in range(5)
    ]

    result = evaluate(
        rows,
        minimum_classified_approvals=5,
        minimum_coverage_rate=100.0,
        maximum_unclassified_approvals=0,
        maximum_classified_block_rate=25.0,
    )

    assert result.ready is True
    assert result.status == "ready"
    assert result.reasons == ()

    assert result.passed_checks


def test_markdown_reports_not_ready_and_reasons():
    result = evaluate(
        [],
        minimum_classified_approvals=1,
        minimum_coverage_rate=100.0,
    )

    markdown = (
        render_enforcement_readiness_markdown(
            result
        )
    )

    required = (
        "NOT-READY",
        "Evidence gate: FAIL",
        "Enforcement must remain disabled",
        "Failed Checks",
        "Application Enforcement: disabled",
    )

    for value in required:
        assert value in markdown
