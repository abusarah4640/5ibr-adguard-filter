"""Run all intelligence validation checks."""

from __future__ import annotations

from scripts.cli import parse_no_args
from scripts.rule_check import validate_rule_config
from scripts.services.analyzer_service import load_analyzer_config
from scripts.services.decision_engine import build_decision, decision_reasons
from scripts.services.explain_engine import make_explanation
from scripts.services.knowledge_service import (
    knowledge_integrity_report,
    load_knowledge_entries,
)


def validate_core_engines() -> tuple[bool, list[str]]:
    errors: list[str] = []

    try:
        explanation = make_explanation(
            source="self-check",
            message="core engine self-check",
            weight=10,
        )
        decision = build_decision(
            vendor="SelfCheck",
            category="System",
            filter_name="system",
            explanations=[explanation],
        )
        reasons = decision_reasons(decision)

        if decision.confidence != 10:
            errors.append("decision engine confidence check failed")

        if "core engine self-check" not in reasons:
            errors.append("explain engine reason check failed")

    except Exception as exc:
        errors.append(f"core engine error: {exc}")

    return len(errors) == 0, errors


def main(argv: list[str] | None = None) -> int:
    parse_no_args(
        prog="fivebr intelligence-check",
        description="Run all intelligence validation checks",
        argv=argv,
    )

    print("=== Intelligence Check ===")

    entries = load_knowledge_entries()
    kb_ok, kb_errors = knowledge_integrity_report()

    print(f"Knowledge entries : {len(entries)}")
    print(f"Knowledge status  : {'OK' if kb_ok else 'FAILED'}")

    config = load_analyzer_config()
    rule_ok, rule_errors = validate_rule_config(config)

    print(f"Vendor groups     : {len(config.get('vendor_patterns', {}))}")
    print(f"Category groups   : {len(config.get('category_keywords', {}))}")
    print(f"Filter mappings   : {len(config.get('filter_map', {}))}")
    print(f"Rule status       : {'OK' if rule_ok else 'FAILED'}")

    core_ok, core_errors = validate_core_engines()

    print(f"Decision Engine   : {'OK' if core_ok else 'FAILED'}")
    print(f"Explain Engine    : {'OK' if core_ok else 'FAILED'}")

    if kb_ok and rule_ok and core_ok:
        print("Overall status    : HEALTHY")
        return 0

    print("Overall status    : FAILED")

    for error in kb_errors:
        print(f"[Knowledge] {error}")

    for error in rule_errors:
        print(f"[Rules] {error}")

    for error in core_errors:
        print(f"[Core] {error}")

    return 1
