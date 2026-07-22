"""Final readiness gate before controlled production enforcement.

This service validates artifacts from Stages 50, 52, and 53. It never
changes Analyzer behavior, configuration, database rows, recommendations,
confidence, or production output.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.services.scoped_policy_shadow import (
    load_scoped_policy_artifact,
)


READY = "PROMOTION_READY"
BLOCKED = "PROMOTION_BLOCKED"


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    passed: bool
    actual: Any
    expected: Any
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "actual": self.actual,
            "expected": self.expected,
            "message": self.message,
        }


@dataclass(frozen=True)
class ProductionSnapshotComparison:
    before_domains: int
    after_domains: int
    common_domains: int
    changed_domains: int
    added_domains: int
    removed_domains: int
    changed: tuple[dict[str, Any], ...] = field(
        default_factory=tuple
    )

    @property
    def unchanged(self) -> int:
        return (
            self.common_domains
            - self.changed_domains
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_domains": self.before_domains,
            "after_domains": self.after_domains,
            "common_domains": self.common_domains,
            "changed_domains": self.changed_domains,
            "unchanged": self.unchanged,
            "added_domains": self.added_domains,
            "removed_domains": self.removed_domains,
            "changed": list(self.changed),
        }


@dataclass(frozen=True)
class PromotionReadinessSummary:
    decision: str
    checks_passed: int
    checks_failed: int
    blocking_reasons: tuple[str, ...]
    policy_sha256: str
    recorded_policy_sha256: str
    policies_loaded: int
    authorized_suffixes: int
    eligible_targets: int
    scoped_changes: int
    shadow_matches: int
    regression_unchanged: int
    regression_common: int
    checks: tuple[ReadinessCheck, ...]
    regression: ProductionSnapshotComparison

    @property
    def ready(self) -> bool:
        return self.decision == READY

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "ready": self.ready,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "blocking_reasons": list(
                self.blocking_reasons
            ),
            "policy_sha256": self.policy_sha256,
            "recorded_policy_sha256": (
                self.recorded_policy_sha256
            ),
            "policies_loaded": self.policies_loaded,
            "authorized_suffixes": (
                self.authorized_suffixes
            ),
            "eligible_targets": (
                self.eligible_targets
            ),
            "scoped_changes": self.scoped_changes,
            "shadow_matches": self.shadow_matches,
            "regression_unchanged": (
                self.regression_unchanged
            ),
            "regression_common": (
                self.regression_common
            ),
            "checks": [
                check.to_dict()
                for check in self.checks
            ],
            "regression": self.regression.to_dict(),
        }


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"expected JSON object: {path}"
        )

    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_recorded_sha256(path: Path) -> str:
    text = path.read_text(
        encoding="utf-8"
    ).strip()

    if not text:
        raise ValueError(
            f"empty SHA-256 record: {path}"
        )

    value = text.split()[0].strip().lower()

    if (
        len(value) != 64
        or any(
            character not in "0123456789abcdef"
            for character in value
        )
    ):
        raise ValueError(
            f"invalid SHA-256 record: {path}"
        )

    return value


def load_suggestion_rows(
    path: Path,
) -> list[dict[str, Any]]:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if isinstance(data, dict):
        rows = data.get("suggestions", [])
    else:
        rows = data

    if not isinstance(rows, list):
        raise ValueError(
            f"invalid suggestions snapshot: {path}"
        )

    return [
        row
        for row in rows
        if (
            isinstance(row, dict)
            and str(
                row.get("domain", "")
            ).strip()
        )
    ]


def normalize_domain(value: object) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .strip(".")
    )


def normalized_decision(
    row: dict[str, Any],
) -> dict[str, Any]:
    return {
        "vendor": str(
            row.get("vendor", "Unknown")
        ),
        "category": str(
            row.get("category", "Unknown")
        ),
        "filter": str(
            row.get("filter", "unknown")
        ),
        "confidence": int(
            float(
                row.get("confidence", 0)
                or 0
            )
        ),
        "recommendation": str(
            row.get(
                "recommendation",
                "unknown",
            )
        ),
    }


def compare_production_snapshots(
    before_rows: list[dict[str, Any]],
    after_rows: list[dict[str, Any]],
) -> ProductionSnapshotComparison:
    before = {
        normalize_domain(
            row.get("domain")
        ): normalized_decision(row)
        for row in before_rows
        if normalize_domain(
            row.get("domain")
        )
    }

    after = {
        normalize_domain(
            row.get("domain")
        ): normalized_decision(row)
        for row in after_rows
        if normalize_domain(
            row.get("domain")
        )
    }

    common = sorted(
        set(before) & set(after)
    )

    changed: list[dict[str, Any]] = []

    for domain in common:
        if before[domain] == after[domain]:
            continue

        changed.append(
            {
                "domain": domain,
                "before": before[domain],
                "after": after[domain],
            }
        )

    return ProductionSnapshotComparison(
        before_domains=len(before),
        after_domains=len(after),
        common_domains=len(common),
        changed_domains=len(changed),
        added_domains=len(
            set(after) - set(before)
        ),
        removed_domains=len(
            set(before) - set(after)
        ),
        changed=tuple(changed),
    )


def add_check(
    checks: list[ReadinessCheck],
    *,
    name: str,
    actual: Any,
    expected: Any,
    message: str,
) -> None:
    checks.append(
        ReadinessCheck(
            name=name,
            passed=actual == expected,
            actual=actual,
            expected=expected,
            message=message,
        )
    )


def evaluate_promotion_readiness(
    *,
    candidate_gate: dict[str, Any],
    scoped_simulation: dict[str, Any],
    shadow_execution: dict[str, Any],
    policy_sha256: str,
    recorded_policy_sha256: str,
    policies_loaded: int,
    authorized_suffixes: int,
    regression: ProductionSnapshotComparison,
) -> PromotionReadinessSummary:
    checks: list[ReadinessCheck] = []

    # Stage 50
    add_check(
        checks,
        name="stage50-eligible",
        actual=candidate_gate.get(
            "eligible"
        ),
        expected=13,
        message=(
            "Stage 50 must provide exactly "
            "13 eligible candidates."
        ),
    )

    add_check(
        checks,
        name="stage50-held",
        actual=candidate_gate.get("held"),
        expected=5,
        message=(
            "Stage 50 must preserve the five "
            "non-promoted candidates for review."
        ),
    )

    add_check(
        checks,
        name="stage50-rejected",
        actual=candidate_gate.get(
            "rejected"
        ),
        expected=0,
        message=(
            "No candidate should fail the "
            "base safety requirements."
        ),
    )

    add_check(
        checks,
        name="stage50-production-changes",
        actual=candidate_gate.get(
            "production_changes"
        ),
        expected=0,
        message=(
            "Candidate evaluation must not "
            "modify production."
        ),
    )

    # Stage 52
    stage52_expected = {
        "target_domains": 13,
        "changed_domains": 13,
        "intended_changes": 13,
        "collateral_changes": 0,
        "unchanged_target_domains": 0,
        "confidence_changes": 0,
        "recommendation_changes": 0,
        "baseline_drift": 0,
        "production_changes": 0,
    }

    for key, expected in (
        stage52_expected.items()
    ):
        add_check(
            checks,
            name=f"stage52-{key}",
            actual=scoped_simulation.get(
                key
            ),
            expected=expected,
            message=(
                "Stage 52 scoped simulation "
                f"requirement: {key}={expected}."
            ),
        )

    # Stage 53
    stage53_expected = {
        "domains_evaluated": 500,
        "policies_loaded": 2,
        "authorized_suffixes": 3,
        "expected_targets": 13,
        "shadow_matches": 13,
        "expected_matches": 13,
        "unexpected_matches": 0,
        "missed_expected_matches": 0,
        "filter_only_changes": 13,
        "confidence_changes": 0,
        "recommendation_changes": 0,
        "baseline_drift": 0,
        "production_changes": 0,
    }

    for key, expected in (
        stage53_expected.items()
    ):
        add_check(
            checks,
            name=f"stage53-{key}",
            actual=shadow_execution.get(
                key
            ),
            expected=expected,
            message=(
                "Stage 53 shadow enforcement "
                f"requirement: {key}={expected}."
            ),
        )

    # Artifact validation
    add_check(
        checks,
        name="policy-sha256",
        actual=policy_sha256,
        expected=recorded_policy_sha256,
        message=(
            "Policy artifact SHA-256 must "
            "match the Stage 53 record."
        ),
    )

    add_check(
        checks,
        name="artifact-policies-loaded",
        actual=policies_loaded,
        expected=2,
        message=(
            "Persistent artifact must load "
            "exactly two policies."
        ),
    )

    add_check(
        checks,
        name="artifact-authorized-suffixes",
        actual=authorized_suffixes,
        expected=3,
        message=(
            "Persistent artifact must contain "
            "exactly three authorized suffixes."
        ),
    )

    # Cross-stage consistency
    add_check(
        checks,
        name="eligible-target-consistency",
        actual=candidate_gate.get(
            "eligible"
        ),
        expected=shadow_execution.get(
            "expected_targets"
        ),
        message=(
            "Eligible candidates and expected "
            "shadow targets must agree."
        ),
    )

    add_check(
        checks,
        name="scoped-shadow-consistency",
        actual=scoped_simulation.get(
            "intended_changes"
        ),
        expected=shadow_execution.get(
            "expected_matches"
        ),
        message=(
            "Scoped intended changes and "
            "shadow expected matches must agree."
        ),
    )

    # Production regression
    regression_expected = {
        "before_domains": 500,
        "after_domains": 500,
        "common_domains": 500,
        "changed_domains": 0,
        "added_domains": 0,
        "removed_domains": 0,
    }

    regression_payload = (
        regression.to_dict()
    )

    for key, expected in (
        regression_expected.items()
    ):
        add_check(
            checks,
            name=f"regression-{key}",
            actual=regression_payload.get(
                key
            ),
            expected=expected,
            message=(
                "Production snapshot requirement: "
                f"{key}={expected}."
            ),
        )

    blockers = tuple(
        (
            f"{check.name}: "
            f"{check.actual!r} != "
            f"{check.expected!r}"
        )
        for check in checks
        if not check.passed
    )

    decision = (
        READY
        if not blockers
        else BLOCKED
    )

    return PromotionReadinessSummary(
        decision=decision,
        checks_passed=sum(
            check.passed
            for check in checks
        ),
        checks_failed=sum(
            not check.passed
            for check in checks
        ),
        blocking_reasons=blockers,
        policy_sha256=policy_sha256,
        recorded_policy_sha256=(
            recorded_policy_sha256
        ),
        policies_loaded=policies_loaded,
        authorized_suffixes=(
            authorized_suffixes
        ),
        eligible_targets=int(
            candidate_gate.get(
                "eligible",
                0,
            )
            or 0
        ),
        scoped_changes=int(
            scoped_simulation.get(
                "intended_changes",
                0,
            )
            or 0
        ),
        shadow_matches=int(
            shadow_execution.get(
                "expected_matches",
                0,
            )
            or 0
        ),
        regression_unchanged=(
            regression.unchanged
        ),
        regression_common=(
            regression.common_domains
        ),
        checks=tuple(checks),
        regression=regression,
    )


def run_production_readiness_gate(
    *,
    candidate_gate_path: Path,
    scoped_simulation_path: Path,
    shadow_execution_path: Path,
    policy_path: Path,
    recorded_sha256_path: Path,
    before_snapshot_path: Path,
    after_snapshot_path: Path,
) -> PromotionReadinessSummary:
    candidate_gate = load_json_object(
        candidate_gate_path
    )

    scoped_simulation = load_json_object(
        scoped_simulation_path
    )

    shadow_execution = load_json_object(
        shadow_execution_path
    )

    policies = load_scoped_policy_artifact(
        policy_path
    )

    suffix_count = sum(
        len(
            policy.authorized_suffixes
        )
        for policy in policies
    )

    policy_sha = sha256_file(
        policy_path
    )

    recorded_sha = load_recorded_sha256(
        recorded_sha256_path
    )

    before_rows = load_suggestion_rows(
        before_snapshot_path
    )

    after_rows = load_suggestion_rows(
        after_snapshot_path
    )

    regression = (
        compare_production_snapshots(
            before_rows,
            after_rows,
        )
    )

    return evaluate_promotion_readiness(
        candidate_gate=candidate_gate,
        scoped_simulation=(
            scoped_simulation
        ),
        shadow_execution=(
            shadow_execution
        ),
        policy_sha256=policy_sha,
        recorded_policy_sha256=(
            recorded_sha
        ),
        policies_loaded=len(policies),
        authorized_suffixes=(
            suffix_count
        ),
        regression=regression,
    )


def build_readiness_report(
    summary: PromotionReadinessSummary,
) -> str:
    lines = [
        "5ibr Production Promotion Readiness",
        "===================================",
        "",
        f"Decision                  : {summary.decision}",
        (
            "Checks passed             : "
            f"{summary.checks_passed}"
        ),
        (
            "Checks failed             : "
            f"{summary.checks_failed}"
        ),
        (
            "Blocking reasons          : "
            f"{len(summary.blocking_reasons)}"
        ),
        "",
        (
            "Policy SHA-256            : "
            f"{summary.policy_sha256}"
        ),
        (
            "Recorded SHA-256          : "
            f"{summary.recorded_policy_sha256}"
        ),
        (
            "Policies loaded           : "
            f"{summary.policies_loaded}"
        ),
        (
            "Authorized suffixes       : "
            f"{summary.authorized_suffixes}"
        ),
        "",
        (
            "Eligible targets          : "
            f"{summary.eligible_targets}"
        ),
        (
            "Scoped changes            : "
            f"{summary.scoped_changes}"
        ),
        (
            "Shadow matches            : "
            f"{summary.shadow_matches}"
        ),
        "",
        (
            "Regression common         : "
            f"{summary.regression_common}"
        ),
        (
            "Regression unchanged      : "
            f"{summary.regression_unchanged}"
        ),
        (
            "Regression changed        : "
            f"{summary.regression.changed_domains}"
        ),
        (
            "Regression added          : "
            f"{summary.regression.added_domains}"
        ),
        (
            "Regression removed        : "
            f"{summary.regression.removed_domains}"
        ),
        "",
        "Checks:",
    ]

    for check in summary.checks:
        marker = "PASS" if check.passed else "FAIL"

        lines.append(
            f"  [{marker}] {check.name}"
        )
        lines.append(
            f"         actual   : {check.actual}"
        )
        lines.append(
            f"         expected : {check.expected}"
        )

    if summary.blocking_reasons:
        lines.extend(
            [
                "",
                "Blocking reasons:",
            ]
        )

        for reason in (
            summary.blocking_reasons
        ):
            lines.append(
                f"  - {reason}"
            )

    return "\n".join(lines).rstrip()
