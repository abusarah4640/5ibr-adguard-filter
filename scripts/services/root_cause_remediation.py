"""Preview remediation plans for attributed coherence root causes.

This module is preview-only. It never modifies Analyzer configuration,
database rows, resolver decisions, confidence, recommendations, or
production output.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from scripts.services.semantic_filter_mapping import (
    normalize_mapping_value,
)


REMEDIATION_ACTIONS = {
    "safe-preview-correction",
    "preserve-and-review",
    "taxonomy-review",
    "insufficient-evidence",
}


@dataclass(frozen=True)
class RemediationProposal:
    """One non-destructive remediation proposal."""

    domain: str
    root_cause: str
    action: str
    current_category: str
    current_filter: str
    proposed_category: str
    proposed_filter: str
    severity: str
    confidence: str
    automatic_candidate: bool
    requires_review: bool
    production_changed: bool = False
    reasons: tuple[str, ...] = field(
        default_factory=tuple
    )
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.action not in REMEDIATION_ACTIONS:
            raise ValueError(
                f"unsupported remediation action: {self.action}"
            )

        if self.production_changed:
            raise ValueError(
                "remediation preview must not change production"
            )

    @property
    def proposes_change(self) -> bool:
        return (
            normalize_mapping_value(
                self.current_category
            )
            != normalize_mapping_value(
                self.proposed_category
            )
            or normalize_mapping_value(
                self.current_filter
            )
            != normalize_mapping_value(
                self.proposed_filter
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "root_cause": self.root_cause,
            "action": self.action,
            "current": {
                "category": self.current_category,
                "filter": self.current_filter,
            },
            "proposed": {
                "category": self.proposed_category,
                "filter": self.proposed_filter,
            },
            "severity": self.severity,
            "confidence": self.confidence,
            "automatic_candidate": (
                self.automatic_candidate
            ),
            "requires_review": self.requires_review,
            "proposes_change": self.proposes_change,
            "production_changed": (
                self.production_changed
            ),
            "reasons": list(self.reasons),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RemediationSummary:
    """Aggregate remediation preview statistics."""

    domains_inspected: int
    proposals_created: int
    action_counts: dict[str, int]
    root_cause_counts: dict[str, int]
    automatic_candidates: int
    requiring_review: int
    proposed_changes: int
    production_changes: int
    proposals: tuple[RemediationProposal, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "domains_inspected": self.domains_inspected,
            "proposals_created": self.proposals_created,
            "action_counts": dict(
                self.action_counts
            ),
            "root_cause_counts": dict(
                self.root_cause_counts
            ),
            "automatic_candidates": (
                self.automatic_candidates
            ),
            "requiring_review": (
                self.requiring_review
            ),
            "proposed_changes": (
                self.proposed_changes
            ),
            "production_changes": (
                self.production_changes
            ),
            "proposals": [
                proposal.to_dict()
                for proposal in self.proposals
            ],
        }


def normalize_domain(value: object) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .strip(".")
    )


def load_attributions(
    path: Path,
) -> list[dict[str, Any]]:
    """Load Stage 48 root-cause attributions."""

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"invalid attribution report: {path}"
        )

    rows = data.get("attributions", [])

    if not isinstance(rows, list):
        raise ValueError(
            "root-cause attributions must be a list"
        )

    return [
        row
        for row in rows
        if isinstance(row, dict)
    ]


def build_remediation_proposal(
    attribution: dict[str, Any],
) -> RemediationProposal:
    """Build one safe preview proposal from one attribution."""

    domain = normalize_domain(
        attribution.get("domain")
    )

    root_cause = str(
        attribution.get(
            "root_cause",
            "cross-field-incoherence",
        )
        or "cross-field-incoherence"
    ).strip()

    category = str(
        attribution.get("category", "")
        or ""
    ).strip()

    actual_filter = str(
        attribution.get("actual_filter", "")
        or ""
    ).strip()

    expected_filter = str(
        attribution.get(
            "expected_filter",
            "",
        )
        or ""
    ).strip()

    severity = str(
        attribution.get("severity", "medium")
        or "medium"
    ).strip().lower()

    conflict = bool(
        attribution.get("conflict", False)
    )

    ambiguous = bool(
        attribution.get("ambiguous", False)
    )

    source_values = attribution.get(
        "filter_sources",
        [],
    )

    filter_sources = tuple(
        sorted(
            {
                str(source).strip().lower()
                for source in (
                    source_values
                    if isinstance(
                        source_values,
                        list,
                    )
                    else []
                )
                if str(source).strip()
            }
        )
    )

    filter_score = int(
        attribution.get(
            "filter_score",
            0,
        )
        or 0
    )

    reasons: list[str] = []

    proposed_category = category
    proposed_filter = actual_filter
    automatic_candidate = False
    requires_review = True
    confidence = "low"

    if root_cause == "legacy-mapping-leakage":
        if (
            expected_filter
            and not ambiguous
            and not conflict
            and filter_sources == ("rule",)
        ):
            action = "safe-preview-correction"
            proposed_filter = expected_filter
            automatic_candidate = True
            requires_review = False
            confidence = "high"

            reasons.extend(
                [
                    (
                        "winning filter matches a legacy "
                        "category mapping"
                    ),
                    (
                        "semantic filter mapping provides "
                        "a coherent replacement"
                    ),
                    (
                        "proposal is limited to preview "
                        "and does not modify production"
                    ),
                ]
            )
        else:
            action = "preserve-and-review"
            confidence = "medium"

            reasons.append(
                "legacy mapping evidence is not isolated enough for safe correction"
            )

    elif root_cause == "direct-evidence-conflict":
        action = "preserve-and-review"
        confidence = "high"

        reasons.extend(
            [
                (
                    "current filter has direct knowledge "
                    "or database evidence"
                ),
                (
                    "automatic replacement could hide "
                    "valid service behavior"
                ),
            ]
        )

    elif root_cause == "ambiguous-resolution":
        action = "preserve-and-review"
        confidence = "high"

        reasons.extend(
            [
                "resolver outcome is ambiguous",
                (
                    "no automatic correction is allowed "
                    "for tied or weakly separated evidence"
                ),
            ]
        )

    elif (
        root_cause
        == "possible-taxonomy-dimension-collision"
    ):
        action = "taxonomy-review"
        confidence = "high"

        reasons.extend(
            [
                (
                    "category and filter may represent "
                    "different semantic dimensions"
                ),
                (
                    "automatic correction is deferred "
                    "until taxonomy boundaries are defined"
                ),
            ]
        )

    elif root_cause == "unresolved-evidence":
        action = "insufficient-evidence"
        confidence = "low"

        reasons.append(
            "resolver did not provide enough evidence for a correction"
        )

    else:
        action = "preserve-and-review"
        confidence = "medium"

        reasons.append(
            "no safe root-cause-specific correction policy exists"
        )

    if conflict:
        reasons.append(
            "competing evidence is present"
        )

    if ambiguous:
        reasons.append(
            "resolution is ambiguous"
        )

    return RemediationProposal(
        domain=domain,
        root_cause=root_cause,
        action=action,
        current_category=category,
        current_filter=actual_filter,
        proposed_category=proposed_category,
        proposed_filter=proposed_filter,
        severity=severity,
        confidence=confidence,
        automatic_candidate=(
            automatic_candidate
        ),
        requires_review=requires_review,
        production_changed=False,
        reasons=tuple(reasons),
        metadata={
            "filter_sources": list(
                filter_sources
            ),
            "filter_score": filter_score,
            "conflict": conflict,
            "ambiguous": ambiguous,
        },
    )


def build_remediation_preview(
    attributions: Iterable[
        dict[str, Any]
    ],
) -> RemediationSummary:
    """Build remediation previews without applying changes."""

    items = tuple(attributions)

    proposals = tuple(
        build_remediation_proposal(
            attribution
        )
        for attribution in items
    )

    action_counts = Counter(
        proposal.action
        for proposal in proposals
    )

    cause_counts = Counter(
        proposal.root_cause
        for proposal in proposals
    )

    return RemediationSummary(
        domains_inspected=len(items),
        proposals_created=len(proposals),
        action_counts=dict(action_counts),
        root_cause_counts=dict(
            cause_counts
        ),
        automatic_candidates=sum(
            proposal.automatic_candidate
            for proposal in proposals
        ),
        requiring_review=sum(
            proposal.requires_review
            for proposal in proposals
        ),
        proposed_changes=sum(
            proposal.proposes_change
            for proposal in proposals
        ),
        production_changes=sum(
            proposal.production_changed
            for proposal in proposals
        ),
        proposals=proposals,
    )


def build_remediation_report(
    summary: RemediationSummary,
) -> str:
    lines = [
        "5ibr Root-Cause Remediation Preview",
        "===================================",
        "",
        (
            "Domains inspected      : "
            f"{summary.domains_inspected}"
        ),
        (
            "Proposals created      : "
            f"{summary.proposals_created}"
        ),
        (
            "Automatic candidates   : "
            f"{summary.automatic_candidates}"
        ),
        (
            "Requiring review       : "
            f"{summary.requiring_review}"
        ),
        (
            "Proposed changes       : "
            f"{summary.proposed_changes}"
        ),
        (
            "Production changes     : "
            f"{summary.production_changes}"
        ),
        "",
        "Actions:",
    ]

    if summary.action_counts:
        for action, count in sorted(
            summary.action_counts.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        ):
            lines.append(
                f"  {action:<30}: {count}"
            )
    else:
        lines.append("  None")

    lines.extend(
        [
            "",
            "Proposal details:",
            "",
        ]
    )

    if not summary.proposals:
        lines.append("  None")
        return "\n".join(lines)

    for proposal in summary.proposals:
        lines.append(
            f"  {proposal.domain}"
        )
        lines.append(
            f"    root cause        : "
            f"{proposal.root_cause}"
        )
        lines.append(
            f"    action            : "
            f"{proposal.action}"
        )
        lines.append(
            f"    current category  : "
            f"{proposal.current_category or 'Unresolved'}"
        )
        lines.append(
            f"    current filter    : "
            f"{proposal.current_filter or 'Unresolved'}"
        )
        lines.append(
            f"    proposed category : "
            f"{proposal.proposed_category or 'Unresolved'}"
        )
        lines.append(
            f"    proposed filter   : "
            f"{proposal.proposed_filter or 'Unresolved'}"
        )
        lines.append(
            f"    severity          : "
            f"{proposal.severity}"
        )
        lines.append(
            f"    confidence        : "
            f"{proposal.confidence}"
        )
        lines.append(
            f"    automatic         : "
            f"{proposal.automatic_candidate}"
        )
        lines.append(
            f"    requires review   : "
            f"{proposal.requires_review}"
        )
        lines.append(
            f"    proposes change   : "
            f"{proposal.proposes_change}"
        )
        lines.append(
            f"    production changed: "
            f"{proposal.production_changed}"
        )

        for reason in proposal.reasons:
            lines.append(
                f"    reason            : "
                f"{reason}"
            )

        lines.append("")

    return "\n".join(lines).rstrip()
