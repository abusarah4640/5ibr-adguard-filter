"""Explicitly scoped semantic promotion policies.

Policies are built only from Stage 50 candidates that passed the safety
gate. Matching uses explicit authorized domain suffixes and never
modifies Analyzer configuration or production data.
"""

from __future__ import annotations

import json
from collections import Counter
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
from scripts.services.semantic_filter_mapping import (
    normalize_mapping_value,
)


@dataclass(frozen=True)
class ScopedPromotionPolicy:
    category: str
    current_filter: str
    proposed_filter: str
    authorized_suffixes: tuple[str, ...]
    source_domains: tuple[str, ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "current_filter": self.current_filter,
            "proposed_filter": self.proposed_filter,
            "authorized_suffixes": list(
                self.authorized_suffixes
            ),
            "source_domains": list(
                self.source_domains
            ),
        }


@dataclass(frozen=True)
class ScopedPromotionChange:
    domain: str
    seen: int
    target_domain: bool
    matched_suffix: str
    policy_category: str
    before: SimulatedDecision
    after: SimulatedDecision
    changed_fields: tuple[str, ...]

    @property
    def collateral(self) -> bool:
        return not self.target_domain

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "seen": self.seen,
            "target_domain": self.target_domain,
            "collateral": self.collateral,
            "matched_suffix": self.matched_suffix,
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
class ScopedPromotionSummary:
    domains_evaluated: int
    target_domains: int
    policies_created: int
    authorized_suffixes: int
    baseline_drift: int
    changed_domains: int
    intended_changes: int
    collateral_changes: int
    unchanged_target_domains: int
    confidence_changes: int
    recommendation_changes: int
    production_changes: int
    policies: tuple[ScopedPromotionPolicy, ...]
    changes: tuple[ScopedPromotionChange, ...]
    baseline_drift_domains: tuple[str, ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "domains_evaluated": (
                self.domains_evaluated
            ),
            "target_domains": self.target_domains,
            "policies_created": (
                self.policies_created
            ),
            "authorized_suffixes": (
                self.authorized_suffixes
            ),
            "baseline_drift": self.baseline_drift,
            "baseline_drift_domains": list(
                self.baseline_drift_domains
            ),
            "changed_domains": self.changed_domains,
            "intended_changes": (
                self.intended_changes
            ),
            "collateral_changes": (
                self.collateral_changes
            ),
            "unchanged_target_domains": (
                self.unchanged_target_domains
            ),
            "confidence_changes": (
                self.confidence_changes
            ),
            "recommendation_changes": (
                self.recommendation_changes
            ),
            "production_changes": (
                self.production_changes
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


def normalize_domain(value: object) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .strip(".")
    )


def domain_matches_suffix(
    domain: str,
    suffix: str,
) -> bool:
    normalized_domain = normalize_domain(domain)
    normalized_suffix = normalize_domain(suffix)

    if not normalized_domain or not normalized_suffix:
        return False

    return (
        normalized_domain == normalized_suffix
        or normalized_domain.endswith(
            f".{normalized_suffix}"
        )
    )


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
            f"invalid suggestions file: {path}"
        )

    return [
        row
        for row in rows
        if (
            isinstance(row, dict)
            and normalize_domain(
                row.get("domain")
            )
        )
    ]


def eligible_gate_rows(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = payload.get("results", [])

    if not isinstance(rows, list):
        raise ValueError(
            "candidate gate results must be a list"
        )

    return [
        row
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
        )
    ]


