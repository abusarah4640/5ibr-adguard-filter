"""Regression coverage for staged build promotion and rollback."""

from __future__ import annotations

import os
import subprocess
from types import SimpleNamespace

import pytest

import scripts.build as build


DIRECTORIES = ("config", "filters", "releases")


def write_tree(root, value):
    for name in DIRECTORIES:
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "marker.txt").write_text(
            f"{value}-{name}",
            encoding="utf-8",
        )


def assert_tree(root, value):
    for name in DIRECTORIES:
        assert (root / name / "marker.txt").read_text(
            encoding="utf-8"
        ) == f"{value}-{name}"


def test_promotion_failure_restores_every_live_directory(
    tmp_path,
    monkeypatch,
):
    runtime = tmp_path / "runtime"
    staging = runtime / ".staging"
    backup = runtime / ".backup"
    runtime.mkdir()
    backup.mkdir()

    write_tree(runtime, "old")
    write_tree(staging, "new")

    real_replace = os.replace

    def fail_release_promotion(source, destination):
        if (
            source == staging / "releases"
            and destination == runtime / "releases"
        ):
            raise OSError("simulated release promotion failure")
        return real_replace(source, destination)

    monkeypatch.setattr(
        build.os,
        "replace",
        fail_release_promotion,
    )

    with pytest.raises(
        OSError,
        match="simulated release promotion failure",
    ):
        build.promote_staged_outputs(
            runtime,
            staging,
            backup,
        )

    assert_tree(runtime, "old")


@pytest.mark.parametrize(
    ("failed_command", "returncode"),
    [
        ("build", 7),
        ("validate", 8),
    ],
)
def test_staged_failure_preserves_live_outputs_and_cleans_temporary_trees(
    tmp_path,
    monkeypatch,
    failed_command,
    returncode,
):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    write_tree(runtime, "old")
    (runtime / "database").mkdir()
    (runtime / "database" / "domains.csv").write_text(
        "Domain,Vendor,Category,Filter,Confidence,Status\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        build,
        "get_runtime_paths",
        lambda: SimpleNamespace(root=runtime),
    )

    commands = []

    def fake_command(staging_root, command):
        commands.append(command)
        write_tree(staging_root, "partial")
        code = returncode if command == failed_command else 0
        return subprocess.CompletedProcess(
            [command],
            code,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        build,
        "run_staging_command",
        fake_command,
    )

    assert build.staged_build() == returncode
    assert_tree(runtime, "old")

    temporary = [
        path.name
        for path in runtime.iterdir()
        if path.name.startswith(".fivebr-build-")
    ]
    assert temporary == []

    expected = (
        ["build"]
        if failed_command == "build"
        else ["build", "validate"]
    )
    assert commands == expected
