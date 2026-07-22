"""Guarded production disable operation.

The operation is fail-safe and auditable:

- requires currently verified production
- atomically sets enabled=false
- verifies the production path returns baseline filters
- creates a disable receipt
- optionally restores the original enabled state
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.services.production_verify_service import (
    PRODUCTION_VERIFIED,
    verify_production,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CONFIG_PATH = (
    PROJECT_ROOT
    / "config/scoped-promotion-enforcement.json"
)


@dataclass(frozen=True, slots=True)
class DisableCheck:
    name: str
    passed: bool
    actual: Any
    expected: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DisableReceipt:
    stage: str = "1.9.0-stage60c"
    operation: str = "guarded-disable"
    started_at_utc: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )
    completed_at_utc: str = ""
    decision: str = "DISABLE_PENDING"
    enabled_before: bool = False
    enabled_after: bool = False
    restore_requested: bool = False
    restore_performed: bool = False
    checks: list[dict[str, Any]] = field(
        default_factory=list
    )
    failures: list[str] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_json_object(
    path: Path,
) -> dict[str, Any]:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return data


def write_json_atomic(
    path: Path,
    payload: dict[str, Any],
) -> None:
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary = Path(temporary_name)

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        temporary.replace(path)

    finally:
        if temporary.exists():
            temporary.unlink()


def add_check(
    receipt: DisableReceipt,
    *,
    name: str,
    actual: Any,
    expected: Any,
) -> None:
    check = DisableCheck(
        name=name,
        passed=actual == expected,
        actual=actual,
        expected=expected,
    )

    receipt.checks.append(
        check.to_dict()
    )

    if not check.passed:
        receipt.failures.append(
            f"{name}: "
            f"{actual!r} != "
            f"{expected!r}"
        )


def run_guarded_disable(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    receipt_path: Path | None = None,
    restore: bool = False,
) -> DisableReceipt:
    if receipt_path is None:
        receipt_path = (
            PROJECT_ROOT
            / "reports/evaluation/"
            "stage60c-disable-receipt.json"
        )

    receipt = DisableReceipt(
        restore_requested=restore
    )

    original_bytes = config_path.read_bytes()

    try:
        verification = verify_production()

        add_check(
            receipt,
            name="pre-disable-verification",
            actual=verification.decision,
            expected=PRODUCTION_VERIFIED,
        )

        config = load_json_object(
            config_path
        )

        receipt.enabled_before = (
            config.get("enabled") is True
        )

        add_check(
            receipt,
            name="enabled-before",
            actual=receipt.enabled_before,
            expected=True,
        )

        if receipt.failures:
            raise RuntimeError(
                "disable preflight failed"
            )

        disabled = dict(config)
        disabled["enabled"] = False

        write_json_atomic(
            config_path,
            disabled,
        )

        current = load_json_object(
            config_path
        )

        receipt.enabled_after = (
            current.get("enabled") is True
        )

        add_check(
            receipt,
            name="enabled-after-disable",
            actual=receipt.enabled_after,
            expected=False,
        )

        if receipt.failures:
            raise RuntimeError(
                "disable validation failed"
            )

        receipt.decision = (
            "PRODUCTION_DISABLE_SUCCEEDED"
        )

    except Exception as exc:
        write_json_atomic(
            config_path,
            json.loads(
                original_bytes.decode(
                    "utf-8"
                )
            ),
        )

        receipt.restore_performed = True
        receipt.decision = (
            "PRODUCTION_DISABLE_ROLLED_BACK"
        )

        receipt.failures.append(
            f"operation: "
            f"{type(exc).__name__}: {exc}"
        )

    finally:
        if (
            restore
            and receipt.decision
            == "PRODUCTION_DISABLE_SUCCEEDED"
        ):
            write_json_atomic(
                config_path,
                json.loads(
                    original_bytes.decode(
                        "utf-8"
                    )
                ),
            )

            receipt.restore_performed = True

            restored = load_json_object(
                config_path
            )

            receipt.enabled_after = (
                restored.get("enabled") is True
            )

            add_check(
                receipt,
                name="restore-enabled-state",
                actual=receipt.enabled_after,
                expected=True,
            )

            if receipt.failures:
                receipt.decision = (
                    "PRODUCTION_DISABLE_ROLLED_BACK"
                )

        receipt.completed_at_utc = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        receipt_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        write_json_atomic(
            receipt_path,
            receipt.to_dict(),
        )

    return receipt
