"""Adapt Rule Engine matches into UnifiedEvidence items."""

from __future__ import annotations

from scripts.services.evidence_quality import EvidenceQuality
from scripts.services.rule_engine import RuleMatch
from scripts.services.unified_evidence import (
    UnifiedEvidence,
    make_unified_evidence,
)


RULE_TYPE_TO_FIELD = {
    "vendor": "vendor",
    "category": "category",
    "filter": "filter",
}


def _evidence_quality_from_metadata(
    match: RuleMatch,
) -> EvidenceQuality:
    """Read EvidenceQuality from RuleMatch metadata safely."""

    raw_quality = str(
        match.metadata.get(
            "evidence_quality",
            EvidenceQuality.MODERATE.value,
        )
    ).strip().upper()

    try:
        return EvidenceQuality(raw_quality)
    except ValueError:
        return EvidenceQuality.MODERATE


def rule_match_to_unified_evidence(
    match: RuleMatch,
) -> UnifiedEvidence:
    """Convert one RuleMatch into a normalized evidence item."""

    rule_type = str(match.rule_type).strip().lower()

    if rule_type not in RULE_TYPE_TO_FIELD:
        raise ValueError(
            f"unsupported rule match type: {match.rule_type}"
        )

    field = RULE_TYPE_TO_FIELD[rule_type]
    quality = _evidence_quality_from_metadata(match)

    evidence_reason = str(
        match.metadata.get(
            "evidence_reason",
            match.reason,
        )
    ).strip()

    metadata = {
        **dict(match.metadata),
        "rule_type": rule_type,
        "original_reason": match.reason,
    }

    return make_unified_evidence(
        source="rule",
        field=field,
        value=match.value,
        quality=quality,
        score=match.score,
        reason=evidence_reason,
        metadata=metadata,
    )


def rule_matches_to_unified_evidence(
    matches: list[RuleMatch],
) -> list[UnifiedEvidence]:
    """Convert a list of RuleMatch objects into unified evidence."""

    return [
        rule_match_to_unified_evidence(match)
        for match in matches
    ]
