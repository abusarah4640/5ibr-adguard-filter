"""Controlled scoped-policy enforcement with a fail-closed kill switch.

Production behavior changes only when all conditions pass:

- enforcement config enabled
- readiness decision is PROMOTION_READY
- readiness report has zero failed checks
- readiness report has zero blockers
- policy SHA-256 matches enforcement config
- persistent policy artifact validates
- domain/category/current-filter match an authorized scoped policy

The service itself does not modify any files.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from scripts.services.analyzer_service import (
    analyze_domain,
)
from scripts.services.controlled_promotion_simulation import (
    SimulatedDecision,
    changed_fields,
    decision_from_result,
)
from scripts.services.database_service import (
    load_database,
)
from scripts.services.scoped_policy_shadow import (
    load_scoped_policy_artifact,
)
from scripts.services.scoped_promotion_policy import (
    ScopedPromotionPolicy,
    apply_scoped_policy,
    find_matching_policy,
    load_suggestion_rows,
    normalize_domain,
)


ENFORCEMENT_SCHEMA_VERSION = 1
READY = "PROMOTION_READY"


@dataclass(frozen=True)
class EnforcementConfiguration:
    enabled: bool
    required_readiness_decision: str
    policy_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": ENFORCEMENT_SCHEMA_VERSION,
            "enabled": self.enabled,
            "required_readiness_decision": (
                self.required_readiness_decision
            ),
            "policy_sha256": self.policy_sha256,
        }


@dataclass(frozen=True)
class EnforcementAuthorization:
    authorized: bool
    reasons: tuple[str, ...]
    policy_sha256: str
    configured_policy_sha256: str
    readiness_decision: str
    enabled: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorized": self.authorized,
            "reasons": list(self.reasons),
            "policy_sha256": self.policy_sha256,
            "configured_policy_sha256": (
                self.configured_policy_sha256
            ),
            "readiness_decision": (
                self.readiness_decision
            ),
            "enabled": self.enabled,
        }


@dataclass(frozen=True)
class EnforcedDecision:
    domain: str
    applied: bool
    matched_suffix: str
    before: SimulatedDecision
    after: SimulatedDecision
    changed_fields: tuple[str, ...]
    reasons: tuple[str, ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "applied": self.applied,
            "matched_suffix": self.matched_suffix,
            "changed_fields": list(
                self.changed_fields
            ),
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class EnforcementSimulationSummary:
    domains_evaluated: int
    expected_targets: int
    authorization: EnforcementAuthorization
    enforcement_enabled: bool
    applied_changes: int
    expected_changes: int
    unexpected_changes: int
    missed_expected_targets: int
    filter_only_changes: int
    vendor_changes: int
    category_changes: int
    confidence_changes: int
    recommendation_changes: int
    production_files_modified: int
    changes: tuple[EnforcedDecision, ...]
    missed_domains: tuple[str, ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "domains_evaluated": self.domains_evaluated,
            "expected_targets": self.expected_targets,
            "authorization": self.authorization.to_dict(),
            "enforcement_enabled": self.enforcement_enabled,
            "applied_changes": self.applied_changes,
            "expected_changes": self.expected_changes,
            "unexpected_changes": self.unexpected_changes,
            "missed_expected_targets": (
                self.missed_expected_targets
            ),
            "filter_only_changes": (
                self.filter_only_changes
            ),
            "vendor_changes": self.vendor_changes,
            "category_changes": self.category_changes,
            "confidence_changes": self.confidence_changes,
            "recommendation_changes": (
                self.recommendation_changes
            ),
            "production_files_modified": (
                self.production_files_modified
            ),
            "missed_domains": list(self.missed_domains),
            "changes": [
                change.to_dict()
                for change in self.changes
            ],
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


def _valid_sha256(value: str) -> bool:
    return (
        len(value) == 64
        and all(
            character in "0123456789abcdef"
            for character in value
        )
    )


def load_enforcement_configuration(
    path: Path,
) -> EnforcementConfiguration:
    payload = load_json_object(path)

    if (
        payload.get("version")
        != ENFORCEMENT_SCHEMA_VERSION
    ):
        raise ValueError(
            "unsupported enforcement configuration version"
        )

    enabled = payload.get("enabled")

    if not isinstance(enabled, bool):
        raise ValueError(
            "enforcement enabled must be boolean"
        )

    required_decision = str(
        payload.get(
            "required_readiness_decision",
            "",
        )
        or ""
    ).strip()

    if required_decision != READY:
        raise ValueError(
            "required readiness decision must be PROMOTION_READY"
        )

    policy_sha = str(
        payload.get("policy_sha256", "")
        or ""
    ).strip().lower()

    if not _valid_sha256(policy_sha):
        raise ValueError(
            "invalid enforcement policy SHA-256"
        )

    return EnforcementConfiguration(
        enabled=enabled,
        required_readiness_decision=(
            required_decision
        ),
        policy_sha256=policy_sha,
    )


def authorize_enforcement(
    *,
    configuration: EnforcementConfiguration,
    readiness_payload: dict[str, Any],
    policy_path: Path,
) -> EnforcementAuthorization:
    reasons: list[str] = []

    readiness_decision = str(
        readiness_payload.get("decision", "")
        or ""
    ).strip()

    checks_failed = int(
        readiness_payload.get(
            "checks_failed",
            0,
        )
        or 0
    )

    blockers = readiness_payload.get(
        "blocking_reasons",
        [],
    )

    if not isinstance(blockers, list):
        blockers = ["invalid blocking reasons payload"]

    actual_sha = sha256_file(policy_path)

    if not configuration.enabled:
        reasons.append(
            "enforcement kill switch is disabled"
        )

    if (
        readiness_decision
        != configuration.required_readiness_decision
    ):
        reasons.append(
            "readiness decision does not authorize enforcement"
        )

    if checks_failed != 0:
        reasons.append(
            "readiness report contains failed checks"
        )

    if blockers:
        reasons.append(
            "readiness report contains blocking reasons"
        )

    if actual_sha != configuration.policy_sha256:
        reasons.append(
            "policy SHA-256 does not match enforcement configuration"
        )

    return EnforcementAuthorization(
        authorized=not reasons,
        reasons=tuple(reasons),
        policy_sha256=actual_sha,
        configured_policy_sha256=(
            configuration.policy_sha256
        ),
        readiness_decision=readiness_decision,
        enabled=configuration.enabled,
    )


def enforce_scoped_decision(
    *,
    domain: str,
    control: SimulatedDecision,
    policies: Iterable[
        ScopedPromotionPolicy
    ],
    authorization: EnforcementAuthorization,
) -> EnforcedDecision:
    normalized_domain = normalize_domain(
        domain
    )

    if not authorization.authorized:
        return EnforcedDecision(
            domain=normalized_domain,
            applied=False,
            matched_suffix="",
            before=control,
            after=control,
            changed_fields=(),
            reasons=authorization.reasons,
        )

    policy, suffix = find_matching_policy(
        domain=normalized_domain,
        decision=control,
        policies=policies,
    )

    if policy is None:
        return EnforcedDecision(
            domain=normalized_domain,
            applied=False,
            matched_suffix="",
            before=control,
            after=control,
            changed_fields=(),
            reasons=(
                "no authorized scoped policy matched",
            ),
        )

    enforced = apply_scoped_policy(
        control,
        policy,
    )

    fields = changed_fields(
        control,
        enforced,
    )

    return EnforcedDecision(
        domain=normalized_domain,
        applied=bool(fields),
        matched_suffix=suffix,
        before=control,
        after=enforced,
        changed_fields=fields,
        reasons=(
            "authorized scoped policy applied",
        ),
    )


def eligible_target_domains(
    gate_payload: dict[str, Any],
) -> set[str]:
    rows = gate_payload.get("results", [])

    if not isinstance(rows, list):
        raise ValueError(
            "candidate gate results must be a list"
        )

    return {
        normalize_domain(
            row.get("domain")
        )
        for row in rows
        if (
            isinstance(row, dict)
            and bool(row.get("eligible", False))
            and row.get("decision")
            == "eligible-for-controlled-promotion"
            and not bool(
                row.get(
                    "production_changed",
                    False,
                )
            )
            and normalize_domain(
                row.get("domain")
            )
        )
    }


def run_enforcement_simulation(
    *,
    suggestions_path: Path,
    gate_path: Path,
    policy_path: Path,
    readiness_path: Path,
    enforcement_config_path: Path,
    analyzer_config_path: Path = Path(
        "config/analyzer.json"
    ),
    database_rows: list[
        dict[str, Any]
    ] | None = None,
    limit: int | None = None,
) -> EnforcementSimulationSummary:
    rows = load_suggestion_rows(
        suggestions_path
    )

    if limit is not None:
        rows = rows[: max(limit, 0)]

    gate_payload = load_json_object(
        gate_path
    )

    readiness_payload = load_json_object(
        readiness_path
    )

    configuration = (
        load_enforcement_configuration(
            enforcement_config_path
        )
    )

    policies = load_scoped_policy_artifact(
        policy_path
    )

    authorization = authorize_enforcement(
        configuration=configuration,
        readiness_payload=readiness_payload,
        policy_path=policy_path,
    )

    targets = eligible_target_domains(
        gate_payload
    )

    effective_database_rows = (
        load_database()
        if database_rows is None
        else database_rows
    )

    results: list[EnforcedDecision] = []

    for row in rows:
        domain = normalize_domain(
            row.get("domain")
        )

        analysis = analyze_domain(
            domain,
            config_path=analyzer_config_path,
            rows=effective_database_rows,
        )

        control = decision_from_result(
            analysis
        )

        result = enforce_scoped_decision(
            domain=domain,
            control=control,
            policies=policies,
            authorization=authorization,
        )

        if result.applied:
            results.append(result)

    applied_domains = {
        result.domain
        for result in results
    }

    expected_changed = (
        applied_domains & targets
    )

    unexpected_changed = (
        applied_domains - targets
    )

    missed = tuple(
        sorted(
            targets - applied_domains
        )
    )

    return EnforcementSimulationSummary(
        domains_evaluated=len(rows),
        expected_targets=len(targets),
        authorization=authorization,
        enforcement_enabled=(
            configuration.enabled
        ),
        applied_changes=len(results),
        expected_changes=len(
            expected_changed
        ),
        unexpected_changes=len(
            unexpected_changed
        ),
        missed_expected_targets=len(
            missed
        ),
        filter_only_changes=sum(
            result.changed_fields
            == ("filter",)
            for result in results
        ),
        vendor_changes=sum(
            "vendor" in result.changed_fields
            for result in results
        ),
        category_changes=sum(
            "category" in result.changed_fields
            for result in results
        ),
        confidence_changes=sum(
            "confidence" in result.changed_fields
            for result in results
        ),
        recommendation_changes=sum(
            "recommendation"
            in result.changed_fields
            for result in results
        ),
        production_files_modified=0,
        changes=tuple(
            sorted(
                results,
                key=lambda result: (
                    result.domain
                    not in targets,
                    result.domain,
                ),
            )
        ),
        missed_domains=missed,
    )


def build_enforcement_report(
    summary: EnforcementSimulationSummary,
) -> str:
    lines = [
        "5ibr Controlled Production Enforcement",
        "======================================",
        "",
        (
            "Enforcement enabled       : "
            f"{summary.enforcement_enabled}"
        ),
        (
            "Enforcement authorized    : "
            f"{summary.authorization.authorized}"
        ),
        (
            "Readiness decision        : "
            f"{summary.authorization.readiness_decision}"
        ),
        (
            "Domains evaluated         : "
            f"{summary.domains_evaluated}"
        ),
        (
            "Expected targets          : "
            f"{summary.expected_targets}"
        ),
        (
            "Applied changes           : "
            f"{summary.applied_changes}"
        ),
        (
            "Expected changes          : "
            f"{summary.expected_changes}"
        ),
        (
            "Unexpected changes        : "
            f"{summary.unexpected_changes}"
        ),
        (
            "Missed expected targets   : "
            f"{summary.missed_expected_targets}"
        ),
        (
            "Filter-only changes       : "
            f"{summary.filter_only_changes}"
        ),
        (
            "Vendor changes            : "
            f"{summary.vendor_changes}"
        ),
        (
            "Category changes          : "
            f"{summary.category_changes}"
        ),
        (
            "Confidence changes        : "
            f"{summary.confidence_changes}"
        ),
        (
            "Recommendation changes    : "
            f"{summary.recommendation_changes}"
        ),
        (
            "Production files modified : "
            f"{summary.production_files_modified}"
        ),
        "",
        "Authorization:",
    ]

    lines.append(
        "  policy SHA-256:"
    )
    lines.append(
        f"    actual     : "
        f"{summary.authorization.policy_sha256}"
    )
    lines.append(
        f"    configured : "
        f"{summary.authorization.configured_policy_sha256}"
    )

    if summary.authorization.reasons:
        for reason in (
            summary.authorization.reasons
        ):
            lines.append(
                f"  reason: {reason}"
            )
    else:
        lines.append(
            "  reason: all authorization checks passed"
        )

    lines.extend(
        [
            "",
            "Applied decisions:",
            "",
        ]
    )

    if not summary.changes:
        lines.append("  None")
    else:
        for result in summary.changes:
            lines.append(
                f"  {result.domain}"
            )
            lines.append(
                f"    suffix         : "
                f"{result.matched_suffix}"
            )
            lines.append(
                f"    changed fields : "
                f"{', '.join(result.changed_fields)}"
            )
            lines.append(
                f"    filter         : "
                f"{result.before.filter_name} "
                f"-> {result.after.filter_name}"
            )
            lines.append(
                f"    confidence     : "
                f"{result.before.confidence} "
                f"-> {result.after.confidence}"
            )
            lines.append(
                f"    recommendation : "
                f"{result.before.recommendation} "
                f"-> {result.after.recommendation}"
            )
            lines.append("")

    if summary.missed_domains:
        lines.extend(
            [
                "Missed expected domains:",
                "",
            ]
        )

        for domain in summary.missed_domains:
            lines.append(
                f"  {domain}"
            )

    return "\n".join(lines).rstrip()
