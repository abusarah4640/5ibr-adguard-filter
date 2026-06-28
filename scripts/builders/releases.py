#!/usr/bin/env python3

"""
Generate release files from config/releases.json
"""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent.parent

CONFIG_FILE = ROOT / "config" / "releases.json"
FILTERS_DIR = ROOT / "filters"
RELEASES_DIR = ROOT / "releases"

HEADER = """! Title: {title}
! Description: {description}
! Homepage: https://github.com/abusarah4640/5ibr-adguard-filter
! License: GPL-3.0
! Generated automatically.
!
"""


def build_releases():

    RELEASES_DIR.mkdir(exist_ok=True)

    with open(CONFIG_FILE, encoding="utf-8") as f:
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

            filter_file = FILTERS_DIR / f"{filter_name}.txt"

            if not filter_file.exists():
                print(f"Warning: {filter_name}.txt not found")
                continue

            output.append(
                f"! ===== {filter_name.upper()} ====="
            )

            output.append(filter_file.read_text(encoding="utf-8"))

        (RELEASES_DIR / f"{release_name}.txt").write_text(
            "\n".join(output),
            encoding="utf-8"
        )

        print(f"Generated {release_name}.txt")