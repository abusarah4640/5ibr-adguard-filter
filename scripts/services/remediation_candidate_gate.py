"""Second-stage safety gate for remediation preview candidates.

This service is evaluation-only. It never changes production files,
Analyzer configuration, database rows, resolver decisions, confidence,
or recommendations.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from scripts.services.semantic_filter_mapping import (
    normalize_mapping_value,
)


GATE_DECISIONS = {
    "eligible-for-controlled-promotion",
    "hold-for-review",
    "reject-auto-promotion",
}


@dataclass(frozen=True)
class CandidateGateResult:
    """Safety-gate decision for one remediation proposal."""

    domain: str
    family: str
    decision: str
    root_cause: str
    current_category: str
    current_filter: str
    proposed_filter: str
    family_support: int
    family_consistent: bool
    base_requirements_passed: bool
    automatic_candidate: bool
    production_changed: bool
    reasons: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.decision not in GATE_DECISIONS:
            raise ValueError(
                f"unsupported gate decision: {self.decision}"
            )

        if self.production_changed:
            raise ValueError(
                "candidate safety gate must not modify production"
            )

    @property
    def eligible(self) -> bool:
        return (
            self.decision
            == "eligible-for-controlled-promotion"
        )

    @property
    def held(self) -> bool:
        return self.decision == "hold-for-review"

    @property
    def rejected(self) -> bool:
        return (
            self.decision
            == "reject-auto-promotion"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "family": self.family,
            "decision": self.decision,
            "eligible": self.eligible,
            "held": self.held,
            "rejected": self.rejected,
            "root_cause": self.root_cause,
            "current": {
                "category": self.current_category,
                "filter": self.current_filter,
            },
            "proposed_filter": self.proposed_filter,
            "family_support": self.family_support,
            "family_consistent": (
                self.family_consistent
            ),
            "base_requirements_passed": (
                self.base_requirements_passed
            ),
            "automatic_candidate": (
                self.automatic_candidate
            ),
            "production_changed": (
                self.production_changed
            ),
            "reasons": list(self.reasons),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class CandidateGateSummary:
    """Aggregate Stage 50 safety-gate results."""

    proposals_inspected: int
    automatic_candidates_inspected: int
    eligible: int
    held: int
    rejected: int
    production_changes: int
    decisions: dict[str, int]
    families: dict[str, int]
    results: tuple[CandidateGateResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposals_inspected": (
                self.proposals_inspected
            ),
            "automatic_candidates_inspected": (
                self.automatic_candidates_inspected
            ),
            "eligible": self.eligible,
            "held": self.held,
            "rejected": self.rejected,
            "production_changes": (
                self.production_changes
            ),
            "decisions": dict(self.decisions),
            "families": dict(self.families),
            "results": [
                result.to_dict()
                for result in self.results
            ],
        }


def normalize_domain(value: object) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .strip(".")
    )


def domain_family(domain: str) -> str:
    """Return a stable family key using the final two labels.

    This intentionally avoids external dependencies. It is suitable for
    the current preview dataset and is not used for production routing.
    """

    normalized = normalize_domain(domain)

    labels = [
        label
        for label in normalized.split(".")
        if label
    ]

    if len(labels) <= 2:
        return normalized

    return ".".join(labels[-2:])


def load_remediation_proposals(
    path: Path,
) -> list[dict[str, Any]]:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"invalid remediation report: {path}"
        )

    proposals = data.get("proposals", [])

    if not isinstance(proposals, list):
        raise ValueError(
            "remediation proposals must be a list"
        )

    return [
        proposal
        for proposal in proposals
        if isinstance(proposal, dict)
    ]


def _proposal_values(
    proposal: dict[str, Any],
) -> tuple[str, str, str]:
    current = proposal.get("current", {})
    proposed = proposal.get("proposed", {})

    if not isinstance(current, dict):
        current = {}

    if not isinstance(proposed, dict):
        proposed = {}

    category = str(
        current.get("category", "")
        or ""
    ).strip()

    current_filter = str(
        current.get("filter", "")
        or ""
    ).strip()

    proposed_filter = str(
        proposed.get("filter", "")
        or ""
    ).strip()

    return (
        category,
        current_filter,
        proposed_filter,
    )


def family_consistency_key(
    proposal: dict[str, Any],
) -> tuple[str, str]:
    category, _, proposed_filter = (
        _proposal_values(proposal)
    )

    return (
        normalize_mapping_value(category),
        normalize_mapping_value(
            proposed_filter
        ),
    )


def build_family_index(
    proposals: Iterable[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    index: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for proposal in proposals:
        domain = normalize_domain(
            proposal.get("domain")
        )

        if not domain:
            continue

        index[domain_family(domain)].append(
            proposal
        )

    return dict(index)


def base_safety_requirements(
    proposal: dict[str, Any],
) -> tuple[bool, tuple[str, ...]]:
    """Validate non-negotiable automatic-promotion requirements."""

    reasons: list[str] = []

    root_cause = str(
        proposal.get("root_cause", "")
        or ""
    ).strip()

    action = str(
        proposal.get("action", "")
        or ""
    ).strip()

    automatic_candidate = bool(
        proposal.get(
            "automatic_candidate",
            False,
        )
    )

    production_changed = bool(
        proposal.get(
            "production_changed",
            False,
        )
    )

    proposes_change = bool(
        proposal.get(
            "proposes_change",
            False,
        )
    )

    metadata = proposal.get(
        "metadata",
        {},
    )

    if not isinstance(metadata, dict):
        metadata = {}

    conflict = bool(
        metadata.get("conflict", False)
    )

    ambiguous = bool(
        metadata.get("ambiguous", False)
    )

    sources_value = metadata.get(
        "filter_sources",
        [],
    )

    sources = tuple(
        sorted(
            {
                str(source).strip().lower()
                for source in (
                    sources_value
                    if isinstance(
                        sources_value,
                        list,
                    )
                    else []
                )
                if str(source).strip()
            }
        )
    )

    if (
        root_cause
        != "legacy-mapping-leakage"
    ):
        reasons.append(
            "root cause is not legacy mapping leakage"
        )

    if action != "safe-preview-correction":
        reasons.append(
            "proposal action is not safe preview correction"
        )

    if not automatic_candidate:
        reasons.append(
            "proposal is not marked as an automatic candidate"
        )

    if production_changed:
        reasons.append(
            "proposal indicates a production change"
        )

    if not proposes_change:
        reasons.append(
            "proposal does not contain an actual change"
        )

    if conflict:
        reasons.append(
            "candidate contains competing evidence"
        )

    if ambiguous:
        reasons.append(
            "candidate resolution is ambiguous"
        )

    if sources != ("rule",):
        reasons.append(
            "winning filter evidence is not isolated to rule evidence"
        )

    return (
        not reasons,
        tuple(reasons),
    )


def evaluate_candidate(
    proposal: dict[str, Any],
    *,
    family_members: list[dict[str, Any]],
    minimum_family_support: int = 3,
) -> CandidateGateResult:
    domain = normalize_domain(
        proposal.get("domain")
    )

    family = domain_family(domain)

    category, current_filter, proposed_filter = (
        _proposal_values(proposal)
    )

    passed, base_reasons = (
        base_safety_requirements(proposal)
    )

    target_key = family_consistency_key(
        proposal
    )

    consistent_members = [
        member
        for member in family_members
        if (
            family_consistency_key(member)
            == target_key
        )
    ]

    family_support = len(
        consistent_members
    )

    family_consistent = (
        family_support
        == len(family_members)
        and family_support > 0
    )

    reasons = list(base_reasons)

    if not passed:
        decision = "reject-auto-promotion"
        reasons.append(
            "candidate failed mandatory safety requirements"
        )

    elif not family_consistent:
        decision = "hold-for-review"
        reasons.append(
            "domain family contains inconsistent remediation targets"
        )

    elif family_support < minimum_family_support:
        decision = "hold-for-review"
        reasons.append(
            "domain family support is below the controlled-promotion threshold"
        )

    else:
        decision = (
            "eligible-for-controlled-promotion"
        )
        reasons.extend(
            [
                "candidate passed all mandatory safety requirements",
                (
                    "domain family supports the same "
                    "category and proposed filter"
                ),
                (
                    "family support meets the "
                    "controlled-promotion threshold"
                ),
            ]
        )

    metadata = proposal.get(
        "metadata",
        {},
    )

    if not isinstance(metadata, dict):
        metadata = {}

    return CandidateGateResult(
        domain=domain,
        family=family,
        decision=decision,
        root_cause=str(
            proposal.get("root_cause", "")
            or ""
        ).strip(),
        current_category=category,
        current_filter=current_filter,
        proposed_filter=proposed_filter,
        family_support=family_support,
        family_consistent=family_consistent,
        base_requirements_passed=passed,
        automatic_candidate=bool(
            proposal.get(
                "automatic_candidate",
                False,
            )
        ),
        production_changed=False,
        reasons=tuple(reasons),
        metadata={
            "minimum_family_support": (
                minimum_family_support
            ),
            "family_member_count": len(
                family_members
            ),
            "filter_sources": list(
                metadata.get(
                    "filter_sources",
                    [],
                )
                or []
            ),
            "filter_score": int(
                metadata.get(
                    "filter_score",
                    0,
                )
                or 0
            ),
        },
    )


def run_candidate_safety_gate(
    proposals: Iterable[dict[str, Any]],
    *,
    minimum_family_support: int = 3,
    automatic_only: bool = True,
) -> CandidateGateSummary:
    items = tuple(proposals)

    selected = [
        proposal
        for proposal in items
        if (
            bool(
                proposal.get(
                    "automatic_candidate",
                    False,
                )
            )
            if automatic_only
            else True
        )
    ]

    family_index = build_family_index(
        selected
    )

    results = tuple(
        evaluate_candidate(
            proposal,
            family_members=family_index.get(
                domain_family(
                    normalize_domain(
                        proposal.get(
                            "domain"
                        )
                    )
                ),
                [],
            ),
            minimum_family_support=(
                minimum_family_support
            ),
        )
        for proposal in selected
    )

    decision_counts = Counter(
        result.decision
        for result in results
    )

    family_counts = Counter(
        result.family
        for result in results
    )

    return CandidateGateSummary(
        proposals_inspected=len(items),
        automatic_candidates_inspected=(
            len(selected)
        ),
        eligible=sum(
            result.eligible
            for result in results
        ),
        held=sum(
            result.held
            for result in results
        ),
        rejected=sum(
            result.rejected
            for result in results
        ),
        production_changes=sum(
            result.production_changed
            for result in results
        ),
        decisions=dict(
            decision_counts
        ),
        families=dict(
            family_counts
        ),
        results=results,
    )


def build_candidate_gate_report(
    summary: CandidateGateSummary,
) -> str:
    lines = [
        "5ibr Remediation Candidate Safety Gate",
        "======================================",
        "",
        (
            "Proposals inspected           : "
            f"{summary.proposals_inspected}"
        ),
        (
            "Automatic candidates inspected: "
            f"{summary.automatic_candidates_inspected}"
        ),
        (
            "Eligible                      : "
            f"{summary.eligible}"
        ),
        (
            "Held for review               : "
            f"{summary.held}"
        ),
        (
            "Rejected                      : "
            f"{summary.rejected}"
        ),
        (
            "Production changes            : "
            f"{summary.production_changes}"
        ),
        "",
        "Decisions:",
    ]

    if summary.decisions:
        for decision, count in sorted(
            summary.decisions.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        ):
            lines.append(
                f"  {decision:<38}: {count}"
            )
    else:
        lines.append("  None")

    lines.extend(
        [
            "",
            "Candidate details:",
            "",
        ]
    )

    if not summary.results:
        lines.append("  None")
        return "\n".join(lines)

    for result in summary.results:
        lines.append(
            f"  {result.domain}"
        )
        lines.append(
            f"    family             : "
            f"{result.family}"
        )
        lines.append(
            f"    decision           : "
            f"{result.decision}"
        )
        lines.append(
            f"    category           : "
            f"{result.current_category}"
        )
        lines.append(
            f"    current filter     : "
            f"{result.current_filter}"
        )
        lines.append(
            f"    proposed filter    : "
            f"{result.proposed_filter}"
        )
        lines.append(
            f"    family support     : "
            f"{result.family_support}"
        )
        lines.append(
            f"    family consistent  : "
            f"{result.family_consistent}"
        )
        lines.append(
            f"    base requirements  : "
            f"{result.base_requirements_passed}"
        )
        lines.append(
            f"    production changed : "
            f"{result.production_changed}"
        )

        for reason in result.reasons:
            lines.append(
                f"    reason             : "
                f"{reason}"
            )

        lines.append("")

    return "\n".join(lines).rstrip()
