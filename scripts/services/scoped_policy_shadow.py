"""Persistent scoped-promotion policy loading and shadow execution.

This module never changes Analyzer output, configuration, confidence,
recommendations, database rows, or production files.
"""

from __future__ import annotations

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
from scripts.services.scoped_promotion_policy import (
    ScopedPromotionPolicy,
    apply_scoped_policy,
    domain_matches_suffix,
    find_matching_policy,
    load_json_object,
    load_suggestion_rows,
    normalize_domain,
)


POLICY_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ShadowPolicyChange:
    domain: str
    seen: int
    expected_target: bool
    matched_suffix: str
    policy_category: str
    before: SimulatedDecision
    after: SimulatedDecision
    changed_fields: tuple[str, ...]

    @property
    def unexpected(self) -> bool:
        return not self.expected_target

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "seen": self.seen,
            "expected_target": (
                self.expected_target
            ),
            "unexpected": self.unexpected,
            "matched_suffix": (
                self.matched_suffix
            ),
            "policy_category": (
                self.policy_category
            ),
            "changed_fields": list(
                self.changed_fields
            ),
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
        }


@dataclass(frozen=True)
class ScopedPolicyShadowSummary:
    domains_evaluated: int
    policies_loaded: int
    authorized_suffixes: int
    expected_targets: int
    shadow_matches: int
    expected_matches: int
    unexpected_matches: int
    missed_expected_matches: int
    filter_only_changes: int
    confidence_changes: int
    recommendation_changes: int
    baseline_drift: int
    production_changes: int
    policies: tuple[
        ScopedPromotionPolicy,
        ...
    ] = field(default_factory=tuple)
    changes: tuple[
        ShadowPolicyChange,
        ...
    ] = field(default_factory=tuple)
    missed_domains: tuple[str, ...] = field(
        default_factory=tuple
    )
    baseline_drift_domains: tuple[
        str,
        ...
    ] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domains_evaluated": (
                self.domains_evaluated
            ),
            "policies_loaded": (
                self.policies_loaded
            ),
            "authorized_suffixes": (
                self.authorized_suffixes
            ),
            "expected_targets": (
                self.expected_targets
            ),
            "shadow_matches": (
                self.shadow_matches
            ),
            "expected_matches": (
                self.expected_matches
            ),
            "unexpected_matches": (
                self.unexpected_matches
            ),
            "missed_expected_matches": (
                self.missed_expected_matches
            ),
            "filter_only_changes": (
                self.filter_only_changes
            ),
            "confidence_changes": (
                self.confidence_changes
            ),
            "recommendation_changes": (
                self.recommendation_changes
            ),
            "baseline_drift": (
                self.baseline_drift
            ),
            "baseline_drift_domains": list(
                self.baseline_drift_domains
            ),
            "production_changes": (
                self.production_changes
            ),
            "missed_domains": list(
                self.missed_domains
            ),
            "policies": [
                policy.to_dict()
                for policy in self.policies
            ],
            "changes": [
                change.to_dict()
                for change in self.changes
            ],
        }


