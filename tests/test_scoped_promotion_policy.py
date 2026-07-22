from scripts.services.controlled_promotion_simulation import (
    SimulatedDecision,
)
from scripts.services.scoped_promotion_policy import (
    apply_scoped_policy,
    build_scoped_policies,
    domain_matches_suffix,
    find_matching_policy,
)


def eligible_row(
    *,
    domain: str,
    family: str,
    category: str,
    current_filter: str,
    proposed_filter: str,
):
    return {
        "domain": domain,
        "family": family,
        "eligible": True,
        "decision": (
            "eligible-for-controlled-promotion"
        ),
        "root_cause": (
            "legacy-mapping-leakage"
        ),
        "current": {
            "category": category,
            "filter": current_filter,
        },
        "proposed_filter": proposed_filter,
        "production_changed": False,
    }


def test_domain_suffix_matching_is_explicit():
    assert domain_matches_suffix(
        "api3.shahid.net",
        "shahid.net",
    )

    assert domain_matches_suffix(
        "shahid.net",
        "shahid.net",
    )

    assert not domain_matches_suffix(
        "notshahid.net",
        "shahid.net",
    )

    assert not domain_matches_suffix(
        "shahid.net.example.com",
        "shahid.net",
    )


def test_build_scoped_policies_groups_suffixes():
    policies = build_scoped_policies(
        [
            eligible_row(
                domain="api3.shahid.net",
                family="shahid.net",
                category="Streaming",
                current_filter="social",
                proposed_filter="streaming",
            ),
            eligible_row(
                domain="qgmg.api.amazonvideo.com",
                family="amazonvideo.com",
                category="Streaming",
                current_filter="social",
                proposed_filter="streaming",
            ),
            eligible_row(
                domain="www.gstatic.com",
                family="gstatic.com",
                category="Connectivity",
                current_filter="privacy",
                proposed_filter="connectivity",
            ),
        ]
    )

    assert len(policies) == 2

    streaming = next(
        policy
        for policy in policies
        if policy.category == "Streaming"
    )

    assert streaming.authorized_suffixes == (
        "amazonvideo.com",
        "shahid.net",
    )


def test_policy_matches_authorized_suffix_only():
    policies = build_scoped_policies(
        [
            eligible_row(
                domain="api3.shahid.net",
                family="shahid.net",
                category="Streaming",
                current_filter="social",
                proposed_filter="streaming",
            )
        ]
    )

    decision = SimulatedDecision(
        vendor="Shahid",
        category="Streaming",
        filter_name="social",
        confidence=65,
        recommendation="review",
    )

    policy, suffix = find_matching_policy(
        domain="tvweb.shahid.net",
        decision=decision,
        policies=policies,
    )

    assert policy is not None
    assert suffix == "shahid.net"

    no_policy, no_suffix = (
        find_matching_policy(
            domain="shahid.mbc.net",
            decision=decision,
            policies=policies,
        )
    )

    assert no_policy is None
    assert no_suffix == ""


def test_policy_requires_category_and_current_filter():
    policies = build_scoped_policies(
        [
            eligible_row(
                domain="www.gstatic.com",
                family="gstatic.com",
                category="Connectivity",
                current_filter="privacy",
                proposed_filter="connectivity",
            )
        ]
    )

    wrong_category = SimulatedDecision(
        vendor="Google",
        category="Telemetry",
        filter_name="privacy",
        confidence=65,
        recommendation="review",
    )

    policy, _ = find_matching_policy(
        domain="www.gstatic.com",
        decision=wrong_category,
        policies=policies,
    )

    assert policy is None


def test_apply_scoped_policy_changes_filter_only():
    policy = build_scoped_policies(
        [
            eligible_row(
                domain="api3.shahid.net",
                family="shahid.net",
                category="Streaming",
                current_filter="social",
                proposed_filter="streaming",
            )
        ]
    )[0]

    before = SimulatedDecision(
        vendor="Shahid",
        category="Streaming",
        filter_name="social",
        confidence=65,
        recommendation="review",
    )

    after = apply_scoped_policy(
        before,
        policy,
    )

    assert after.vendor == before.vendor
    assert after.category == before.category
    assert after.filter_name == "streaming"
    assert after.confidence == before.confidence
    assert (
        after.recommendation
        == before.recommendation
    )
