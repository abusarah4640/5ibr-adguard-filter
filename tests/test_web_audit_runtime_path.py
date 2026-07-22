import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)


def test_audit_log_uses_fivebr_home(
    tmp_path,
):
    runtime = tmp_path / "runtime"
    runtime.mkdir()

    environment = os.environ.copy()

    environment["FIVEBR_HOME"] = str(
        runtime
    )

    environment["PYTHONPATH"] = str(
        PROJECT_ROOT
    )

    code = """
from scripts.services.audit_service import (
    log_event,
)

log_event(
    action="stage63e.audit",
    target="runtime.invalid",
)
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

    audit = (
        runtime
        / "data"
        / "audit"
        / "web-audit.csv"
    )

    assert audit.is_file()

    text = audit.read_text(
        encoding="utf-8"
    )

    assert "stage63e.audit" in text
    assert "runtime.invalid" in text
