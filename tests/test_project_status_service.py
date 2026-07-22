import csv
import json
from pathlib import Path

from scripts.runtime.project_init import (
    initialize_project,
)
from scripts.services.project_status_service import (
    PROJECT_INITIALIZED,
    PROJECT_INVALID,
    PROJECT_OPERATIONAL,
    evaluate_project_status,
)


def test_initialized_project_is_valid(
    tmp_path,
):
    root = tmp_path / "project"

    initialize_project(root)

    result = evaluate_project_status(
        root
    )

    assert (
        result.decision
        == PROJECT_INITIALIZED
    )
    assert result.valid is True
    assert result.database_rows == 0
    assert result.checks_failed == 0


def test_project_with_rows_is_operational(
    tmp_path,
):
    root = tmp_path / "project"

    initialize_project(root)

    database = (
        root
        / "database"
        / "domains.csv"
    )

    with database.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle)

        writer.writerow(
            [
                "example.com",
                "Example",
                "Privacy",
                "privacy",
                "90",
                "Approved",
            ]
        )

    result = evaluate_project_status(
        root
    )

    assert (
        result.decision
        == PROJECT_OPERATIONAL
    )
    assert result.valid is True
    assert result.database_rows == 1


def test_missing_config_is_invalid(
    tmp_path,
):
    root = tmp_path / "project"

    initialize_project(root)

    (
        root
        / "config"
        / "vendors.json"
    ).unlink()

    result = evaluate_project_status(
        root
    )

    assert (
        result.decision
        == PROJECT_INVALID
    )
    assert result.valid is False
    assert result.checks_failed == 1


def test_invalid_json_is_invalid(
    tmp_path,
):
    root = tmp_path / "project"

    initialize_project(root)

    (
        root
        / "config"
        / "categories.json"
    ).write_text(
        "{broken",
        encoding="utf-8",
    )

    result = evaluate_project_status(
        root
    )

    assert (
        result.decision
        == PROJECT_INVALID
    )
    assert result.valid is False


def test_missing_referenced_filter_is_invalid(
    tmp_path,
):
    root = tmp_path / "project"

    initialize_project(root)

    releases_path = (
        root
        / "config"
        / "releases.json"
    )

    releases = json.loads(
        releases_path.read_text(
            encoding="utf-8"
        )
    )

    referenced = {
        filter_name
        for release in releases.values()
        for filter_name in release.get(
            "filters",
            [],
        )
    }

    target = sorted(referenced)[0]

    (
        root
        / "filters"
        / f"{target}.txt"
    ).unlink()

    result = evaluate_project_status(
        root
    )

    assert (
        result.decision
        == PROJECT_INVALID
    )
    assert result.valid is False


def test_empty_directory_is_invalid(
    tmp_path,
):
    root = tmp_path / "empty"
    root.mkdir()

    result = evaluate_project_status(
        root
    )

    assert (
        result.decision
        == PROJECT_INVALID
    )
    assert result.valid is False
    assert result.checks_failed > 0
