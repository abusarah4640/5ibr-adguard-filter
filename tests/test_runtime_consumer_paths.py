import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)


def run_probe(
    *,
    runtime_root: Path | None,
) -> dict:
    environment = os.environ.copy()

    if runtime_root is None:
        environment.pop(
            "FIVEBR_HOME",
            None,
        )
    else:
        environment[
            "FIVEBR_HOME"
        ] = str(runtime_root)

    code = r"""
import json

import scripts.database as database
import scripts.doctor as doctor

print(
    json.dumps(
        {
            "database_root": str(
                database.ROOT
            ),
            "database_file": str(
                database.DATABASE
            ),
            "doctor_root": str(
                doctor.ROOT
            ),
            "doctor_config": str(
                doctor.CONFIG
            ),
            "doctor_filters": str(
                doctor.FILTERS
            ),
            "doctor_releases": str(
                doctor.RELEASES
            ),
        }
    )
)
"""

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=True,
    )

    return json.loads(
        completed.stdout
    )


def test_consumers_use_explicit_home(
    tmp_path,
):
    root = tmp_path / "runtime"

    result = run_probe(
        runtime_root=root
    )

    resolved = root.resolve()

    assert result == {
        "database_root": str(
            resolved
        ),
        "database_file": str(
            resolved
            / "database"
            / "domains.csv"
        ),
        "doctor_root": str(
            resolved
        ),
        "doctor_config": str(
            resolved / "config"
        ),
        "doctor_filters": str(
            resolved / "filters"
        ),
        "doctor_releases": str(
            resolved / "releases"
        ),
    }


def test_consumers_default_to_source_root():
    result = run_probe(
        runtime_root=None
    )

    assert result[
        "database_root"
    ] == str(PROJECT_ROOT)

    assert result[
        "doctor_root"
    ] == str(PROJECT_ROOT)


def test_consumer_imports_do_not_create_home(
    tmp_path,
):
    root = (
        tmp_path
        / "not-created"
    )

    run_probe(
        runtime_root=root
    )

    assert not root.exists()
