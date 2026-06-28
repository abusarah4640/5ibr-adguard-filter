#!/usr/bin/env python3

"""
Generate configuration files from the centralized domain database.
"""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent.parent

CONFIG_DIR = ROOT / "config"


def build_config(rows):

    CONFIG_DIR.mkdir(exist_ok=True)

    vendors = {}
    signatures = {}

    for row in rows:

        vendor = row["Vendor"].strip()
        category = row["Category"].strip()
        domain = row["Domain"].strip()

        if vendor not in vendors:
            vendors[vendor] = []

        if category not in vendors[vendor]:
            vendors[vendor].append(category)

        signatures[domain] = {
            "vendor": vendor,
            "category": category,
            "filter": row["Filter"],
            "confidence": int(row["Confidence"])
        }

    with open(CONFIG_DIR / "vendors.json", "w", encoding="utf-8") as f:
        json.dump(
            vendors,
            f,
            indent=4,
            ensure_ascii=False,
            sort_keys=True
        )

    with open(CONFIG_DIR / "signatures.json", "w", encoding="utf-8") as f:
        json.dump(
            signatures,
            f,
            indent=4,
            ensure_ascii=False,
            sort_keys=True
        )

    print("Generated vendors.json")
    print("Generated signatures.json")