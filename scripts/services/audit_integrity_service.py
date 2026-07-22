"""Integrity evaluation for production enforcement audit events.

Historical policy hashes are valid historical evidence. They are not
treated as corruption merely because they differ from the current policy.

The integrity gate fails only for structurally invalid or semantically
invalid audit events.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.services.scoped_policy_shadow import (
    load_scoped_policy_artifact,
)
from scripts.services.scoped_promotion_policy import (
    domain_matches_suffix,
)


AUDIT_INTEGRITY_PASS = "AUDIT_INTEGRITY_PASS"
AUDIT_INTEGRITY_FAIL = "AUDIT_INTEGRITY_FAIL"

CURRENT_POLICY = "CURRENT_POLICY"
HISTORICAL_POLICY = "HISTORICAL_POLICY"
INVALID = "INVALID"

DEFAULT_AUDIT_PATH = Path(
    "reports/audit/"
    "scoped-production-enforcement.jsonl"
)

DEFAULT_POLICY_PATH = Path(
    "config/scoped-promotion-policies.json"
)


REQUIRED_FIELDS = {
    "timestamp_utc",
    "domain",
    "matched_suffix",
    "category",
    "before_filter",
    "after_filter",
    "confidence",
    "recommendation",
    "policy_sha256",
    "readiness_decision",
    "enforcement_enabled",
}


@dataclass(frozen=True)
class AuditEventAssessment:
    line_number: int
    classification: str
    domain: str
    policy_sha256: str
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["errors"] = list(self.errors)
        return result


@dataclass(frozen=True)
class AuditIntegrityResult:
    decision: str
    raw_lines: int
    non_empty_lines: int
    valid_events: int
    invalid_events: int
    current_policy_events: int
    historical_policy_events: int
    unique_domains: int
    duplicate_domains: dict[str, int]
    current_policy_sha256: str
    assessments: tuple[
        AuditEventAssessment,
        ...,
    ]

    @property
    def passed(self) -> bool:
        return (
            self.decision
            == AUDIT_INTEGRITY_PASS
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "passed": self.passed,
            "raw_lines": self.raw_lines,
            "non_empty_lines": (
                self.non_empty_lines
            ),
            "valid_events": self.valid_events,
            "invalid_events": (
                self.invalid_events
            ),
            "current_policy_events": (
                self.current_policy_events
            ),
            "historical_policy_events": (
                self.historical_policy_events
            ),
            "unique_domains": (
                self.unique_domains
            ),
            "duplicate_domains": (
                self.duplicate_domains
            ),
            "current_policy_sha256": (
                self.current_policy_sha256
            ),
            "assessments": [
                item.to_dict()
                for item in self.assessments
            ],
        }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "")

    return (
        len(text) == 64
        and all(
            character
            in "0123456789abcdef"
            for character in text
        )
    )


def _validate_timestamp(
    value: Any,
) -> bool:
    text = str(value or "")

    try:
        datetime.fromisoformat(
            text.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError:
        return False

    return True


def _validate_policy_scope(
    event: dict[str, Any],
    policies: list[Any],
) -> bool:
    domain = str(
        event.get("domain", "")
    )

    matched_suffix = str(
        event.get(
            "matched_suffix",
            "",
        )
    )

    category = str(
        event.get("category", "")
    )

    before_filter = str(
        event.get(
            "before_filter",
            "",
        )
    )

    after_filter = str(
        event.get(
            "after_filter",
            "",
        )
    )

    matches = [
        policy
        for policy in policies
        if (
            policy.category == category
            and policy.current_filter
            == before_filter
            and policy.proposed_filter
            == after_filter
            and matched_suffix
            in policy.authorized_suffixes
            and domain_matches_suffix(
                domain,
                matched_suffix,
            )
        )
    ]

    return len(matches) == 1


def evaluate_audit_integrity(
    *,
    audit_path: Path = DEFAULT_AUDIT_PATH,
    policy_path: Path = DEFAULT_POLICY_PATH,
) -> AuditIntegrityResult:
    current_sha = _sha256_file(
        policy_path
    )

    policies = load_scoped_policy_artifact(
        policy_path
    )

    raw_lines = (
        audit_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if audit_path.exists()
        else []
    )

    assessments = []
    valid_domains = []

    current_count = 0
    historical_count = 0
    invalid_count = 0
    non_empty_count = 0

    for line_number, raw_line in enumerate(
        raw_lines,
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        non_empty_count += 1
        errors = []

        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            assessments.append(
                AuditEventAssessment(
                    line_number=line_number,
                    classification=INVALID,
                    domain="",
                    policy_sha256="",
                    errors=(
                        f"invalid JSON: {exc}",
                    ),
                )
            )
            invalid_count += 1
            continue

        if not isinstance(event, dict):
            assessments.append(
                AuditEventAssessment(
                    line_number=line_number,
                    classification=INVALID,
                    domain="",
                    policy_sha256="",
                    errors=(
                        "event is not a JSON object",
                    ),
                )
            )
            invalid_count += 1
            continue

        missing = sorted(
            REQUIRED_FIELDS - set(event)
        )

        if missing:
            errors.append(
                "missing fields: "
                + ", ".join(missing)
            )

        if not _validate_timestamp(
            event.get("timestamp_utc")
        ):
            errors.append(
                "invalid timestamp_utc"
            )

        if not str(
            event.get("domain", "")
        ).strip():
            errors.append(
                "empty domain"
            )

        if not str(
            event.get(
                "matched_suffix",
                "",
            )
        ).strip():
            errors.append(
                "empty matched_suffix"
            )

        if (
            event.get("before_filter")
            == event.get("after_filter")
        ):
            errors.append(
                "no filter transition"
            )

        if (
            event.get(
                "readiness_decision"
            )
            != "PROMOTION_READY"
        ):
            errors.append(
                "invalid readiness decision"
            )

        if (
            event.get(
                "enforcement_enabled"
            )
            is not True
        ):
            errors.append(
                "enforcement was not enabled"
            )

        event_sha = str(
            event.get(
                "policy_sha256",
                "",
            )
        )

        if not _valid_sha256(event_sha):
            errors.append(
                "invalid policy SHA-256"
            )

        if (
            not errors
            and not _validate_policy_scope(
                event,
                policies,
            )
        ):
            errors.append(
                "event is outside authorized "
                "policy scope"
            )

        domain = str(
            event.get("domain", "")
        )

        if errors:
            classification = INVALID
            invalid_count += 1
        elif event_sha == current_sha:
            classification = CURRENT_POLICY
            current_count += 1
            valid_domains.append(domain)
        else:
            classification = (
                HISTORICAL_POLICY
            )
            historical_count += 1
            valid_domains.append(domain)

        assessments.append(
            AuditEventAssessment(
                line_number=line_number,
                classification=classification,
                domain=domain,
                policy_sha256=event_sha,
                errors=tuple(errors),
            )
        )

    domain_counts = Counter(
        valid_domains
    )

    duplicates = {
        domain: count
        for domain, count
        in domain_counts.items()
        if count > 1
    }

    decision = (
        AUDIT_INTEGRITY_PASS
        if invalid_count == 0
        else AUDIT_INTEGRITY_FAIL
    )

    return AuditIntegrityResult(
        decision=decision,
        raw_lines=len(raw_lines),
        non_empty_lines=non_empty_count,
        valid_events=(
            current_count
            + historical_count
        ),
        invalid_events=invalid_count,
        current_policy_events=current_count,
        historical_policy_events=(
            historical_count
        ),
        unique_domains=len(
            domain_counts
        ),
        duplicate_domains=duplicates,
        current_policy_sha256=current_sha,
        assessments=tuple(
            assessments
        ),
    )
