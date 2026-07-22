"""Guarded permanent activation for scoped production enforcement.

The operation:

1. Verifies permanent activation readiness.
2. Verifies policy SHA-256 and audit integrity.
3. Captures a fresh OFF baseline.
4. Atomically enables enforcement.
5. Runs a production-path canary over 500 domains.
6. Requires exactly 13 filter-only changes and 13 matching audit events.
7. Keeps enforcement enabled only when every check passes.
8. Automatically restores enabled=false on failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.services.audit_integrity_service import (
    AUDIT_INTEGRITY_PASS,
    evaluate_audit_integrity,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_DOMAINS = 500
EXPECTED_TARGETS = 13


@dataclass(frozen=True)
class ActivationCheck:
    name: str
    passed: bool
    actual: Any
    expected: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "actual": self.actual,
            "expected": self.expected,
        }


@dataclass
class ActivationReceipt:
    stage: str = "1.9.0-stage59"
    operation: str = "guarded-permanent-activation"
    started_at_utc: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )
    completed_at_utc: str = ""
    decision: str = "ACTIVATION_PENDING"
    enforcement_enabled_before: bool = False
    enforcement_enabled_after: bool = False
    rollback_performed: bool = False
    policy_sha256: str = ""
    baseline_domains: int = 0
    activated_domains: int = 0
    target_domains: int = 0
    changed_domains: int = 0
    expected_changes: int = 0
    unexpected_changes: int = 0
    missed_targets: int = 0
    added_domains: int = 0
    removed_domains: int = 0
    non_filter_changes: int = 0
    vendor_changes: int = 0
    category_changes: int = 0
    confidence_changes: int = 0
    recommendation_changes: int = 0
    audit_events_before: int = 0
    audit_events_after: int = 0
    new_audit_events: int = 0
    invalid_new_audit_events: int = 0
    audit_domain_mismatches: int = 0
    checks: list[dict[str, Any]] = field(
        default_factory=list
    )
    failures: list[str] = field(
        default_factory=list
    )
    changed: list[dict[str, Any]] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return vars(self)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"expected JSON object: {path}"
        )

    return data


def write_json_atomic(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary = Path(temporary_name)

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
            )

            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        temporary.replace(path)

    finally:
        if temporary.exists():
            temporary.unlink()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def audit_lines(path: Path) -> list[str]:
    if not path.exists():
        return []

    return [
        line
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]


def suggestion_rows(
    path: Path,
) -> dict[str, dict[str, Any]]:
    payload = load_json(path)

    rows = payload.get(
        "suggestions",
        [],
    )

    if not isinstance(rows, list):
        raise ValueError(
            f"invalid suggestions payload: {path}"
        )

    return {
        str(row["domain"]): row
        for row in rows
        if (
            isinstance(row, dict)
            and row.get("domain")
        )
    }


def target_domains(
    candidate_gate_path: Path,
) -> set[str]:
    payload = load_json(
        candidate_gate_path
    )

    rows = payload.get(
        "results",
        [],
    )

    if not isinstance(rows, list):
        raise ValueError(
            "candidate gate results must be a list"
        )

    return {
        str(row["domain"])
        for row in rows
        if (
            isinstance(row, dict)
            and row.get("eligible") is True
            and row.get("decision")
            == "eligible-for-controlled-promotion"
            and not bool(
                row.get(
                    "production_changed",
                    False,
                )
            )
        )
    }


def run_analyze_log(
    *,
    output_path: Path,
    snapshot_path: Path,
) -> None:
    command = [
        "fivebr",
        "analyze-log",
        "/opt/5ibr/data/querylogs/latest.json",
        "--min-seen",
        "10",
        "--limit",
        "500",
        "--min-confidence",
        "0",
        "--sort",
        "seen",
        "--format",
        "json",
        "--export",
        "json",
        "--no-reports",
    ]

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            stdout=handle,
            check=True,
        )

    source = (
        PROJECT_ROOT
        / "reports/suggestions.filtered.json"
    )

    shutil.copy2(
        source,
        snapshot_path,
    )


def compare_snapshots(
    *,
    before_path: Path,
    after_path: Path,
    targets: set[str],
) -> dict[str, Any]:
    before = suggestion_rows(before_path)
    after = suggestion_rows(after_path)

    before_domains = set(before)
    after_domains = set(after)

    added = sorted(
        after_domains - before_domains
    )

    removed = sorted(
        before_domains - after_domains
    )

    fields = (
        "vendor",
        "category",
        "filter",
        "confidence",
        "recommendation",
    )

    changes = []

    for domain in sorted(
        before_domains & after_domains
    ):
        changed_fields = [
            field
            for field in fields
            if (
                before[domain].get(field)
                != after[domain].get(field)
            )
        ]

        if not changed_fields:
            continue

        changes.append(
            {
                "domain": domain,
                "targeted": domain in targets,
                "changed_fields": changed_fields,
                "before": {
                    field: before[domain].get(
                        field
                    )
                    for field in fields
                },
                "after": {
                    field: after[domain].get(
                        field
                    )
                    for field in fields
                },
            }
        )

    changed_domains = {
        item["domain"]
        for item in changes
    }

    return {
        "before_count": len(before),
        "after_count": len(after),
        "targets": len(targets),
        "changes": changes,
        "changed_count": len(changes),
        "expected_count": sum(
            item["targeted"]
            for item in changes
        ),
        "unexpected": sorted(
            changed_domains - targets
        ),
        "missed": sorted(
            targets - changed_domains
        ),
        "added": added,
        "removed": removed,
        "non_filter": [
            item
            for item in changes
            if item["changed_fields"]
            != ["filter"]
        ],
        "vendor": [
            item
            for item in changes
            if "vendor"
            in item["changed_fields"]
        ],
        "category": [
            item
            for item in changes
            if "category"
            in item["changed_fields"]
        ],
        "confidence": [
            item
            for item in changes
            if "confidence"
            in item["changed_fields"]
        ],
        "recommendation": [
            item
            for item in changes
            if "recommendation"
            in item["changed_fields"]
        ],
    }


def validate_new_audit_events(
    *,
    audit_path: Path,
    before_count: int,
    expected_domains: set[str],
    policy_sha: str,
) -> dict[str, Any]:
    lines = audit_lines(audit_path)

    new_lines = lines[before_count:]

    events = []
    invalid = []

    for offset, line in enumerate(
        new_lines,
        start=before_count + 1,
    ):
        errors = []

        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            invalid.append(
                {
                    "line": offset,
                    "errors": [
                        f"invalid JSON: {exc}"
                    ],
                }
            )
            continue

        if not isinstance(event, dict):
            invalid.append(
                {
                    "line": offset,
                    "errors": [
                        "event is not an object"
                    ],
                }
            )
            continue

        if (
            event.get("policy_sha256")
            != policy_sha
        ):
            errors.append(
                "policy SHA-256 mismatch"
            )

        if (
            event.get(
                "readiness_decision"
            )
            != "PROMOTION_READY"
        ):
            errors.append(
                "readiness is not PROMOTION_READY"
            )

        if (
            event.get(
                "enforcement_enabled"
            )
            is not True
        ):
            errors.append(
                "enforcement_enabled is not true"
            )

        if (
            event.get("before_filter")
            == event.get("after_filter")
        ):
            errors.append(
                "no filter transition"
            )

        if not event.get(
            "matched_suffix"
        ):
            errors.append(
                "missing matched suffix"
            )

        if errors:
            invalid.append(
                {
                    "line": offset,
                    "domain": event.get(
                        "domain"
                    ),
                    "errors": errors,
                }
            )

        events.append(event)

    domains = {
        str(event.get("domain", ""))
        for event in events
    }

    return {
        "after_count": len(lines),
        "new_count": len(new_lines),
        "events": events,
        "domains": domains,
        "invalid": invalid,
        "missing_domains": sorted(
            expected_domains - domains
        ),
        "unexpected_domains": sorted(
            domains - expected_domains
        ),
    }


def add_check(
    receipt: ActivationReceipt,
    *,
    name: str,
    actual: Any,
    expected: Any,
) -> None:
    check = ActivationCheck(
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


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dry-run-failure",
        action="store_true",
        help=(
            "Force a controlled failure after "
            "activation to verify rollback."
        ),
    )

    args = parser.parse_args(argv)

    config_path = (
        PROJECT_ROOT
        / "config/"
        "scoped-promotion-enforcement.json"
    )

    policy_path = (
        PROJECT_ROOT
        / "config/"
        "scoped-promotion-policies.json"
    )

    readiness_path = (
        PROJECT_ROOT
        / "reports/evaluation/"
        "stage58c-permanent-readiness.json"
    )

    candidate_gate_path = (
        PROJECT_ROOT
        / "reports/evaluation/"
        "stage50-candidate-safety-gate.json"
    )

    audit_path = (
        PROJECT_ROOT
        / "reports/audit/"
        "scoped-production-enforcement.jsonl"
    )

    baseline_output = (
        PROJECT_ROOT
        / "reports/evaluation/"
        "stage59-baseline-output.json"
    )

    baseline_snapshot = (
        PROJECT_ROOT
        / "reports/evaluation/"
        "stage59-baseline-suggestions.json"
    )

    activated_output = (
        PROJECT_ROOT
        / "reports/evaluation/"
        "stage59-activated-output.json"
    )

    activated_snapshot = (
        PROJECT_ROOT
        / "reports/evaluation/"
        "stage59-activated-suggestions.json"
    )

    receipt_path = (
        PROJECT_ROOT
        / "reports/evaluation/"
        "stage59-activation-receipt.json"
    )

    receipt = ActivationReceipt()

    original_config = config_path.read_bytes()
    activation_succeeded = False

    try:
        config = load_json(config_path)
        readiness = load_json(
            readiness_path
        )

        policy_sha = sha256_file(
            policy_path
        )

        receipt.policy_sha256 = policy_sha
        receipt.enforcement_enabled_before = bool(
            config.get("enabled", False)
        )

        add_check(
            receipt,
            name="initial-kill-switch",
            actual=config.get("enabled"),
            expected=False,
        )

        add_check(
            receipt,
            name="permanent-readiness-decision",
            actual=readiness.get(
                "decision"
            ),
            expected=(
                "PERMANENT_ACTIVATION_READY"
            ),
        )

        add_check(
            receipt,
            name="permanent-readiness-failures",
            actual=readiness.get(
                "checks_failed"
            ),
            expected=0,
        )

        add_check(
            receipt,
            name="permanent-readiness-blockers",
            actual=len(
                readiness.get(
                    "blocking_reasons",
                    [],
                )
            ),
            expected=0,
        )

        add_check(
            receipt,
            name="policy-sha-binding",
            actual=config.get(
                "policy_sha256"
            ),
            expected=policy_sha,
        )

        integrity = evaluate_audit_integrity(
            audit_path=audit_path,
            policy_path=policy_path,
        )

        add_check(
            receipt,
            name="pre-activation-audit-integrity",
            actual=integrity.decision,
            expected=AUDIT_INTEGRITY_PASS,
        )

        add_check(
            receipt,
            name="pre-activation-invalid-audit-events",
            actual=integrity.invalid_events,
            expected=0,
        )

        if receipt.failures:
            raise RuntimeError(
                "preflight checks failed"
            )

        targets = target_domains(
            candidate_gate_path
        )

        receipt.target_domains = len(
            targets
        )

        add_check(
            receipt,
            name="target-domain-count",
            actual=len(targets),
            expected=EXPECTED_TARGETS,
        )

        before_audit = audit_lines(
            audit_path
        )

        receipt.audit_events_before = len(
            before_audit
        )

        run_analyze_log(
            output_path=baseline_output,
            snapshot_path=baseline_snapshot,
        )

        receipt.baseline_domains = len(
            suggestion_rows(
                baseline_snapshot
            )
        )

        add_check(
            receipt,
            name="baseline-domain-count",
            actual=receipt.baseline_domains,
            expected=EXPECTED_DOMAINS,
        )

        if receipt.failures:
            raise RuntimeError(
                "baseline checks failed"
            )

        enabled_config = dict(config)
        enabled_config["enabled"] = True

        write_json_atomic(
            config_path,
            enabled_config,
        )

        verified = load_json(
            config_path
        )

        add_check(
            receipt,
            name="atomic-enablement",
            actual=verified.get("enabled"),
            expected=True,
        )

        if args.dry_run_failure:
            raise RuntimeError(
                "forced rollback verification"
            )

        run_analyze_log(
            output_path=activated_output,
            snapshot_path=activated_snapshot,
        )

        comparison = compare_snapshots(
            before_path=baseline_snapshot,
            after_path=activated_snapshot,
            targets=targets,
        )

        receipt.activated_domains = (
            comparison["after_count"]
        )

        receipt.changed_domains = (
            comparison["changed_count"]
        )

        receipt.expected_changes = (
            comparison["expected_count"]
        )

        receipt.unexpected_changes = len(
            comparison["unexpected"]
        )

        receipt.missed_targets = len(
            comparison["missed"]
        )

        receipt.added_domains = len(
            comparison["added"]
        )

        receipt.removed_domains = len(
            comparison["removed"]
        )

        receipt.non_filter_changes = len(
            comparison["non_filter"]
        )

        receipt.vendor_changes = len(
            comparison["vendor"]
        )

        receipt.category_changes = len(
            comparison["category"]
        )

        receipt.confidence_changes = len(
            comparison["confidence"]
        )

        receipt.recommendation_changes = len(
            comparison["recommendation"]
        )

        receipt.changed = comparison[
            "changes"
        ]

        expectations = {
            "activated-domain-count": (
                receipt.activated_domains,
                EXPECTED_DOMAINS,
            ),
            "changed-domain-count": (
                receipt.changed_domains,
                EXPECTED_TARGETS,
            ),
            "expected-change-count": (
                receipt.expected_changes,
                EXPECTED_TARGETS,
            ),
            "unexpected-change-count": (
                receipt.unexpected_changes,
                0,
            ),
            "missed-target-count": (
                receipt.missed_targets,
                0,
            ),
            "added-domain-count": (
                receipt.added_domains,
                0,
            ),
            "removed-domain-count": (
                receipt.removed_domains,
                0,
            ),
            "non-filter-change-count": (
                receipt.non_filter_changes,
                0,
            ),
            "vendor-change-count": (
                receipt.vendor_changes,
                0,
            ),
            "category-change-count": (
                receipt.category_changes,
                0,
            ),
            "confidence-change-count": (
                receipt.confidence_changes,
                0,
            ),
            "recommendation-change-count": (
                receipt.recommendation_changes,
                0,
            ),
        }

        for name, (
            actual,
            expected,
        ) in expectations.items():
            add_check(
                receipt,
                name=name,
                actual=actual,
                expected=expected,
            )

        changed_domains = {
            item["domain"]
            for item in comparison[
                "changes"
            ]
        }

        audit_validation = (
            validate_new_audit_events(
                audit_path=audit_path,
                before_count=len(
                    before_audit
                ),
                expected_domains=(
                    changed_domains
                ),
                policy_sha=policy_sha,
            )
        )

        receipt.audit_events_after = (
            audit_validation[
                "after_count"
            ]
        )

        receipt.new_audit_events = (
            audit_validation[
                "new_count"
            ]
        )

        receipt.invalid_new_audit_events = len(
            audit_validation[
                "invalid"
            ]
        )

        receipt.audit_domain_mismatches = (
            len(
                audit_validation[
                    "missing_domains"
                ]
            )
            + len(
                audit_validation[
                    "unexpected_domains"
                ]
            )
        )

        add_check(
            receipt,
            name="new-audit-event-count",
            actual=receipt.new_audit_events,
            expected=EXPECTED_TARGETS,
        )

        add_check(
            receipt,
            name="invalid-new-audit-events",
            actual=(
                receipt.invalid_new_audit_events
            ),
            expected=0,
        )

        add_check(
            receipt,
            name="audit-domain-mismatches",
            actual=(
                receipt.audit_domain_mismatches
            ),
            expected=0,
        )

        post_integrity = (
            evaluate_audit_integrity(
                audit_path=audit_path,
                policy_path=policy_path,
            )
        )

        add_check(
            receipt,
            name="post-activation-audit-integrity",
            actual=post_integrity.decision,
            expected=AUDIT_INTEGRITY_PASS,
        )

        add_check(
            receipt,
            name="post-activation-invalid-audit-events",
            actual=post_integrity.invalid_events,
            expected=0,
        )

        final_config = load_json(
            config_path
        )

        add_check(
            receipt,
            name="final-kill-switch",
            actual=final_config.get(
                "enabled"
            ),
            expected=True,
        )

        if receipt.failures:
            raise RuntimeError(
                "activation validation failed"
            )

        activation_succeeded = True
        receipt.decision = (
            "PERMANENT_ACTIVATION_SUCCEEDED"
        )
        receipt.enforcement_enabled_after = True

    except Exception as exc:
        write_json_atomic(
            config_path,
            json.loads(
                original_config.decode(
                    "utf-8"
                )
            ),
        )

        receipt.rollback_performed = True
        receipt.decision = (
            "PERMANENT_ACTIVATION_ROLLED_BACK"
        )

        restored = load_json(
            config_path
        )

        receipt.enforcement_enabled_after = bool(
            restored.get(
                "enabled",
                False,
            )
        )

        receipt.failures.append(
            f"operation: {type(exc).__name__}: {exc}"
        )

    finally:
        receipt.completed_at_utc = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        write_json_atomic(
            receipt_path,
            receipt.to_dict(),
        )

    print(
        "Decision                  :",
        receipt.decision,
    )

    print(
        "Enforcement before        :",
        receipt.enforcement_enabled_before,
    )

    print(
        "Enforcement after         :",
        receipt.enforcement_enabled_after,
    )

    print(
        "Rollback performed        :",
        receipt.rollback_performed,
    )

    print(
        "Changed domains           :",
        receipt.changed_domains,
    )

    print(
        "Expected changes          :",
        receipt.expected_changes,
    )

    print(
        "Unexpected changes        :",
        receipt.unexpected_changes,
    )

    print(
        "Missed targets            :",
        receipt.missed_targets,
    )

    print(
        "Non-filter changes        :",
        receipt.non_filter_changes,
    )

    print(
        "New audit events          :",
        receipt.new_audit_events,
    )

    print(
        "Invalid new audit events  :",
        receipt.invalid_new_audit_events,
    )

    print(
        "Audit domain mismatches   :",
        receipt.audit_domain_mismatches,
    )

    print(
        "Checks failed             :",
        len(receipt.failures),
    )

    print(
        "Receipt                   :",
        receipt_path,
    )

    if activation_succeeded:
        return 0

    for failure in receipt.failures:
        print(" -", failure)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
