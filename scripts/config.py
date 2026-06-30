#!/usr/bin/env python3

"""
5ibr Configuration Loader
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "database.json"


@lru_cache(maxsize=1)
def load_database_config() -> dict:
    """
    Load database configuration.
    """

    with CONFIG.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def get_categories() -> dict:
    """
    Return configured categories.
    """

    return load_database_config()["categories"]


def get_category_names() -> list[str]:
    """
    Return display names of all categories.
    """

    return [
        category["name"]
        for category in get_categories().values()
    ]


def get_filters() -> list[str]:
    """
    Return all available filters.
    """

    return [
        category["filter"]
        for category in get_categories().values()
    ]


def get_confidence_limits() -> tuple[int, int]:
    """
    Return minimum and maximum confidence.
    """

    confidence = load_database_config()["confidence"]

    return (
        confidence["min"],
        confidence["max"],
    )


def get_default_confidence() -> int:
    """
    Return default confidence value.
    """

    return load_database_config()["confidence"]["default"]
