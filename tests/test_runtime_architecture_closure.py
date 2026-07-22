from pathlib import Path
from zipfile import ZipFile

from scripts.services.production_verify_service import (
    PRODUCTION_VERIFIED,
)
from scripts.services.runtime_architecture_closure import (
    PROJECT_ROOT,
    REQUIRED_SEED_FILES,
    RUNTIME_CLOSURE_ACCEPTED,
    RUNTIME_CLOSURE_REJECTED,
    WHEEL_SEED_PREFIX,
    evaluate_runtime_architecture,
)


class GoodProduction:
    decision = PRODUCTION_VERIFIED
    checks_failed = 0


class BadProduction:
    decision = (
        "PRODUCTION_VERIFICATION_FAILED"
    )
    checks_failed = 1


def make_wheel(
    tmp_path: Path,
    *,
    omit: str | None = None,
) -> Path:
    wheel = tmp_path / "test.whl"

    with ZipFile(
        wheel,
        "w",
    ) as archive:
        for name in sorted(
            REQUIRED_SEED_FILES
        ):
            if name == omit:
                continue

            archive.writestr(
                WHEEL_SEED_PREFIX + name,
                "",
            )

    return wheel


def test_valid_runtime_architecture_is_accepted(
    tmp_path,
):
    wheel = make_wheel(
        tmp_path
    )

    result = evaluate_runtime_architecture(
        project_root=PROJECT_ROOT,
        wheel_path=wheel,
        production_verifier=(
            lambda: GoodProduction()
        ),
    )

    assert result.accepted is True

    assert (
        result.decision
        == RUNTIME_CLOSURE_ACCEPTED
    )

    assert result.checks_failed == 0

    assert not result.blocking_reasons


def test_missing_wheel_seed_is_rejected(
    tmp_path,
):
    missing = (
        "config/vendors.json"
    )

    wheel = make_wheel(
        tmp_path,
        omit=missing,
    )

    result = evaluate_runtime_architecture(
        project_root=PROJECT_ROOT,
        wheel_path=wheel,
        production_verifier=(
            lambda: GoodProduction()
        ),
    )

    assert result.accepted is False

    assert (
        result.decision
        == RUNTIME_CLOSURE_REJECTED
    )

    assert result.checks_failed >= 1


def test_missing_wheel_is_rejected():
    result = evaluate_runtime_architecture(
        project_root=PROJECT_ROOT,
        wheel_path=None,
        production_verifier=(
            lambda: GoodProduction()
        ),
    )

    assert result.accepted is False

    assert (
        "wheel-supplied"
        in result.blocking_reasons[0]
        or any(
            "wheel-supplied"
            in reason
            for reason in (
                result.blocking_reasons
            )
        )
    )


def test_failed_production_blocks_closure(
    tmp_path,
):
    wheel = make_wheel(
        tmp_path
    )

    result = evaluate_runtime_architecture(
        project_root=PROJECT_ROOT,
        wheel_path=wheel,
        production_verifier=(
            lambda: BadProduction()
        ),
    )

    assert result.accepted is False

    assert (
        result.decision
        == RUNTIME_CLOSURE_REJECTED
    )

    assert any(
        "production-verification"
        in reason
        for reason in (
            result.blocking_reasons
        )
    )
