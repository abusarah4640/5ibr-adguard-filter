from scripts.services.analyzer_service import (
    DomainAnalysis,
    analyze_domain,
)


def test_ads_receive_safe_to_block_policy():
    result = analyze_domain(
        "tpc.googlesyndication.com",
        rows=[],
    )

    assert result.suggested_category == "Ads"

    assert (
        result.blocking_policy
        == "safe-to-block"
    )

    assert (
        result.blocking_policy_source
        == "category-policy"
    )

    assert "Advertising" in (
        result.blocking_policy_reason
    )


def test_telemetry_receives_needs_testing_policy():
    result = analyze_domain(
        "beacons.gvt2.com",
        rows=[],
    )

    assert (
        result.suggested_category
        == "Telemetry"
    )

    assert (
        result.blocking_policy
        == "needs-testing"
    )

    assert "test" in (
        result.blocking_policy_reason
        .lower()
    )


def test_streaming_is_protected_by_policy():
    result = analyze_domain(
        "youtubei.googleapis.com",
        rows=[],
    )

    assert (
        result.suggested_category
        == "Streaming"
    )

    # Confidence and recommendation describe
    # classification evidence, not blocking safety.
    assert result.confidence > 0

    assert (
        result.blocking_policy
        == "do-not-block"
    )

    assert (
        result.blocking_policy_source
        == "category-policy"
    )

    assert "Streaming" in (
        result.blocking_policy_reason
    )


def test_gaming_is_protected_from_default_blocking():
    result = analyze_domain(
        "event.api.np.km.playstation.net",
        rows=[],
    )

    assert (
        result.suggested_category
        == "Gaming"
    )

    assert (
        result.blocking_policy
        == "do-not-block"
    )


def test_unknown_category_uses_unknown_policy():
    result = analyze_domain(
        "unknown-random-policy.invalid",
        rows=[],
    )

    assert (
        result.suggested_category
        == "Unknown"
    )

    assert (
        result.blocking_policy
        == "unknown"
    )

    assert (
        result.blocking_policy_source
        == "fallback"
    )


def test_domain_analysis_defaults_remain_compatible():
    result = DomainAnalysis(
        domain="example.invalid",
        root_domain="example.invalid",
    )

    assert (
        result.recommendation
        == "unknown"
    )

    assert (
        result.blocking_policy
        == "unknown"
    )

    assert (
        result.blocking_policy_reason
        == ""
    )

    assert (
        result.blocking_policy_source
        == "fallback"
    )

    assert result.reasons == []