def _normalized_suffixes(
    value: object,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(
            "authorized_suffixes must be a list"
        )

    suffixes: list[str] = []

    for item in value:
        suffix = normalize_domain(item)

        if not suffix:
            raise ValueError(
                "authorized suffix cannot be empty"
            )

        if "*" in suffix:
            raise ValueError(
                "wildcards are not allowed in authorized suffixes"
            )

        if "." not in suffix:
            raise ValueError(
                "authorized suffix must contain a dot"
            )

        suffixes.append(suffix)

    if not suffixes:
        raise ValueError(
            "policy requires at least one authorized suffix"
        )

    if len(suffixes) != len(set(suffixes)):
        raise ValueError(
            "duplicate authorized suffix in policy"
        )

    return tuple(sorted(suffixes))


def validate_policy_overlaps(
    policies: Iterable[
        ScopedPromotionPolicy
    ],
) -> None:
    """Reject overlapping policies that could match one decision twice."""

    items = tuple(policies)

    for index, left in enumerate(items):
        for right in items[
            index + 1:
        ]:
            if (
                left.category.casefold()
                != right.category.casefold()
                or left.current_filter.casefold()
                != right.current_filter.casefold()
            ):
                continue

            for left_suffix in (
                left.authorized_suffixes
            ):
                for right_suffix in (
                    right.authorized_suffixes
                ):
                    if (
                        domain_matches_suffix(
                            left_suffix,
                            right_suffix,
                        )
                        or domain_matches_suffix(
                            right_suffix,
                            left_suffix,
                        )
                    ):
                        raise ValueError(
                            "overlapping scoped policies: "
                            f"{left_suffix} / "
                            f"{right_suffix}"
                        )


def load_scoped_policy_artifact(
    path: Path,
) -> tuple[ScopedPromotionPolicy, ...]:
    payload = load_json_object(path)

    version = payload.get("version")

    if version != POLICY_SCHEMA_VERSION:
        raise ValueError(
            "unsupported scoped policy version: "
            f"{version}"
        )

    mode = str(
        payload.get("mode", "")
        or ""
    ).strip().lower()

    if mode != "shadow":
        raise ValueError(
            "scoped policy artifact must use shadow mode"
        )

    rows = payload.get("policies", [])

    if not isinstance(rows, list):
        raise ValueError(
            "policies must be a list"
        )

    if not rows:
        raise ValueError(
            "scoped policy artifact is empty"
        )

    policies: list[
        ScopedPromotionPolicy
    ] = []

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(
                "policy entry must be an object"
            )

        category = str(
            row.get("category", "")
            or ""
        ).strip()

        current_filter = str(
            row.get(
                "current_filter",
                "",
            )
            or ""
        ).strip()

        proposed_filter = str(
            row.get(
                "proposed_filter",
                "",
            )
            or ""
        ).strip()

        if not all(
            (
                category,
                current_filter,
                proposed_filter,
            )
        ):
            raise ValueError(
                "policy is missing required fields"
            )

        if (
            current_filter.casefold()
            == proposed_filter.casefold()
        ):
            raise ValueError(
                "policy does not change the filter"
            )

        policies.append(
            ScopedPromotionPolicy(
                category=category,
                current_filter=(
                    current_filter
                ),
                proposed_filter=(
                    proposed_filter
                ),
                authorized_suffixes=(
                    _normalized_suffixes(
                        row.get(
                            "authorized_suffixes"
                        )
                    )
                ),
                source_domains=(),
            )
        )

    validate_policy_overlaps(policies)

    return tuple(
        sorted(
            policies,
            key=lambda policy: (
                policy.category.casefold(),
                policy.current_filter.casefold(),
                policy.proposed_filter.casefold(),
            ),
        )
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
            and bool(
                row.get("eligible", False)
            )
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


def evaluate_shadow_decision(
    *,
    domain: str,
    seen: int,
    control: SimulatedDecision,
    policies: Iterable[
        ScopedPromotionPolicy
    ],
    target_domains: set[str],
) -> ShadowPolicyChange | None:
    policy, suffix = find_matching_policy(
        domain=domain,
        decision=control,
        policies=policies,
    )

    if policy is None:
        return None

    shadow = apply_scoped_policy(
        control,
        policy,
    )

    fields = changed_fields(
        control,
        shadow,
    )

    if not fields:
        return None

    return ShadowPolicyChange(
        domain=normalize_domain(domain),
        seen=seen,
        expected_target=(
            normalize_domain(domain)
            in target_domains
        ),
        matched_suffix=suffix,
        policy_category=policy.category,
        before=control,
        after=shadow,
        changed_fields=fields,
    )


def run_scoped_policy_shadow(
    *,
    suggestions_path: Path,
    gate_path: Path,
    policy_path: Path,
    analyzer_config_path: Path = Path(
        "config/analyzer.json"
    ),
    database_rows: list[
        dict[str, Any]
    ] | None = None,
    limit: int | None = None,
) -> ScopedPolicyShadowSummary:
    rows = load_suggestion_rows(
        suggestions_path
    )

    if limit is not None:
        rows = rows[: max(limit, 0)]

    policies = load_scoped_policy_artifact(
        policy_path
    )

    gate_payload = load_json_object(
        gate_path
    )

    target_domains = eligible_target_domains(
        gate_payload
    )

    effective_database_rows = (
        load_database()
        if database_rows is None
        else database_rows
    )

    changes: list[
        ShadowPolicyChange
    ] = []

    drift_domains: list[str] = []

    for row in rows:
        domain = normalize_domain(
            row.get("domain")
        )

        result = analyze_domain(
            domain,
            config_path=(
                analyzer_config_path
            ),
            rows=effective_database_rows,
        )

        control = decision_from_result(
            result
        )

        baseline = SimulatedDecision(
            vendor=str(
                row.get(
                    "vendor",
                    "Unknown",
                )
            ),
            category=str(
                row.get(
                    "category",
                    "Unknown",
                )
            ),
            filter_name=str(
                row.get(
                    "filter",
                    "unknown",
                )
            ),
            confidence=int(
                float(
                    row.get(
                        "confidence",
                        0,
                    )
                    or 0
                )
            ),
            recommendation=str(
                row.get(
                    "recommendation",
                    "unknown",
                )
            ),
        )

        if changed_fields(
            baseline,
            control,
        ):
            drift_domains.append(domain)

        change = evaluate_shadow_decision(
            domain=domain,
            seen=int(
                row.get("seen", 0)
                or 0
            ),
            control=control,
            policies=policies,
            target_domains=target_domains,
        )

        if change is not None:
            changes.append(change)

    matched_expected = {
        change.domain
        for change in changes
        if change.expected_target
    }

    missed = tuple(
        sorted(
            target_domains
            - matched_expected
        )
    )

    return ScopedPolicyShadowSummary(
        domains_evaluated=len(rows),
        policies_loaded=len(policies),
        authorized_suffixes=sum(
            len(
                policy.authorized_suffixes
            )
            for policy in policies
        ),
        expected_targets=len(
            target_domains
        ),
        shadow_matches=len(changes),
        expected_matches=sum(
            change.expected_target
            for change in changes
        ),
        unexpected_matches=sum(
            change.unexpected
            for change in changes
        ),
        missed_expected_matches=len(
            missed
        ),
        filter_only_changes=sum(
            change.changed_fields
            == ("filter",)
            for change in changes
        ),
        confidence_changes=sum(
            change.before.confidence
            != change.after.confidence
            for change in changes
        ),
        recommendation_changes=sum(
            change.before.recommendation
            != change.after.recommendation
            for change in changes
        ),
        baseline_drift=len(
            set(drift_domains)
        ),
        production_changes=0,
        policies=policies,
        changes=tuple(
            sorted(
                changes,
                key=lambda change: (
                    not change.expected_target,
                    -change.seen,
                    change.domain,
                ),
            )
        ),
        missed_domains=missed,
        baseline_drift_domains=tuple(
            sorted(
                set(drift_domains)
            )
        ),
    )


def build_scoped_policy_shadow_report(
    summary: ScopedPolicyShadowSummary,
) -> str:
    lines = [
        "5ibr Scoped Policy Enforcement Shadow",
        "=====================================",
        "",
        (
            "Domains evaluated        : "
            f"{summary.domains_evaluated}"
        ),
        (
            "Policies loaded          : "
            f"{summary.policies_loaded}"
        ),
        (
            "Authorized suffixes      : "
            f"{summary.authorized_suffixes}"
        ),
        (
            "Expected targets         : "
            f"{summary.expected_targets}"
        ),
        (
            "Shadow matches           : "
            f"{summary.shadow_matches}"
        ),
        (
            "Expected matches         : "
            f"{summary.expected_matches}"
        ),
        (
            "Unexpected matches       : "
            f"{summary.unexpected_matches}"
        ),
        (
            "Missed expected matches  : "
            f"{summary.missed_expected_matches}"
        ),
        (
            "Filter-only changes      : "
            f"{summary.filter_only_changes}"
        ),
        (
            "Confidence changes       : "
            f"{summary.confidence_changes}"
        ),
        (
            "Recommendation changes   : "
            f"{summary.recommendation_changes}"
        ),
        (
            "Baseline drift           : "
            f"{summary.baseline_drift}"
        ),
        (
            "Production changes       : "
            f"{summary.production_changes}"
        ),
        "",
        "Loaded policies:",
    ]

    for policy in summary.policies:
        lines.append(
            f"  {policy.category}: "
            f"{policy.current_filter} "
            f"-> {policy.proposed_filter}"
        )

        for suffix in (
            policy.authorized_suffixes
        ):
            lines.append(
                f"    suffix: {suffix}"
            )

    lines.extend(
        [
            "",
            "Shadow matches:",
            "",
        ]
    )

    if not summary.changes:
        lines.append("  None")
    else:
        for change in summary.changes:
            lines.append(
                f"  {change.domain}"
            )
            lines.append(
                f"    expected target : "
                f"{change.expected_target}"
            )
            lines.append(
                f"    matched suffix  : "
                f"{change.matched_suffix}"
            )
            lines.append(
                f"    category        : "
                f"{change.policy_category}"
            )
            lines.append(
                f"    filter          : "
                f"{change.before.filter_name} "
                f"-> {change.after.filter_name}"
            )
            lines.append(
                f"    confidence      : "
                f"{change.before.confidence} "
                f"-> {change.after.confidence}"
            )
            lines.append(
                f"    recommendation  : "
                f"{change.before.recommendation} "
                f"-> {change.after.recommendation}"
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
