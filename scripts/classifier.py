#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIG = ROOT / "config" / "categories.json"


class DomainClassifier:

    def __init__(self):

        with open(CONFIG, encoding="utf-8") as f:
            self.categories = json.load(f)

    def classify(self, domain):

        domain = domain.lower()

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

        confidence = min(best_score * 30, 100)

        return {
            "category": best_category,
            "confidence": confidence
        }


if __name__ == "__main__":

    classifier = DomainClassifier()

    tests = [
        "mobile.events.data.microsoft.com",
        "sdkconfig.ad.xiaomi.com",
        "graph.facebook.com",
        "telemetry.riotgames.com",
        "eic.lgtvcommon.com"
    ]

    for domain in tests:
        print(domain, "=>", classifier.classify(domain))