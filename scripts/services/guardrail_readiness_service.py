"""Readiness gate for future guardrail enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.services.guardrail_report_service import (
    GuardrailDryRunSummary,
    build_guardrail_dry_run_summary,
    load_guardrail_decisions,
)


@dataclass(frozen=True, slots=True)
class EnforcementReadinessThresholds:
    """Minimum evidence required before enforcement."""

    minimum_classified_approvals: int = 100
    minimum_coverage_rate: float = 95.0
    maximum_unclassified_approvals: int = 5
    maximum_classified_block_rate: float = 25.0
    require_shadow_rows: bool = True
    require_zero_enforce_rows: bool = True


@dataclass(frozen=True, slots=True)
class ReadinessDiagnosticCheck:
    """Structured, read-only explanation of one readiness check."""

    key: str
    label: str
    current: str
    target: str
    passed: bool
    guidance: str


@dataclass(frozen=True, slots=True)
class ReadinessProgress:
    """Read-only progress toward satisfying every readiness threshold."""

    percent: float
    passed_checks: int
    total_checks: int
    classified_approvals_remaining: int
    coverage_gap: float
    unclassified_approvals_excess: int
    classified_block_rate_excess: float
    shadow_rows_remaining: int
    enforce_rows_excess: int


@dataclass(frozen=True, slots=True)
class EnforcementReadinessResult:
    """Result of evaluating enforcement readiness."""

    ready: bool
    status: str
    reasons: tuple[str, ...]
    passed_checks: tuple[str, ...]
    thresholds: EnforcementReadinessThresholds
    summary: GuardrailDryRunSummary

    @property
    def progress(self) -> ReadinessProgress:
        """Return bounded, deterministic progress toward READY."""

        summary = self.summary
        limits = self.thresholds

        classified_ratio = (
            1.0
            if limits.minimum_classified_approvals <= 0
            else min(
                summary.classified_approval_attempts
                / limits.minimum_classified_approvals,
                1.0,
            )
        )
        coverage_ratio = (
            1.0
            if limits.minimum_coverage_rate <= 0
            else min(
                summary.guardrail_coverage_rate
                / limits.minimum_coverage_rate,
                1.0,
            )
        )
        unclassified_ratio = (
            1.0
            if summary.unclassified_approval_attempts
            <= limits.maximum_unclassified_approvals
            else (
                limits.maximum_unclassified_approvals
                / summary.unclassified_approval_attempts
                if limits.maximum_unclassified_approvals > 0
                else 0.0
            )
        )
        block_rate_ratio = (
            1.0
            if summary.classified_approval_block_rate
            <= limits.maximum_classified_block_rate
            else (
                limits.maximum_classified_block_rate
                / summary.classified_approval_block_rate
                if limits.maximum_classified_block_rate > 0
                else 0.0
            )
        )
        shadow_ratio = (
            1.0
            if not limits.require_shadow_rows or summary.shadow_rows > 0
            else 0.0
        )
        enforce_ratio = (
            1.0
            if not limits.require_zero_enforce_rows or summary.enforce_rows == 0
            else 0.0
        )

        ratios = (
            classified_ratio,
            coverage_ratio,
            unclassified_ratio,
            block_rate_ratio,
            shadow_ratio,
            enforce_ratio,
        )
        diagnostics = self.diagnostics

        return ReadinessProgress(
            percent=round(sum(ratios) / len(ratios) * 100.0, 2),
            passed_checks=sum(check.passed for check in diagnostics),
            total_checks=len(diagnostics),
            classified_approvals_remaining=max(
                limits.minimum_classified_approvals
                - summary.classified_approval_attempts,
                0,
            ),
            coverage_gap=round(max(
                limits.minimum_coverage_rate
                - summary.guardrail_coverage_rate,
                0.0,
            ), 2),
            unclassified_approvals_excess=max(
                summary.unclassified_approval_attempts
                - limits.maximum_unclassified_approvals,
                0,
            ),
            classified_block_rate_excess=round(max(
                summary.classified_approval_block_rate
                - limits.maximum_classified_block_rate,
                0.0,
            ), 2),
            shadow_rows_remaining=(
                1
                if limits.require_shadow_rows and summary.shadow_rows == 0
                else 0
            ),
            enforce_rows_excess=(
                summary.enforce_rows
                if limits.require_zero_enforce_rows
                else 0
            ),
        )

    @property
    def diagnostics(self) -> tuple[ReadinessDiagnosticCheck, ...]:
        """Return deterministic diagnostics without changing enforcement state."""

        summary = self.summary
        limits = self.thresholds

        return (
            ReadinessDiagnosticCheck(
                key="classified-approvals",
                label="Classified approvals",
                current=str(summary.classified_approval_attempts),
                target=f">= {limits.minimum_classified_approvals}",
                passed=(
                    summary.classified_approval_attempts
                    >= limits.minimum_classified_approvals
                ),
                guidance="Collect more approval attempts while guardrails run in shadow mode.",
            ),
            ReadinessDiagnosticCheck(
                key="coverage",
                label="Guardrail coverage",
                current=f"{summary.guardrail_coverage_rate:.2f}%",
                target=f">= {limits.minimum_coverage_rate:.2f}%",
                passed=(
                    summary.guardrail_coverage_rate
                    >= limits.minimum_coverage_rate
                ),
                guidance="Reduce legacy or unclassified approvals by recording guardrail outcomes.",
            ),
            ReadinessDiagnosticCheck(
                key="unclassified-approvals",
                label="Unclassified approvals",
                current=str(summary.unclassified_approval_attempts),
                target=f"<= {limits.maximum_unclassified_approvals}",
                passed=(
                    summary.unclassified_approval_attempts
                    <= limits.maximum_unclassified_approvals
                ),
                guidance="Review or replace approval rows that do not contain guardrail evidence.",
            ),
            ReadinessDiagnosticCheck(
                key="classified-block-rate",
                label="Classified block rate",
                current=f"{summary.classified_approval_block_rate:.2f}%",
                target=f"<= {limits.maximum_classified_block_rate:.2f}%",
                passed=(
                    summary.classified_approval_block_rate
                    <= limits.maximum_classified_block_rate
                ),
                guidance="Investigate approvals that shadow guardrails would have blocked.",
            ),
            ReadinessDiagnosticCheck(
                key="shadow-observations",
                label="Shadow observations",
                current=str(summary.shadow_rows),
                target=("> 0" if limits.require_shadow_rows else "not required"),
                passed=(
                    summary.shadow_rows > 0
                    if limits.require_shadow_rows
                    else True
                ),
                guidance="Keep guardrails in shadow mode and collect at least one observation.",
            ),
            ReadinessDiagnosticCheck(
                key="enforce-rows",
                label="Enforce rows",
                current=str(summary.enforce_rows),
                target=("0" if limits.require_zero_enforce_rows else "not required"),
                passed=(
                    summary.enforce_rows == 0
                    if limits.require_zero_enforce_rows
                    else True
                ),
                guidance="Remove unexpected enforce-mode evidence; application enforcement stays disabled.",
            ),
        )


def evaluate_enforcement_readiness(
    summary: GuardrailDryRunSummary,
    *,
    thresholds: EnforcementReadinessThresholds | None = None,
) -> EnforcementReadinessResult:
    """Evaluate whether collected evidence is sufficient."""

    limits = (
        thresholds
        or EnforcementReadinessThresholds()
    )

    failures: list[str] = []
    passes: list[str] = []

    if (
        summary.classified_approval_attempts
        >= limits.minimum_classified_approvals
    ):
        passes.append(
            "minimum classified approvals satisfied"
        )
    else:
        failures.append(
            "insufficient classified approval attempts: "
            f"{summary.classified_approval_attempts} "
            f"< {limits.minimum_classified_approvals}"
        )

    if (
        summary.guardrail_coverage_rate
        >= limits.minimum_coverage_rate
    ):
        passes.append(
            "minimum guardrail coverage satisfied"
        )
    else:
        failures.append(
            "insufficient guardrail coverage: "
            f"{summary.guardrail_coverage_rate:.2f}% "
            f"< {limits.minimum_coverage_rate:.2f}%"
        )

    if (
        summary.unclassified_approval_attempts
        <= limits.maximum_unclassified_approvals
    ):
        passes.append(
            "unclassified approval limit satisfied"
        )
    else:
        failures.append(
            "too many unclassified approval attempts: "
            f"{summary.unclassified_approval_attempts} "
            f"> {limits.maximum_unclassified_approvals}"
        )

    if (
        summary.classified_approval_block_rate
        <= limits.maximum_classified_block_rate
    ):
        passes.append(
            "classified block-rate limit satisfied"
        )
    else:
        failures.append(
            "classified approval block rate is too high: "
            f"{summary.classified_approval_block_rate:.2f}% "
            f"> {limits.maximum_classified_block_rate:.2f}%"
        )

    if limits.require_shadow_rows:
        if summary.shadow_rows > 0:
            passes.append(
                "shadow observations are present"
            )
        else:
            failures.append(
                "no shadow guardrail observations are present"
            )

    if limits.require_zero_enforce_rows:
        if summary.enforce_rows == 0:
            passes.append(
                "no enforce-mode rows are present"
            )
        else:
            failures.append(
                "enforce-mode rows already exist: "
                f"{summary.enforce_rows}"
            )

    ready = not failures

    return EnforcementReadinessResult(
        ready=ready,
        status=(
            "ready"
            if ready
            else "not-ready"
        ),
        reasons=tuple(failures),
        passed_checks=tuple(passes),
        thresholds=limits,
        summary=summary,
    )


def load_enforcement_readiness(
    decisions_path: Path | str | None = None,
    *,
    thresholds: EnforcementReadinessThresholds | None = None,
) -> EnforcementReadinessResult:
    """Load decision history and evaluate readiness."""

    source, rows = load_guardrail_decisions(
        decisions_path
    )

    summary = build_guardrail_dry_run_summary(
        rows,
        source_path=source,
    )

    return evaluate_enforcement_readiness(
        summary,
        thresholds=thresholds,
    )


def render_enforcement_readiness_markdown(
    result: EnforcementReadinessResult,
) -> str:
    """Render a human-readable readiness report."""

    summary = result.summary
    limits = result.thresholds

    lines = [
        "# 5ibr Guardrail Enforcement Readiness",
        "",
        f"- Status: **{result.status.upper()}**",
        f"- Ready: `{str(result.ready).lower()}`",
        f"- Source: `{summary.source_path}`",
        f"- Generated: {summary.generated_at}",
        "",
        "## Evidence",
        "",
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
            "- Classified Approval Block Rate: "
            f"{summary.classified_approval_block_rate:.2f}%"
        ),
        f"- Shadow Rows: {summary.shadow_rows}",
        f"- Enforce Rows: {summary.enforce_rows}",
        "",
        "## Thresholds",
        "",
        (
            "- Minimum Classified Approvals: "
            f"{limits.minimum_classified_approvals}"
        ),
        (
            "- Minimum Coverage Rate: "
            f"{limits.minimum_coverage_rate:.2f}%"
        ),
        (
            "- Maximum Unclassified Approvals: "
            f"{limits.maximum_unclassified_approvals}"
        ),
        (
            "- Maximum Classified Block Rate: "
            f"{limits.maximum_classified_block_rate:.2f}%"
        ),
        (
            "- Require Shadow Rows: "
            f"{str(limits.require_shadow_rows).lower()}"
        ),
        (
            "- Require Zero Enforce Rows: "
            f"{str(limits.require_zero_enforce_rows).lower()}"
        ),
        "",
        "## Failed Checks",
        "",
    ]

    if result.reasons:
        for reason in result.reasons:
            lines.append(
                f"- {reason}"
            )
    else:
        lines.append(
            "- None."
        )

    lines.extend(
        [
            "",
            "## Passed Checks",
            "",
        ]
    )

    if result.passed_checks:
        for check in result.passed_checks:
            lines.append(
                f"- {check}"
            )
    else:
        lines.append(
            "- None."
        )

    lines.extend(
        [
            "",
            "## Decision",
            "",
        ]
    )

    if result.ready:
        lines.extend(
            [
                "- Evidence gate: PASS",
                (
                    "- This result does not activate "
                    "enforcement automatically."
                ),
            ]
        )
    else:
        lines.extend(
            [
                "- Evidence gate: FAIL",
                "- Enforcement must remain disabled.",
            ]
        )

    lines.extend(
        [
            "- Application Enforcement: disabled",
            "- Approval Workflow: unchanged",
            "",
        ]
    )

    return "\n".join(lines)


def write_enforcement_readiness_report(
    output_path: Path | str,
    *,
    decisions_path: Path | str | None = None,
    thresholds: EnforcementReadinessThresholds | None = None,
) -> EnforcementReadinessResult:
    """Evaluate and write the readiness report."""

    result = load_enforcement_readiness(
        decisions_path,
        thresholds=thresholds,
    )

    output = Path(
        output_path
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        render_enforcement_readiness_markdown(
            result
        ),
        encoding="utf-8",
    )

    return result
