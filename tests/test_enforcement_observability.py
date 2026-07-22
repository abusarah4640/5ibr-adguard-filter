import hashlib
import json
from pathlib import Path

from scripts.services.analyzer_service import (
    analyze_domain,
)
from scripts.services.enforcement_observability import (
    append_audit_event,
    create_audit_event,
    load_audit_events,
)
from scripts.services.production_enforcement_hook import (
    apply_production_enforcement,
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


def build_artifacts(
    tmp_path: Path,
    *,
    enabled: bool,
):
    policy = tmp_path / "policies.json"

    write_json(
        policy,
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

    policy_sha = hashlib.sha256(
        policy.read_bytes()
    ).hexdigest()

    config = tmp_path / "enforcement.json"

    write_json(
        config,
        {
            "version": 1,
            "enabled": enabled,
            "required_readiness_decision": (
                "PROMOTION_READY"
            ),
            "policy_sha256": policy_sha,
            "authorized_domains": [
                "api3.shahid.net",
                "placeholder-01.example",
                "placeholder-02.example",
                "placeholder-03.example",
                "placeholder-04.example",
                "placeholder-05.example",
                "placeholder-06.example",
                "placeholder-07.example",
                "placeholder-08.example",
                "placeholder-09.example",
                "placeholder-10.example",
                "placeholder-11.example",
                "placeholder-12.example"
            ],
        },
    )

    readiness = tmp_path / "readiness.json"

    write_json(
        readiness,
        {
            "decision": "PROMOTION_READY",
            "checks_failed": 0,
            "blocking_reasons": [],
        },
    )

    return (
        config,
        policy,
        readiness,
        policy_sha,
    )


def test_append_and_load_audit_event(
    tmp_path,
):
    path = tmp_path / "audit.jsonl"

    event = create_audit_event(
        domain="api3.shahid.net",
        matched_suffix="shahid.net",
        category="Streaming",
        before_filter="social",
        after_filter="streaming",
        confidence=65,
        recommendation="review",
        policy_sha256="a" * 64,
        readiness_decision=(
            "PROMOTION_READY"
        ),
        enforcement_enabled=True,
    )

    assert append_audit_event(
        event,
        path=path,
    )

    rows = load_audit_events(path)

    assert len(rows) == 1
    assert (
        rows[0]["domain"]
        == "api3.shahid.net"
    )
    assert (
        rows[0]["before_filter"]
        == "social"
    )
    assert (
        rows[0]["after_filter"]
        == "streaming"
    )


def test_disabled_hook_does_not_write_audit(
    tmp_path,
):
    config, policy, readiness, _ = (
        build_artifacts(
            tmp_path,
            enabled=False,
        )
    )

    audit = tmp_path / "audit.jsonl"

    analysis = analyze_domain(
        "api3.shahid.net",
        rows=[],
    )

    result = apply_production_enforcement(
        analysis,
        enforcement_config_path=config,
        policy_path=policy,
        readiness_path=readiness,
        audit_path=audit,
    )

    assert result is analysis
    assert not audit.exists()


def test_enabled_hook_writes_one_event(
    tmp_path,
):
    (
        config,
        policy,
        readiness,
        policy_sha,
    ) = build_artifacts(
        tmp_path,
        enabled=True,
    )

    audit = tmp_path / "audit.jsonl"

    analysis = analyze_domain(
        "api3.shahid.net",
        rows=[],
    )

    result = apply_production_enforcement(
        analysis,
        enforcement_config_path=config,
        policy_path=policy,
        readiness_path=readiness,
        audit_path=audit,
    )

    assert (
        result.suggested_filter
        == "streaming"
    )

    rows = load_audit_events(audit)

    assert len(rows) == 1

    event = rows[0]

    assert event["domain"] == (
        "api3.shahid.net"
    )
    assert event["matched_suffix"] == (
        "shahid.net"
    )
    assert event["category"] == (
        "Streaming"
    )
    assert event["policy_sha256"] == (
        policy_sha
    )
    assert event["readiness_decision"] == (
        "PROMOTION_READY"
    )
    assert (
        event["enforcement_enabled"]
        is True
    )


def test_non_matching_domain_does_not_write(
    tmp_path,
):
    config, policy, readiness, _ = (
        build_artifacts(
            tmp_path,
            enabled=True,
        )
    )

    audit = tmp_path / "audit.jsonl"

    analysis = analyze_domain(
        "example.invalid",
        rows=[],
    )

    result = apply_production_enforcement(
        analysis,
        enforcement_config_path=config,
        policy_path=policy,
        readiness_path=readiness,
        audit_path=audit,
    )

    assert result is analysis
    assert not audit.exists()


def test_audit_failure_does_not_block_change(
    tmp_path,
):
    config, policy, readiness, _ = (
        build_artifacts(
            tmp_path,
            enabled=True,
        )
    )

    invalid_target = (
        tmp_path
        / "directory-as-file"
    )

    invalid_target.mkdir()

    analysis = analyze_domain(
        "api3.shahid.net",
        rows=[],
    )

    result = apply_production_enforcement(
        analysis,
        enforcement_config_path=config,
        policy_path=policy,
        readiness_path=readiness,
        audit_path=invalid_target,
    )

    assert (
        result.suggested_filter
        == "streaming"
    )
    assert (
        result.confidence
        == analysis.confidence
    )
