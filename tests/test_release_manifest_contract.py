from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

MANIFEST = (
    PROJECT_ROOT / "MANIFEST.in"
)

REQUIRED_LINES = {
    "include README.md",
    "include CHANGELOG.md",
    "include RELEASE_NOTES.md",
    "include LICENSE",
    "include VERSION",
}


def test_manifest_exists():
    assert MANIFEST.is_file()


def test_manifest_includes_release_documents():
    lines = {
        line.strip()
        for line in MANIFEST.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    }

    assert REQUIRED_LINES <= lines
