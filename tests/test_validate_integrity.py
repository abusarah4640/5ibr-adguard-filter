"""Integrity regression tests for runtime validation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.runtime.project_init import initialize_project
from scripts.validate import (
    validate_filter_rule,
    validate_runtime,
)


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


@pytest.mark.parametrize(
    ("filename", "rule"),
    (
        ("ads.txt", "example.com"),
        ("telemetry.txt", "sub.example.co.uk"),
        ("ads.txt", "مثال.إختبار"),
        ("whitelist.txt", "@@||account.example.com^"),
    ),
)
def test_supported_filter_rule_shapes_are_accepted(
    filename,
    rule,
):
    assert validate_filter_rule(filename, rule) is None


@pytest.mark.parametrize(
    ("filename", "rule", "message"),
    (
        ("ads.txt", "https://example.com", "invalid domain"),
        ("ads.txt", "*.example.com", "invalid domain"),
        ("ads.txt", "Example.com", "lowercase"),
        ("ads.txt", "localhost", "at least two labels"),
        ("ads.txt", "-bad.example", "invalid domain label"),
        (
            "ads.txt",
            "@@||example.com^",
            "only allowed in whitelist.txt",
        ),
        (
            "whitelist.txt",
            "example.com",
            "must use @@||domain^ syntax",
        ),
        (
            "whitelist.txt",
            "@@||example.com/path^",
            "invalid domain",
        ),
    ),
)
def test_unsupported_filter_rule_shapes_are_rejected(
    filename,
    rule,
    message,
):
    error = validate_filter_rule(filename, rule)

    assert error is not None
    assert message in error


def test_validate_reports_invalid_rule_file_and_line(
    built_runtime,
):
    path = built_runtime / "filters" / "ads.txt"
    original = path.read_text(encoding="utf-8")
    line_number = len(original.splitlines()) + 1
    path.write_text(
        original + "https://invalid.example/path\n",
        encoding="utf-8",
    )

    errors = validate_runtime(built_runtime)

    assert any(
        error.startswith(
            f"filters/ads.txt:{line_number}: "
        )
        and "invalid domain" in error
        for error in errors
    )
