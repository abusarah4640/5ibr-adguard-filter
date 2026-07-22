"""Check analyzer rule configuration."""

from __future__ import annotations

from scripts.cli import parse_no_args
from scripts.services.analyzer_service import load_analyzer_config


REQUIRED_SECTIONS = (
    "vendor_patterns",
    "category_keywords",
    "filter_map",
)


def validate_rule_config(config: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []

    for section in REQUIRED_SECTIONS:
        if section not in config:
            errors.append(f"missing required section: {section}")
        elif not isinstance(config[section], dict):
            errors.append(f"section must be an object: {section}")

    return len(errors) == 0, errors


def main(argv: list[str] | None = None) -> int:
    parse_no_args(
        prog="fivebr rule-check",
        description="Check analyzer rule configuration",
        argv=argv,
    )

    config = load_analyzer_config()
    ok, errors = validate_rule_config(config)

    print("Rule config: config/analyzer.json")
    print(f"Vendor groups: {len(config.get('vendor_patterns', {}))}")
    print(f"Category groups: {len(config.get('category_keywords', {}))}")
    print(f"Filter mappings: {len(config.get('filter_map', {}))}")

    if ok:
        print("Rule Config: OK")
        return 0

    print("Rule Config: FAILED")
    for error in errors:
        print(f"- {error}")

    return 1
