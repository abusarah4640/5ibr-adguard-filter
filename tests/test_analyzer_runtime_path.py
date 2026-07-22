import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)


def test_analyzer_config_uses_fivebr_home(
    tmp_path,
):
    runtime = tmp_path / "runtime"

    config = runtime / "config"
    config.mkdir(parents=True)

    expected = {
        "vendor_patterns": {},
        "category_keywords": {},
        "filter_map": {},
    }

    (
        config / "analyzer.json"
    ).write_text(
        json.dumps(expected),
        encoding="utf-8",
    )

    environment = os.environ.copy()

    environment["FIVEBR_HOME"] = str(
        runtime
    )
    environment["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + environment.get("PYTHONPATH", "")

    code = """
import json

from scripts.services.analyzer_service import (
    load_analyzer_config,
)

print(json.dumps(load_analyzer_config()))
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
        completed.stderr
    )

    assert json.loads(
        completed.stdout
    ) == expected
