#!/usr/bin/env python3
"""Review workflow command: submit, pending, approve and reject."""

from __future__ import annotations

import argparse

from scripts.services.review_service import pending_domains, set_review_status, submit_domain


def _add_domain_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--domain", required=True)
    parser.add_argument("--vendor", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--filter", required=True)
    parser.add_argument("--confidence", required=True, type=int)
    parser.add_argument("--source", default="")
    parser.add_argument("--evidence", default="")
    parser.add_argument("--notes", default="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fivebr review", description="Manage Pending -> Approved review workflow")
    subparsers = parser.add_subparsers(dest="action", required=True)

    submit_parser = subparsers.add_parser("submit", help="Submit a pending domain")
    _add_domain_args(submit_parser)

    subparsers.add_parser("pending", help="List pending domains")

    approve_parser = subparsers.add_parser("approve", help="Approve a pending domain")
    approve_parser.add_argument("domain")
    approve_parser.add_argument("--reviewer", default="")
    approve_parser.add_argument("--notes", default="")

    reject_parser = subparsers.add_parser("reject", help="Reject a pending domain")
    reject_parser.add_argument("domain")
    reject_parser.add_argument("--reviewer", default="")
    reject_parser.add_argument("--notes", default="")

    args = parser.parse_args(argv)

    if args.action == "submit":
        ok, errors = submit_domain(
            domain=args.domain,
            vendor=args.vendor,
            category=args.category,
            filter_name=args.filter,
            confidence=args.confidence,
            source=args.source,
            evidence=args.evidence,
            notes=args.notes,
        )
        if not ok:
            print("ERROR: Unable to submit domain.")
            for error in errors:
                print(f"- {error}")
            return 1
        print("Domain submitted for review.")
        return 0

    if args.action == "pending":
        rows = pending_domains()
        print("Domain                         Vendor              Category        Filter       Confidence")
        print("-" * 92)
        for row in rows:
            print(f"{row.get('Domain',''):<30} {row.get('Vendor',''):<19} {row.get('Category',''):<15} {row.get('Filter',''):<12} {row.get('Confidence','')}")
        print(f"\nPending: {len(rows)}")
        return 0

    if args.action == "approve":
        ok, errors = set_review_status(args.domain, "Approved", reviewer=args.reviewer, notes=args.notes)
        label = "approved"
    else:
        ok, errors = set_review_status(args.domain, "Rejected", reviewer=args.reviewer, notes=args.notes)
        label = "rejected"

    if not ok:
        print("ERROR: Review update failed.")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Domain {label}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
