"""Collect unified evidence from all 5ibr intelligence sources."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from scripts.services.canonical_evidence_identity import (
    canonical_evidence_identity,
)

from scripts.services.database_evidence_adapter import (
    database_evidence_to_unified_evidence,
)
from scripts.services.database_evidence_engine import (
    DatabaseEvidence,
)
from scripts.services.knowledge_evidence_adapter import (
    knowledge_entry_to_unified_evidence,
)
from scripts.services.knowledge_service import (
    KnowledgeEntry,
    normalize_text,
)
from scripts.services.rule_engine import RuleMatch
from scripts.services.rule_evidence_adapter import (
    rule_matches_to_unified_evidence,
)
from scripts.services.unified_evidence import (
    UnifiedEvidence,
    group_evidence_by_field,
    strongest_evidence,
)



def normalize_evidence_value(value: str) -> str:
    """Normalize evidence values for semantic conflict comparison."""

    normalized = (value or "").strip().casefold()
    normalized = re.sub(r"[_-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def evidence_value_groups(
    evidence_items: list[UnifiedEvidence],
) -> dict[str, list[UnifiedEvidence]]:
    """Group positive evidence by normalized semantic value."""

    grouped: dict[str, list[UnifiedEvidence]] = {}

    for item in evidence_items:
        if not item.is_positive:
            continue

        normalized_value = canonical_evidence_identity(
            item.field,
            item.value,
        )

        if not normalized_value:
            continue

        grouped.setdefault(
            normalized_value,
            [],
        ).append(item)

    return grouped


@dataclass(frozen=True)
class UnifiedEvidenceBundle:
    """Evidence collected for one normalized domain."""

    domain: str
    evidence: list[UnifiedEvidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        normalized_domain = normalize_text(self.domain).strip(".")

        if not normalized_domain:
            raise ValueError("bundle domain is required")

        object.__setattr__(
            self,
            "domain",
            normalized_domain,
        )
        object.__setattr__(
            self,
            "evidence",
            list(self.evidence),
        )

    def all(self) -> list[UnifiedEvidence]:
        return list(self.evidence)

    def by_source(
        self,
        source: str,
    ) -> list[UnifiedEvidence]:
        normalized_source = (source or "").strip().lower()

        return [
            item
            for item in self.evidence
            if item.source == normalized_source
        ]

    def by_field(
        self,
        field_name: str,
    ) -> list[UnifiedEvidence]:
        normalized_field = (
            field_name or ""
        ).strip().lower()

        return [
            item
            for item in self.evidence
            if item.field == normalized_field
        ]

    def grouped_by_field(
        self,
    ) -> dict[str, list[UnifiedEvidence]]:
        return group_evidence_by_field(
            self.evidence
        )

    def explicit_conflicts(self) -> list[UnifiedEvidence]:
        """Return evidence explicitly marked as CONFLICT."""

        return [
            item
            for item in self.evidence
            if item.is_conflict
        ]

    def conflicts(self) -> list[UnifiedEvidence]:
        """Backward-compatible alias for explicit conflicts."""

        return self.explicit_conflicts()

    def value_conflicts(
        self,
    ) -> dict[str, dict[str, list[UnifiedEvidence]]]:
        """Return fields containing multiple semantic values."""

        conflicts: dict[
            str,
            dict[str, list[UnifiedEvidence]],
        ] = {}

        for field_name, items in self.grouped_by_field().items():
            grouped_values = evidence_value_groups(
                items
            )

            if len(grouped_values) > 1:
                conflicts[field_name] = grouped_values

        return conflicts

    def conflicting_fields(self) -> list[str]:
        """Return fields with explicit or semantic conflicts."""

        fields = set(self.value_conflicts())

        fields.update(
            item.field
            for item in self.explicit_conflicts()
        )

        return sorted(fields)

    def has_conflicts(self) -> bool:
        """Return True when any explicit or value conflict exists."""

        return bool(
            self.explicit_conflicts()
            or self.value_conflicts()
        )

    def strongest(
        self,
        field_name: str,
    ) -> UnifiedEvidence | None:
        return strongest_evidence(
            self.by_field(field_name)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "evidence_count": len(self.evidence),
            "has_conflicts": self.has_conflicts(),
            "conflicting_fields": self.conflicting_fields(),
            "explicit_conflict_count": len(
                self.explicit_conflicts()
            ),
            "value_conflicts": {
                field_name: sorted(groups)
                for field_name, groups
                in self.value_conflicts().items()
            },
            "evidence": [
                item.to_dict()
                for item in self.evidence
            ],
        }


def collect_unified_evidence(
    domain: str,
    *,
    rule_matches: list[RuleMatch] | None = None,
    knowledge_entries: list[KnowledgeEntry] | None = None,
    database_evidence: DatabaseEvidence | None = None,
    additional_evidence: list[UnifiedEvidence] | None = None,
) -> UnifiedEvidenceBundle:
    """Collect evidence from rule, knowledge, and database adapters."""

    normalized_domain = normalize_text(domain).strip(".")

    if not normalized_domain:
        raise ValueError("domain is required")

    collected: list[UnifiedEvidence] = []

    if rule_matches:
        collected.extend(
            rule_matches_to_unified_evidence(
                rule_matches
            )
        )

    for entry in knowledge_entries or []:
        collected.extend(
            knowledge_entry_to_unified_evidence(
                normalized_domain,
                entry,
            )
        )

    if database_evidence is not None:
        collected.extend(
            database_evidence_to_unified_evidence(
                database_evidence
            )
        )

    if additional_evidence:
        collected.extend(additional_evidence)

    return UnifiedEvidenceBundle(
        domain=normalized_domain,
        evidence=collected,
    )
