"""Final acceptance gate for the production activation lifecycle.

This service performs read-only validation of the completed Stage 60
lifecycle and produces a deterministic acceptance decision.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scripts.services.production_status_service import (
    PRODUCTION_ACTIVE,
    get_production_status,
)
from scripts.services.production_verify_service import (
    PRODUCTION_VERIFIED,
    verify_production,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DISABLE_RECEIPT_PATH = (
    PROJECT_ROOT
    / "reports/evaluation/"
    "stage60c-disable-receipt.json"
)

DEFAULT_REENABLE_RECEIPT_PATH = (
    PROJECT_ROOT
    / "reports/evaluation/"
    "stage60d-reenable-receipt.json"
)

DEFAULT_FINAL_VERIFY_PATH = (
    PROJECT_ROOT
    / "reports/evaluation/"
    "stage60d-final-production-verify.json"
)


LIFECYCLE_ACCEPTED = (
    "PRODUCTION_LIFECYCLE_ACCEPTED"
)

LIFECYCLE_REJECTED = (
    "PRODUCTION_LIFECYCLE_REJECTED"
)


@dataclass(frozen=True, slots=True)
class LifecycleAcceptanceCheck:
    name: str
    passed: bool
    actual: Any
    expected: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LifecycleAcceptance:
    decision: str
    accepted: bool
    checks_passed: int
    checks_failed: int
    blocking_reasons: tuple[str, ...]
    checks: tuple[
        LifecycleAcceptanceCheck,
        ...,
    ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "accepted": self.accepted,
            "checks_passed": (
                self.checks_passed
            ),
            "checks_failed": (
                self.checks_failed
            ),
            "blocking_reasons": list(
                self.blocking_reasons
            ),
            "checks": [
                check.to_dict()
                for check in self.checks
            ],
        }


def _load_json_object(
    path: Path,
) -> dict[str, Any]:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return data


def _add_check(
    checks: list[
        LifecycleAcceptanceCheck
    ],
    *,
    name: str,
    actual: Any,
    expected: Any,
) -> None:
    checks.append(
        LifecycleAcceptanceCheck(
            name=name,
            passed=actual == expected,
            actual=actual,
            expected=expected,
        )
    )


def evaluate_lifecycle_acceptance(
    *,
    disable_receipt_path: str | Path = (
        DEFAULT_DISABLE_RECEIPT_PATH
    ),
    reenable_receipt_path: str | Path = (
        DEFAULT_REENABLE_RECEIPT_PATH
    ),
    final_verify_path: str | Path = (
        DEFAULT_FINAL_VERIFY_PATH
    ),
) -> LifecycleAcceptance:
    checks: list[
        LifecycleAcceptanceCheck
    ] = []

    try:
        status = get_production_status()

        _add_check(
            checks,
            name="production-status",
            actual=status.decision,
            expected=PRODUCTION_ACTIVE,
        )

        _add_check(
            checks,
            name="production-healthy",
            actual=status.healthy,
            expected=True,
        )

        _add_check(
            checks,
            name="enforcement-enabled",
            actual=status.enforcement_enabled,
            expected=True,
        )

        _add_check(
            checks,
            name="authorized-domains",
            actual=status.authorized_domains,
            expected=13,
        )

        _add_check(
            checks,
            name="policy-sha-match",
            actual=status.policy_sha_matches,
            expected=True,
        )

        _add_check(
            checks,
            name="audit-integrity",
            actual=(
                status.audit_integrity_decision
            ),
            expected="AUDIT_INTEGRITY_PASS",
        )

        _add_check(
            checks,
            name="invalid-audit-events",
            actual=status.audit_invalid_events,
            expected=0,
        )

    except Exception as exc:
        _add_check(
            checks,
            name="production-status-readable",
            actual=(
                f"{type(exc).__name__}: {exc}"
            ),
            expected="readable",
        )

    try:
        verification = verify_production()

        _add_check(
            checks,
            name="live-verification",
            actual=verification.decision,
            expected=PRODUCTION_VERIFIED,
        )

        _add_check(
            checks,
            name="live-verification-failures",
            actual=verification.checks_failed,
            expected=0,
        )

    except Exception as exc:
        _add_check(
            checks,
            name="live-verification-readable",
            actual=(
                f"{type(exc).__name__}: {exc}"
            ),
            expected="readable",
        )

    try:
        disable = _load_json_object(
            Path(disable_receipt_path)
        )

        _add_check(
            checks,
            name="disable-decision",
            actual=disable.get("decision"),
            expected=(
                "PRODUCTION_DISABLE_SUCCEEDED"
            ),
        )

        _add_check(
            checks,
            name="disable-enabled-before",
            actual=disable.get(
                "enabled_before"
            ),
            expected=True,
        )

        _add_check(
            checks,
            name="disable-enabled-after",
            actual=disable.get(
                "enabled_after"
            ),
            expected=False,
        )

        _add_check(
            checks,
            name="disable-failures",
            actual=len(
                disable.get("failures", [])
            ),
            expected=0,
        )

    except Exception as exc:
        _add_check(
            checks,
            name="disable-receipt-readable",
            actual=(
                f"{type(exc).__name__}: {exc}"
            ),
            expected="readable",
        )

    try:
        reenable = _load_json_object(
            Path(reenable_receipt_path)
        )

        _add_check(
            checks,
            name="reenable-decision",
            actual=reenable.get("decision"),
            expected=(
                "PRODUCTION_REENABLE_SUCCEEDED"
            ),
        )

        _add_check(
            checks,
            name="reenable-enabled-before",
            actual=reenable.get(
                "enabled_before"
            ),
            expected=False,
        )

        _add_check(
            checks,
            name="reenable-enabled-after",
            actual=reenable.get(
                "enabled_after"
            ),
            expected=True,
        )

        _add_check(
            checks,
            name="reenable-rollback",
            actual=reenable.get(
                "rollback_performed"
            ),
            expected=False,
        )

        _add_check(
            checks,
            name="reenable-failures",
            actual=len(
                reenable.get("failures", [])
            ),
            expected=0,
        )

    except Exception as exc:
        _add_check(
            checks,
            name="reenable-receipt-readable",
            actual=(
                f"{type(exc).__name__}: {exc}"
            ),
            expected="readable",
        )

    try:
        final_verify = _load_json_object(
            Path(final_verify_path)
        )

        _add_check(
            checks,
            name="final-verify-decision",
            actual=final_verify.get(
                "decision"
            ),
            expected=PRODUCTION_VERIFIED,
        )

        _add_check(
            checks,
            name="final-verify-verified",
            actual=final_verify.get(
                "verified"
            ),
            expected=True,
        )

        _add_check(
            checks,
            name="final-verify-failures",
            actual=final_verify.get(
                "checks_failed"
            ),
            expected=0,
        )

        _add_check(
            checks,
            name="final-verify-blockers",
            actual=len(
                final_verify.get(
                    "blocking_reasons",
                    [],
                )
            ),
            expected=0,
        )

    except Exception as exc:
        _add_check(
            checks,
            name="final-verify-readable",
            actual=(
                f"{type(exc).__name__}: {exc}"
            ),
            expected="readable",
        )

    blocking_reasons = tuple(
        (
            f"{check.name}: "
            f"{check.actual!r} != "
            f"{check.expected!r}"
        )
        for check in checks
        if not check.passed
    )

    accepted = not blocking_reasons

    return LifecycleAcceptance(
        decision=(
            LIFECYCLE_ACCEPTED
            if accepted
            else LIFECYCLE_REJECTED
        ),
        accepted=accepted,
        checks_passed=sum(
            check.passed
            for check in checks
        ),
        checks_failed=sum(
            not check.passed
            for check in checks
        ),
        blocking_reasons=(
            blocking_reasons
        ),
        checks=tuple(checks),
    )
