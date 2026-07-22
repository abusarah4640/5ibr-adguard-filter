#!/usr/bin/env python3
"""5ibr Domain Analyzer command."""

from __future__ import annotations

import argparse

from scripts.services.analyzer_service import analyze_domain


def main(argv: list[str] | None = None) -> int:
    """Analyze one domain and print a local rule-based suggestion."""

    parser = argparse.ArgumentParser(
        prog="fivebr analyze",
        description="Analyze a domain using local rule-based intelligence",
    )
    parser.add_argument("domain", help="Domain to analyze")
    args = parser.parse_args(argv)

    result = analyze_domain(args.domain)

    print()
    print("===================================")
    print("5ibr Domain Analysis")
    print("===================================")
    print()
    print(f"Domain             : {result.domain}")
    print(f"Root               : {result.root_domain}")
    print()
    print(f"Suggested Vendor   : {result.suggested_vendor}")
    print(f"Suggested Category : {result.suggested_category}")
    print(f"Suggested Filter   : {result.suggested_filter}")
    print(f"Confidence         : {result.confidence}")
    print(f"Recommendation     : {result.recommendation}")

    print(
        "Blocking Policy     : "
        f"{result.blocking_policy}"
    )

    print(
        "Policy Reason       : "
        f"{result.blocking_policy_reason}"
    )

    print(
        "Policy Source       : "
        f"{result.blocking_policy_source}"
    )
    print()
    print("Reasons")
    for reason in result.reasons:
        print(f"- {reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
