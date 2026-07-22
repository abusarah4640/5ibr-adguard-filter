"""Integrity regression tests for runtime validation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.runtime.project_init import initialize_project
from scripts.validate import validate_runtime


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def built_runtime(tmp_path):
    runtime = tmp_path / "runtime"
    initialize_project(runtime)

    environment = os.environ.copy()
    environment["FIVEBR_HOME"] = str(runtime)
    environment["PYTHONPATH"] = str(PROJECT_ROOT)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fivebr",
            "build",
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, (
        completed.stdout + "\n" + completed.stderr
    )
    assert validate_runtime(runtime) == []

    return runtime


def test_validate_rejects_invalid_utf8_filter(built_runtime):
    path = built_runtime / "filters" / "privacy.txt"
    path.write_bytes(b"\xff\xfeinvalid")

    errors = validate_runtime(built_runtime)

    assert any(
        "filters/privacy.txt" in error
        and "decode" in error.lower()
        for error in errors
    )


def test_validate_rejects_filter_symlink(
    built_runtime,
    tmp_path,
):
    external = tmp_path / "external-filter.txt"
    external.write_text(
        "external.example\n",
        encoding="utf-8",
    )

    path = built_runtime / "filters" / "privacy.txt"
    path.unlink()
    path.symlink_to(external)

    errors = validate_runtime(built_runtime)

    assert any(
        "filters/privacy.txt" in error
        and "symbolic links" in error
        for error in errors
    )


def test_validate_rejects_malformed_json(built_runtime):
    path = built_runtime / "config" / "categories.json"
    path.write_text("{", encoding="utf-8")

    errors = validate_runtime(built_runtime)

    assert any(
        "config/categories.json" in error
        for error in errors
    )


def test_validate_rejects_stale_release(built_runtime):
    path = built_runtime / "releases" / "obsolete.txt"
    path.write_text(
        "stale release\n",
        encoding="utf-8",
    )

    errors = validate_runtime(built_runtime)

    assert (
        "releases/obsolete.txt: unexpected stale release"
        in errors
    )


def test_validate_rejects_tampered_release(built_runtime):
    path = built_runtime / "releases" / "home.txt"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\ntampered.example\n",
        encoding="utf-8",
    )

    errors = validate_runtime(built_runtime)

    assert any(
        "releases/home.txt" in error
        and "does not match" in error
        for error in errors
    )
