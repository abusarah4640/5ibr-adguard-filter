"""Fail-closed production hook for scoped filter enforcement.

This module intentionally does not import analyzer_service or
scoped_policy_enforcement, avoiding circular dependencies.

The hook changes only DomainAnalysis.suggested_filter and only when all
authorization conditions pass. Any configuration, artifact, readiness,
hash, or validation failure returns the original analysis unchanged.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from scripts.services.controlled_promotion_simulation import (
    SimulatedDecision,
)
from scripts.services.enforcement_observability import (
    append_audit_event,
    create_audit_event,
)
from scripts.services.scoped_policy_shadow import (
    load_scoped_policy_artifact,
)
from scripts.services.scoped_promotion_policy import (
    find_matching_policy,
)


READY = "PROMOTION_READY"

DEFAULT_ENFORCEMENT_CONFIG = Path(
    "config/scoped-promotion-enforcement.json"
)

DEFAULT_POLICY_PATH = Path(
    "config/scoped-promotion-policies.json"
)

DEFAULT_READINESS_PATH = Path(
    "reports/evaluation/stage54-production-readiness.json"
)


def _load_json_object(
    path: Path,
) -> dict[str, Any]:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"expected JSON object: {path}"
        )

    return data


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def apply_production_enforcement(
    analysis: Any,
    *,
    enforcement_config_path: Path = (
        DEFAULT_ENFORCEMENT_CONFIG
    ),
    policy_path: Path = DEFAULT_POLICY_PATH,
    readiness_path: Path = DEFAULT_READINESS_PATH,
    audit_path: Path | None = None,
) -> Any:
    """Return original analysis unless enforcement is fully authorized.

    Fail-closed behavior is deliberate: every exception or failed
    authorization check returns the exact original object unchanged.
    """

    try:
        config = _load_json_object(
            enforcement_config_path
        )

        if config.get("version") != 1:
            return analysis

        if config.get("enabled") is not True:
            return analysis

        required_decision = str(
            config.get(
                "required_readiness_decision",
                "",
            )
            or ""
        ).strip()

        if required_decision != READY:
            return analysis

        configured_sha = str(
            config.get("policy_sha256", "")
            or ""
        ).strip().lower()

        if len(configured_sha) != 64:
            return analysis

        authorized_domains_raw = config.get(
            "authorized_domains",
            [],
        )

        if not isinstance(
            authorized_domains_raw,
            list,
        ):
            return analysis

        authorized_domains = {
            str(domain)
            .strip()
            .lower()
            .strip(".")
            for domain in authorized_domains_raw
            if str(domain).strip()
        }

        if len(authorized_domains) != 13:
            return analysis

        normalized_analysis_domain = (
            str(analysis.domain)
            .strip()
            .lower()
            .strip(".")
        )

        if (
            normalized_analysis_domain
            not in authorized_domains
        ):
            return analysis

        readiness = _load_json_object(
            readiness_path
        )

        if (
            readiness.get("decision")
            != required_decision
        ):
            return analysis

        if int(
            readiness.get(
                "checks_failed",
                0,
            )
            or 0
        ) != 0:
            return analysis

        blockers = readiness.get(
            "blocking_reasons",
            [],
        )

        if (
            not isinstance(blockers, list)
            or blockers
        ):
            return analysis

        if (
            _sha256_file(policy_path)
            != configured_sha
        ):
            return analysis

        policies = (
            load_scoped_policy_artifact(
                policy_path
            )
        )

        control = SimulatedDecision(
            vendor=analysis.suggested_vendor,
            category=analysis.suggested_category,
            filter_name=analysis.suggested_filter,
            confidence=analysis.confidence,
            recommendation=analysis.recommendation,
        )

        policy, _suffix = (
            find_matching_policy(
                domain=analysis.domain,
                decision=control,
                policies=policies,
            )
        )

        if policy is None:
            return analysis

        if (
            analysis.suggested_filter
            != policy.current_filter
        ):
            return analysis

        enforced = replace(
            analysis,
            suggested_filter=(
                policy.proposed_filter
            ),
        )

        event = create_audit_event(
            domain=analysis.domain,
            matched_suffix=_suffix,
            category=analysis.suggested_category,
            before_filter=(
                analysis.suggested_filter
            ),
            after_filter=(
                enforced.suggested_filter
            ),
            confidence=analysis.confidence,
            recommendation=(
                analysis.recommendation
            ),
            policy_sha256=configured_sha,
            readiness_decision=(
                readiness.get(
                    "decision",
                    "",
                )
            ),
            enforcement_enabled=True,
        )

        append_audit_event(
            event,
            path=audit_path,
        )

        return enforced

    except Exception:
        return analysis
