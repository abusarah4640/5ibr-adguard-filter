#!/usr/bin/env python3
"""Reusable reporting helpers."""

from __future__ import annotations

from collections import Counter
from scripts.database import load_database


def status_report() -> Counter:
    return Counter(row.get("Status", "Approved") or "Approved" for row in load_database())


def vendor_report() -> Counter:
    return Counter(row.get("Vendor", "") for row in load_database())


def category_report() -> Counter:
    return Counter(row.get("Category", "") for row in load_database())
