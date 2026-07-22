"""Evidence quality levels for 5ibr Filter Toolkit."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceQuality(StrEnum):
    EXACT = "EXACT"
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class EvidenceAssessment:
    quality: EvidenceQuality
    score: int
    reason: str


def quality_score(quality: EvidenceQuality) -> int:
    scores = {
        EvidenceQuality.EXACT: 50,
        EvidenceQuality.STRONG: 35,
        EvidenceQuality.MODERATE: 20,
        EvidenceQuality.WEAK: 10,
        EvidenceQuality.CONFLICT: 0,
    }

    return scores[quality]


def assess_domain_evidence(
    domain: str,
    pattern: str,
) -> EvidenceAssessment:
    normalized_domain = (domain or "").strip().lower().strip(".")
    normalized_pattern = (pattern or "").strip().lower().strip(".")

    if not normalized_domain or not normalized_pattern:
        return EvidenceAssessment(
            quality=EvidenceQuality.WEAK,
            score=quality_score(EvidenceQuality.WEAK),
            reason="empty or incomplete evidence",
        )

    if normalized_domain == normalized_pattern:
        return EvidenceAssessment(
            quality=EvidenceQuality.EXACT,
            score=quality_score(EvidenceQuality.EXACT),
            reason=f"exact domain match: {normalized_pattern}",
        )

    if (
        "." in normalized_pattern
        and normalized_domain.endswith(f".{normalized_pattern}")
    ):
        return EvidenceAssessment(
            quality=EvidenceQuality.STRONG,
            score=quality_score(EvidenceQuality.STRONG),
            reason=f"trusted domain suffix match: {normalized_pattern}",
        )

    if normalized_pattern in normalized_domain:
        return EvidenceAssessment(
            quality=EvidenceQuality.MODERATE,
            score=quality_score(EvidenceQuality.MODERATE),
            reason=f"keyword match: {normalized_pattern}",
        )

    return EvidenceAssessment(
        quality=EvidenceQuality.WEAK,
        score=quality_score(EvidenceQuality.WEAK),
        reason=f"weak unmatched evidence: {normalized_pattern}",
    )


def conflict_evidence(
    *,
    rule_value: str,
    knowledge_value: str,
    field_name: str,
) -> EvidenceAssessment:
    return EvidenceAssessment(
        quality=EvidenceQuality.CONFLICT,
        score=quality_score(EvidenceQuality.CONFLICT),
        reason=(
            f"conflicting {field_name} evidence: "
            f"rule={rule_value}, knowledge={knowledge_value}"
        ),
    )
