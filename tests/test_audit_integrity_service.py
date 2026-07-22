import hashlib
import json
from pathlib import Path

from scripts.services.audit_integrity_service import (
    AUDIT_INTEGRITY_FAIL,
    AUDIT_INTEGRITY_PASS,
    CURRENT_POLICY,
    HISTORICAL_POLICY,
    INVALID,
    evaluate_audit_integrity,
)


def write_json(
    path: Path,
    payload: dict,
) -> None:
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def make_policy(
    tmp_path: Path,
) -> tuple[Path, str]:
    path = tmp_path / "policies.json"

    write_json(
        path,
        {
            "version": 1,
            "mode": "shadow",
            "policies": [
                {
                    "category": "Streaming",
                    "current_filter": "social",
                    "proposed_filter": "streaming",
                    "authorized_suffixes": [
                        "shahid.net"
                    ],
                }
            ],
        },
    )

    sha = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

    return path, sha


def make_event(
    sha: str,
    **overrides,
) -> dict:
    event = {
        "timestamp_utc": (
            "2026-07-12T07:26:29+00:00"
        ),
        "domain": "api3.shahid.net",
        "matched_suffix": "shahid.net",
        "category": "Streaming",
        "before_filter": "social",
        "after_filter": "streaming",
        "confidence": 65,
        "recommendation": "review",
        "policy_sha256": sha,
        "readiness_decision": (
            "PROMOTION_READY"
        ),
        "enforcement_enabled": True,
    }

    event.update(overrides)
    return event


def write_events(
    path: Path,
    events: list[dict],
) -> None:
    path.write_text(
        "".join(
            json.dumps(event) + "\n"
            for event in events
        ),
        encoding="utf-8",
    )


def test_current_policy_event_passes(
    tmp_path,
):
    policy, sha = make_policy(tmp_path)
    audit = tmp_path / "audit.jsonl"

    write_events(
        audit,
        [make_event(sha)],
    )

    result = evaluate_audit_integrity(
        audit_path=audit,
        policy_path=policy,
    )

    assert (
        result.decision
        == AUDIT_INTEGRITY_PASS
    )
    assert result.current_policy_events == 1
    assert (
        result.assessments[0].classification
        == CURRENT_POLICY
    )


def test_historical_hash_is_valid(
    tmp_path,
):
    policy, _ = make_policy(tmp_path)
    audit = tmp_path / "audit.jsonl"

    write_events(
        audit,
        [make_event("a" * 64)],
    )

    result = evaluate_audit_integrity(
        audit_path=audit,
        policy_path=policy,
    )

    assert (
        result.decision
        == AUDIT_INTEGRITY_PASS
    )
    assert (
        result.historical_policy_events
        == 1
    )
    assert (
        result.assessments[0].classification
        == HISTORICAL_POLICY
    )


def test_duplicate_domain_is_not_corruption(
    tmp_path,
):
    policy, sha = make_policy(tmp_path)
    audit = tmp_path / "audit.jsonl"

    write_events(
        audit,
        [
            make_event(sha),
            make_event(sha),
        ],
    )

    result = evaluate_audit_integrity(
        audit_path=audit,
        policy_path=policy,
    )

    assert (
        result.decision
        == AUDIT_INTEGRITY_PASS
    )
    assert result.valid_events == 2
    assert result.unique_domains == 1
    assert result.duplicate_domains == {
        "api3.shahid.net": 2
    }


def test_invalid_json_fails(
    tmp_path,
):
    policy, _ = make_policy(tmp_path)
    audit = tmp_path / "audit.jsonl"

    audit.write_text(
        "{broken json\n",
        encoding="utf-8",
    )

    result = evaluate_audit_integrity(
        audit_path=audit,
        policy_path=policy,
    )

    assert (
        result.decision
        == AUDIT_INTEGRITY_FAIL
    )
    assert result.invalid_events == 1
    assert (
        result.assessments[0].classification
        == INVALID
    )


def test_missing_field_fails(
    tmp_path,
):
    policy, sha = make_policy(tmp_path)
    audit = tmp_path / "audit.jsonl"

    event = make_event(sha)
    del event["matched_suffix"]

    write_events(audit, [event])

    result = evaluate_audit_integrity(
        audit_path=audit,
        policy_path=policy,
    )

    assert (
        result.decision
        == AUDIT_INTEGRITY_FAIL
    )
    assert result.invalid_events == 1


def test_out_of_scope_event_fails(
    tmp_path,
):
    policy, sha = make_policy(tmp_path)
    audit = tmp_path / "audit.jsonl"

    write_events(
        audit,
        [
            make_event(
                sha,
                domain="example.invalid",
            )
        ],
    )

    result = evaluate_audit_integrity(
        audit_path=audit,
        policy_path=policy,
    )

    assert (
        result.decision
        == AUDIT_INTEGRITY_FAIL
    )
    assert result.invalid_events == 1
