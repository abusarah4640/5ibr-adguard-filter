import json

import scripts.services.guarded_disable_service as service
from scripts.services.production_verify_service import (
    PRODUCTION_VERIFIED,
)


class FakeVerification:
    decision = PRODUCTION_VERIFIED


def write_json(path, payload):
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_disable_changes_enabled_to_false(
    tmp_path,
    monkeypatch,
):
    config = tmp_path / "config.json"
    receipt = tmp_path / "receipt.json"

    write_json(
        config,
        {
            "enabled": True,
            "policy_sha256": "a" * 64,
        },
    )

    monkeypatch.setattr(
        service,
        "verify_production",
        lambda: FakeVerification(),
    )

    result = service.run_guarded_disable(
        config_path=config,
        receipt_path=receipt,
        restore=False,
    )

    payload = json.loads(
        config.read_text(encoding="utf-8")
    )

    assert result.decision == (
        "PRODUCTION_DISABLE_SUCCEEDED"
    )
    assert payload["enabled"] is False
    assert result.enabled_before is True
    assert result.enabled_after is False


def test_disable_with_restore_returns_true(
    tmp_path,
    monkeypatch,
):
    config = tmp_path / "config.json"
    receipt = tmp_path / "receipt.json"

    write_json(
        config,
        {
            "enabled": True,
            "policy_sha256": "a" * 64,
        },
    )

    monkeypatch.setattr(
        service,
        "verify_production",
        lambda: FakeVerification(),
    )

    result = service.run_guarded_disable(
        config_path=config,
        receipt_path=receipt,
        restore=True,
    )

    payload = json.loads(
        config.read_text(encoding="utf-8")
    )

    assert payload["enabled"] is True
    assert result.restore_performed is True
    assert result.enabled_after is True
    assert result.decision == (
        "PRODUCTION_DISABLE_SUCCEEDED"
    )


def test_failed_verification_does_not_disable(
    tmp_path,
    monkeypatch,
):
    config = tmp_path / "config.json"
    receipt = tmp_path / "receipt.json"

    write_json(
        config,
        {
            "enabled": True,
        },
    )

    class FailedVerification:
        decision = (
            "PRODUCTION_VERIFICATION_FAILED"
        )

    monkeypatch.setattr(
        service,
        "verify_production",
        lambda: FailedVerification(),
    )

    result = service.run_guarded_disable(
        config_path=config,
        receipt_path=receipt,
    )

    payload = json.loads(
        config.read_text(encoding="utf-8")
    )

    assert payload["enabled"] is True
    assert result.decision == (
        "PRODUCTION_DISABLE_ROLLED_BACK"
    )
    assert result.restore_performed is True


def test_receipt_is_written(
    tmp_path,
    monkeypatch,
):
    config = tmp_path / "config.json"
    receipt = tmp_path / "receipt.json"

    write_json(
        config,
        {
            "enabled": True,
        },
    )

    monkeypatch.setattr(
        service,
        "verify_production",
        lambda: FakeVerification(),
    )

    service.run_guarded_disable(
        config_path=config,
        receipt_path=receipt,
        restore=True,
    )

    payload = json.loads(
        receipt.read_text(encoding="utf-8")
    )

    assert payload["operation"] == (
        "guarded-disable"
    )
    assert payload["restore_performed"] is True
    assert payload["failures"] == []
