"""Preview-only resolution of UnifiedEvidence bundles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scripts.services.canonical_evidence_identity import (
    canonical_evidence_identity,
    preferred_evidence_label,
)
from scripts.services.evidence_quality import EvidenceQuality
from scripts.services.unified_evidence import (
    UnifiedEvidence,
    strongest_evidence,
)
from scripts.services.unified_evidence_collector import (
    UnifiedEvidenceBundle,
)


QUALITY_RANK = {
    EvidenceQuality.EXACT: 5,
    EvidenceQuality.STRONG: 4,
    EvidenceQuality.MODERATE: 3,
    EvidenceQuality.WEAK: 2,
    EvidenceQuality.CONFLICT: 1,
}


@dataclass(frozen=True)
class EvidenceCandidate:
    """Aggregated evidence supporting one canonical value."""

    identity: str
    value: str
    score: int
    quality: EvidenceQuality
    sources: tuple[str, ...]
    evidence: tuple[UnifiedEvidence, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "value": self.value,
            "score": self.score,
            "quality": self.quality.value,
            "sources": list(self.sources),
            "evidence_count": len(self.evidence),
            "evidence": [
                item.to_dict()
                for item in self.evidence
            ],
        }


@dataclass(frozen=True)
class ResolvedEvidenceField:
    """Preview result for one evidence field."""

    field: str
    value: str
    identity: str
    score: int
    quality: EvidenceQuality
    sources: tuple[str, ...]
    supporting: tuple[UnifiedEvidence, ...]
    competing: tuple[EvidenceCandidate, ...] = field(
        default_factory=tuple
    )
    explicit_conflicts: tuple[UnifiedEvidence, ...] = field(
        default_factory=tuple
    )
    ambiguous: bool = False
    reason: str = ""

    @property
    def has_conflict(self) -> bool:
        return bool(
            self.competing
            or self.explicit_conflicts
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "identity": self.identity,
            "score": self.score,
            "quality": self.quality.value,
            "sources": list(self.sources),
            "supporting_count": len(self.supporting),
            "competing_count": len(self.competing),
            "explicit_conflict_count": len(
                self.explicit_conflicts
            ),
            "has_conflict": self.has_conflict,
            "ambiguous": self.ambiguous,
            "reason": self.reason,
            "supporting": [
                item.to_dict()
                for item in self.supporting
            ],
            "competing": [
                candidate.to_dict()
                for candidate in self.competing
            ],
            "explicit_conflicts": [
                item.to_dict()
                for item in self.explicit_conflicts
            ],
        }


@dataclass(frozen=True)
class UnifiedEvidenceResolution:
    """Preview resolution for all supported evidence fields."""

    domain: str
    fields: dict[str, ResolvedEvidenceField]
    unresolved_fields: tuple[str, ...] = field(
        default_factory=tuple
    )

    def get(
        self,
        field_name: str,
    ) -> ResolvedEvidenceField | None:
        return self.fields.get(
            (field_name or "").strip().lower()
        )

    @property
    def has_conflicts(self) -> bool:
        return any(
            result.has_conflict
            for result in self.fields.values()
        )

    @property
    def has_ambiguity(self) -> bool:
        return any(
            result.ambiguous
            for result in self.fields.values()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "has_conflicts": self.has_conflicts,
            "has_ambiguity": self.has_ambiguity,
            "unresolved_fields": list(
                self.unresolved_fields
            ),
            "fields": {
                field_name: result.to_dict()
                for field_name, result
                in self.fields.items()
            },
        }


def is_derived_filter_evidence(
    evidence: UnifiedEvidence,
) -> bool:
    """Return True for filter evidence derived from a category rule."""

    return (
        evidence.field == "filter"
        and str(
            evidence.metadata.get(
                "derived_from",
                "",
            )
        ).strip().lower()
        == "category"
    )


def candidate_has_direct_evidence(
    candidate: EvidenceCandidate,
) -> bool:
    """Return True when a candidate has at least one direct evidence item."""

    return any(
        not is_derived_filter_evidence(item)
        for item in candidate.evidence
    )


def _candidate_sort_key(
    candidate: EvidenceCandidate,
    *,
    field_name: str,
) -> tuple[int, int, int, int, str]:
    """Return the resolver precedence key.

    For filter resolution, direct evidence outranks category-derived
    filter evidence even when the derived rule has a larger raw score.
    Other fields preserve the established ordering.
    """

    direct_priority = 1

    if field_name == "filter":
        direct_priority = int(
            candidate_has_direct_evidence(
                candidate
            )
        )

    return (
        direct_priority,
        candidate.score,
        QUALITY_RANK[candidate.quality],
        len(candidate.sources),
        candidate.identity,
    )


def _build_candidates(
    field_name: str,
    evidence_items: list[UnifiedEvidence],
) -> list[EvidenceCandidate]:
    grouped: dict[str, list[UnifiedEvidence]] = {}

    for item in evidence_items:
        if not item.is_positive:
            continue

        identity = canonical_evidence_identity(
            field_name,
            item.value,
        )

        if not identity:
            continue

        grouped.setdefault(
            identity,
            [],
        ).append(item)

    candidates: list[EvidenceCandidate] = []

    for identity, items in grouped.items():
        strongest = strongest_evidence(items)

        if strongest is None:
            continue

        sources = tuple(
            sorted(
                {
                    item.source
                    for item in items
                }
            )
        )

        candidates.append(
            EvidenceCandidate(
                identity=identity,
                value=preferred_evidence_label(
                    field_name,
                    identity,
                    strongest.value,
                ),
                score=min(
                    sum(
                        item.score
                        for item in items
                    ),
                    100,
                ),
                quality=strongest.quality,
                sources=sources,
                evidence=tuple(items),
            )
        )

    return sorted(
        candidates,
        key=lambda candidate: _candidate_sort_key(
            candidate,
            field_name=field_name,
        ),
        reverse=True,
    )


def resolve_evidence_field(
    bundle: UnifiedEvidenceBundle,
    field_name: str,
) -> ResolvedEvidenceField | None:
    """Resolve one field from a unified evidence bundle."""

    normalized_field = (
        field_name or ""
    ).strip().lower()

    field_items = bundle.by_field(
        normalized_field
    )

    candidates = _build_candidates(
        normalized_field,
        field_items,
    )

    if not candidates:
        return None

    winner = candidates[0]
    competing = tuple(candidates[1:])

    explicit_conflicts = tuple(
        item
        for item in field_items
        if item.is_conflict
    )

    ambiguous = False

    if competing:
        first_competitor = competing[0]

        ambiguous = (
            winner.score
            == first_competitor.score
            and QUALITY_RANK[winner.quality]
            == QUALITY_RANK[
                first_competitor.quality
            ]
            and len(winner.sources)
            == len(first_competitor.sources)
        )

    reason = (
        f"selected {winner.value} from "
        f"{len(winner.evidence)} evidence item(s) "
        f"across {len(winner.sources)} source(s); "
        f"score={winner.score}, "
        f"quality={winner.quality.value}"
    )

    if competing:
        reason += (
            f"; competing values="
            f"{', '.join(item.value for item in competing)}"
        )

    if explicit_conflicts:
        reason += (
            f"; explicit conflicts="
            f"{len(explicit_conflicts)}"
        )

    if ambiguous:
        reason += "; resolution is ambiguous"

    return ResolvedEvidenceField(
        field=normalized_field,
        value=winner.value,
        identity=winner.identity,
        score=winner.score,
        quality=winner.quality,
        sources=winner.sources,
        supporting=winner.evidence,
        competing=competing,
        explicit_conflicts=explicit_conflicts,
        ambiguous=ambiguous,
        reason=reason,
    )


def resolve_unified_evidence(
    bundle: UnifiedEvidenceBundle,
    *,
    fields: tuple[str, ...] = (
        "vendor",
        "category",
        "filter",
    ),
) -> UnifiedEvidenceResolution:
    """Resolve a bundle in preview mode without changing Analyzer output."""

    resolved: dict[str, ResolvedEvidenceField] = {}
    unresolved: list[str] = []

    for field_name in fields:
        result = resolve_evidence_field(
            bundle,
            field_name,
        )

        if result is None:
            unresolved.append(field_name)
            continue

        resolved[field_name] = result

    return UnifiedEvidenceResolution(
        domain=bundle.domain,
        fields=resolved,
        unresolved_fields=tuple(unresolved),
    )
