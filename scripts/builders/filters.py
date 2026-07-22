#!/usr/bin/env python3

"""Build individual filter files."""

from pathlib import Path

from scripts.runtime.paths import (
    get_runtime_paths,
)


def get_filters_dir() -> Path:
    """Return the active runtime filters directory."""

    return get_runtime_paths().filters


FILTERS = get_filters_dir()


def build_filters(rows: list[dict]) -> None:
    """Build filter files from approved database rows."""

    filters_dir = get_filters_dir()

    filters_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    grouped: dict[str, list[str]] = {}

    for row in rows:
        filter_name = (
            row.get("Filter", "")
            .strip()
        )

        domain = (
            row.get("Domain", "")
            .strip()
            .lower()
        )

        if not filter_name or not domain:
            continue

        grouped.setdefault(
            filter_name,
            [],
        ).append(domain)

    for filter_name, domains in grouped.items():
        target = (
            filters_dir
            / f"{filter_name}.txt"
        )

        content = "\n".join(
            sorted(set(domains))
        )

        if content:
            content += "\n"

        target.write_text(
            content,
            encoding="utf-8",
        )

        print(
            f"Generated {target.name}"
        )
