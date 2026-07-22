import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)


def test_backup_uses_fivebr_home(
    tmp_path,
):
    runtime = tmp_path / "runtime"

    (runtime / "database").mkdir(
        parents=True
    )

    (
        runtime
        / "database"
        / "domains.csv"
    ).write_text(
        (
            "Domain,Vendor,Category,"
            "Filter,Confidence,Status\n"
        ),
        encoding="utf-8",
    )

    environment = os.environ.copy()

    environment["FIVEBR_HOME"] = str(
        runtime
    )

    environment["PYTHONPATH"] = str(
        PROJECT_ROOT
    )

    code = """
from scripts.services.backup_service import (
    create_backup,
)

path = create_backup(
    "stage63e-runtime-test"
)

print(path)
"""

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
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

    backup_root = (
        runtime
        / "data"
        / "backups"
    )

    assert backup_root.is_dir()

    backups = [
        path
        for path in backup_root.iterdir()
        if path.is_dir()
    ]

    assert backups

    copied_database = [
        path
        for path in backups[0].rglob(
            "domains.csv"
        )
    ]

    assert copied_database
