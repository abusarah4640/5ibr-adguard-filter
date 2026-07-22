"""Permanent production activation readiness gate.

This gate is read-only. It validates prior readiness, audit integrity,
policy binding, activation trial evidence, regression, and the current
kill-switch state. It never enables enforcement or modifies production.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PERMANENT_ACTIVATION_READY = (
    "PERMANENT_ACTIVATION_READY"
)

PERMANENT_ACTIVATION_BLOCKED = (
    "PERMANENT_ACTIVATION_BLOCKED"
)


@dataclass(frozen=True)
class ActivationReadinessCheck:
    name: str
    passed: bool
    actual: Any
    expected: Any
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PermanentActivationReadiness:
    decision: str
    ready: bool
    checks_passed: int
    checks_failed: int
    blocking_reasons: tuple[str, ...]
    policy_sha256: str
    configured_policy_sha256: str
    kill_switch_enabled: bool
    checks: tuple[
        ActivationReadinessCheck,
        ...,
    ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "ready": self.ready,
            "checks_passed": (
                self.checks_passed
            ),
            "checks_failed": (
                self.checks_failed
            ),
            "blocking_reasons": list(
                self.blocking_reasons
            ),
            "policy_sha256": (
                self.policy_sha256
            ),
            "configured_policy_sha256": (
                self.configured_policy_sha256
            ),
            "kill_switch_enabled": (
                self.kill_switch_enabled
            ),
            "checks": [
                check.to_dict()
                for check in self.checks
            ],
        }


def load_json_object(
    path: Path,
) -> dict[str, Any]:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"expected JSON object: {path}"
        )

    return data


def sha256_file(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def add_check(
    checks: list[
        ActivationReadinessCheck
    ],
    *,
    name: str,
    actual: Any,
    expected: Any,
    message: str,
) -> None:
    checks.append(
        ActivationReadinessCheck(
            name=name,
            passed=actual == expected,
            actual=actual,
            expected=expected,
            message=message,
        )
    )


def evaluate_permanent_activation_readiness(
    *,
    production_readiness: dict[str, Any],
    audit_integrity: dict[str, Any],
    activation_receipt: dict[str, Any],
    regression: dict[str, Any],
    enforcement_config: dict[str, Any],
    policy_sha256: str,
) -> PermanentActivationReadiness:
    checks: list[
        ActivationReadinessCheck
    ] = []

    configured_sha = str(
        enforcement_config.get(
            "policy_sha256",
            "",
        )
        or ""
    ).strip().lower()

    enabled = bool(
        enforcement_config.get(
            "enabled",
            False,
        )
    )

    add_check(
        checks,
        name="production-readiness-decision",
        actual=production_readiness.get(
            "decision"
        ),
        expected="PROMOTION_READY",
        message=(
            "Stage 54 must authorize promotion."
        ),
    )

    add_check(
        checks,
        name="production-readiness-failures",
        actual=production_readiness.get(
            "checks_failed"
        ),
        expected=0,
        message=(
            "Stage 54 must have zero failed checks."
        ),
    )

    add_check(
        checks,
        name="production-readiness-blockers",
        actual=len(
            production_readiness.get(
                "blocking_reasons",
                [],
            )
        ),
        expected=0,
        message=(
            "Stage 54 must have no blockers."
        ),
    )

    add_check(
        checks,
        name="audit-integrity-decision",
        actual=audit_integrity.get(
            "decision"
        ),
        expected="AUDIT_INTEGRITY_PASS",
        message=(
            "Audit integrity must pass."
        ),
    )

    add_check(
        checks,
        name="audit-invalid-events",
        actual=audit_integrity.get(
            "invalid_events"
        ),
        expected=0,
        message=(
            "Audit log must contain no invalid events."
        ),
    )

    add_check(
        checks,
        name="activation-validation",
        actual=activation_receipt.get(
            "validation_passed"
        ),
        expected=True,
        message=(
            "Controlled activation trial must pass."
        ),
    )

    activation_expectations = {
        "target_domains": 13,
        "changed_domains": 13,
        "expected_changes": 13,
        "unexpected_changes": 0,
        "missed_targets": 0,
        "non_filter_changes": 0,
        "vendor_changes": 0,
        "category_changes": 0,
        "confidence_changes": 0,
        "recommendation_changes": 0,
    }

    for key, expected in (
        activation_expectations.items()
    ):
        add_check(
            checks,
            name=f"activation-{key}",
            actual=activation_receipt.get(
                key
            ),
            expected=expected,
            message=(
                "Stage 56C activation requirement: "
                f"{key}={expected}."
            ),
        )

    add_check(
        checks,
        name="regression-common-domains",
        actual=regression.get(
            "common_domains"
        ),
        expected=500,
        message=(
            "Regression snapshot must compare "
            "500 common domains."
        ),
    )

    add_check(
        checks,
        name="regression-changed-domains",
        actual=regression.get(
            "changed_domains"
        ),
        expected=0,
        message=(
            "Post-rollback production must "
            "have zero changed domains."
        ),
    )

    add_check(
        checks,
        name="policy-sha-binding",
        actual=configured_sha,
        expected=policy_sha256,
        message=(
            "Enforcement config must bind to "
            "the current policy SHA-256."
        ),
    )

    add_check(
        checks,
        name="kill-switch-safe-state",
        actual=enabled,
        expected=False,
        message=(
            "Permanent readiness must be "
            "evaluated while enforcement is OFF."
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

    ready = not blockers

    return PermanentActivationReadiness(
        decision=(
            PERMANENT_ACTIVATION_READY
            if ready
            else PERMANENT_ACTIVATION_BLOCKED
        ),
        ready=ready,
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
        configured_policy_sha256=(
            configured_sha
        ),
        kill_switch_enabled=enabled,
        checks=tuple(checks),
    )


def run_permanent_activation_readiness(
    *,
    production_readiness_path: Path,
    audit_integrity_path: Path,
    activation_receipt_path: Path,
    regression_path: Path,
    enforcement_config_path: Path,
    policy_path: Path,
) -> PermanentActivationReadiness:
    return evaluate_permanent_activation_readiness(
        production_readiness=load_json_object(
            production_readiness_path
        ),
        audit_integrity=load_json_object(
            audit_integrity_path
        ),
        activation_receipt=load_json_object(
            activation_receipt_path
        ),
        regression=load_json_object(
            regression_path
        ),
        enforcement_config=load_json_object(
            enforcement_config_path
        ),
        policy_sha256=sha256_file(
            policy_path
        ),
    )


def build_permanent_readiness_report(
    result: PermanentActivationReadiness,
) -> str:
    lines = [
        "5ibr Permanent Activation Readiness",
        "===================================",
        "",
        f"Decision                  : {result.decision}",
        f"Ready                     : {result.ready}",
        (
            "Checks passed             : "
            f"{result.checks_passed}"
        ),
        (
            "Checks failed             : "
            f"{result.checks_failed}"
        ),
        (
            "Blocking reasons          : "
            f"{len(result.blocking_reasons)}"
        ),
        (
            "Kill switch enabled       : "
            f"{result.kill_switch_enabled}"
        ),
        "",
        (
            "Policy SHA-256            : "
            f"{result.policy_sha256}"
        ),
        (
            "Configured policy SHA-256 : "
            f"{result.configured_policy_sha256}"
        ),
        "",
        "Checks:",
    ]

    for check in result.checks:
        marker = (
            "PASS"
            if check.passed
            else "FAIL"
        )

        lines.append(
            f"  [{marker}] {check.name}"
        )
        lines.append(
            f"         actual   : "
            f"{check.actual}"
        )
        lines.append(
            f"         expected : "
            f"{check.expected}"
        )

    if result.blocking_reasons:
        lines.extend(
            [
                "",
                "Blocking reasons:",
            ]
        )

        for reason in (
            result.blocking_reasons
        ):
            lines.append(
                f"  - {reason}"
            )

    return "\n".join(lines)
