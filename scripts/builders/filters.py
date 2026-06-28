#!/usr/bin/env python3

from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent.parent

FILTERS = ROOT / "filters"

HEADER = """! Title: 5ibr Filter
! Generated automatically.
!
"""


def build_filters(rows):

    FILTERS.mkdir(exist_ok=True)

    groups = defaultdict(list)

    for row in rows:

        groups[row["Filter"]].append(
            "||" + row["Domain"] + "^"
        )

    for name, rules in groups.items():

        output = FILTERS / f"{name}.txt"

        output.write_text(
            HEADER +
            "\n".join(sorted(set(rules))) +
            "\n",
            encoding="utf-8"
        )

        print(f"Generated {output.name}")