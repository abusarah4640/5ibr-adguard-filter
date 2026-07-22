"""Adapt DatabaseEvidence into UnifiedEvidence items."""

from __future__ import annotations

from scripts.services.database_evidence_engine import (
    DatabaseEvidence,
)
from scripts.services.evidence_quality import (
    EvidenceQuality,
)
from scripts.services.unified_evidence import (
    UnifiedEvidence,
    make_unified_evidence,
)


DATABASE_FIELD_MAP = {
    "vendor": "vendor",
    "category": "category",
    "filter_name": "filter",
}


def _database_evidence_quality(
    evidence: DatabaseEvidence,
) -> EvidenceQuality:
    """Read EvidenceQuality from DatabaseEvidence safely."""

    raw_quality = str(
        evidence.evidence_quality
        or EvidenceQuality.MODERATE.value
    ).strip().upper()

    try:
        return EvidenceQuality(raw_quality)
    except ValueError:
        return EvidenceQuality.MODERATE


def database_evidence_to_unified_evidence(
    evidence: DatabaseEvidence,
) -> list[UnifiedEvidence]:
    """Convert DatabaseEvidence into normalized evidence items."""

    if evidence.score <= 0:
        return []

    quality = _database_evidence_quality(evidence)

    reason = (
        evidence.evidence_reason.strip()
        if evidence.evidence_reason
        else (
            evidence.reasons[0].strip()
            if evidence.reasons
            else "database evidence match"
        )
    )

    common_metadata = {
        "database_score": evidence.score,
        "database_reasons": list(evidence.reasons),
        "evidence_quality": quality.value,
        "evidence_reason": reason,
    }

    evidence_items: list[UnifiedEvidence] = []

    for attribute, field in DATABASE_FIELD_MAP.items():
        value = str(
            getattr(evidence, attribute, "") or ""
        ).strip()

        if not value:
            continue

        if field == "vendor" and value == "Unknown":
            continue

        if field == "category" and value == "Unknown":
            continue

        if field == "filter" and value == "unknown":
            continue

        evidence_items.append(
            make_unified_evidence(
                source="database",
                field=field,
                value=value,
                quality=quality,
                score=evidence.score,
                reason=reason,
                metadata={
                    **common_metadata,
                    "target": field,
                    "source_attribute": attribute,
                },
            )
        )

    return evidence_items
