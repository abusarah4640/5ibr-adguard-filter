#!/usr/bin/env python3

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

SIGNATURES_FILE = ROOT / "config" / "signatures.json"
VENDORS_FILE = ROOT / "config" / "vendors.json"


class DomainClassifier:

    def __init__(self):

        with open(SIGNATURES_FILE, encoding="utf-8") as f:
            self.signatures = json.load(f)

        with open(VENDORS_FILE, encoding="utf-8") as f:
            self.vendors = json.load(f)

    def classify(self, domain: str):

        domain = domain.lower()

        for vendor, data in self.signatures.items():

            for pattern in data["patterns"]:

                if pattern.lower() in domain:

                    vendor_info = self.vendors.get(vendor, {})

                    return {
                        "vendor": vendor,
                        "category": data["category"],
                        "confidence": data["confidence"],
                        "country": vendor_info.get("country"),
                        "website": vendor_info.get("website"),
                        "type": vendor_info.get("type"),
                        "products": vendor_info.get("products", []),
                        "matched_pattern": pattern
                    }

        return {
            "vendor": "Unknown",
            "category": "unknown",
            "confidence": 0,
            "country": None,
            "website": None,
            "type": None,
            "products": [],
            "matched_pattern": None
        }


if __name__ == "__main__":

    classifier = DomainClassifier()

    result = classifier.classify(
        "firebaseinstallations.googleapis.com"
    )

    print(result)