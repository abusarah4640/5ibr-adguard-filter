#!/usr/bin/env python3

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

VERSION_FILE = ROOT / "VERSION"


def get_version():

    return VERSION_FILE.read_text(
        encoding="utf-8"
    ).strip()


def set_version(version):

    VERSION_FILE.write_text(
        version.strip() + "\n",
        encoding="utf-8"
    )


if __name__ == "__main__":

    print(get_version())