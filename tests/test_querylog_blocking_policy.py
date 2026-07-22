from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]


def write_querylog(
    path: Path,
) -> None:
    """Write valid AdGuard NDJSON test traffic."""

    records = [
        {
            "T": "2026-07-15T00:00:00Z",
            "QH": "tpc.googlesyndication.com",
            "QT": "A",
            "QC": "IN",
            "CP": "",
            "Upstream": "1.1.1.1:53",
            "Answer": "",
            "IP": "192.0.2.10",
            "Result": {},
            "Elapsed": 1000,
        },
        {
            "T": "2026-07-15T00:00:01Z",
            "QH": "beacons.gvt2.com",
            "QT": "A",
            "QC": "IN",
            "CP": "",
            "Upstream": "1.1.1.1:53",
            "Answer": "",
            "IP": "192.0.2.10",
            "Result": {},
            "Elapsed": 1000,
        },
        {
            "T": "2026-07-15T00:00:02Z",
            "QH": "youtubei.googleapis.com",
            "QT": "A",
            "QC": "IN",
            "CP": "",
            "Upstream": "1.1.1.1:53",
            "Answer": "",
            "IP": "192.0.2.10",
            "Result": {},
            "Elapsed": 1000,
        },
    ]

    with path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        for record in records:
            handle.write(
                json.dumps(record)
                + "\n"
            )


def run_analyze_log(
    runtime: Path,
    querylog: Path,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()

    environment["FIVEBR_HOME"] = str(
        runtime
    )

    environment["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + environment.get("PYTHONPATH", "")

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "fivebr",
            "analyze-log",
            str(querylog),
            "--min-seen",
            "1",
            "--limit",
            "10",
            "--min-confidence",
            "0",
        ],
        cwd=querylog.parent,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_analyze_log_writes_reports_to_fivebr_home(
    tmp_path: Path,
):
    runtime = (
        tmp_path
        / "runtime"
    )

    reports = (
        runtime
        / "reports"
    )

    reports.mkdir(
        parents=True,
    )

    querylog = (
        tmp_path
        / "querylog.ndjson"
    )

    write_querylog(querylog)

    completed = run_analyze_log(
        runtime,
        querylog,
    )

    assert completed.returncode == 0, (
        completed.stdout
        + "\n"
        + completed.stderr
    )

    assert (
        reports
        / "suggestions.csv"
    ).is_file()

    assert (
        reports
        / "suggestions.md"
    ).is_file()

    assert str(
        reports
        / "suggestions.csv"
    ) in completed.stdout

    assert str(
        reports
        / "suggestions.md"
    ) in completed.stdout


def test_querylog_csv_contains_blocking_policy(
    tmp_path: Path,
):
    runtime = (
        tmp_path
        / "runtime"
    )

    (
        runtime
        / "reports"
    ).mkdir(
        parents=True,
    )

    querylog = (
        tmp_path
        / "querylog.ndjson"
    )

    write_querylog(querylog)

    completed = run_analyze_log(
        runtime,
        querylog,
    )

    assert completed.returncode == 0, (
        completed.stdout
        + "\n"
        + completed.stderr
    )

    csv_path = (
        runtime
        / "reports"
        / "suggestions.csv"
    )

    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(
            csv.DictReader(handle)
        )

    assert len(rows) == 3

    required_columns = {
        "Blocking Policy",
        "Blocking Policy Reason",
        "Blocking Policy Source",
    }

    assert required_columns <= set(
        rows[0]
    )

    by_domain = {
        row["Domain"]: row
        for row in rows
    }

    assert (
        by_domain[
            "tpc.googlesyndication.com"
        ]["Blocking Policy"]
        == "safe-to-block"
    )

    assert (
        by_domain[
            "beacons.gvt2.com"
        ]["Blocking Policy"]
        == "needs-testing"
    )

    assert (
        by_domain[
            "youtubei.googleapis.com"
        ]["Blocking Policy"]
        == "do-not-block"
    )

    for row in rows:
        assert row[
            "Blocking Policy Reason"
        ]

        assert row[
            "Blocking Policy Source"
        ]


def test_querylog_markdown_contains_policy_fields(
    tmp_path: Path,
):
    runtime = (
        tmp_path
        / "runtime"
    )

    (
        runtime
        / "reports"
    ).mkdir(
        parents=True,
    )

    querylog = (
        tmp_path
        / "querylog.ndjson"
    )

    write_querylog(querylog)

    completed = run_analyze_log(
        runtime,
        querylog,
    )

    assert completed.returncode == 0, (
        completed.stdout
        + "\n"
        + completed.stderr
    )

    markdown = (
        runtime
        / "reports"
        / "suggestions.md"
    ).read_text(
        encoding="utf-8"
    )

    required_text = (
        "Blocking Policy",
        "Blocking Policy Reason",
        "Blocking Policy Source",
        "safe-to-block",
        "needs-testing",
        "do-not-block",
    )

    for value in required_text:
        assert value in markdown
