"""Knowledge Engine for querying 5ibr Knowledge Base."""

from __future__ import annotations

from scripts.services.evidence_quality import (
    EvidenceAssessment,
    EvidenceQuality,
    assess_domain_evidence,
)

from scripts.services.knowledge_service import (
    KnowledgeEntry,
    explain_knowledge_match,
    load_knowledge_entries,
    match_knowledge,
    normalize_text,
)


def find_by_domain(domain: str) -> list[KnowledgeEntry]:
    return match_knowledge(domain)


def first_domain_match(domain: str) -> KnowledgeEntry | None:
    matches = find_by_domain(domain)
    return matches[0] if matches else None


def explain_domain_match(domain: str) -> list[str]:
    return explain_knowledge_match(domain)


def find_by_keyword(keyword: str) -> list[KnowledgeEntry]:
    normalized = normalize_text(keyword)
    if not normalized:
        return []

    return [
        entry
        for entry in load_knowledge_entries()
        if any(normalize_text(item) == normalized for item in entry.keywords)
    ]


def find_by_vendor(vendor: str) -> list[KnowledgeEntry]:
    normalized = normalize_text(vendor)
    if not normalized:
        return []

    return [
        entry
        for entry in load_knowledge_entries()
        if normalize_text(entry.vendor) == normalized
    ]


def find_by_category(category: str) -> list[KnowledgeEntry]:
    normalized = normalize_text(category)
    if not normalized:
        return []

    return [
        entry
        for entry in load_knowledge_entries()
        if normalize_text(entry.category) == normalized
    ]


def find_by_technology(technology: str) -> list[KnowledgeEntry]:
    normalized = normalize_text(technology)
    if not normalized:
        return []

    return [
        entry
        for entry in load_knowledge_entries()
        if any(normalize_text(item) == normalized for item in entry.technologies)
    ]



def knowledge_match_assessment(
    domain: str,
    entry: KnowledgeEntry,
) -> EvidenceAssessment:
    """Return the strongest evidence assessment for a knowledge entry."""

    assessments = [
        assess_domain_evidence(domain, keyword)
        for keyword in entry.keywords
        if normalize_text(keyword)
    ]

    if not assessments:
        return assess_domain_evidence(domain, "")

    ranking = {
        EvidenceQuality.EXACT: 5,
        EvidenceQuality.STRONG: 4,
        EvidenceQuality.MODERATE: 3,
        EvidenceQuality.WEAK: 2,
        EvidenceQuality.CONFLICT: 1,
    }

    return max(
        assessments,
        key=lambda assessment: (
            ranking[assessment.quality],
            assessment.score,
        ),
    )


def knowledge_match_score(
    domain: str,
    entry: KnowledgeEntry,
) -> int:
    """Return calibrated knowledge confidence from evidence quality.

    Exact domain evidence keeps the full 50 points.
    Trusted suffix evidence receives a 15-point knowledge-source bonus,
    preserving the established 50-point behavior.
    Generic keyword evidence remains 20 points.
    """

    assessment = knowledge_match_assessment(domain, entry)

    if assessment.quality == EvidenceQuality.EXACT:
        return 50

    if assessment.quality == EvidenceQuality.STRONG:
        return min(assessment.score + 15, 50)

    if assessment.quality == EvidenceQuality.MODERATE:
        return assessment.score

    return 0
