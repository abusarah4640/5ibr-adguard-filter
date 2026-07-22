"""Append-only observability for scoped production enforcement.

Audit failures must never alter Analyzer decisions. Records are written
only after an authorized scoped filter change has been produced.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_AUDIT_PATH = Path(
    "reports/audit/"
    "scoped-production-enforcement.jsonl"
)


@dataclass(frozen=True)
class EnforcementAuditEvent:
    timestamp_utc: str
    domain: str
    matched_suffix: str
    category: str
    before_filter: str
    after_filter: str
    confidence: int
    recommendation: str
    policy_sha256: str
    readiness_decision: str
    enforcement_enabled: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_audit_path(
    explicit_path: Path | None = None,
) -> Path:
    if explicit_path is not None:
        return explicit_path

    environment_path = os.environ.get(
        "FIVEBR_ENFORCEMENT_AUDIT_PATH",
        "",
    ).strip()

    if environment_path:
        return Path(environment_path)

    return DEFAULT_AUDIT_PATH


def create_audit_event(
    *,
    domain: str,
    matched_suffix: str,
    category: str,
    before_filter: str,
    after_filter: str,
    confidence: int,
    recommendation: str,
    policy_sha256: str,
    readiness_decision: str,
    enforcement_enabled: bool,
) -> EnforcementAuditEvent:
    return EnforcementAuditEvent(
        timestamp_utc=datetime.now(
            timezone.utc
        ).isoformat(),
        domain=domain,
        matched_suffix=matched_suffix,
        category=category,
        before_filter=before_filter,
        after_filter=after_filter,
        confidence=int(confidence),
        recommendation=recommendation,
        policy_sha256=policy_sha256,
        readiness_decision=readiness_decision,
        enforcement_enabled=(
            enforcement_enabled
        ),
    )


def append_audit_event(
    event: EnforcementAuditEvent,
    *,
    path: Path | None = None,
) -> bool:
    """Append one JSONL event.

    Returns False on any I/O failure. Audit failure never propagates into
    the Analyzer or changes an enforcement decision.
    """

    try:
        target = resolve_audit_path(path)

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with target.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    event.to_dict(),
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

        return True

    except Exception:
        return False


def load_audit_events(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    events: list[dict[str, Any]] = []

    for line_number, raw_line in enumerate(
        path.read_text(
            encoding="utf-8"
        ).splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        payload = json.loads(line)

        if not isinstance(payload, dict):
            raise ValueError(
                "invalid audit event at line "
                f"{line_number}"
            )

        events.append(payload)

    return events
