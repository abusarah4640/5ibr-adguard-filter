from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

VERSION = "1.9.0"


def read(name: str) -> str:
    return (
        PROJECT_ROOT / name
    ).read_text(
        encoding="utf-8"
    )


def test_changelog_contains_final_release():
    text = read("CHANGELOG.md")

    assert VERSION in text
    assert "Runtime project architecture" in text
    assert "422 automated tests passed" in text
    assert (
        "Production service remained active"
        in text
    )


def test_release_notes_match_final_version():
    text = read("RELEASE_NOTES.md")

    assert (
        "# 5ibr 1.9.0 Final Release"
        in text
    )

    assert (
        "Release date: 2026-07-15"
        in text
    )

    assert (
        "FINAL RELEASE READY"
        in text
    )


def test_release_notes_have_artifact_sections():
    text = read("RELEASE_NOTES.md")

    assert (
        "fivebr-1.9.0-py3-none-any.whl"
        in text
    )

    assert (
        "fivebr-1.9.0.tar.gz"
        in text
    )

    assert "SHA256SUMS.txt" in text


def test_release_notes_document_runtime_isolation():
    text = read("RELEASE_NOTES.md")

    assert "FIVEBR_HOME" in text
    assert "Installed Wheel validation" in text
    assert "Mutable-service isolation" in text

    assert (
        "production database rows"
        in text.lower()
    )


def test_readme_documents_final_runtime_workflow():
    text = read("README.md")

    assert (
        "<!-- fivebr-runtime-release -->"
        in text
    )

    assert (
        "## 1.9.0 Runtime Projects"
        in text
    )

    assert (
        "fivebr init /path/to/project"
        in text
    )

    assert "FIVEBR_HOME" in text
    assert "fivebr project-status" in text
    assert "fivebr validate" in text
    assert "fivebr build" in text


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
