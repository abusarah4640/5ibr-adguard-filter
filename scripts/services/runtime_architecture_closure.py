"""Final audit for the 5ibr runtime resource architecture."""

from __future__ import annotations

import json
import tempfile
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from zipfile import BadZipFile, ZipFile

from scripts.runtime.project_init import (
    initialize_project,
)
from scripts.services.production_verify_service import (
    PRODUCTION_VERIFIED,
    verify_production,
)
from scripts.services.project_status_service import (
    PROJECT_INITIALIZED,
    PROJECT_OPERATIONAL,
    evaluate_project_status,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RUNTIME_CLOSURE_ACCEPTED = (
    "RUNTIME_ARCHITECTURE_ACCEPTED"
)

RUNTIME_CLOSURE_REJECTED = (
    "RUNTIME_ARCHITECTURE_REJECTED"
)


REQUIRED_SEED_FILES = {
    "__init__.py",
    "config/analyzer.json",
    "config/categories.json",
    "config/database.json",
    "config/releases.json",
    "config/signatures.json",
    "config/vendors.json",
    "database/domains.csv",
    "filters/ads.txt",
    "filters/adult.txt",
    "filters/gaming.txt",
    "filters/mobile.txt",
    "filters/privacy.txt",
    "filters/smart-tv.txt",
    "filters/social.txt",
    "filters/telemetry.txt",
    "filters/whitelist.txt",
}


FORBIDDEN_SEED_FILES = {
    (
        "config/"
        "scoped-promotion-enforcement.json"
    ),
    (
        "config/"
        "scoped-promotion-policies.json"
    ),
}


WHEEL_SEED_PREFIX = (
    "scripts/runtime/seeds/"
)


@dataclass(frozen=True, slots=True)
class RuntimeClosureCheck:
    name: str
    passed: bool
    actual: Any
    expected: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RuntimeClosureResult:
    decision: str
    accepted: bool
    checks_passed: int
    checks_failed: int
    blocking_reasons: tuple[str, ...]
    checks: tuple[
        RuntimeClosureCheck,
        ...,
    ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "accepted": self.accepted,
            "checks_passed": (
                self.checks_passed
            ),
            "checks_failed": (
                self.checks_failed
            ),
            "blocking_reasons": list(
                self.blocking_reasons
            ),
            "checks": [
                check.to_dict()
                for check in self.checks
            ],
        }


def _add_check(
    checks: list[RuntimeClosureCheck],
    *,
    name: str,
    actual: Any,
    expected: Any,
) -> None:
    checks.append(
        RuntimeClosureCheck(
            name=name,
            passed=actual == expected,
            actual=actual,
            expected=expected,
        )
    )


def _seed_source_files(
    root: Path,
) -> set[str]:
    seed_root = (
        root
        / "scripts"
        / "runtime"
        / "seeds"
    )

    return {
        path.relative_to(
            seed_root
        ).as_posix()
        for path in seed_root.rglob("*")
        if (
            path.is_file()
            and "__pycache__"
            not in path.parts
            and path.suffix != ".pyc"
        )
    }


def _load_package_configuration(
    root: Path,
) -> tuple[list[str], dict[str, Any]]:
    with (
        root / "pyproject.toml"
    ).open("rb") as handle:
        data = tomllib.load(handle)

    setuptools = (
        data["tool"]["setuptools"]
    )

    packages = list(
        setuptools.get(
            "packages",
            [],
        )
    )

    package_data = dict(
        setuptools.get(
            "package-data",
            {},
        )
    )

    return packages, package_data


def _wheel_seed_files(
    wheel_path: Path,
) -> set[str]:
    with ZipFile(wheel_path) as archive:
        names = archive.namelist()

    return {
        name.removeprefix(
            WHEEL_SEED_PREFIX
        )
        for name in names
        if name.startswith(
            WHEEL_SEED_PREFIX
        )
    }


def evaluate_runtime_architecture(
    *,
    project_root: str | Path = (
        PROJECT_ROOT
    ),
    wheel_path: str | Path | None = None,
    production_verifier: Callable[
        [],
        Any,
    ] = verify_production,
) -> RuntimeClosureResult:
    root = Path(
        project_root
    ).resolve()

    checks: list[
        RuntimeClosureCheck
    ] = []

    try:
        packages, package_data = (
            _load_package_configuration(
                root
            )
        )

        _add_check(
            checks,
            name="runtime-package-registered",
            actual=(
                "scripts.runtime"
                in packages
            ),
            expected=True,
        )

        _add_check(
            checks,
            name="seed-package-registered",
            actual=(
                "scripts.runtime.seeds"
                in packages
            ),
            expected=True,
        )

        _add_check(
            checks,
            name="seed-package-data",
            actual=package_data.get(
                "scripts.runtime.seeds"
            ),
            expected=[
                "config/*.json",
                "database/*.csv",
                "filters/*.txt",
            ],
        )

    except Exception as exc:
        _add_check(
            checks,
            name="package-configuration-readable",
            actual=(
                f"{type(exc).__name__}: {exc}"
            ),
            expected="readable",
        )

    source_seeds = (
        _seed_source_files(root)
    )

    _add_check(
        checks,
        name="source-seed-contract",
        actual=sorted(source_seeds),
        expected=sorted(
            REQUIRED_SEED_FILES
        ),
    )

    _add_check(
        checks,
        name="production-seeds-excluded",
        actual=sorted(
            source_seeds
            & FORBIDDEN_SEED_FILES
        ),
        expected=[],
    )

    for relative in (
        "scripts/database.py",
        "scripts/doctor.py",
    ):
        path = root / relative

        try:
            source = path.read_text(
                encoding="utf-8"
            )

            centralized = (
                "scripts.runtime.paths"
                in source
                and "get_runtime_paths"
                in source
            )

        except OSError:
            centralized = False

        _add_check(
            checks,
            name=(
                "central-runtime-paths:"
                f"{relative}"
            ),
            actual=centralized,
            expected=True,
        )

    try:
        source_status = (
            evaluate_project_status(
                root
            )
        )

        _add_check(
            checks,
            name="source-project-status",
            actual=source_status.decision,
            expected=PROJECT_OPERATIONAL,
        )

        _add_check(
            checks,
            name="source-project-valid",
            actual=source_status.valid,
            expected=True,
        )

    except Exception as exc:
        _add_check(
            checks,
            name="source-project-readable",
            actual=(
                f"{type(exc).__name__}: {exc}"
            ),
            expected="readable",
        )

    try:
        with tempfile.TemporaryDirectory(
            prefix="fivebr-closure-"
        ) as temporary:
            initialized_root = (
                Path(temporary)
                / "project"
            )

            initialize_project(
                initialized_root
            )

            initialized_status = (
                evaluate_project_status(
                    initialized_root
                )
            )

            _add_check(
                checks,
                name=(
                    "initialized-project-status"
                ),
                actual=(
                    initialized_status.decision
                ),
                expected=PROJECT_INITIALIZED,
            )

            _add_check(
                checks,
                name=(
                    "initialized-project-valid"
                ),
                actual=(
                    initialized_status.valid
                ),
                expected=True,
            )

            initialized_files = {
                path.relative_to(
                    initialized_root
                ).as_posix()
                for path in (
                    initialized_root.rglob(
                        "*"
                    )
                )
                if path.is_file()
            }

            expected_runtime_files = {
                path
                for path in REQUIRED_SEED_FILES
                if path != "__init__.py"
            }

            _add_check(
                checks,
                name=(
                    "initialized-file-contract"
                ),
                actual=sorted(
                    initialized_files
                ),
                expected=sorted(
                    expected_runtime_files
                ),
            )

    except Exception as exc:
        _add_check(
            checks,
            name="project-initialization",
            actual=(
                f"{type(exc).__name__}: {exc}"
            ),
            expected="successful",
        )

    if wheel_path is None:
        _add_check(
            checks,
            name="wheel-supplied",
            actual=False,
            expected=True,
        )

    else:
        wheel = Path(
            wheel_path
        ).resolve()

        _add_check(
            checks,
            name="wheel-exists",
            actual=wheel.is_file(),
            expected=True,
        )

        if wheel.is_file():
            try:
                wheel_seeds = (
                    _wheel_seed_files(
                        wheel
                    )
                )

                _add_check(
                    checks,
                    name="wheel-seed-contract",
                    actual=sorted(
                        wheel_seeds
                    ),
                    expected=sorted(
                        REQUIRED_SEED_FILES
                    ),
                )

                _add_check(
                    checks,
                    name=(
                        "wheel-production-seeds-excluded"
                    ),
                    actual=sorted(
                        wheel_seeds
                        & FORBIDDEN_SEED_FILES
                    ),
                    expected=[],
                )

            except (
                OSError,
                BadZipFile,
            ) as exc:
                _add_check(
                    checks,
                    name="wheel-readable",
                    actual=(
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                    expected="readable",
                )

    try:
        production = (
            production_verifier()
        )

        _add_check(
            checks,
            name="production-verification",
            actual=production.decision,
            expected=PRODUCTION_VERIFIED,
        )

        _add_check(
            checks,
            name="production-check-failures",
            actual=production.checks_failed,
            expected=0,
        )

    except Exception as exc:
        _add_check(
            checks,
            name="production-verifier-readable",
            actual=(
                f"{type(exc).__name__}: {exc}"
            ),
            expected="readable",
        )

    blocking_reasons = tuple(
        (
            f"{check.name}: "
            f"{check.actual!r} != "
            f"{check.expected!r}"
        )
        for check in checks
        if not check.passed
    )

    accepted = not blocking_reasons

    return RuntimeClosureResult(
        decision=(
            RUNTIME_CLOSURE_ACCEPTED
            if accepted
            else RUNTIME_CLOSURE_REJECTED
        ),
        accepted=accepted,
        checks_passed=sum(
            check.passed
            for check in checks
        ),
        checks_failed=sum(
            not check.passed
            for check in checks
        ),
        blocking_reasons=(
            blocking_reasons
        ),
        checks=tuple(checks),
    )
