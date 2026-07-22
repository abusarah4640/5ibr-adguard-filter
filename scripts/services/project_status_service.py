"""Project runtime lifecycle status.

The service distinguishes:

- PROJECT_INITIALIZED:
  Required runtime structure is valid, but the database has no rows.

- PROJECT_OPERATIONAL:
  Required runtime structure is valid and the database has rows.

- PROJECT_INVALID:
  Required files are missing, malformed, or inconsistent.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scripts.database import FIELDNAMES
from scripts.runtime.paths import (
    get_runtime_paths,
)


PROJECT_INITIALIZED = (
    "PROJECT_INITIALIZED"
)

PROJECT_OPERATIONAL = (
    "PROJECT_OPERATIONAL"
)

PROJECT_INVALID = "PROJECT_INVALID"


REQUIRED_CONFIG = (
    "categories.json",
    "database.json",
    "releases.json",
    "signatures.json",
    "vendors.json",
)


@dataclass(frozen=True, slots=True)
class ProjectStatusCheck:
    name: str
    passed: bool
    actual: Any
    expected: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProjectStatus:
    decision: str
    valid: bool
    root: Path
    database_rows: int
    checks_passed: int
    checks_failed: int
    issues: tuple[str, ...]
    checks: tuple[
        ProjectStatusCheck,
        ...,
    ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "valid": self.valid,
            "root": str(self.root),
            "database_rows": (
                self.database_rows
            ),
            "checks_passed": (
                self.checks_passed
            ),
            "checks_failed": (
                self.checks_failed
            ),
            "issues": list(self.issues),
            "checks": [
                check.to_dict()
                for check in self.checks
            ],
        }


def _add_check(
    checks: list[ProjectStatusCheck],
    *,
    name: str,
    actual: Any,
    expected: Any,
) -> None:
    checks.append(
        ProjectStatusCheck(
            name=name,
            passed=actual == expected,
            actual=actual,
            expected=expected,
        )
    )


def _load_json_object(
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


def evaluate_project_status(
    root: str | Path | None = None,
) -> ProjectStatus:
    paths = get_runtime_paths(root)

    checks: list[
        ProjectStatusCheck
    ] = []

    for directory in (
        paths.config,
        paths.database,
        paths.filters,
        paths.releases,
        paths.reports,
        paths.data,
    ):
        _add_check(
            checks,
            name=(
                "directory:"
                f"{directory.name}"
            ),
            actual=directory.is_dir(),
            expected=True,
        )

    config_objects: dict[
        str,
        dict[str, Any],
    ] = {}

    for name in REQUIRED_CONFIG:
        path = paths.config / name

        exists = path.is_file()

        _add_check(
            checks,
            name=f"config-exists:{name}",
            actual=exists,
            expected=True,
        )

        if not exists:
            continue

        try:
            config_objects[name] = (
                _load_json_object(path)
            )

            valid_json = True

        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
        ):
            valid_json = False

        _add_check(
            checks,
            name=f"config-valid:{name}",
            actual=valid_json,
            expected=True,
        )

    database_path = (
        paths.database / "domains.csv"
    )

    database_exists = (
        database_path.is_file()
    )

    _add_check(
        checks,
        name="database-exists",
        actual=database_exists,
        expected=True,
    )

    database_rows = 0
    headers: list[str] = []

    if database_exists:
        try:
            with database_path.open(
                newline="",
                encoding="utf-8",
            ) as handle:
                reader = csv.DictReader(
                    handle
                )

                headers = list(
                    reader.fieldnames or []
                )

                rows = list(reader)

            database_rows = len(rows)
            database_readable = True

        except (OSError, csv.Error):
            database_readable = False

        _add_check(
            checks,
            name="database-readable",
            actual=database_readable,
            expected=True,
        )

        if database_readable:
            missing_fields = sorted(
                set(FIELDNAMES)
                - set(headers)
            )

            _add_check(
                checks,
                name="database-schema",
                actual=missing_fields,
                expected=[],
            )

    releases = config_objects.get(
        "releases.json",
        {},
    )

    referenced_filters: set[str] = set()

    for release in releases.values():
        if not isinstance(
            release,
            dict,
        ):
            continue

        filters = release.get(
            "filters",
            [],
        )

        if not isinstance(filters, list):
            continue

        referenced_filters.update(
            str(name).strip()
            for name in filters
            if str(name).strip()
        )

    for name in sorted(
        referenced_filters
    ):
        _add_check(
            checks,
            name=f"filter-exists:{name}",
            actual=(
                paths.filters
                / f"{name}.txt"
            ).is_file(),
            expected=True,
        )

    issues = tuple(
        (
            f"{check.name}: "
            f"{check.actual!r} != "
            f"{check.expected!r}"
        )
        for check in checks
        if not check.passed
    )

    valid = not issues

    if not valid:
        decision = PROJECT_INVALID

    elif database_rows == 0:
        decision = PROJECT_INITIALIZED

    else:
        decision = PROJECT_OPERATIONAL

    return ProjectStatus(
        decision=decision,
        valid=valid,
        root=paths.root,
        database_rows=database_rows,
        checks_passed=sum(
            check.passed
            for check in checks
        ),
        checks_failed=sum(
            not check.passed
            for check in checks
        ),
        issues=issues,
        checks=tuple(checks),
    )
