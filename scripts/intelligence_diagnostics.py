"""CLI output for structured intelligence diagnostics."""

from __future__ import annotations

from scripts.cli import parse_no_args
from scripts.services.intelligence_diagnostics_service import (
    build_intelligence_diagnostics,
)


def build_diagnostics_report() -> str:
    diagnostics = build_intelligence_diagnostics()

    lines = [
        "5ibr Intelligence Diagnostics",
        "==============================",
        "",
    ]

    for component in diagnostics.components:
        status = (
            "HEALTHY"
            if component.status == "Healthy"
            else "WARNING"
        )

        lines.append(f"{component.name} [{status}]")

        for check in component.checks:
            result = "PASS" if check.ok else "FAIL"
            lines.append(f"  [{result}] {check.name}")
            lines.append(f"         {check.detail}")
            lines.append("")

    overall = (
        "HEALTHY"
        if diagnostics.status == "Healthy"
        else "WARNING"
    )

    lines.append(f"Overall Status: {overall}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parse_no_args(
        prog="fivebr intelligence-diagnostics",
        description="Run detailed intelligence diagnostics",
        argv=argv,
    )

    diagnostics = build_intelligence_diagnostics()
    print(build_diagnostics_report())

    return 0 if diagnostics.status == "Healthy" else 1
