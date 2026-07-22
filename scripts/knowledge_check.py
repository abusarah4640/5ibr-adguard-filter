"""Check Knowledge Base integrity."""

from __future__ import annotations

from scripts.cli import parse_no_args
from scripts.services.knowledge_service import (
    knowledge_integrity_report,
    load_knowledge_entries,
)


def main(argv: list[str] | None = None) -> int:
    parse_no_args(
        prog="fivebr knowledge-check",
        description="Check Knowledge Base integrity",
        argv=argv,
    )

    ok, errors = knowledge_integrity_report()
    entries = load_knowledge_entries()

    print(f"Knowledge entries: {len(entries)}")

    if ok:
        print("Knowledge Base: OK")
        return 0

    print("Knowledge Base: FAILED")
    for error in errors:
        print(f"- {error}")

    return 1
