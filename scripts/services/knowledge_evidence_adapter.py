"""Adapt Knowledge Engine matches into UnifiedEvidence items."""

from __future__ import annotations

from scripts.services.knowledge_engine import (
    knowledge_match_assessment,
    knowledge_match_score,
)
from scripts.services.knowledge_service import (
    KnowledgeEntry,
    normalize_text,
)
from scripts.services.unified_evidence import (
    UnifiedEvidence,
    make_unified_evidence,
)


def matched_knowledge_keywords(
    domain: str,
    entry: KnowledgeEntry,
) -> tuple[str, ...]:
    """Return entry keywords that matched the supplied domain."""

    normalized_domain = normalize_text(domain)

    return tuple(
        keyword
        for keyword in entry.keywords
        if normalize_text(keyword)
        and normalize_text(keyword) in normalized_domain
    )


def knowledge_entry_to_unified_evidence(
    domain: str,
    entry: KnowledgeEntry,
) -> list[UnifiedEvidence]:
    """Convert a matched KnowledgeEntry into normalized evidence items.

    The adapter does not alter Analyzer behavior. It only exposes the
    existing Knowledge Engine result through the UnifiedEvidence model.
    """

    assessment = knowledge_match_assessment(
        domain,
        entry,
    )

    score = knowledge_match_score(
        domain,
        entry,
    )

    if score <= 0:
        return []

    matched_keywords = matched_knowledge_keywords(
        domain,
        entry,
    )

    common_metadata = {
        "domain": normalize_text(domain),
        "entry_name": entry.name,
        "entry_kind": entry.kind,
        "matched_keywords": list(matched_keywords),
        "technologies": list(entry.technologies),
        "assessment_score": assessment.score,
    }

    evidence_items: list[UnifiedEvidence] = []

    if entry.vendor and entry.vendor != "Unknown":
        evidence_items.append(
            make_unified_evidence(
                source="knowledge",
                field="vendor",
                value=entry.vendor,
                quality=assessment.quality,
                score=score,
                reason=(
                    f"knowledge matched {entry.kind}: "
                    f"{entry.name}; {assessment.reason}"
                ),
                metadata={
                    **common_metadata,
                    "target": "vendor",
                },
            )
        )

    if entry.category and entry.category != "Unknown":
        evidence_items.append(
            make_unified_evidence(
                source="knowledge",
                field="category",
                value=entry.category,
                quality=assessment.quality,
                score=score,
                reason=(
                    f"knowledge matched {entry.kind}: "
                    f"{entry.name}; {assessment.reason}"
                ),
                metadata={
                    **common_metadata,
                    "target": "category",
                },
            )
        )

    if entry.filter_name and entry.filter_name != "unknown":
        evidence_items.append(
            make_unified_evidence(
                source="knowledge",
                field="filter",
                value=entry.filter_name,
                quality=assessment.quality,
                score=score,
                reason=(
                    f"knowledge matched {entry.kind}: "
                    f"{entry.name}; {assessment.reason}"
                ),
                metadata={
                    **common_metadata,
                    "target": "filter",
                },
            )
        )

    return evidence_items