def build_scoped_policies(
    eligible_rows: Iterable[
        dict[str, Any]
    ],
) -> tuple[ScopedPromotionPolicy, ...]:
    """Build policies grouped by semantic transition.

    Authorized suffixes come from the Stage 50 family field and are
    treated as explicit allow-list suffixes.
    """

    grouped: dict[
        tuple[str, str, str],
        dict[str, set[str]],
    ] = {}

    for row in eligible_rows:
        current = row.get("current", {})

        if not isinstance(current, dict):
            current = {}

        category = str(
            current.get("category", "")
            or ""
        ).strip()

        current_filter = str(
            current.get("filter", "")
            or ""
        ).strip()

        proposed_filter = str(
            row.get("proposed_filter", "")
            or ""
        ).strip()

        suffix = normalize_domain(
            row.get("family")
        )

        domain = normalize_domain(
            row.get("domain")
        )

        if not all(
            (
                category,
                current_filter,
                proposed_filter,
                suffix,
                domain,
            )
        ):
            raise ValueError(
                "eligible gate row is incomplete"
            )

        key = (
            normalize_mapping_value(category),
            normalize_mapping_value(
                current_filter
            ),
            normalize_mapping_value(
                proposed_filter
            ),
        )

        bucket = grouped.setdefault(
            key,
            {
                "categories": set(),
                "current_filters": set(),
                "proposed_filters": set(),
                "suffixes": set(),
                "domains": set(),
            },
        )

        bucket["categories"].add(category)
        bucket["current_filters"].add(
            current_filter
        )
        bucket["proposed_filters"].add(
            proposed_filter
        )
        bucket["suffixes"].add(suffix)
        bucket["domains"].add(domain)

    policies: list[ScopedPromotionPolicy] = []

    for bucket in grouped.values():
        if (
            len(bucket["categories"]) != 1
            or len(
                bucket["current_filters"]
            )
            != 1
            or len(
                bucket["proposed_filters"]
            )
            != 1
        ):
            raise ValueError(
                "inconsistent scoped promotion group"
            )

        policies.append(
            ScopedPromotionPolicy(
                category=next(
                    iter(
                        bucket["categories"]
                    )
                ),
                current_filter=next(
                    iter(
                        bucket[
                            "current_filters"
                        ]
                    )
                ),
                proposed_filter=next(
                    iter(
                        bucket[
                            "proposed_filters"
                        ]
                    )
                ),
                authorized_suffixes=tuple(
                    sorted(
                        bucket["suffixes"]
                    )
                ),
                source_domains=tuple(
                    sorted(
                        bucket["domains"]
                    )
                ),
            )
        )

    return tuple(
        sorted(
            policies,
            key=lambda item: (
                item.category.casefold(),
                item.proposed_filter.casefold(),
            ),
        )
    )


def find_matching_policy(
    *,
    domain: str,
    decision: SimulatedDecision,
    policies: Iterable[
        ScopedPromotionPolicy
    ],
) -> tuple[
    ScopedPromotionPolicy | None,
    str,
]:
    matches: list[
        tuple[
            ScopedPromotionPolicy,
            str,
        ]
    ] = []

    for policy in policies:
        if (
            normalize_mapping_value(
                decision.category
            )
            != normalize_mapping_value(
                policy.category
            )
        ):
            continue

        if (
            normalize_mapping_value(
                decision.filter_name
            )
            != normalize_mapping_value(
                policy.current_filter
            )
        ):
            continue

        for suffix in (
            policy.authorized_suffixes
        ):
            if domain_matches_suffix(
                domain,
                suffix,
            ):
                matches.append(
                    (
                        policy,
                        suffix,
                    )
                )

    if len(matches) > 1:
        raise ValueError(
            f"multiple scoped policies matched: {domain}"
        )

    if not matches:
        return None, ""

    return matches[0]


def apply_scoped_policy(
    decision: SimulatedDecision,
    policy: ScopedPromotionPolicy,
) -> SimulatedDecision:
    """Return a preview decision with only the filter replaced."""

    return SimulatedDecision(
        vendor=decision.vendor,
        category=decision.category,
        filter_name=policy.proposed_filter,
        confidence=decision.confidence,
        recommendation=(
            decision.recommendation
        ),
    )


