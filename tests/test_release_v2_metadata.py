"""Metadata contract for the 2.2.0rc1 candidate."""

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_VERSION = "2.2.0rc1"


def test_release_candidate_metadata_is_consistent():
    runtime_version = (
        PROJECT_ROOT
        / "VERSION"
    ).read_text(encoding="utf-8").strip()

    pyproject = (
        PROJECT_ROOT
        / "pyproject.toml"
    ).read_text(encoding="utf-8")

    assert runtime_version == CANDIDATE_VERSION
    assert re.search(
        r'(?m)^version\s*=\s*["\']2\.2\.0rc1["\']\s*$',
        pyproject,
    )


def test_candidate_documents_fail_closed_release_status():
    changelog = (
        PROJECT_ROOT
        / "CHANGELOG.md"
    ).read_text(encoding="utf-8")

    notes = (
        PROJECT_ROOT
        / "RELEASE_NOTES.md"
    ).read_text(encoding="utf-8")

    assert "## [2.2.0rc1] - Unreleased" in changelog
    assert "Release status remains NOT READY" in changelog
    assert "# 5ibr 2.2.0rc1 Release Candidate" in notes
    assert "Independent review" in notes
    assert "PENDING" in notes
    assert "Release status" in notes
    assert "NOT READY" in notes


def test_historical_v2_release_notes_remain_available():
    notes = (
        PROJECT_ROOT
        / "docs"
        / "RELEASE_NOTES_2.0.0.md"
    ).read_text(encoding="utf-8")

    assert "Manual approval gate" in notes
    assert "Append-only audit" in notes
