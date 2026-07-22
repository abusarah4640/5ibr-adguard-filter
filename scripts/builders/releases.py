#!/usr/bin/env python3

"""
Generate release files from config/releases.json
"""

from pathlib import Path
import json
from scripts.runtime.paths import (
    get_runtime_paths,
)



HEADER = """! Title: {title}
! Description: {description}
! Homepage: https://github.com/abusarah4640/5ibr-adguard-filter
! License: GPL-3.0
! Generated automatically.
!
"""



def get_filters_dir() -> Path:
    return get_runtime_paths().filters


def get_releases_dir() -> Path:
    return get_runtime_paths().releases


def get_releases_config_path() -> Path:
    return (
        get_runtime_paths().config
        / "releases.json"
    )

def build_releases():

    releases_dir = get_releases_dir()
    filters_dir = get_filters_dir()
    config_file = (
        get_releases_config_path()
    )

    releases_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    with config_file.open(encoding="utf-8") as f:
        releases = json.load(f)

    for release_name, release in releases.items():

        output = []

        output.append(
            HEADER.format(
                title=release.get("title", release_name),
                description=release.get("description", "")
            )
        )

        for filter_name in release["filters"]:

            filter_file = filters_dir / f"{filter_name}.txt"

            if not filter_file.exists():
                raise FileNotFoundError(
                    f"Release '{release_name}' references missing filter: "
                    f"{filter_name}.txt"
                )

            output.append(
                f"! ===== {filter_name.upper()} ====="
            )

            output.append(filter_file.read_text(encoding="utf-8"))

        (releases_dir / f"{release_name}.txt").write_text(
            "\n".join(output),
            encoding="utf-8"
        )

        print(f"Generated {release_name}.txt")
