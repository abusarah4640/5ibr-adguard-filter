"""Simulate controlled promotion of approved semantic mappings.

The simulation writes a temporary analyzer configuration and runs both
the current and proposed configurations against the same domains and
database rows. Production configuration and data are never modified.
"""

from __future__ import annotations

import json
import tempfile
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from scripts.services.analyzer_service import analyze_domain
from scripts.services.database_service import load_database
from scripts.services.semantic_filter_mapping import (
    normalize_mapping_value,
)


@dataclass(frozen=True)
class SimulatedDecision:
    vendor: str
    category: str
    filter_name: str
    confidence: int
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor": self.vendor,
            "category": self.category,
            "filter": self.filter_name,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class PromotionSimulationChange:
    domain: str
    seen: int
    targeted: bool
    before: SimulatedDecision
    after: SimulatedDecision
    changed_fields: tuple[str, ...]
    confidence_delta: int
    recommendation_changed: bool

    @property
    def is_collateral(self) -> bool:
        return not self.targeted

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "seen": self.seen,
            "targeted": self.targeted,
            "collateral": self.is_collateral,
            "changed_fields": list(
                self.changed_fields
            ),
            "confidence_delta": (
                self.confidence_delta
            ),
            "recommendation_changed": (
                self.recommendation_changed
            ),
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
        }


