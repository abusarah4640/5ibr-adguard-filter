#!/usr/bin/env python3

"""Backup helpers for Web UI write operations."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from scripts.runtime.paths import (
    get_runtime_paths,
)


def get_backup_root() -> Path:
    """Return the active runtime backup directory."""

    return (
        get_runtime_paths().data
        / "backups"
    )


def get_files_to_backup() -> tuple[Path, ...]:
    """Return mutable files from the active runtime."""

    paths = get_runtime_paths()

    return (
        paths.database / "domains.csv",
        paths.config / "analyzer.json",
        paths.reports / "suggestions.csv",
        paths.reports / "suggestions.md",
    )


# Compatibility constants for older consumers and tests.
BACKUP_ROOT = get_backup_root()
FILES_TO_BACKUP = list(
    get_files_to_backup()
)


def timestamp() -> str:
    """Return a UTC backup timestamp."""

    return datetime.now(
        UTC
    ).strftime(
        "%Y%m%d-%H%M%S"
    )


def create_backup(
    reason: str = "manual",
) -> Path:
    """Create a timestamped backup of runtime files."""

    paths = get_runtime_paths()

    backup_root = (
        paths.data
        / "backups"
    )

    files_to_backup = (
        paths.database
        / "domains.csv",
        paths.config
        / "analyzer.json",
        paths.reports
        / "suggestions.csv",
        paths.reports
        / "suggestions.md",
    )

    safe_reason = "".join(
        (
            character
            if (
                character.isalnum()
                or character in "-_"
            )
            else "-"
        )
        for character in reason
    )[:48]

    backup_dir = (
        backup_root
        / (
            f"{timestamp()}-"
            f"{safe_reason or 'backup'}"
        )
    )

    backup_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for source in files_to_backup:
        if not source.exists():
            continue

        destination = (
            backup_dir
            / source.relative_to(
                paths.root
            )
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            destination,
        )

    return backup_dir
