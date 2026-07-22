"""Initialize a safe 5ibr runtime project."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path


DIRECTORIES = (
    "config",
    "database",
    "filters",
    "releases",
    "reports",
    "data",
)


@dataclass(
    frozen=True,
    slots=True,
)
class InitResult:
    root: Path
    created_files: tuple[Path, ...]
    skipped_files: tuple[Path, ...]
    created_directories: tuple[Path, ...]


def initialize_project(
    root: str | Path,
    *,
    force: bool = False,
) -> InitResult:
    target_root = (
        Path(root)
        .expanduser()
        .resolve()
    )

    created_directories = []

    for name in DIRECTORIES:
        directory = target_root / name

        if not directory.exists():
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            created_directories.append(
                directory
            )

    seed_root = files(
        "scripts.runtime.seeds"
    )

    created_files = []
    skipped_files = []

    for group in (
        "config",
        "database",
        "filters",
    ):
        source_group = (
            seed_root / group
        )

        for source in source_group.iterdir():
            if not source.is_file():
                continue

            target = (
                target_root
                / group
                / source.name
            )

            if target.exists() and not force:
                skipped_files.append(
                    target
                )
                continue

            with source.open("rb") as input_file:
                with target.open("wb") as output_file:
                    shutil.copyfileobj(
                        input_file,
                        output_file,
                    )

            created_files.append(
                target
            )

    return InitResult(
        root=target_root,
        created_files=tuple(
            created_files
        ),
        skipped_files=tuple(
            skipped_files
        ),
        created_directories=tuple(
            created_directories
        ),
    )
