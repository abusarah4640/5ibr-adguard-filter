import os
import sys
import subprocess
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)


def test_active_intelligence_commands_do_not_report_unknown_version(
    tmp_path,
):
    runtime = tmp_path / "runtime"

    environment = os.environ.copy()

    environment["FIVEBR_HOME"] = str(
        runtime
    )

    environment["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + environment.get("PYTHONPATH", "")

    init = subprocess.run(
        [
            sys.executable,
            "-m",
            "fivebr",
            "init",
            str(runtime),
        ],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert init.returncode == 0, (
        init.stdout
        + "\n"
        + init.stderr
    )

    for command in (
        "intelligence-check",
        "intelligence-diagnostics",
        "intelligence-report",
    ):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "fivebr",
                command,
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

        assert completed.returncode == 0, (
            command
            + "\n"
            + combined
        )

        assert (
            "Version            : unknown"
            not in combined
        )

        assert (
            "Version: unknown"
            not in combined
        )
