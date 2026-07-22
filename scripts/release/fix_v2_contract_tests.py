#!/usr/bin/env python3
"""Update stale v1.9.0 release-contract assertions for the v2.0.0 release."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TARGET_VERSION = (PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").strip()
EXPECTED_VERSION = "2.0.0"
TEST_FILES = (
    PROJECT_ROOT / "tests" / "test_release_version_contract.py",
    PROJECT_ROOT / "tests" / "test_web_runtime_paths.py",
)


def update_test_file(path: Path) -> int:
    if not path.exists():
        raise FileNotFoundError(f"Missing expected test file: {path}")

    original = path.read_text(encoding="utf-8")
    updated = original.replace('"1.9.0"', f'"{EXPECTED_VERSION}"')
    updated = updated.replace("'1.9.0'", f"'{EXPECTED_VERSION}'")

    changed = int(updated != original)
    if changed:
        path.write_text(updated, encoding="utf-8")
    return changed


def main() -> None:
    if TARGET_VERSION != EXPECTED_VERSION:
        raise RuntimeError(
            f"VERSION is {TARGET_VERSION!r}; expected {EXPECTED_VERSION!r}. "
            "Run prepare_v2_0_0.py first."
        )

    changed = sum(update_test_file(path) for path in TEST_FILES)

    stale = [
        str(path)
        for path in TEST_FILES
        if "1.9.0" in path.read_text(encoding="utf-8")
    ]
    if stale:
        raise RuntimeError(
            "Stale 1.9.0 assertions remain in: " + ", ".join(stale)
        )

    print(f"Updated release contract tests for {EXPECTED_VERSION}.")
    print(f"Files changed: {changed}")
    print("Application and production code were not modified.")


if __name__ == "__main__":
    main()
