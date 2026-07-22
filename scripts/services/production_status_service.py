"""Read-only production lifecycle status.

This service provides a deterministic, fail-closed view of the current
production enforcement state. It performs no writes and never changes
the production kill switch.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_ENFORCEMENT_CONFIG_PATH = (
    PROJECT_ROOT
    / "config/scoped-promotion-enforcement.json"
)

DEFAULT_POLICY_PATH = (
    PROJECT_ROOT
    / "config/scoped-promotion-policies.json"
)

DEFAULT_READINESS_PATH = (
    PROJECT_ROOT
    / "reports/evaluation/"
    "stage54-production-readiness.json"
)

DEFAULT_ACTIVATION_RECEIPT_PATH = (
    PROJECT_ROOT
    / "reports/evaluation/"
    "stage59-activation-receipt.json"
)

DEFAULT_AUDIT_INTEGRITY_PATH = (
    PROJECT_ROOT
    / "reports/evaluation/"
    "stage59-post-activation-audit-integrity.json"
)


PRODUCTION_ACTIVE = "PRODUCTION_ACTIVE"
PRODUCTION_INACTIVE = "PRODUCTION_INACTIVE"
PRODUCTION_DEGRADED = "PRODUCTION_DEGRADED"


@dataclass(frozen=True, slots=True)
class ProductionStatus:
    decision: str
    healthy: bool

    enforcement_enabled: bool
    authorized_domains: int

    configured_policy_sha256: str
    actual_policy_sha256: str
    policy_sha_matches: bool

    readiness_decision: str

    activation_decision: str
    activation_completed_at_utc: str
    activation_rollback_performed: bool

    audit_integrity_decision: str
    audit_invalid_events: int

    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["issues"] = list(self.issues)
        return data


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


def _sha256_file(
    path: Path,
) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def get_production_status(
    *,
    enforcement_config_path: str | Path = (
        DEFAULT_ENFORCEMENT_CONFIG_PATH
    ),
    policy_path: str | Path = (
        DEFAULT_POLICY_PATH
    ),
    readiness_path: str | Path = (
        DEFAULT_READINESS_PATH
    ),
    activation_receipt_path: str | Path = (
        DEFAULT_ACTIVATION_RECEIPT_PATH
    ),
    audit_integrity_path: str | Path = (
        DEFAULT_AUDIT_INTEGRITY_PATH
    ),
) -> ProductionStatus:
    config_path = Path(
        enforcement_config_path
    )
    policy = Path(policy_path)
    readiness_file = Path(readiness_path)
    receipt_file = Path(
        activation_receipt_path
    )
    audit_file = Path(
        audit_integrity_path
    )

    issues: list[str] = []

    try:
        config = _load_json_object(
            config_path
        )
    except Exception as exc:
        return ProductionStatus(
            decision=PRODUCTION_DEGRADED,
            healthy=False,
            enforcement_enabled=False,
            authorized_domains=0,
            configured_policy_sha256="",
            actual_policy_sha256="",
            policy_sha_matches=False,
            readiness_decision="",
            activation_decision="",
            activation_completed_at_utc="",
            activation_rollback_performed=False,
            audit_integrity_decision="",
            audit_invalid_events=0,
            issues=(
                "enforcement-config-unreadable:"
                f"{type(exc).__name__}",
            ),
        )

    enforcement_enabled = (
        config.get("enabled") is True
    )

    raw_domains = config.get(
        "authorized_domains",
        [],
    )

    if isinstance(raw_domains, list):
        normalized_domains = {
            str(domain)
            .strip()
            .lower()
            .strip(".")
            for domain in raw_domains
            if str(domain).strip()
        }
    else:
        normalized_domains = set()
        issues.append(
            "authorized-domains-invalid"
        )

    authorized_domains = len(
        normalized_domains
    )

    configured_sha = str(
        config.get(
            "policy_sha256",
            "",
        )
        or ""
    ).strip().lower()

    try:
        actual_sha = _sha256_file(
            policy
        )
    except Exception as exc:
        actual_sha = ""
        issues.append(
            "policy-unreadable:"
            f"{type(exc).__name__}"
        )

    policy_sha_matches = bool(
        configured_sha
        and actual_sha
        and configured_sha == actual_sha
    )

    if not policy_sha_matches:
        issues.append(
            "policy-sha-mismatch"
        )

    try:
        readiness = _load_json_object(
            readiness_file
        )
        readiness_decision = str(
            readiness.get(
                "decision",
                "",
            )
        )
    except Exception as exc:
        readiness_decision = ""
        issues.append(
            "readiness-unreadable:"
            f"{type(exc).__name__}"
        )

    try:
        receipt = _load_json_object(
            receipt_file
        )

        activation_decision = str(
            receipt.get(
                "decision",
                "",
            )
        )

        activation_completed_at_utc = str(
            receipt.get(
                "completed_at_utc",
                "",
            )
        )

        activation_rollback_performed = (
            receipt.get(
                "rollback_performed"
            )
            is True
        )

    except Exception as exc:
        activation_decision = ""
        activation_completed_at_utc = ""
        activation_rollback_performed = False

        issues.append(
            "activation-receipt-unreadable:"
            f"{type(exc).__name__}"
        )

    try:
        audit = _load_json_object(
            audit_file
        )

        audit_integrity_decision = str(
            audit.get(
                "decision",
                "",
            )
        )

        audit_invalid_events = int(
            audit.get(
                "invalid_events",
                0,
            )
        )

    except Exception as exc:
        audit_integrity_decision = ""
        audit_invalid_events = 0

        issues.append(
            "audit-integrity-unreadable:"
            f"{type(exc).__name__}"
        )

    if authorized_domains == 0:
        issues.append(
            "no-authorized-domains"
        )

    if (
        readiness_decision
        != "PROMOTION_READY"
    ):
        issues.append(
            "readiness-not-ready"
        )

    if (
        activation_decision
        != "PERMANENT_ACTIVATION_SUCCEEDED"
    ):
        issues.append(
            "activation-not-succeeded"
        )

    if activation_rollback_performed:
        issues.append(
            "activation-rollback-recorded"
        )

    if (
        audit_integrity_decision
        != "AUDIT_INTEGRITY_PASS"
    ):
        issues.append(
            "audit-integrity-not-pass"
        )

    if audit_invalid_events != 0:
        issues.append(
            "invalid-audit-events"
        )

    healthy = len(issues) == 0

    if enforcement_enabled and healthy:
        decision = PRODUCTION_ACTIVE

    elif (
        not enforcement_enabled
        and healthy
    ):
        decision = PRODUCTION_INACTIVE

    else:
        decision = PRODUCTION_DEGRADED

    return ProductionStatus(
        decision=decision,
        healthy=healthy,
        enforcement_enabled=(
            enforcement_enabled
        ),
        authorized_domains=(
            authorized_domains
        ),
        configured_policy_sha256=(
            configured_sha
        ),
        actual_policy_sha256=(
            actual_sha
        ),
        policy_sha_matches=(
            policy_sha_matches
        ),
        readiness_decision=(
            readiness_decision
        ),
        activation_decision=(
            activation_decision
        ),
        activation_completed_at_utc=(
            activation_completed_at_utc
        ),
        activation_rollback_performed=(
            activation_rollback_performed
        ),
        audit_integrity_decision=(
            audit_integrity_decision
        ),
        audit_invalid_events=(
            audit_invalid_events
        ),
        issues=tuple(issues),
    )
