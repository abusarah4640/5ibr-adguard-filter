#!/usr/bin/env python3
"""Blocking-policy foundation for classified domains.

This module intentionally does not replace Analyzer confidence or
recommendation decisions. It adds a separate answer to the question:

    Should a correctly classified domain be considered for blocking?
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BlockingPolicy(StrEnum):
    """Supported blocking-policy decisions."""

    SAFE_TO_BLOCK = "safe-to-block"
    LIKELY_SAFE = "likely-safe"
    NEEDS_TESTING = "needs-testing"
    DO_NOT_BLOCK = "do-not-block"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class BlockingPolicyDecision:
    """One deterministic blocking-policy result."""

    policy: BlockingPolicy
    reason: str
    source: str = "category-policy"


def normalize_category(
    category: str | None,
) -> str:
    """Normalize a category for policy lookup."""

    return " ".join(
        (category or "")
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


CATEGORY_POLICIES: dict[
    str,
    BlockingPolicyDecision,
] = {
    # Advertising endpoints are the safest initial
    # candidates for blocking.
    "ads": BlockingPolicyDecision(
        policy=BlockingPolicy.SAFE_TO_BLOCK,
        reason=(
            "Advertising endpoint classified "
            "under the Ads category."
        ),
    ),
    "advertising": BlockingPolicyDecision(
        policy=BlockingPolicy.SAFE_TO_BLOCK,
        reason=(
            "Advertising endpoint classified "
            "under the Advertising category."
        ),
    ),
    "tracking": BlockingPolicyDecision(
        policy=BlockingPolicy.SAFE_TO_BLOCK,
        reason=(
            "Tracking endpoint classified "
            "under the Tracking category."
        ),
    ),
    "malvertising": BlockingPolicyDecision(
        policy=BlockingPolicy.SAFE_TO_BLOCK,
        reason=(
            "Malvertising endpoint is a direct "
            "blocking candidate."
        ),
    ),

    # Telemetry-like traffic may be safe to block,
    # but requires device and application testing.
    "telemetry": BlockingPolicyDecision(
        policy=BlockingPolicy.NEEDS_TESTING,
        reason=(
            "Telemetry can often be blocked, "
            "but application impact must be tested."
        ),
    ),
    "analytics": BlockingPolicyDecision(
        policy=BlockingPolicy.NEEDS_TESTING,
        reason=(
            "Analytics traffic requires impact "
            "testing before blocking."
        ),
    ),
    "metrics": BlockingPolicyDecision(
        policy=BlockingPolicy.NEEDS_TESTING,
        reason=(
            "Metrics traffic requires impact "
            "testing before blocking."
        ),
    ),
    "crash reporting": BlockingPolicyDecision(
        policy=BlockingPolicy.NEEDS_TESTING,
        reason=(
            "Crash-reporting traffic may affect "
            "diagnostics and requires testing."
        ),
    ),

    # Operational service categories are protected
    # by the conservative foundation policy.
    "streaming": BlockingPolicyDecision(
        policy=BlockingPolicy.DO_NOT_BLOCK,
        reason=(
            "Streaming endpoints may be required "
            "for playback, discovery or session control."
        ),
    ),
    "gaming": BlockingPolicyDecision(
        policy=BlockingPolicy.DO_NOT_BLOCK,
        reason=(
            "Gaming endpoints may be required "
            "for login, matchmaking or game services."
        ),
    ),
    "smart tv": BlockingPolicyDecision(
        policy=BlockingPolicy.DO_NOT_BLOCK,
        reason=(
            "Smart TV endpoints may be required "
            "for device and application operation."
        ),
    ),
    "connectivity": BlockingPolicyDecision(
        policy=BlockingPolicy.DO_NOT_BLOCK,
        reason=(
            "Connectivity endpoints are required "
            "for network-state and captive-portal checks."
        ),
    ),
    "system": BlockingPolicyDecision(
        policy=BlockingPolicy.DO_NOT_BLOCK,
        reason=(
            "System endpoints are protected by "
            "the conservative blocking policy."
        ),
    ),
    "updates": BlockingPolicyDecision(
        policy=BlockingPolicy.DO_NOT_BLOCK,
        reason=(
            "Update endpoints are protected to "
            "avoid breaking security and software updates."
        ),
    ),
    "authentication": BlockingPolicyDecision(
        policy=BlockingPolicy.DO_NOT_BLOCK,
        reason=(
            "Authentication endpoints are required "
            "for account and session access."
        ),
    ),
    "cdn": BlockingPolicyDecision(
        policy=BlockingPolicy.DO_NOT_BLOCK,
        reason=(
            "CDN endpoints may deliver required "
            "application or media content."
        ),
    ),
    "dns": BlockingPolicyDecision(
        policy=BlockingPolicy.DO_NOT_BLOCK,
        reason=(
            "DNS infrastructure must not be blocked "
            "by the default policy."
        ),
    ),
    "ntp": BlockingPolicyDecision(
        policy=BlockingPolicy.DO_NOT_BLOCK,
        reason=(
            "Time-synchronization infrastructure "
            "must not be blocked by the default policy."
        ),
    ),
}


def classify_blocking_policy(
    category: str | None,
) -> BlockingPolicyDecision:
    """Return the conservative policy for a category."""

    normalized = normalize_category(
        category
    )

    if not normalized:
        return BlockingPolicyDecision(
            policy=BlockingPolicy.UNKNOWN,
            reason=(
                "No category was available for "
                "blocking-policy evaluation."
            ),
            source="fallback",
        )

    decision = CATEGORY_POLICIES.get(
        normalized
    )

    if decision is not None:
        return decision

    return BlockingPolicyDecision(
        policy=BlockingPolicy.UNKNOWN,
        reason=(
            "No blocking policy is defined for "
            f"category: {category}."
        ),
        source="fallback",
    )


def blocking_policy_value(
    category: str | None,
) -> str:
    """Return only the serialized policy value."""

    return classify_blocking_policy(
        category
    ).policy.value
