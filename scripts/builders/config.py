#!/usr/bin/env python3

"""Generate runtime vendor and signature configuration."""

import json
from pathlib import Path

from scripts.runtime.paths import (
    get_runtime_paths,
)


def get_config_dir() -> Path:
    """Return the active runtime config directory."""

    return get_runtime_paths().config


CONFIG_DIR = get_config_dir()


def build_config(
    rows: list[dict],
) -> None:
    """Generate vendors.json and signatures.json."""

    config_dir = get_config_dir()

    config_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    vendors: dict[str, list[str]] = {}
    signatures: dict[str, dict] = {}

    for row in rows:
        vendor = row["Vendor"].strip()
        category = row["Category"].strip()
        domain = row["Domain"].strip()

        if vendor not in vendors:
            vendors[vendor] = []

        if category not in vendors[vendor]:
            vendors[vendor].append(
                category
            )

        signatures[domain] = {
            "vendor": vendor,
            "category": category,
            "filter": row["Filter"],
            "confidence": int(
                row["Confidence"]
            ),
        }

    (
        config_dir
        / "vendors.json"
    ).write_text(
        json.dumps(
            vendors,
            indent=4,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    (
        config_dir
        / "signatures.json"
    ).write_text(
        json.dumps(
            signatures,
            indent=4,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("Generated vendors.json")
    print("Generated signatures.json")
