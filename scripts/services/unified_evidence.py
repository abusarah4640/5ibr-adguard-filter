"""Unified evidence model for 5ibr Filter Toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scripts.services.evidence_quality import EvidenceQuality


VALID_SOURCES = {
    "rule",
    "knowledge",
    "database",
    "analyzer",
    "system",
}

VALID_FIELDS = {
    "vendor",
    "category",
    "filter",
    "domain",
    "recommendation",
}


@dataclass(frozen=True)
class UnifiedEvidence:
    """A normalized evidence item shared by all intelligence engines."""

    source: str
    field: str
    value: str
    quality: EvidenceQuality
    score: int
    reason: str
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        normalized_source = self.source.strip().lower()
        normalized_field = self.field.strip().lower()
        normalized_value = self.value.strip()
        normalized_reason = self.reason.strip()

        if normalized_source not in VALID_SOURCES:
            raise ValueError(
                f"unsupported evidence source: {self.source}"
            )

        if normalized_field not in VALID_FIELDS:
            raise ValueError(
                f"unsupported evidence field: {self.field}"
            )

        if not normalized_value:
            raise ValueError("evidence value is required")

        if not normalized_reason:
            raise ValueError("evidence reason is required")

        if not 0 <= self.score <= 100:
            raise ValueError(
                "evidence score must be between 0 and 100"
            )

        object.__setattr__(
            self,
            "source",
            normalized_source,
        )
        object.__setattr__(
            self,
            "field",
            normalized_field,
        )
        object.__setattr__(
            self,
            "value",
            normalized_value,
        )
        object.__setattr__(
            self,
            "reason",
            normalized_reason,
        )
        object.__setattr__(
            self,
            "metadata",
            dict(self.metadata or {}),
        )

    @property
    def is_conflict(self) -> bool:
        return self.quality == EvidenceQuality.CONFLICT

    @property
    def is_positive(self) -> bool:
        return (
            not self.is_conflict
            and self.score > 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "field": self.field,
            "value": self.value,
            "quality": self.quality.value,
            "score": self.score,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }


def make_unified_evidence(
    *,
    source: str,
    field: str,
    value: str,
    quality: EvidenceQuality,
    score: int,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> UnifiedEvidence:
    """Create a validated unified evidence item."""

    return UnifiedEvidence(
        source=source,
        field=field,
        value=value,
        quality=quality,
        score=score,
        reason=reason,
        metadata=metadata or {},
    )


def evidence_total(
    evidence_items: list[UnifiedEvidence],
) -> int:
    """Return the capped score of positive evidence."""

    return min(
        sum(
            item.score
            for item in evidence_items
            if item.is_positive
        ),
        100,
    )


def group_evidence_by_field(
    evidence_items: list[UnifiedEvidence],
) -> dict[str, list[UnifiedEvidence]]:
    """Group evidence by normalized target field."""

    grouped: dict[str, list[UnifiedEvidence]] = {}

    for item in evidence_items:
        grouped.setdefault(item.field, []).append(item)

    return grouped


def strongest_evidence(
    evidence_items: list[UnifiedEvidence],
) -> UnifiedEvidence | None:
    """Return the strongest non-conflicting evidence item."""

    quality_rank = {
        EvidenceQuality.EXACT: 5,
        EvidenceQuality.STRONG: 4,
        EvidenceQuality.MODERATE: 3,
        EvidenceQuality.WEAK: 2,
        EvidenceQuality.CONFLICT: 1,
    }

    candidates = [
        item
        for item in evidence_items
        if not item.is_conflict
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: (
            quality_rank[item.quality],
            item.score,
        ),
    )