def run_scoped_promotion_simulation(
    *,
    suggestions_path: Path,
    gate_path: Path,
    config_path: Path = Path(
        "config/analyzer.json"
    ),
    database_rows: list[
        dict[str, Any]
    ] | None = None,
    limit: int | None = None,
) -> ScopedPromotionSummary:
    rows = load_suggestion_rows(
        suggestions_path
    )

    if limit is not None:
        rows = rows[: max(limit, 0)]

    gate_payload = load_json_object(
        gate_path
    )

    eligible = eligible_gate_rows(
        gate_payload
    )

    policies = build_scoped_policies(
        eligible
    )

    target_domains = {
        normalize_domain(
            row.get("domain")
        )
        for row in eligible
    }

    effective_database_rows = (
        load_database()
        if database_rows is None
        else database_rows
    )

    baseline_drift_domains: list[str] = []
    changes: list[
        ScopedPromotionChange
    ] = []

    for row in rows:
        domain = normalize_domain(
            row.get("domain")
        )

        result = analyze_domain(
            domain,
            config_path=config_path,
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
            baseline_drift_domains.append(
                domain
            )

        policy, suffix = (
            find_matching_policy(
                domain=domain,
                decision=control,
                policies=policies,
            )
        )

        if policy is None:
            continue

        simulated = apply_scoped_policy(
            control,
            policy,
        )

        fields = changed_fields(
            control,
            simulated,
        )

        if not fields:
            continue

        changes.append(
            ScopedPromotionChange(
                domain=domain,
                seen=int(
                    row.get("seen", 0)
                    or 0
                ),
                target_domain=(
                    domain in target_domains
                ),
                matched_suffix=suffix,
                policy_category=(
                    policy.category
                ),
                before=control,
                after=simulated,
                changed_fields=fields,
            )
        )

    changed_target_domains = {
        change.domain
        for change in changes
        if change.target_domain
    }

    return ScopedPromotionSummary(
        domains_evaluated=len(rows),
        target_domains=len(
            target_domains
        ),
        policies_created=len(policies),
        authorized_suffixes=sum(
            len(
                policy.authorized_suffixes
            )
            for policy in policies
        ),
        baseline_drift=len(
            baseline_drift_domains
        ),
        changed_domains=len(changes),
        intended_changes=sum(
            change.target_domain
            for change in changes
        ),
        collateral_changes=sum(
            change.collateral
            for change in changes
        ),
        unchanged_target_domains=len(
            target_domains
            - changed_target_domains
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
        production_changes=0,
        policies=policies,
        changes=tuple(
            sorted(
                changes,
                key=lambda change: (
                    not change.target_domain,
                    -change.seen,
                    change.domain,
                ),
            )
        ),
        baseline_drift_domains=tuple(
            sorted(
                set(
                    baseline_drift_domains
                )
            )
        ),
    )


def build_scoped_promotion_report(
    summary: ScopedPromotionSummary,
) -> str:
    lines = [
        "5ibr Scoped Promotion Simulation",
        "================================",
        "",
        (
            "Domains evaluated        : "
            f"{summary.domains_evaluated}"
        ),
        (
            "Target domains           : "
            f"{summary.target_domains}"
        ),
        (
            "Policies created         : "
            f"{summary.policies_created}"
        ),
        (
            "Authorized suffixes      : "
            f"{summary.authorized_suffixes}"
        ),
        (
            "Baseline drift           : "
            f"{summary.baseline_drift}"
        ),
        (
            "Changed domains          : "
            f"{summary.changed_domains}"
        ),
        (
            "Intended changes         : "
            f"{summary.intended_changes}"
        ),
        (
            "Collateral changes       : "
            f"{summary.collateral_changes}"
        ),
        (
            "Unchanged target domains : "
            f"{summary.unchanged_target_domains}"
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
            "Production changes       : "
            f"{summary.production_changes}"
        ),
        "",
        "Scoped policies:",
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

    if not summary.policies:
        lines.append("  None")

    lines.extend(
        [
            "",
            "Changed domains:",
            "",
        ]
    )

    if not summary.changes:
        lines.append("  None")
        return "\n".join(lines)

    for change in summary.changes:
        lines.append(
            f"  {change.domain}"
        )
        lines.append(
            f"    targeted       : "
            f"{change.target_domain}"
        )
        lines.append(
            f"    matched suffix : "
            f"{change.matched_suffix}"
        )
        lines.append(
            f"    category       : "
            f"{change.policy_category}"
        )
        lines.append(
            f"    filter         : "
            f"{change.before.filter_name} "
            f"-> {change.after.filter_name}"
        )
        lines.append(
            f"    confidence     : "
            f"{change.before.confidence} "
            f"-> {change.after.confidence}"
        )
        lines.append(
            f"    recommendation : "
            f"{change.before.recommendation} "
            f"-> {change.after.recommendation}"
        )
        lines.append("")

    return "\n".join(lines).rstrip()
