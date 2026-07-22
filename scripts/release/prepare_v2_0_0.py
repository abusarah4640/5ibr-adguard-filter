from __future__ import annotations

import re
from pathlib import Path

TARGET_VERSION = "2.0.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = PROJECT_ROOT / "VERSION"
PYPROJECT_FILE = PROJECT_ROOT / "pyproject.toml"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"
RELEASE_NOTES_FILE = PROJECT_ROOT / "docs" / "RELEASE_NOTES_2.0.0.md"

CHANGELOG_SECTION = """## [2.0.0] - 2026-07-17

### Added
- Complete guardrail readiness governance flow: evaluation, dashboard visibility, diagnostics, progress, history and trends.
- Explainable readiness decision engine with stability-window rules.
- Manual approval gate with reviewer confirmation and decision fingerprinting.
- Append-only readiness decision and approval audit archive.

### Safety
- Enforcement remains disabled and is never activated automatically by the readiness workflow.

"""


def update_version_file() -> None:
    if not VERSION_FILE.exists():
        raise FileNotFoundError(f"Missing VERSION file: {VERSION_FILE}")
    VERSION_FILE.write_text(TARGET_VERSION + "\n", encoding="utf-8")


def update_pyproject() -> None:
    if not PYPROJECT_FILE.exists():
        raise FileNotFoundError(f"Missing pyproject.toml: {PYPROJECT_FILE}")

    original = PYPROJECT_FILE.read_text(encoding="utf-8")
    pattern = re.compile(r'(?m)^(version\s*=\s*)["\'][^"\']+["\']\s*$')
    updated, count = pattern.subn(rf'\g<1>"{TARGET_VERSION}"', original, count=1)
    if count != 1:
        raise RuntimeError(
            "Could not find exactly one static version assignment in pyproject.toml. "
            "No files beyond VERSION were changed."
        )
    PYPROJECT_FILE.write_text(updated, encoding="utf-8")


def update_changelog() -> None:
    if CHANGELOG_FILE.exists():
        current = CHANGELOG_FILE.read_text(encoding="utf-8")
        if "## [2.0.0]" in current:
            return
        if current.startswith("# Changelog"):
            rest = current[len("# Changelog"):].lstrip("\n")
            content = "# Changelog\n\n" + CHANGELOG_SECTION + rest
        else:
            content = "# Changelog\n\n" + CHANGELOG_SECTION + current
    else:
        content = "# Changelog\n\n" + CHANGELOG_SECTION
    CHANGELOG_FILE.write_text(content.rstrip() + "\n", encoding="utf-8")


def verify_release_notes() -> None:
    if not RELEASE_NOTES_FILE.exists():
        raise FileNotFoundError(f"Missing release notes: {RELEASE_NOTES_FILE}")


def main() -> None:
    verify_release_notes()
    update_version_file()
    update_pyproject()
    update_changelog()
    print(f"Prepared 5ibr Filter Toolkit v{TARGET_VERSION}")
    print(f"VERSION: {VERSION_FILE}")
    print(f"pyproject: {PYPROJECT_FILE}")
    print(f"changelog: {CHANGELOG_FILE}")
    print("Enforcement remains disabled.")


if __name__ == "__main__":
    main()
