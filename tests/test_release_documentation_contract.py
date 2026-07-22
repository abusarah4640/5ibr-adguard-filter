"""Release-documentation contracts for the current candidate."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.2.0rc1"


def read(name: str) -> str:
    return (
        PROJECT_ROOT / name
    ).read_text(encoding="utf-8")


def test_changelog_describes_candidate_status():
    text = read("CHANGELOG.md")

    assert f"## [{VERSION}] - Unreleased" in text
    assert "709 automated tests" in text
    assert "Independent technical review remains pending" in text
    assert "Release status remains NOT READY" in text


def test_release_notes_match_candidate_identity():
    text = read("RELEASE_NOTES.md")

    assert f"# 5ibr {VERSION} Release Candidate" in text
    assert "Candidate date: 2026-07-22" in text
    assert "Independent review" in text
    assert "PENDING" in text
    assert "NOT READY" in text
    assert "FINAL RELEASE READY" not in text


def test_release_notes_document_candidate_artifact():
    text = read("RELEASE_NOTES.md")

    assert f"fivebr-{VERSION}-py3-none-any.whl" in text
    assert "SHA-256" in text


def test_release_notes_document_runtime_isolation():
    text = read("RELEASE_NOTES.md")
    lowered = text.lower()

    assert "FIVEBR_HOME" in text
    assert "installed wheel" in lowered
    assert "mutable runtime" in lowered
    assert "production database rows" in lowered


def test_readme_documents_candidate_workflow():
    text = read("README.md")

    assert f"Current stabilization target: `{VERSION}`" in text
    assert "NOT READY" in text
    assert "fivebr init /path/to/project" in text
    assert "FIVEBR_HOME" in text
    assert "fivebr project-status" in text
    assert "fivebr validate" in text
    assert "fivebr build" in text


def test_historical_release_notes_are_archived():
    text = read("docs/RELEASE_NOTES_1.9.0.md")

    assert "# 5ibr 1.9.0 Final Release" in text
    assert "Release date: 2026-07-15" in text


def test_release_documents_explain_package_safety():
    combined = (
        read("README.md")
        + "\n"
        + read("RELEASE_NOTES.md")
        + "\n"
        + read("CHANGELOG.md")
    ).lower()

    required = (
        "production policies",
        "audit logs",
        "runtime backups",
        "production database rows",
    )

    for phrase in required:
        assert phrase in combined


def test_release_documents_have_no_sensitive_tokens():
    combined = (
        read("README.md")
        + "\n"
        + read("RELEASE_NOTES.md")
        + "\n"
        + read("CHANGELOG.md")
    ).lower()

    forbidden = (
        "sv_licensekey",
        "begin private key",
        "authorization: bearer",
        "private_key=",
        "password=",
    )

    for token in forbidden:
        assert token not in combined
