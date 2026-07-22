"""Central runtime path resolution for 5ibr.

Resolution order:

1. Explicit FIVEBR_HOME environment variable.
2. Source checkout root when a valid project tree is detected.
3. Installed package location as a compatibility fallback.

This module only resolves paths. It does not create directories,
copy defaults, or mutate runtime state.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


FIVEBR_HOME_ENV = "FIVEBR_HOME"

PACKAGE_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


@dataclass(
    frozen=True,
    slots=True,
)
class RuntimePaths:
    """Resolved filesystem paths used by 5ibr."""

    root: Path
    config: Path
    database: Path
    filters: Path
    releases: Path
    reports: Path
    data: Path
    version_file: Path


def _looks_like_source_root(
    path: Path,
) -> bool:
    """Return whether path resembles a 5ibr source checkout."""

    return (
        (path / "fivebr.py").is_file()
        and (path / "scripts").is_dir()
    )


def resolve_runtime_root() -> Path:
    """Resolve the active 5ibr runtime root."""

    configured = os.environ.get(
        FIVEBR_HOME_ENV,
        "",
    ).strip()

    if configured:
        return (
            Path(configured)
            .expanduser()
            .resolve()
        )

    if _looks_like_source_root(
        PACKAGE_ROOT
    ):
        return PACKAGE_ROOT

    return PACKAGE_ROOT


def get_runtime_paths(
    root: str | Path | None = None,
) -> RuntimePaths:
    """Return all central runtime paths."""

    resolved_root = (
        Path(root)
        .expanduser()
        .resolve()
        if root is not None
        else resolve_runtime_root()
    )

    return RuntimePaths(
        root=resolved_root,
        config=resolved_root / "config",
        database=resolved_root / "database",
        filters=resolved_root / "filters",
        releases=resolved_root / "releases",
        reports=resolved_root / "reports",
        data=resolved_root / "data",
        version_file=(
            resolved_root / "VERSION"
        ),
    )


RUNTIME_PATHS = get_runtime_paths()

ROOT = RUNTIME_PATHS.root
CONFIG = RUNTIME_PATHS.config
DATABASE = RUNTIME_PATHS.database
FILTERS = RUNTIME_PATHS.filters
RELEASES = RUNTIME_PATHS.releases
REPORTS = RUNTIME_PATHS.reports
DATA = RUNTIME_PATHS.data
VERSION_FILE = RUNTIME_PATHS.version_file
