from scripts.services.production_readiness_gate import (
    BLOCKED,
    READY,
    ProductionSnapshotComparison,
    build_readiness_report,
    compare_production_snapshots,
    evaluate_promotion_readiness,
    load_recorded_sha256,
)


SHA = "a" * 64


def candidate_gate():
    return {
        "eligible": 13,
        "held": 5,
        "rejected": 0,
        "production_changes": 0,
    }


def scoped_simulation():
    return {
        "target_domains": 13,
        "changed_domains": 13,
        "intended_changes": 13,
        "collateral_changes": 0,
        "unchanged_target_domains": 0,
        "confidence_changes": 0,
        "recommendation_changes": 0,
        "baseline_drift": 0,
        "production_changes": 0,
    }


def shadow_execution():
    return {
        "domains_evaluated": 500,
        "policies_loaded": 2,
        "authorized_suffixes": 3,
        "expected_targets": 13,
        "shadow_matches": 13,
        "expected_matches": 13,
        "unexpected_matches": 0,
        "missed_expected_matches": 0,
        "filter_only_changes": 13,
        "confidence_changes": 0,
        "recommendation_changes": 0,
        "baseline_drift": 0,
        "production_changes": 0,
    }


def regression():
    return ProductionSnapshotComparison(
        before_domains=500,
        after_domains=500,
        common_domains=500,
        changed_domains=0,
        added_domains=0,
        removed_domains=0,
    )


def test_load_recorded_sha256(tmp_path):
    path = tmp_path / "sha.txt"

    path.write_text(
        f"{SHA}  policies.json\n",
        encoding="utf-8",
    )

    assert (
        load_recorded_sha256(path)
        == SHA
    )


def test_compare_unchanged_snapshots():
    rows = [
        {
            "domain": "example.com",
            "vendor": "Example",
            "category": "Streaming",
            "filter": "social",
            "confidence": 50,
            "recommendation": "review",
        }
    ]

    result = compare_production_snapshots(
        rows,
        rows,
    )

    assert result.common_domains == 1
    assert result.changed_domains == 0
    assert result.unchanged == 1
    assert result.added_domains == 0
    assert result.removed_domains == 0


def test_ready_when_all_requirements_pass():
    summary = evaluate_promotion_readiness(
        candidate_gate=candidate_gate(),
        scoped_simulation=(
            scoped_simulation()
        ),
        shadow_execution=(
            shadow_execution()
        ),
        policy_sha256=SHA,
        recorded_policy_sha256=SHA,
        policies_loaded=2,
        authorized_suffixes=3,
        regression=regression(),
    )

    assert summary.decision == READY
    assert summary.ready
    assert summary.checks_failed == 0
    assert not summary.blocking_reasons


def test_blocked_on_unexpected_shadow_match():
    shadow = shadow_execution()
    shadow["unexpected_matches"] = 1

    summary = evaluate_promotion_readiness(
        candidate_gate=candidate_gate(),
        scoped_simulation=(
            scoped_simulation()
        ),
        shadow_execution=shadow,
        policy_sha256=SHA,
        recorded_policy_sha256=SHA,
        policies_loaded=2,
        authorized_suffixes=3,
        regression=regression(),
    )

    assert summary.decision == BLOCKED
    assert not summary.ready
    assert summary.checks_failed == 1


def test_blocked_on_policy_hash_mismatch():
    summary = evaluate_promotion_readiness(
        candidate_gate=candidate_gate(),
        scoped_simulation=(
            scoped_simulation()
        ),
        shadow_execution=(
            shadow_execution()
        ),
        policy_sha256="b" * 64,
        recorded_policy_sha256=SHA,
        policies_loaded=2,
        authorized_suffixes=3,
        regression=regression(),
    )

    assert summary.decision == BLOCKED
    assert summary.checks_failed == 1


def test_readiness_report():
    summary = evaluate_promotion_readiness(
        candidate_gate=candidate_gate(),
        scoped_simulation=(
            scoped_simulation()
        ),
        shadow_execution=(
            shadow_execution()
        ),
        policy_sha256=SHA,
        recorded_policy_sha256=SHA,
        policies_loaded=2,
        authorized_suffixes=3,
        regression=regression(),
    )

    report = build_readiness_report(
        summary
    )

    assert (
        "5ibr Production Promotion Readiness"
        in report
    )
    assert "PROMOTION_READY" in report
    assert "Blocking reasons          : 0" in report
