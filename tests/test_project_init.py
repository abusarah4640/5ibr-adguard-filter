from pathlib import Path

from scripts.runtime.project_init import (
    initialize_project,
)


def test_initialize_creates_structure(
    tmp_path,
):
    root = tmp_path / "project"

    result = initialize_project(
        root
    )

    for name in (
        "config",
        "database",
        "filters",
        "releases",
        "reports",
        "data",
    ):
        assert (
            root / name
        ).is_dir()

    assert result.root == root.resolve()


def test_initialize_creates_safe_config(
    tmp_path,
):
    root = tmp_path / "project"

    initialize_project(root)

    expected = {
        "analyzer.json",
        "categories.json",
        "database.json",
        "releases.json",
        "signatures.json",
        "vendors.json",
    }

    actual = {
        path.name
        for path in (
            root / "config"
        ).iterdir()
        if path.is_file()
    }

    assert actual == expected

    assert not (
        root
        / "config"
        / "scoped-promotion-enforcement.json"
    ).exists()

    assert not (
        root
        / "config"
        / "scoped-promotion-policies.json"
    ).exists()


def test_database_seed_has_header_only(
    tmp_path,
):
    root = tmp_path / "project"

    initialize_project(root)

    lines = (
        root
        / "database"
        / "domains.csv"
    ).read_text(
        encoding="utf-8"
    ).splitlines()

    assert lines == [
        (
            "Domain,Vendor,Category,"
            "Filter,Confidence,Status"
        )
    ]


def test_existing_files_are_not_overwritten(
    tmp_path,
):
    root = tmp_path / "project"

    initialize_project(root)

    target = (
        root
        / "config"
        / "categories.json"
    )

    target.write_text(
        '{"custom": true}',
        encoding="utf-8",
    )

    result = initialize_project(root)

    assert target.read_text(
        encoding="utf-8"
    ) == '{"custom": true}'

    assert target in result.skipped_files


def test_force_overwrites_seed_files(
    tmp_path,
):
    root = tmp_path / "project"

    initialize_project(root)

    target = (
        root
        / "config"
        / "categories.json"
    )

    target.write_text(
        '{"custom": true}',
        encoding="utf-8",
    )

    initialize_project(
        root,
        force=True,
    )

    assert target.read_text(
        encoding="utf-8"
    ) != '{"custom": true}'


def test_initialization_is_idempotent(
    tmp_path,
):
    root = tmp_path / "project"

    first = initialize_project(root)
    second = initialize_project(root)

    assert first.created_files
    assert not second.created_files
    assert second.skipped_files
