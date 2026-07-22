"""Regression coverage for deterministic runtime builds."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

from scripts.runtime.project_init import initialize_project


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORIES = (
    "config",
    "filters",
    "releases",
)


def output_snapshot(runtime: Path) -> dict[str, str]:
    """Return SHA-256 hashes for every runtime build artifact."""

    snapshot = {}

    for directory_name in OUTPUT_DIRECTORIES:
        directory = runtime / directory_name

        for path in sorted(directory.rglob("*")):
            if path.is_file():
                relative = path.relative_to(runtime).as_posix()
                snapshot[relative] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()

    return snapshot


def run_build(
    runtime: Path,
    working_directory: Path,
) -> subprocess.CompletedProcess[str]:
    """Run one isolated CLI build for the supplied runtime."""

    environment = os.environ.copy()
    environment["FIVEBR_HOME"] = str(runtime)
    environment["PYTHONPATH"] = str(PROJECT_ROOT)

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "fivebr",
            "build",
        ],
        cwd=working_directory,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_repeated_builds_have_identical_sha256_outputs(
    tmp_path,
):
    runtime = tmp_path / "runtime"
    initialize_project(runtime)

    first_build = run_build(runtime, tmp_path)
    assert first_build.returncode == 0, (
        first_build.stdout
        + "\n"
        + first_build.stderr
    )
    first_snapshot = output_snapshot(runtime)

    second_build = run_build(runtime, tmp_path)
    assert second_build.returncode == 0, (
        second_build.stdout
        + "\n"
        + second_build.stderr
    )
    second_snapshot = output_snapshot(runtime)

    assert first_snapshot
    assert second_snapshot == first_snapshot

    temporary_paths = [
        path.name
        for path in runtime.iterdir()
        if path.name.startswith(".fivebr-build-")
    ]
    assert temporary_paths == []
