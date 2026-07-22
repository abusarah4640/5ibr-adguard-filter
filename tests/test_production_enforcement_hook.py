import hashlib
import json
from pathlib import Path

from scripts.services.analyzer_service import (
    analyze_domain,
)
from scripts.services.production_enforcement_hook import (
    apply_production_enforcement,
)


def write_json(
    path: Path,
    data: dict,
) -> None:
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def make_artifacts(
    tmp_path,
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

    return config, policy, readiness


def test_disabled_returns_original_object(
    tmp_path,
):
    config, policy, readiness = (
        make_artifacts(
            tmp_path,
            enabled=False,
        )
    )

    analysis = analyze_domain(
        "api3.shahid.net",
        rows=[],
    )

    result = apply_production_enforcement(
        analysis,
        enforcement_config_path=config,
        policy_path=policy,
        readiness_path=readiness,
    )

    assert result is analysis


def test_enabled_changes_filter_only(
    tmp_path,
):
    config, policy, readiness = (
        make_artifacts(
            tmp_path,
            enabled=True,
        )
    )

    analysis = analyze_domain(
        "api3.shahid.net",
        rows=[],
    )

    audit_path = tmp_path / "audit.jsonl"

    result = apply_production_enforcement(
        analysis,
        enforcement_config_path=config,
        policy_path=policy,
        readiness_path=readiness,
        audit_path=audit_path,
    )

    assert result is not analysis
    assert audit_path.exists()

    assert (
        analysis.suggested_filter
        == "social"
    )

    assert (
        result.suggested_filter
        == "streaming"
    )

    assert (
        result.suggested_vendor
        == analysis.suggested_vendor
    )

    assert (
        result.suggested_category
        == analysis.suggested_category
    )

    assert (
        result.confidence
        == analysis.confidence
    )

    assert (
        result.recommendation
        == analysis.recommendation
    )

    assert result.reasons == analysis.reasons


def test_wrong_hash_fails_closed(
    tmp_path,
):
    config, policy, readiness = (
        make_artifacts(
            tmp_path,
            enabled=True,
        )
    )

    payload = json.loads(
        config.read_text(encoding="utf-8")
    )

    payload["policy_sha256"] = "a" * 64

    write_json(config, payload)

    analysis = analyze_domain(
        "api3.shahid.net",
        rows=[],
    )

    result = apply_production_enforcement(
        analysis,
        enforcement_config_path=config,
        policy_path=policy,
        readiness_path=readiness,
    )

    assert result is analysis


def test_blocked_readiness_fails_closed(
    tmp_path,
):
    config, policy, readiness = (
        make_artifacts(
            tmp_path,
            enabled=True,
        )
    )

    payload = json.loads(
        readiness.read_text(
            encoding="utf-8"
        )
    )

    payload["decision"] = (
        "PROMOTION_BLOCKED"
    )

    write_json(readiness, payload)

    analysis = analyze_domain(
        "api3.shahid.net",
        rows=[],
    )

    result = apply_production_enforcement(
        analysis,
        enforcement_config_path=config,
        policy_path=policy,
        readiness_path=readiness,
    )

    assert result is analysis


def test_non_matching_domain_is_unchanged(
    tmp_path,
):
    config, policy, readiness = (
        make_artifacts(
            tmp_path,
            enabled=True,
        )
    )

    analysis = analyze_domain(
        "example.invalid",
        rows=[],
    )

    result = apply_production_enforcement(
        analysis,
        enforcement_config_path=config,
        policy_path=policy,
        readiness_path=readiness,
    )

    assert result is analysis


def test_matching_suffix_but_unauthorized_domain_is_unchanged(
    tmp_path,
):
    config, policy, readiness = (
        make_artifacts(
            tmp_path,
            enabled=True,
        )
    )

    audit_path = (
        tmp_path / "audit.jsonl"
    )

    analysis = analyze_domain(
        "tvweb.shahid.net",
        rows=[],
    )

    result = apply_production_enforcement(
        analysis,
        enforcement_config_path=config,
        policy_path=policy,
        readiness_path=readiness,
        audit_path=audit_path,
    )

    assert result is analysis
    assert (
        result.suggested_filter
        == analysis.suggested_filter
    )
    assert not audit_path.exists()


def test_missing_authorized_domains_fails_closed(
    tmp_path,
):
    config, policy, readiness = (
        make_artifacts(
            tmp_path,
            enabled=True,
        )
    )

    payload = json.loads(
        config.read_text(encoding="utf-8")
    )

    payload.pop(
        "authorized_domains"
    )

    write_json(
        config,
        payload,
    )

    audit_path = (
        tmp_path / "audit.jsonl"
    )

    analysis = analyze_domain(
        "api3.shahid.net",
        rows=[],
    )

    result = apply_production_enforcement(
        analysis,
        enforcement_config_path=config,
        policy_path=policy,
        readiness_path=readiness,
        audit_path=audit_path,
    )

    assert result is analysis
    assert not audit_path.exists()
