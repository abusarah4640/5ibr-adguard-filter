#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CATEGORY_DB = ROOT / "config" / "categories.json"
SIGNATURE_DB = ROOT / "config" / "signatures.json"


class DomainClassifier:

    def __init__(self):

        with open(CATEGORY_DB, encoding="utf-8") as f:
            self.categories = json.load(f)

        with open(SIGNATURE_DB, encoding="utf-8") as f:
            self.signatures = json.load(f)

    def classify(self, domain):

        domain = domain.lower()

        if domain in self.signatures:

            item = self.signatures[domain]

            return {
                "category": item["category"],
                "confidence": item["confidence"],
                "vendor": item["vendor"],
                "reason": item["reason"],
                "source": "signature"
            }

        best_category = "unknown"
        best_score = 0

        for category, keywords in self.categories.items():

            score = 0

            for keyword in keywords:

                if keyword.lower() in domain:
                    score += 1

            if score > best_score:
                best_score = score
                best_category = category

        confidence = min(best_score * 30, 90)

        return {
            "category": best_category,
            "confidence": confidence,
            "vendor": "Unknown",
            "reason": "Keyword classification",
            "source": "keywords"
        }


if __name__ == "__main__":

    classifier = DomainClassifier()

    tests = [
        "mobile.events.data.microsoft.com",
        "sdkconfig.ad.xiaomi.com",
        "graph.facebook.com",
        "telemetry.riotgames.com",
        "unknown.example.com"
    ]

    for domain in tests:
        print(domain)
        print(classifier.classify(domain))
        print()