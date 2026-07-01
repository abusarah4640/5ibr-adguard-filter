#!/usr/bin/env python3
"""Central integrity validation for 5ibr database rows."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "config"
FILTERS = ROOT / "filters"

VALID_STATUSES = {"Pending", "Approved", "Rejected"}
DOMAIN_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$", re.I)


@dataclass
class ValidationResult:
    """Collect row validation errors and warnings."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def extend(self, other: "ValidationResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def known_categories() -> set[str]:
    """Return configured category names in CSV display format."""

    raw = _load_json(CONFIG / "categories.json")
    return {name.strip().lower() for name in raw} | {name.strip().replace("-", " ").lower() for name in raw}


def known_vendors() -> set[str]:
    """Return configured vendor names."""

    raw = _load_json(CONFIG / "vendors.json")
    return {name.strip().lower() for name in raw} | {name.strip().replace("-", " ").lower() for name in raw}


def known_filters() -> set[str]:
    """Return existing filter file names without extension."""

    return {path.stem.lower() for path in FILTERS.glob("*.txt")}


def validate_domain(domain: str) -> bool:
    """Validate a plain domain name."""

    domain = (domain or "").strip().lower()
    if not domain or "/" in domain or " " in domain or domain.startswith("."):
        return False
    return bool(DOMAIN_RE.match(domain))


def validate_row(row: dict, *, strict_vendor: bool = False) -> ValidationResult:
    """Validate one database row against central integrity rules."""

    result = ValidationResult()

    domain = row.get("Domain", "").strip()
    vendor = row.get("Vendor", "").strip()
    category = row.get("Category", "").strip()
    filter_name = row.get("Filter", "").strip()
    confidence_raw = row.get("Confidence", "").strip()
    status = row.get("Status", "Approved").strip() or "Approved"

    if not validate_domain(domain):
        result.errors.append(f"Invalid domain: {domain or '<empty>'}")

    if not vendor:
        result.errors.append(f"Missing vendor for {domain or '<empty>'}")
    elif strict_vendor and vendor.lower() not in known_vendors():
        result.warnings.append(f"Unknown vendor: {vendor}")

    categories = known_categories()
    if not category:
        result.errors.append(f"Missing category for {domain or '<empty>'}")
    elif categories and category.lower() not in categories:
        result.errors.append(f"Unknown category: {category}")

    filters = known_filters()
    if not filter_name:
        result.errors.append(f"Missing filter for {domain or '<empty>'}")
    elif filters and filter_name.lower() not in filters:
        result.errors.append(f"Unknown filter: {filter_name}")

    try:
        confidence = int(confidence_raw)
    except ValueError:
        result.errors.append(f"Invalid confidence for {domain or '<empty>'}: {confidence_raw}")
    else:
        if confidence < 0 or confidence > 100:
            result.errors.append(f"Confidence out of range for {domain or '<empty>'}: {confidence}")

    if status not in VALID_STATUSES:
        result.errors.append(f"Invalid status for {domain or '<empty>'}: {status}")

    return result


def validate_rows(rows: list[dict]) -> ValidationResult:
    """Validate all rows and detect database-level integrity issues."""

    result = ValidationResult()
    seen: dict[str, int] = {}

    for index, row in enumerate(rows, start=2):
        row_result = validate_row(row)
        for error in row_result.errors:
            result.errors.append(f"row {index}: {error}")
        for warning in row_result.warnings:
            result.warnings.append(f"row {index}: {warning}")

        domain = row.get("Domain", "").strip().lower()
        if domain:
            seen[domain] = seen.get(domain, 0) + 1

    for domain, count in sorted(seen.items()):
        if count > 1:
            result.errors.append(f"Duplicate domain: {domain} ({count} rows)")

    return result
