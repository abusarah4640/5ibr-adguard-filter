"""Rule Engine foundation for 5ibr Filter Toolkit."""

from __future__ import annotations

from scripts.services.evidence_quality import (
    EvidenceAssessment,
    assess_domain_evidence,
)

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RuleMatch:
    rule_type: str
    value: str
    score: int
    reason: str
    metadata: dict[str, str] = field(default_factory=dict)


def normalize_rule_text(value: str) -> str:
    return (value or "").strip().lower()


def matches_pattern(domain: str, pattern: str) -> bool:
    normalized_domain = normalize_rule_text(domain)
    normalized_pattern = normalize_rule_text(pattern)

    if not normalized_domain or not normalized_pattern:
        return False

    return (
        normalized_domain == normalized_pattern
        or normalized_domain.endswith(f".{normalized_pattern}")
        or normalized_pattern in normalized_domain
    )



def rule_evidence_assessment(
    domain: str,
    pattern: str,
) -> EvidenceAssessment:
    """Return structured evidence quality for a rule match."""

    return assess_domain_evidence(domain, pattern)


def rule_evidence_metadata(
    assessment: EvidenceAssessment,
    *,
    key: str,
    value: str,
) -> dict[str, str]:
    """Build serializable metadata for a rule match."""

    return {
        key: value,
        "evidence_quality": assessment.quality.value,
        "evidence_reason": assessment.reason,
    }

def match_vendor_rules(domain: str, vendor_patterns: dict[str, list[str]]) -> list[RuleMatch]:
    matches: list[RuleMatch] = []

    for vendor, patterns in vendor_patterns.items():
        for pattern in patterns:
            if matches_pattern(domain, pattern):
                assessment = rule_evidence_assessment(
                    domain,
                    pattern,
                )

                matches.append(
                    RuleMatch(
                        rule_type="vendor",
                        value=vendor,
                        score=35,
                        reason=f"matched known vendor namespace: {pattern}",
                        metadata=rule_evidence_metadata(
                            assessment,
                            key="pattern",
                            value=pattern,
                        ),
                    )
                )
                break

    return matches


def match_category_rules(domain: str, category_keywords: dict[str, list[str]]) -> list[RuleMatch]:
    normalized = normalize_rule_text(domain)
    matches: list[RuleMatch] = []

    if not normalized:
        return matches

    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if normalize_rule_text(keyword) in normalized:
                assessment = rule_evidence_assessment(
                    domain,
                    keyword,
                )

                matches.append(
                    RuleMatch(
                        rule_type="category",
                        value=category,
                        score=30,
                        reason=f"matched category keyword: {keyword}",
                        metadata=rule_evidence_metadata(
                            assessment,
                            key="keyword",
                            value=keyword,
                        ),
                    )
                )
                break

    return matches


def first_match(matches: list[RuleMatch], rule_type: str) -> RuleMatch | None:
    for match in matches:
        if match.rule_type == rule_type:
            return match
    return None


def total_score(matches: list[RuleMatch]) -> int:
    return sum(match.score for match in matches)
