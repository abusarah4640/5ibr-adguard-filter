"""Generate 5ibr Intelligence Report."""

from __future__ import annotations

from scripts.version import get_version

from scripts.cli import parse_no_args
from scripts.database import load_database
from scripts.intelligence_check import validate_core_engines
from scripts.rule_check import validate_rule_config
from scripts.services.analyzer_service import load_analyzer_config
from scripts.services.knowledge_service import (
    knowledge_integrity_report,
    load_knowledge_entries,
)


def read_version() -> str:
    """Return the installed package version."""

    return get_version()


def build_report() -> str:
    entries = load_knowledge_entries()
    kb_ok, _ = knowledge_integrity_report()

    config = load_analyzer_config()
    rule_ok, _ = validate_rule_config(config)

    core_ok, _ = validate_core_engines()

    rows = load_database()
    approved = sum(1 for row in rows if (row.get("Status") or "Approved") == "Approved")
    pending = sum(1 for row in rows if (row.get("Status") or "Approved") != "Approved")

    overall = "HEALTHY" if kb_ok and rule_ok and core_ok else "FAILED"

    return f"""5ibr Intelligence Report
========================

Knowledge Base
--------------
Entries            : {len(entries)}
Status             : {'OK' if kb_ok else 'FAILED'}

Rule Engine
-----------
Vendor Groups      : {len(config.get('vendor_patterns', {}))}
Category Groups    : {len(config.get('category_keywords', {}))}
Filter Mappings    : {len(config.get('filter_map', {}))}
Status             : {'OK' if rule_ok else 'FAILED'}

Core Engines
------------
Decision Engine    : {'OK' if core_ok else 'FAILED'}
Explain Engine     : {'OK' if core_ok else 'FAILED'}

Database
--------
Known Domains      : {len(rows)}
Approved           : {approved}
Pending            : {pending}

Overall
-------
Status             : {overall}
Version            : {read_version()}
"""


def main(argv: list[str] | None = None) -> int:
    parse_no_args(
        prog="fivebr intelligence-report",
        description="Generate intelligence report",
        argv=argv,
    )

    print(build_report())
    return 0
