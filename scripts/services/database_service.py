#!/usr/bin/env python3
"""Reusable database business logic for CLI, future API and future UI."""

from __future__ import annotations

from datetime import UTC, datetime

from scripts.database import add_domain, load_database, save_database, sort_database, update_domain
from scripts.services.integrity_service import validate_row, validate_rows

METADATA_FIELDS = ["Status", "Created", "Updated", "Reviewer", "Source", "Evidence", "Notes"]


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def enrich_row(row: dict, *, status: str = "Approved", reviewer: str = "") -> dict:
    """Return a row with standard metadata defaults."""

    now = utc_now()
    enriched = dict(row)
    enriched.setdefault("Status", status)
    enriched["Status"] = enriched.get("Status") or status
    enriched.setdefault("Created", now)
    enriched["Created"] = enriched.get("Created") or now
    enriched["Updated"] = now
    enriched.setdefault("Reviewer", reviewer)
    enriched.setdefault("Source", "")
    enriched.setdefault("Evidence", "")
    enriched.setdefault("Notes", "")
    return enriched


def add_validated_domain(*, domain: str, vendor: str, category: str, filter_name: str, confidence: int, status: str = "Approved", source: str = "", evidence: str = "", notes: str = "", reviewer: str = "") -> tuple[bool, list[str]]:
    """Validate and add a domain through one shared service path."""

    row = enrich_row(
        {
            "Domain": domain.strip().lower(),
            "Vendor": vendor.strip(),
            "Category": category.strip(),
            "Filter": filter_name.strip(),
            "Confidence": str(confidence),
            "Status": status,
            "Source": source.strip(),
            "Evidence": evidence.strip(),
            "Notes": notes.strip(),
        },
        status=status,
        reviewer=reviewer,
    )
    validation = validate_row(row)
    if not validation.ok:
        return False, validation.errors

    added = add_domain(domain=row["Domain"], vendor=row["Vendor"], category=row["Category"], filter_name=row["Filter"], confidence=int(row["Confidence"]))
    if not added:
        return False, ["Domain already exists."]

    rows = load_database()
    for existing in rows:
        if existing.get("Domain", "").lower() == row["Domain"].lower():
            existing.update(row)
            break
    save_database(sort_database(rows))
    return True, []


def update_validated_domain(*, domain: str, vendor: str, category: str, filter_name: str, confidence: int) -> tuple[bool, list[str]]:
    row = {"Domain": domain.strip().lower(), "Vendor": vendor.strip(), "Category": category.strip(), "Filter": filter_name.strip(), "Confidence": str(confidence), "Status": "Approved"}
    validation = validate_row(row)
    if not validation.ok:
        return False, validation.errors
    updated = update_domain(domain, vendor, category, filter_name, confidence)
    return (updated, [] if updated else ["Domain not found."])


def database_integrity_report() -> tuple[bool, list[str], list[str]]:
    """Validate the complete database."""

    result = validate_rows(load_database())
    return result.ok, result.errors, result.warnings
