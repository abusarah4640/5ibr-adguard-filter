from pathlib import Path
import re


def test_release_v2_metadata_is_consistent():
    root = Path(__file__).resolve().parents[1]
    assert (root / "VERSION").read_text(encoding="utf-8").strip() == "2.2.0"

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'(?m)^version\s*=\s*["\']2\.0\.1["\']\s*$', pyproject)

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [2.0.0]" in changelog
    assert "Enforcement remains disabled" in changelog

    notes = (root / "docs" / "RELEASE_NOTES_2.0.0.md").read_text(encoding="utf-8")
    assert "Manual approval gate" in notes
    assert "Append-only audit" in notes
