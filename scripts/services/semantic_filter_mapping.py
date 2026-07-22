"""Canonical semantic mapping from categories to filter identities.

This mapping is used by diagnostics and preview systems only.
It does not replace the legacy Analyzer configuration.
"""

from __future__ import annotations


SEMANTIC_FILTER_MAP: dict[str, str] = {
    "Ads": "ads",
    "Telemetry": "telemetry",
    "Privacy": "privacy",
    "Crash Reporting": "telemetry",
    "Social": "social",
    "Gaming": "gaming",
    "Streaming": "streaming",
    "Connectivity": "connectivity",
    "Smart TV": "smart-tv",
    "Mobile": "mobile",
}


def normalize_mapping_value(value: str) -> str:
    return " ".join(
        (value or "")
        .strip()
        .casefold()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


def semantic_filter_for_category(
    category: str,
) -> str:
    """Return the canonical filter identity for a category."""

    normalized = normalize_mapping_value(category)

    if not normalized:
        return ""

    for category_name, filter_name in (
        SEMANTIC_FILTER_MAP.items()
    ):
        if (
            normalize_mapping_value(category_name)
            == normalized
        ):
            return filter_name

    return ""


def compare_filter_mappings(
    configured_map: dict[str, str],
) -> list[dict[str, str]]:
    """Return differences between legacy and semantic mappings."""

    differences: list[dict[str, str]] = []

    for category, semantic_filter in (
        SEMANTIC_FILTER_MAP.items()
    ):
        configured_filter = ""

        for key, value in configured_map.items():
            if (
                normalize_mapping_value(key)
                == normalize_mapping_value(category)
            ):
                configured_filter = str(value).strip()
                break

        if (
            normalize_mapping_value(configured_filter)
            != normalize_mapping_value(semantic_filter)
        ):
            differences.append(
                {
                    "category": category,
                    "configured_filter": configured_filter,
                    "semantic_filter": semantic_filter,
                }
            )

    return differences
