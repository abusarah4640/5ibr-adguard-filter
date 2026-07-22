"""Guarded production re-enable operation.

The operation:

- requires enforcement to be disabled
- validates the disabled production state
- atomically enables enforcement
- verifies the resulting production state
- automatically rolls back on failure
- writes an auditable receipt
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from scripts.services.guarded_disable_service import (
    load_json_object,
    write_json_atomic,
)
from scripts.services.production_status_service import (
    PRODUCTION_INACTIVE,
    get_production_status,
)
from scripts.services.production_verify_service import (
    PRODUCTION_VERIFIED,
    verify_production,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CONFIG_PATH = (
    PROJECT_ROOT
    / "config/scoped-promotion-enforcement.json"
)

DEFAULT_RECEIPT_PATH = (
    PROJECT_ROOT
    / "reports/evaluation/"
    "stage60d-reenable-receipt.json"
)


@dataclass(frozen=True, slots=True)
class ReenableCheck:
    name: str
    passed: bool
    actual: Any
    expected: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReenableReceipt:
    stage: str = "1.9.0-stage60d"
    operation: str = "guarded-reenable"

    started_at_utc: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    completed_at_utc: str = ""

    decision: str = "REENABLE_PENDING"

    enabled_before: bool = False
    enabled_after: bool = False

    rollback_performed: bool = False

    checks: list[dict[str, Any]] = field(
        default_factory=list
    )

    failures: list[str] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def add_check(
    receipt: ReenableReceipt,
    *,
    name: str,
    actual: Any,
    expected: Any,
) -> None:
    check = ReenableCheck(
        name=name,
        passed=actual == expected,
        actual=actual,
        expected=expected,
    )

    receipt.checks.append(
        check.to_dict()
    )

    if not check.passed:
        receipt.failures.append(
            f"{name}: "
            f"{actual!r} != "
            f"{expected!r}"
        )


def run_guarded_reenable(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    receipt_path: Path = DEFAULT_RECEIPT_PATH,
    status_loader: Callable[..., Any] = (
        get_production_status
    ),
    verifier: Callable[..., Any] = (
        verify_production
    ),
) -> ReenableReceipt:
    receipt = ReenableReceipt()

    original_bytes = config_path.read_bytes()

    try:
        config = load_json_object(
            config_path
        )

        receipt.enabled_before = (
            config.get("enabled") is True
        )

        add_check(
            receipt,
            name="enabled-before",
            actual=receipt.enabled_before,
            expected=False,
        )

        if receipt.failures:
            raise RuntimeError(
                "reenable preflight failed"
            )

        status = status_loader()

        add_check(
            receipt,
            name="disabled-production-status",
            actual=status.decision,
            expected=PRODUCTION_INACTIVE,
        )

        add_check(
            receipt,
            name="disabled-production-health",
            actual=status.healthy,
            expected=True,
        )

        add_check(
            receipt,
            name="policy-sha-match",
            actual=status.policy_sha_matches,
            expected=True,
        )

        add_check(
            receipt,
            name="authorized-domain-count",
            actual=status.authorized_domains,
            expected=13,
        )

        add_check(
            receipt,
            name="audit-integrity",
            actual=(
                status.audit_integrity_decision
            ),
            expected="AUDIT_INTEGRITY_PASS",
        )

        add_check(
            receipt,
            name="invalid-audit-events",
            actual=status.audit_invalid_events,
            expected=0,
        )

        if receipt.failures:
            raise RuntimeError(
                "reenable preflight failed"
            )

        enabled = dict(config)
        enabled["enabled"] = True

        write_json_atomic(
            config_path,
            enabled,
        )

        current = load_json_object(
            config_path
        )

        receipt.enabled_after = (
            current.get("enabled") is True
        )

        add_check(
            receipt,
            name="enabled-after",
            actual=receipt.enabled_after,
            expected=True,
        )

        verification = verifier()

        add_check(
            receipt,
            name="post-enable-verification",
            actual=verification.decision,
            expected=PRODUCTION_VERIFIED,
        )

        if receipt.failures:
            raise RuntimeError(
                "reenable validation failed"
            )

        receipt.decision = (
            "PRODUCTION_REENABLE_SUCCEEDED"
        )

    except Exception as exc:
        original = json.loads(
            original_bytes.decode("utf-8")
        )

        write_json_atomic(
            config_path,
            original,
        )

        receipt.rollback_performed = True

        restored = load_json_object(
            config_path
        )

        receipt.enabled_after = (
            restored.get("enabled") is True
        )

        receipt.decision = (
            "PRODUCTION_REENABLE_ROLLED_BACK"
        )

        receipt.failures.append(
            f"operation: "
            f"{type(exc).__name__}: {exc}"
        )

    finally:
        receipt.completed_at_utc = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        receipt_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        write_json_atomic(
            receipt_path,
            receipt.to_dict(),
        )

    return receipt
