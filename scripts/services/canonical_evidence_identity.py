"""Canonical identities for semantically equivalent evidence values."""

from __future__ import annotations

import re


VENDOR_ALIASES: dict[str, set[str]] = {
    "sony-playstation": {
        "sony",
        "sony playstation",
        "playstation",
        "psn",
    },
    "meta": {
        "meta",
        "facebook",
        "facebook inc",
        "facebook incorporated",
    },
}


def normalize_identity_text(value: str) -> str:
    """Normalize text before canonical identity lookup."""

    normalized = (value or "").strip().casefold()
    normalized = re.sub(r"[_-]+", " ", normalized)
    normalized = re.sub(r"[^\w\s]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def _normalized_vendor_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}

    for canonical, values in VENDOR_ALIASES.items():
        canonical_key = normalize_identity_text(canonical).replace(
            " ",
            "-",
        )

        for value in values:
            aliases[normalize_identity_text(value)] = canonical_key

    return aliases


def canonical_vendor_identity(value: str) -> str:
    """Resolve a vendor label to a controlled canonical identity."""

    normalized = normalize_identity_text(value)

    if not normalized:
        return ""

    aliases = _normalized_vendor_aliases()

    return aliases.get(
        normalized,
        normalized,
    )


def canonical_evidence_identity(
    field_name: str,
    value: str,
) -> str:
    """Resolve an evidence value according to its semantic field."""

    normalized_field = (
        field_name or ""
    ).strip().casefold()

    if normalized_field == "vendor":
        return canonical_vendor_identity(value)

    return normalize_identity_text(value)


CANONICAL_PREFERRED_LABELS: dict[str, dict[str, str]] = {
    "vendor": {
        "sony-playstation": "Sony PlayStation",
        "meta": "Meta",
    },
}


def preferred_evidence_label(
    field_name: str,
    identity: str,
    fallback: str,
) -> str:
    """Return the preferred display label for a canonical identity."""

    normalized_field = (
        field_name or ""
    ).strip().casefold()

    normalized_identity = (
        identity or ""
    ).strip().casefold()

    preferred = CANONICAL_PREFERRED_LABELS.get(
        normalized_field,
        {},
    ).get(normalized_identity)

    if preferred:
        return preferred

    normalized_fallback = (fallback or "").strip()

    if normalized_fallback:
        return normalized_fallback

    return normalized_identity
