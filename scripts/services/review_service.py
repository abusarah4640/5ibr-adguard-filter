#!/usr/bin/env python3
"""Pending -> Approved review workflow service."""

from __future__ import annotations

from scripts.database import load_database, save_database, sort_database
from scripts.services.database_service import enrich_row
from scripts.services.integrity_service import validate_row


def submit_domain(*, domain: str, vendor: str, category: str, filter_name: str, confidence: int, source: str = "", evidence: str = "", notes: str = "") -> tuple[bool, list[str]]:
    """Submit a domain as Pending."""

    rows = load_database()
    if any(row.get("Domain", "").lower() == domain.strip().lower() for row in rows):
        return False, ["Domain already exists."]

    row = enrich_row(
        {
            "Domain": domain.strip().lower(),
            "Vendor": vendor.strip(),
            "Category": category.strip(),
            "Filter": filter_name.strip(),
            "Confidence": str(confidence),
            "Status": "Pending",
            "Source": source.strip(),
            "Evidence": evidence.strip(),
            "Notes": notes.strip(),
        },
        status="Pending",
    )
    validation = validate_row(row)
    if not validation.ok:
        return False, validation.errors

    rows.append(row)
    save_database(sort_database(rows))
    return True, []


def pending_domains() -> list[dict]:
    return [row for row in load_database() if row.get("Status", "Approved") == "Pending"]


def set_review_status(domain: str, status: str, *, reviewer: str = "", notes: str = "") -> tuple[bool, list[str]]:
    if status not in {"Approved", "Rejected"}:
        return False, ["Status must be Approved or Rejected."]

    rows = load_database()
    domain_key = domain.strip().lower()
    for row in rows:
        if row.get("Domain", "").lower() == domain_key:
            row["Status"] = status
            if reviewer:
                row["Reviewer"] = reviewer
            if notes:
                row["Notes"] = notes
            row.update(enrich_row(row, status=status, reviewer=reviewer))
            save_database(sort_database(rows))
            return True, []
    return False, ["Domain not found."]
