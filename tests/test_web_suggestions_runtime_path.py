import csv
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)


FIELDNAMES = [
    "Domain",
    "Seen",
    "Root",
    "Suggested Vendor",
    "Suggested Category",
    "Suggested Filter",
    "Confidence",
    "Recommendation",
    "Reasons",
]


def write_suggestions(
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDNAMES,
        )

        writer.writeheader()

        writer.writerow(
            {
                "Domain": (
                    "stage63e-suggestion.invalid"
                ),
                "Seen": "12",
                "Root": (
                    "stage63e-suggestion.invalid"
                ),
                "Suggested Vendor": (
                    "Runtime Vendor"
                ),
                "Suggested Category": (
                    "Telemetry"
                ),
                "Suggested Filter": (
                    "telemetry"
                ),
                "Confidence": "80",
                "Recommendation": "review",
                "Reasons": "runtime test",
            }
        )


def test_suggestions_use_fivebr_home(
    tmp_path,
):
    runtime = tmp_path / "runtime"

    suggestions = (
        runtime
        / "reports"
        / "suggestions.csv"
    )

    write_suggestions(
        suggestions
    )

    environment = os.environ.copy()

    environment["FIVEBR_HOME"] = str(
        runtime
    )

    environment["PYTHONPATH"] = str(
        PROJECT_ROOT
    )

    code = """
from scripts.services.suggestions_service import (
    find_suggestion,
    load_suggestions,
    remove_suggestion,
)

rows = load_suggestions()

assert len(rows) == 1

item = find_suggestion(
    "stage63e-suggestion.invalid"
)

assert item is not None

assert (
    item["Suggested Vendor"]
    == "Runtime Vendor"
)

removed = remove_suggestion(
    "stage63e-suggestion.invalid"
)

assert removed is True
assert load_suggestions() == []
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

    with suggestions.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(
            csv.DictReader(handle)
        )

    assert rows == []


def test_review_decisions_use_fivebr_home(
    tmp_path,
):
    runtime = tmp_path / "runtime"

    suggestions = (
        runtime
        / "reports"
        / "suggestions.csv"
    )

    write_suggestions(
        suggestions
    )

    environment = os.environ.copy()

    environment["FIVEBR_HOME"] = str(
        runtime
    )

    environment["PYTHONPATH"] = str(
        PROJECT_ROOT
    )

    code = """
from scripts.services.suggestions_service import (
    append_decision,
    load_decisions,
    load_suggestions,
)

row = load_suggestions()[0]

append_decision(
    row,
    action="approved",
    reason="runtime decision",
)

decisions = load_decisions()

assert len(decisions) == 1

assert (
    decisions[0]["Domain"]
    == "stage63e-suggestion.invalid"
)

assert (
    decisions[0]["Action"]
    == "approved"
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

    decisions = (
        runtime
        / "reports"
        / "suggestion-decisions.csv"
    )

    assert decisions.is_file()

    with decisions.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as handle:
        rows = list(
            csv.DictReader(handle)
        )

    assert len(rows) == 1
    assert rows[0]["Action"] == "approved"
