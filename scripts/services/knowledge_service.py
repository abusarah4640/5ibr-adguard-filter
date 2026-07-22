"""Knowledge Base service for 5ibr Filter Toolkit."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KNOWLEDGE_PATH = PROJECT_ROOT / "data" / "knowledge" / "base.json"


@dataclass(frozen=True)
class KnowledgeEntry:
    name: str
    kind: str
    keywords: tuple[str, ...] = field(default_factory=tuple)
    vendor: str = "Unknown"
    category: str = "Unknown"
    filter_name: str = "unknown"
    technologies: tuple[str, ...] = field(default_factory=tuple)


_DEFAULT_ENTRIES: tuple[KnowledgeEntry, ...] = (
    KnowledgeEntry(
        name="Netflix",
        kind="service",
        keywords=("netflix", "nflxvideo", "nflximg", "nccp", "nrdp"),
        vendor="Netflix",
        category="Streaming",
        filter_name="streaming",
        technologies=("video", "cdn"),
    ),
    KnowledgeEntry(
        name="PlayStation Network",
        kind="service",
        keywords=("playstation", "psn", "np.km.playstation.net"),
        vendor="Sony",
        category="Gaming",
        filter_name="gaming",
        technologies=("console", "gaming"),
    ),
    KnowledgeEntry(
        name="YouTube",
        kind="service",
        keywords=("youtube", "googlevideo", "ytimg"),
        vendor="Google",
        category="Streaming",
        filter_name="streaming",
        technologies=("video", "cdn"),
    ),
    KnowledgeEntry(
        name="LG Smart TV",
        kind="product",
        keywords=("lgtvsdp.com", "lge.com", "lgsmartad.com"),
        vendor="LG",
        category="Smart TV",
        filter_name="smart-tv",
        technologies=("smart-tv", "telemetry", "advertising"),
    ),
    KnowledgeEntry(
        name="Google Ads",
        kind="service",
        keywords=(
            "googleadservices.com",
            "googlesyndication.com",
            "doubleclick.net",
        ),
        vendor="Google",
        category="Ads",
        filter_name="ads",
        technologies=("advertising", "tracking"),
    ),
    KnowledgeEntry(
        name="Epic Games",
        kind="service",
        keywords=(
            "epicgames.com",
            "datarouter.ol.epicgames.com",
        ),
        vendor="Epic Games",
        category="Gaming",
        filter_name="gaming",
        technologies=("gaming", "telemetry"),
    ),
)


def _entry_from_dict(item: dict) -> KnowledgeEntry:
    return KnowledgeEntry(
        name=str(item.get("name", "")).strip(),
        kind=str(item.get("kind", "service")).strip(),
        keywords=tuple(str(value).strip() for value in item.get("keywords", []) if str(value).strip()),
        vendor=str(item.get("vendor", "Unknown")).strip() or "Unknown",
        category=str(item.get("category", "Unknown")).strip() or "Unknown",
        filter_name=str(item.get("filter_name", "unknown")).strip() or "unknown",
        technologies=tuple(str(value).strip() for value in item.get("technologies", []) if str(value).strip()),
    )


def load_knowledge_entries(path: Path | None = None) -> list[KnowledgeEntry]:
    knowledge_path = path if path is not None else DEFAULT_KNOWLEDGE_PATH

    if not knowledge_path.exists():
        return list(_DEFAULT_ENTRIES)

    try:
        with knowledge_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return list(_DEFAULT_ENTRIES)

    if not isinstance(data, list):
        return list(_DEFAULT_ENTRIES)

    entries = [_entry_from_dict(item) for item in data if isinstance(item, dict)]
    entries = [entry for entry in entries if entry.name and entry.keywords]

    return entries or list(_DEFAULT_ENTRIES)


def normalize_text(value: str) -> str:
    return (value or "").strip().lower()


def match_knowledge(domain: str, entries: list[KnowledgeEntry] | None = None) -> list[KnowledgeEntry]:
    normalized = normalize_text(domain)
    if not normalized:
        return []

    source_entries = entries if entries is not None else load_knowledge_entries()
    matches: list[KnowledgeEntry] = []

    for entry in source_entries:
        if any(normalize_text(keyword) in normalized for keyword in entry.keywords):
            matches.append(entry)

    return matches


def explain_knowledge_match(domain: str, entries: list[KnowledgeEntry] | None = None) -> list[str]:
    reasons: list[str] = []

    for entry in match_knowledge(domain, entries):
        normalized = normalize_text(domain)
        for keyword in entry.keywords:
            if normalize_text(keyword) in normalized:
                reasons.append(
                    f"knowledge matched {entry.kind}: {entry.name} via keyword: {keyword}"
                )

    return reasons


def validate_knowledge_entries(entries: list[KnowledgeEntry]) -> tuple[bool, list[str]]:
    errors: list[str] = []

    for index, entry in enumerate(entries, start=1):
        prefix = f"entry #{index}"

        if not entry.name.strip():
            errors.append(f"{prefix}: name is required")

        if not entry.kind.strip():
            errors.append(f"{prefix}: kind is required")

        if not entry.keywords:
            errors.append(f"{prefix}: at least one keyword is required")

        if not entry.vendor.strip():
            errors.append(f"{prefix}: vendor is required")

        if not entry.category.strip():
            errors.append(f"{prefix}: category is required")

        if not entry.filter_name.strip():
            errors.append(f"{prefix}: filter_name is required")

    return len(errors) == 0, errors


def knowledge_integrity_report(path: Path | None = None) -> tuple[bool, list[str]]:
    entries = load_knowledge_entries(path)
    return validate_knowledge_entries(entries)
