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


def test_validate_uses_fivebr_home_from_arbitrary_cwd(
    tmp_path,
):
    runtime = tmp_path / "runtime"

    initialize_project(runtime)

    environment = os.environ.copy()

    environment["FIVEBR_HOME"] = str(
        runtime
    )

    environment["PYTHONPATH"] = str(
        PROJECT_ROOT
    )

    built = subprocess.run(
        [
            sys.executable,
            "-m",
            "fivebr",
            "build",
        ],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert built.returncode == 0, (
        built.stdout
        + "\n"
        + built.stderr
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fivebr",
            "validate",
        ],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, (
        completed.stdout
        + "\n"
        + completed.stderr
    )

    assert "Traceback" not in completed.stderr
    assert "FileNotFoundError" not in completed.stderr


def test_validate_does_not_require_package_config(
    tmp_path,
):
    runtime = tmp_path / "runtime"

    initialize_project(runtime)

    environment = os.environ.copy()

    environment["FIVEBR_HOME"] = str(
        runtime
    )

    environment["PYTHONPATH"] = str(
        PROJECT_ROOT
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "fivebr",
            "validate",
        ],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    combined = (
        completed.stdout
        + "\n"
        + completed.stderr
    )

    assert (
        "site-packages/config/releases.json"
        not in combined
    )
