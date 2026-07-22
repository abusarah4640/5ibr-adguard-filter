#!/usr/bin/env python3

"""Build filters, config and releases through a validated staging tree."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.builders.config import build_config
from scripts.builders.database import load_database
from scripts.builders.filters import build_filters
from scripts.builders.releases import build_releases
from scripts.cli import parse_no_args
from scripts.runtime.paths import get_runtime_paths


PROMOTED_DIRECTORIES = ("config", "filters", "releases")


def build_in_place() -> int:
    """Run the existing builders against the active runtime root."""

    print("===================================")
    print("5ibr Filter Build System")
    print("===================================")
    print()

    print("Loading database...")
    rows = load_database()
    print(f"Loaded {len(rows)} approved domains.")
    print()

    print("Generating filters...")
    build_filters(rows)
    print()

    print("Generating config...")
    build_config(rows)
    print()

    print("Generating releases...")
    build_releases()
    print()

    print("===================================")
    print("Build completed successfully.")
    print("===================================")

    return 0


def copy_runtime_inputs(runtime_root: Path, staging_root: Path) -> None:
    """Copy required build inputs without touching live outputs."""

    for name in ("config", "database", "filters"):
        source = runtime_root / name
        destination = staging_root / name
        if source.exists():
            shutil.copytree(source, destination)
        else:
            destination.mkdir(parents=True, exist_ok=True)

    version_file = runtime_root / "VERSION"
    if version_file.exists():
        shutil.copy2(version_file, staging_root / "VERSION")


def run_staging_command(
    staging_root: Path,
    command: str,
) -> subprocess.CompletedProcess[str]:
    """Run one CLI command against the isolated staging runtime."""

    environment = os.environ.copy()
    environment["FIVEBR_HOME"] = str(staging_root)

    if command == "build":
        invocation = [
            sys.executable,
            "-c",
            (
                "from scripts.build import build_in_place; "
                "raise SystemExit(build_in_place())"
            ),
        ]
    else:
        invocation = [
            sys.executable,
            "-m",
            "fivebr",
            command,
        ]

    completed = subprocess.run(
        invocation,
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)

    return completed


def remove_path(path: Path) -> None:
    """Remove a file, symlink or directory without following symlinks."""

    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def promote_staged_outputs(
    runtime_root: Path,
    staging_root: Path,
    backup_root: Path,
) -> None:
    """Promote staged directories and restore every prior output on error."""

    promoted: list[tuple[str, bool]] = []

    try:
        for name in PROMOTED_DIRECTORIES:
            staged = staging_root / name
            current = runtime_root / name
            backup = backup_root / name

            if not staged.is_dir():
                raise RuntimeError(
                    f"Staged build did not produce required directory: {name}"
                )

            had_current = current.exists() or current.is_symlink()
            if had_current:
                os.replace(current, backup)

            try:
                os.replace(staged, current)
            except Exception:
                if had_current and backup.exists():
                    os.replace(backup, current)
                raise

            promoted.append((name, had_current))

    except Exception:
        for name, had_current in reversed(promoted):
            current = runtime_root / name
            backup = backup_root / name
            remove_path(current)
            if had_current and backup.exists():
                os.replace(backup, current)
        raise


def staged_build() -> int:
    """Build, validate and promote without exposing partial outputs."""

    runtime_root = get_runtime_paths().root
    runtime_root.mkdir(parents=True, exist_ok=True)

    staging_root = Path(
        tempfile.mkdtemp(
            prefix=".fivebr-build-staging-",
            dir=runtime_root,
        )
    )
    backup_root = Path(
        tempfile.mkdtemp(
            prefix=".fivebr-build-backup-",
            dir=runtime_root,
        )
    )

    try:
        copy_runtime_inputs(runtime_root, staging_root)

        print(f"Building in staging runtime: {staging_root}")
        build_result = run_staging_command(staging_root, "build")
        if build_result.returncode != 0:
            print("Staged build FAILED; live outputs were not changed.")
            return build_result.returncode

        print("Validating staged outputs...")
        validate_result = run_staging_command(staging_root, "validate")
        if validate_result.returncode != 0:
            print("Staged validation FAILED; live outputs were not changed.")
            return validate_result.returncode

        promote_staged_outputs(
            runtime_root,
            staging_root,
            backup_root,
        )

        print("Validated staged outputs promoted successfully.")
        return 0

    finally:
        remove_path(staging_root)
        remove_path(backup_root)


def main(argv: list[str] | None = None) -> int:
    """Build filters, generated config files and release bundles."""

    parse_no_args(
        prog="fivebr build",
        description="Build filters, configs and releases",
        argv=argv,
    )

    return staged_build()


if __name__ == "__main__":
    raise SystemExit(main())
