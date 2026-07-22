"""Formal production verification gate.

This service converts ProductionStatus into an auditable verification
decision. It performs no writes and never changes enforcement state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from scripts.services.production_status_service import (
    PRODUCTION_ACTIVE,
    ProductionStatus,
    get_production_status,
)


PRODUCTION_VERIFIED = "PRODUCTION_VERIFIED"

PRODUCTION_VERIFICATION_FAILED = (
    "PRODUCTION_VERIFICATION_FAILED"
)


@dataclass(frozen=True, slots=True)
class ProductionVerifyCheck:
    name: str
    passed: bool
    actual: Any
    expected: Any
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProductionVerification:
    decision: str
    verified: bool
    checks_passed: int
    checks_failed: int
    blocking_reasons: tuple[str, ...]
    status: ProductionStatus
    checks: tuple[
        ProductionVerifyCheck,
        ...,
    ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "verified": self.verified,
            "checks_passed": (
                self.checks_passed
            ),
            "checks_failed": (
                self.checks_failed
            ),
            "blocking_reasons": list(
                self.blocking_reasons
            ),
            "status": self.status.to_dict(),
            "checks": [
                check.to_dict()
                for check in self.checks
            ],
        }


def _add_check(
    checks: list[
        ProductionVerifyCheck
    ],
    *,
    name: str,
    actual: Any,
    expected: Any,
    message: str,
) -> None:
    checks.append(
        ProductionVerifyCheck(
            name=name,
            passed=actual == expected,
            actual=actual,
            expected=expected,
            message=message,
        )
    )


def verify_production_status(
    status: ProductionStatus,
) -> ProductionVerification:
    checks: list[
        ProductionVerifyCheck
    ] = []

    _add_check(
        checks,
        name="production-decision",
        actual=status.decision,
        expected=PRODUCTION_ACTIVE,
        message=(
            "Production must report "
            "PRODUCTION_ACTIVE."
        ),
    )

    _add_check(
        checks,
        name="production-health",
        actual=status.healthy,
        expected=True,
        message=(
            "Production status must be healthy."
        ),
    )

    _add_check(
        checks,
        name="enforcement-enabled",
        actual=status.enforcement_enabled,
        expected=True,
        message=(
            "Scoped production enforcement "
            "must be enabled."
        ),
    )

    _add_check(
        checks,
        name="authorized-domain-count",
        actual=status.authorized_domains,
        expected=13,
        message=(
            "Exactly 13 domains must be "
            "authorized."
        ),
    )

    _add_check(
        checks,
        name="policy-sha-match",
        actual=status.policy_sha_matches,
        expected=True,
        message=(
            "Configured and actual policy "
            "SHA-256 values must match."
        ),
    )

    _add_check(
        checks,
        name="readiness-decision",
        actual=status.readiness_decision,
        expected="PROMOTION_READY",
        message=(
            "Production readiness must remain "
            "PROMOTION_READY."
        ),
    )

    _add_check(
        checks,
        name="activation-decision",
        actual=status.activation_decision,
        expected=(
            "PERMANENT_ACTIVATION_SUCCEEDED"
        ),
        message=(
            "The latest activation receipt "
            "must record success."
        ),
    )

    _add_check(
        checks,
        name="activation-rollback",
        actual=(
            status
            .activation_rollback_performed
        ),
        expected=False,
        message=(
            "The successful activation receipt "
            "must not record rollback."
        ),
    )

    _add_check(
        checks,
        name="audit-integrity-decision",
        actual=(
            status.audit_integrity_decision
        ),
        expected="AUDIT_INTEGRITY_PASS",
        message=(
            "Audit integrity must pass."
        ),
    )

    _add_check(
        checks,
        name="invalid-audit-events",
        actual=status.audit_invalid_events,
        expected=0,
        message=(
            "Audit integrity must report "
            "zero invalid events."
        ),
    )

    _add_check(
        checks,
        name="status-issues",
        actual=len(status.issues),
        expected=0,
        message=(
            "Production status must report "
            "zero issues."
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

    verified = not blockers

    return ProductionVerification(
        decision=(
            PRODUCTION_VERIFIED
            if verified
            else PRODUCTION_VERIFICATION_FAILED
        ),
        verified=verified,
        checks_passed=sum(
            check.passed
            for check in checks
        ),
        checks_failed=sum(
            not check.passed
            for check in checks
        ),
        blocking_reasons=blockers,
        status=status,
        checks=tuple(checks),
    )


def verify_production(
    **status_kwargs: Any,
) -> ProductionVerification:
    return verify_production_status(
        get_production_status(
            **status_kwargs
        )
    )


def build_production_verify_report(
    result: ProductionVerification,
) -> str:
    lines = [
        "5ibr Production Verification",
        "============================",
        "",
        (
            "Decision                  : "
            f"{result.decision}"
        ),
        (
            "Verified                  : "
            f"{result.verified}"
        ),
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
            "Production status         : "
            f"{result.status.decision}"
        ),
        (
            "Enforcement enabled       : "
            f"{result.status.enforcement_enabled}"
        ),
        (
            "Authorized domains        : "
            f"{result.status.authorized_domains}"
        ),
        (
            "Policy SHA matches        : "
            f"{result.status.policy_sha_matches}"
        ),
        (
            "Audit integrity           : "
            f"{result.status.audit_integrity_decision}"
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
