"""Database Evidence Engine for 5ibr Filter Toolkit."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from scripts.services.evidence_quality import (
    EvidenceAssessment,
    EvidenceQuality,
    assess_domain_evidence,
)


@dataclass(frozen=True)
class DatabaseEvidence:
    vendor: str = ""
    category: str = ""
    filter_name: str = ""
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    evidence_quality: str = ""
    evidence_reason: str = ""


def normalize_evidence_domain(domain: str) -> str:
    value = (domain or "").strip().lower()
    value = value.removeprefix("http://").removeprefix("https://")
    value = value.split("/", 1)[0].split(":", 1)[0].strip(".")
    return value


def evidence_root_domain(domain: str) -> str:
    parts = [
        part
        for part in normalize_evidence_domain(domain).split(".")
        if part
    ]

    if len(parts) <= 2:
        return ".".join(parts)

    return ".".join(parts[-2:])


def database_evidence_assessment(
    domain: str,
    existing_domain: str,
) -> EvidenceAssessment:
    """Return structured quality for database evidence."""

    normalized = normalize_evidence_domain(domain)
    existing = normalize_evidence_domain(existing_domain)

    if normalized == existing:
        return assess_domain_evidence(
            normalized,
            existing,
        )

    domain_root = evidence_root_domain(normalized)
    existing_root = evidence_root_domain(existing)

    if domain_root and domain_root == existing_root:
        return EvidenceAssessment(
            quality=EvidenceQuality.STRONG,
            score=35,
            reason=f"shared database root match: {domain_root}",
        )

    return assess_domain_evidence(
        normalized,
        existing,
    )


def _strongest_assessment(
    assessments: list[EvidenceAssessment],
) -> EvidenceAssessment | None:
    if not assessments:
        return None

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


def match_database_evidence(
    domain: str,
    rows: list[dict],
) -> DatabaseEvidence:
    """Infer values from existing database domains with shared patterns."""

    normalized = normalize_evidence_domain(domain)
    domain_root = evidence_root_domain(normalized)

    vendor_votes: Counter[str] = Counter()
    category_votes: Counter[str] = Counter()
    filter_votes: Counter[str] = Counter()

    reasons: list[str] = []
    assessments: list[EvidenceAssessment] = []
    score = 0

    for row in rows:
        existing = normalize_evidence_domain(
            row.get("Domain", "")
        )

        if not existing:
            continue

        existing_root = evidence_root_domain(existing)

        if normalized == existing:
            vendor_votes[row.get("Vendor", "")] += 4
            category_votes[row.get("Category", "")] += 4
            filter_votes[row.get("Filter", "")] += 4

            reasons.append(
                f"matched existing database domain: {existing}"
            )

            assessments.append(
                database_evidence_assessment(
                    normalized,
                    existing,
                )
            )

            # Preserve existing analyzer behavior.
            score += 35

        elif domain_root and domain_root == existing_root:
            vendor_votes[row.get("Vendor", "")] += 2
            category_votes[row.get("Category", "")] += 1
            filter_votes[row.get("Filter", "")] += 1

            reason = (
                f"matched existing database root: {domain_root}"
            )

            if reason not in reasons:
                reasons.append(reason)

            assessments.append(
                database_evidence_assessment(
                    normalized,
                    existing,
                )
            )

            # Preserve existing analyzer behavior.
            score += 20

    vendor = (
        vendor_votes.most_common(1)[0][0]
        if vendor_votes
        else ""
    )

    category = (
        category_votes.most_common(1)[0][0]
        if category_votes
        else ""
    )

    filter_name = (
        filter_votes.most_common(1)[0][0]
        if filter_votes
        else ""
    )

    strongest = _strongest_assessment(assessments)

    return DatabaseEvidence(
        vendor=vendor,
        category=category,
        filter_name=filter_name,
        score=min(score, 35),
        reasons=reasons,
        evidence_quality=(
            strongest.quality.value
            if strongest
            else ""
        ),
        evidence_reason=(
            strongest.reason
            if strongest
            else ""
        ),
    )
