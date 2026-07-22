import csv
import os
import subprocess
import sys
from pathlib import Path

from scripts.runtime.project_init import (
    initialize_project,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)


def run_doctor(
    root: Path,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()

    environment[
        "FIVEBR_HOME"
    ] = str(root)

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.doctor",
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_initialized_project_is_healthy(
    tmp_path,
):
    root = tmp_path / "project"

    initialize_project(root)

    result = run_doctor(root)

    assert result.returncode == 0

    assert (
        "PROJECT_INITIALIZED"
        in result.stdout
    )

    assert (
        "Doctor INITIALIZED"
        in result.stdout
    )

    assert (
        "Doctor FAILED"
        not in result.stdout
    )


def test_operational_project_passes(
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

    result = run_doctor(root)

    assert result.returncode == 0

    assert (
        "PROJECT_OPERATIONAL"
        in result.stdout
    )

    assert (
        "Doctor PASSED"
        in result.stdout
    )


def test_invalid_project_fails(
    tmp_path,
):
    root = tmp_path / "project"

    initialize_project(root)

    (
        root
        / "config"
        / "vendors.json"
    ).unlink()

    result = run_doctor(root)

    assert result.returncode == 1

    assert (
        "PROJECT_INVALID"
        in result.stdout
    )

    assert (
        "Doctor FAILED"
        in result.stdout
    )


def test_empty_directory_fails(
    tmp_path,
):
    root = tmp_path / "empty"

    root.mkdir()

    result = run_doctor(root)

    assert result.returncode == 1

    assert (
        "PROJECT_INVALID"
        in result.stdout
    )

    assert (
        "Doctor FAILED"
        in result.stdout
    )
