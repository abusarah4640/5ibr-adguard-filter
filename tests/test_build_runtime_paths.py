import json
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


def test_build_uses_fivebr_home_from_arbitrary_cwd(
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
            "build",
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

    releases = runtime / "releases"

    assert releases.is_dir()

    expected = {
        "home.txt",
        "family.txt",
        "privacy.txt",
        "gaming.txt",
        "strict-family.txt",
        "all.txt",
    }

    actual = {
        path.name
        for path in releases.glob("*.txt")
    }

    assert expected <= actual


def test_build_does_not_write_to_source_tree(
    tmp_path,
):
    runtime = tmp_path / "runtime"

    initialize_project(runtime)

    source_directories = (
        PROJECT_ROOT / "config",
        PROJECT_ROOT / "filters",
        PROJECT_ROOT / "releases",
    )

    def source_snapshot():
        return {
            file.relative_to(PROJECT_ROOT): file.read_bytes()
            for directory in source_directories
            for file in directory.rglob("*")
            if file.is_file()
        }

    before = source_snapshot()

    environment = os.environ.copy()

    environment["FIVEBR_HOME"] = str(
        runtime
    )

    environment["PYTHONPATH"] = str(
        PROJECT_ROOT
    )

    subprocess.run(
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

    after = source_snapshot()

    assert after == before



def test_build_writes_generated_config_to_runtime(
    tmp_path,
):
    runtime = tmp_path / "runtime"

    initialize_project(runtime)

    database = (
        runtime
        / "database"
        / "domains.csv"
    )

    database.write_text(
        (
            "Domain,Vendor,Category,"
            "Filter,Confidence,Status\n"
            "runtime-stage63d.invalid,"
            "Runtime Stage63D,"
            "Telemetry,"
            "telemetry,"
            "100,"
            "Approved\n"
        ),
        encoding="utf-8",
    )

    source_vendors = (
        PROJECT_ROOT
        / "config"
        / "vendors.json"
    )

    source_signatures = (
        PROJECT_ROOT
        / "config"
        / "signatures.json"
    )

    source_vendors_before = (
        source_vendors.read_bytes()
    )

    source_signatures_before = (
        source_signatures.read_bytes()
    )

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
            "build",
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

    vendors = json.loads(
        (
            runtime
            / "config"
            / "vendors.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    signatures = json.loads(
        (
            runtime
            / "config"
            / "signatures.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert vendors == {
        "Runtime Stage63D": [
            "Telemetry"
        ]
    }

    assert signatures[
        "runtime-stage63d.invalid"
    ] == {
        "vendor": "Runtime Stage63D",
        "category": "Telemetry",
        "filter": "telemetry",
        "confidence": 100,
    }

    assert (
        source_vendors.read_bytes()
        == source_vendors_before
    )

    assert (
        source_signatures.read_bytes()
        == source_signatures_before
    )
