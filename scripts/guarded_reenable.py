"""CLI for guarded production re-enable."""

from __future__ import annotations

from scripts.services.guarded_reenable_service import (
    run_guarded_reenable,
)


def main() -> int:
    result = run_guarded_reenable()

    print(
        "Decision           :",
        result.decision,
    )
    print(
        "Enabled before     :",
        result.enabled_before,
    )
    print(
        "Enabled after      :",
        result.enabled_after,
    )
    print(
        "Rollback performed :",
        result.rollback_performed,
    )
    print(
        "Checks failed      :",
        len(result.failures),
    )

    for failure in result.failures:
        print(" -", failure)

    return (
        0
        if result.decision
        == "PRODUCTION_REENABLE_SUCCEEDED"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
