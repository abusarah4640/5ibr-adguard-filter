#!/usr/bin/env python3

from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent

FILTERS = [
    "ads.txt",
    "telemetry.txt",
    "privacy.txt",
    "social.txt",
    "mobile.txt",
    "gaming.txt",
    "smart-tv.txt",
]

FILTER_DIR = ROOT / "filters"
OUTPUT_DIR = ROOT / "releases"

OUTPUT_FILE = OUTPUT_DIR / "home.txt"

VERSION = "1.0.0"

HEADER = f"""! Title: 5ibr Home Filter
! Description: Combined filter generated automatically.
! Author: 5ibr
! Homepage: https://github.com/abusarah4640/5ibr-adguard-filter
! Version: {VERSION}
! Last modified: {date.today()}
! Expires: 7 days

"""

rules = []

for file in FILTERS:

    path = FILTER_DIR / file

    if not path.exists():
        continue

    for line in path.read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith("!"):
            continue

        if line not in rules:
            rules.append(line)

OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_FILE.write_text(
    HEADER + "\n".join(rules),
    encoding="utf-8"
)

print(f"Generated {OUTPUT_FILE}")