@dataclass(frozen=True)
class ControlledPromotionSummary:
    domains_evaluated: int
    target_domains: int
    mapping_updates: dict[str, str]
    baseline_drift: int
    changed_domains: int
    intended_changes: int
    collateral_changes: int
    unchanged_target_domains: int
    confidence_changes: int
    recommendation_changes: int
    recommendation_transitions: dict[str, int]
    production_changes: int
    changes: tuple[PromotionSimulationChange, ...] = field(
        default_factory=tuple
    )
    baseline_drift_domains: tuple[str, ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "domains_evaluated": (
                self.domains_evaluated
            ),
            "target_domains": self.target_domains,
            "mapping_updates": dict(
                self.mapping_updates
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
            "recommendation_transitions": dict(
                self.recommendation_transitions
            ),
            "production_changes": (
                self.production_changes
            ),
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


def load_json_object(path: Path) -> dict[str, Any]:
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


def eligible_gate_results(
    gate_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = gate_payload.get("results", [])

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
            and str(
                row.get("decision", "")
            ).strip()
            == "eligible-for-controlled-promotion"
        )
    ]


def build_mapping_updates(
    gate_results: Iterable[
        dict[str, Any]
    ],
) -> dict[str, str]:
    """Build deduplicated category/filter updates.

    Conflicting proposals for the same category are rejected.
    """

    updates: dict[str, str] = {}
    normalized_updates: dict[str, str] = {}

    for row in gate_results:
        current = row.get("current", {})

        if not isinstance(current, dict):
            current = {}

        category = str(
            current.get("category", "")
            or ""
        ).strip()

        proposed_filter = str(
            row.get("proposed_filter", "")
            or ""
        ).strip()

        if not category or not proposed_filter:
            raise ValueError(
                "eligible candidate is missing category or proposed filter"
            )

        normalized_category = (
            normalize_mapping_value(category)
        )

        normalized_filter = (
            normalize_mapping_value(
                proposed_filter
            )
        )

        previous = normalized_updates.get(
            normalized_category
        )

        if (
            previous is not None
            and previous != normalized_filter
        ):
            raise ValueError(
                "conflicting promotion proposals "
                f"for category: {category}"
            )

        normalized_updates[
            normalized_category
        ] = normalized_filter

        updates[category] = proposed_filter

    return updates


def apply_mapping_updates(
    config: dict[str, Any],
    updates: dict[str, str],
) -> dict[str, Any]:
    """Return a modified in-memory config copy."""

    simulated = deepcopy(config)

    filter_map = simulated.get(
        "filter_map",
        {},
    )

    if not isinstance(filter_map, dict):
        filter_map = {}

    filter_map = {
        str(key): str(value)
        for key, value in filter_map.items()
    }

    for category, proposed_filter in (
        updates.items()
    ):
        matched_key: str | None = None

        for existing_key in filter_map:
            if (
                normalize_mapping_value(
                    existing_key
                )
                == normalize_mapping_value(
                    category
                )
            ):
                matched_key = existing_key
                break

        filter_map[
            matched_key or category
        ] = proposed_filter

    simulated["filter_map"] = filter_map

    return simulated


def decision_from_result(
    result: object,
) -> SimulatedDecision:
    return SimulatedDecision(
        vendor=str(
            getattr(
                result,
                "suggested_vendor",
                "Unknown",
            )
        ),
        category=str(
            getattr(
                result,
                "suggested_category",
                "Unknown",
            )
        ),
        filter_name=str(
            getattr(
                result,
                "suggested_filter",
                "unknown",
            )
        ),
        confidence=int(
            getattr(
                result,
                "confidence",
                0,
            )
            or 0
        ),
        recommendation=str(
            getattr(
                result,
                "recommendation",
                "unknown",
            )
        ),
    )


def decision_from_row(
    row: dict[str, Any],
) -> SimulatedDecision:
    return SimulatedDecision(
        vendor=str(
            row.get("vendor", "Unknown")
        ),
        category=str(
            row.get("category", "Unknown")
        ),
        filter_name=str(
            row.get("filter", "unknown")
        ),
        confidence=int(
            float(
                row.get("confidence", 0)
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


def changed_fields(
    before: SimulatedDecision,
    after: SimulatedDecision,
) -> tuple[str, ...]:
    fields: list[str] = []

    if before.vendor != after.vendor:
        fields.append("vendor")

    if before.category != after.category:
        fields.append("category")

    if before.filter_name != after.filter_name:
        fields.append("filter")

    if before.confidence != after.confidence:
        fields.append("confidence")

    if (
        before.recommendation
        != after.recommendation
    ):
        fields.append("recommendation")

    return tuple(fields)


def run_controlled_promotion_simulation(
    *,
    suggestions_path: Path,
    gate_path: Path,
    config_path: Path = Path(
        "config/analyzer.json"
    ),
    database_rows: list[dict[str, Any]] | None = None,
    limit: int | None = None,
) -> ControlledPromotionSummary:
    """Run current and proposed configs without changing production."""

    baseline_rows = load_suggestion_rows(
        suggestions_path
    )

    if limit is not None:
        baseline_rows = baseline_rows[
            : max(limit, 0)
        ]

    gate_payload = load_json_object(
        gate_path
    )

    eligible = eligible_gate_results(
        gate_payload
    )

    target_domains = {
        normalize_domain(row.get("domain"))
        for row in eligible
        if normalize_domain(
            row.get("domain")
        )
    }

    updates = build_mapping_updates(
        eligible
    )

    current_config = load_json_object(
        config_path
    )

    simulated_config = apply_mapping_updates(
        current_config,
        updates,
    )

    effective_database_rows = (
        load_database()
        if database_rows is None
        else database_rows
    )

    changes: list[
        PromotionSimulationChange
    ] = []

    baseline_drift_domains: list[str] = []

    recommendation_transitions: Counter[
        str
    ] = Counter()

    with tempfile.TemporaryDirectory(
        prefix="fivebr-stage51-"
    ) as temp_dir:
        temp_root = Path(temp_dir)

        control_path = (
            temp_root / "control.json"
        )

        simulation_path = (
            temp_root / "simulation.json"
        )

        control_path.write_text(
            json.dumps(
                current_config,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        simulation_path.write_text(
            json.dumps(
                simulated_config,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        for row in baseline_rows:
            domain = normalize_domain(
                row.get("domain")
            )

            baseline = decision_from_row(row)

            control_result = analyze_domain(
                domain,
                config_path=control_path,
                rows=effective_database_rows,
            )

            simulation_result = (
                analyze_domain(
                    domain,
                    config_path=simulation_path,
                    rows=effective_database_rows,
                )
            )

            control = decision_from_result(
                control_result
            )

            simulated = decision_from_result(
                simulation_result
            )

            if changed_fields(
                baseline,
                control,
            ):
                baseline_drift_domains.append(
                    domain
                )

            fields = changed_fields(
                control,
                simulated,
            )

            if not fields:
                continue

            recommendation_changed = (
                control.recommendation
                != simulated.recommendation
            )

            if recommendation_changed:
                recommendation_transitions[
                    (
                        f"{control.recommendation}"
                        f" -> "
                        f"{simulated.recommendation}"
                    )
                ] += 1

            changes.append(
                PromotionSimulationChange(
                    domain=domain,
                    seen=int(
                        row.get("seen", 0)
                        or 0
                    ),
                    targeted=(
                        domain in target_domains
                    ),
                    before=control,
                    after=simulated,
                    changed_fields=fields,
                    confidence_delta=(
                        simulated.confidence
                        - control.confidence
                    ),
                    recommendation_changed=(
                        recommendation_changed
                    ),
                )
            )

    changed_target_domains = {
        change.domain
        for change in changes
        if change.targeted
    }

    return ControlledPromotionSummary(
        domains_evaluated=len(
            baseline_rows
        ),
        target_domains=len(
            target_domains
        ),
        mapping_updates=updates,
        baseline_drift=len(
            baseline_drift_domains
        ),
        changed_domains=len(changes),
        intended_changes=sum(
            change.targeted
            for change in changes
        ),
        collateral_changes=sum(
            change.is_collateral
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
            change.recommendation_changed
            for change in changes
        ),
        recommendation_transitions=dict(
            recommendation_transitions
        ),
        production_changes=0,
        changes=tuple(
            sorted(
                changes,
                key=lambda item: (
                    not item.targeted,
                    -item.seen,
                    item.domain,
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


def build_controlled_promotion_report(
    summary: ControlledPromotionSummary,
) -> str:
    lines = [
        "5ibr Controlled Promotion Simulation",
        "====================================",
        "",
        (
            "Domains evaluated          : "
            f"{summary.domains_evaluated}"
        ),
        (
            "Target domains             : "
            f"{summary.target_domains}"
        ),
        (
            "Baseline drift             : "
            f"{summary.baseline_drift}"
        ),
        (
            "Changed domains            : "
            f"{summary.changed_domains}"
        ),
        (
            "Intended target changes    : "
            f"{summary.intended_changes}"
        ),
        (
            "Collateral changes         : "
            f"{summary.collateral_changes}"
        ),
        (
            "Unchanged target domains   : "
            f"{summary.unchanged_target_domains}"
        ),
        (
            "Confidence changes         : "
            f"{summary.confidence_changes}"
        ),
        (
            "Recommendation changes     : "
            f"{summary.recommendation_changes}"
        ),
        (
            "Production changes         : "
            f"{summary.production_changes}"
        ),
        "",
        "Simulated mapping updates:",
    ]

    if summary.mapping_updates:
        for category, filter_name in sorted(
            summary.mapping_updates.items()
        ):
            lines.append(
                f"  {category:<20} -> "
                f"{filter_name}"
            )
    else:
        lines.append("  None")

    lines.extend(
        [
            "",
            "Recommendation transitions:",
        ]
    )

    if summary.recommendation_transitions:
        for transition, count in sorted(
            summary.recommendation_transitions.items()
        ):
            lines.append(
                f"  {transition:<30}: "
                f"{count}"
            )
    else:
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
            f"    targeted          : "
            f"{change.targeted}"
        )
        lines.append(
            f"    seen              : "
            f"{change.seen}"
        )
        lines.append(
            f"    changed fields    : "
            f"{', '.join(change.changed_fields)}"
        )
        lines.append(
            f"    filter            : "
            f"{change.before.filter_name} "
            f"-> {change.after.filter_name}"
        )
        lines.append(
            f"    confidence        : "
            f"{change.before.confidence} "
            f"-> {change.after.confidence} "
            f"({change.confidence_delta:+d})"
        )
        lines.append(
            f"    recommendation    : "
            f"{change.before.recommendation} "
            f"-> {change.after.recommendation}"
        )
        lines.append("")

    return "\n".join(lines).rstrip()
