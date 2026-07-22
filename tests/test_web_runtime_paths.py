import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)


def test_web_uses_fivebr_home_from_arbitrary_cwd(
    tmp_path,
):
    runtime = tmp_path / "runtime"

    environment = os.environ.copy()

    environment["FIVEBR_HOME"] = str(
        runtime
    )

    environment["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + environment.get("PYTHONPATH", "")

    code = """
from web.app import (
    RELEASES_DIR,
    REPORTS_DIR,
    UPLOADS_DIR,
)

print(RELEASES_DIR)
print(REPORTS_DIR)
print(UPLOADS_DIR)
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

    lines = [
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip()
    ]

    assert lines == [
        str(runtime / "releases"),
        str(runtime / "reports"),
        str(runtime / "data" / "uploads"),
    ]


def test_web_version_uses_package_metadata(
    tmp_path,
):
    runtime = tmp_path / "runtime"

    environment = os.environ.copy()

    environment["FIVEBR_HOME"] = str(
        runtime
    )

    environment["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + environment.get("PYTHONPATH", "")

    code = """
from web.app import app

app.testing = True

with app.test_client() as client:
    response = client.get("/")

text = response.data.decode(
    "utf-8",
    errors="replace",
)

assert response.status_code == 200
assert "2.2.0" in text
assert "Version unknown" not in text
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
