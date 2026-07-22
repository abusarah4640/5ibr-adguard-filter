#!/usr/bin/env python3
"""Version access helpers for source and installed environments."""

from __future__ import annotations

from importlib.metadata import (
    PackageNotFoundError,
    version as package_version,
)
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
PACKAGE_NAME = "fivebr"


def get_version() -> str:
    """Return the runtime version.

    Source checkouts prefer the VERSION file so staged operational
    versions remain visible. Installed distributions fall back to
    package metadata.
    """

    if VERSION_FILE.is_file():
        value = VERSION_FILE.read_text(
            encoding="utf-8"
        ).strip()

        if value:
            return value

    try:
        return package_version(PACKAGE_NAME)

    except PackageNotFoundError:
        return "unknown"


def set_version(version: str) -> None:
    """Write the source-tree VERSION file."""

    value = version.strip()

    if not value:
        raise ValueError(
            "Version must not be empty."
        )

    VERSION_FILE.write_text(
        value + "\n",
        encoding="utf-8",
    )


def main(
    argv: list[str] | None = None,
) -> int:
    """Print the current runtime version."""

    del argv

    print(get_version())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
