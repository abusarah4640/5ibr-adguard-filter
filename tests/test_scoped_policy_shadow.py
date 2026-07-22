import json

from scripts.services.controlled_promotion_simulation import (
    SimulatedDecision,
)
from scripts.services.scoped_policy_shadow import (
    eligible_target_domains,
    evaluate_shadow_decision,
    load_scoped_policy_artifact,
)


def write_policy(
    path,
    *,
    policies=None,
):
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "shadow",
                "policies": (
                    policies
                    if policies is not None
                    else [
                        {
                            "category": "Streaming",
                            "current_filter": "social",
                            "proposed_filter": "streaming",
                            "authorized_suffixes": [
                                "shahid.net"
                            ],
                        }
                    ]
                ),
            }
        ),
        encoding="utf-8",
    )


def test_load_valid_policy_artifact(tmp_path):
    path = tmp_path / "policies.json"
    write_policy(path)

    policies = (
        load_scoped_policy_artifact(
            path
        )
    )

    assert len(policies) == 1

    policy = policies[0]

    assert policy.category == "Streaming"
    assert policy.current_filter == "social"
    assert (
        policy.proposed_filter
        == "streaming"
    )
    assert policy.authorized_suffixes == (
        "shahid.net",
    )


def test_policy_artifact_requires_shadow_mode(
    tmp_path,
):
    path = tmp_path / "policies.json"

    path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "production",
                "policies": [],
            }
        ),
        encoding="utf-8",
    )

    try:
        load_scoped_policy_artifact(path)
    except ValueError as exc:
        assert "shadow mode" in str(exc)
    else:
        raise AssertionError(
            "production policy artifact was accepted"
        )


def test_overlapping_policy_suffixes_are_rejected(
    tmp_path,
):
    path = tmp_path / "policies.json"

    write_policy(
        path,
        policies=[
            {
                "category": "Streaming",
                "current_filter": "social",
                "proposed_filter": "streaming",
                "authorized_suffixes": [
                    "example.com"
                ],
            },
            {
                "category": "Streaming",
                "current_filter": "social",
                "proposed_filter": "streaming",
                "authorized_suffixes": [
                    "video.example.com"
                ],
            },
        ],
    )

    try:
        load_scoped_policy_artifact(path)
    except ValueError as exc:
        assert (
            "overlapping scoped policies"
            in str(exc)
        )
    else:
        raise AssertionError(
            "overlapping policies were accepted"
        )


def test_eligible_target_domains():
    targets = eligible_target_domains(
        {
            "results": [
                {
                    "domain": "api3.shahid.net",
                    "eligible": True,
                    "decision": (
                        "eligible-for-controlled-promotion"
                    ),
                    "production_changed": False,
                },
                {
                    "domain": "media.net",
                    "eligible": False,
                    "decision": "hold-for-review",
                    "production_changed": False,
                },
            ]
        }
    )

    assert targets == {
        "api3.shahid.net"
    }


def test_shadow_decision_changes_filter_only(
    tmp_path,
):
    path = tmp_path / "policies.json"
    write_policy(path)

    policies = (
        load_scoped_policy_artifact(
            path
        )
    )

    control = SimulatedDecision(
        vendor="Shahid",
        category="Streaming",
        filter_name="social",
        confidence=65,
        recommendation="review",
    )

    change = evaluate_shadow_decision(
        domain="api3.shahid.net",
        seen=100,
        control=control,
        policies=policies,
        target_domains={
            "api3.shahid.net"
        },
    )

    assert change is not None
    assert change.expected_target
    assert change.matched_suffix == (
        "shahid.net"
    )
    assert change.changed_fields == (
        "filter",
    )
    assert (
        change.after.filter_name
        == "streaming"
    )
    assert (
        change.after.confidence
        == control.confidence
    )
    assert (
        change.after.recommendation
        == control.recommendation
    )
