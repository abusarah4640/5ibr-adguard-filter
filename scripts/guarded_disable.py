"""CLI for guarded production disable."""

from __future__ import annotations

import argparse

from scripts.services.guarded_disable_service import (
    run_guarded_disable,
)


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="guarded-disable",
    )

    parser.add_argument(
        "--restore",
        action="store_true",
        help=(
            "Restore the original enabled "
            "state after verifying disable."
        ),
    )

    args = parser.parse_args(argv)

    result = run_guarded_disable(
        restore=args.restore,
    )

    print(
        "Decision          :",
        result.decision,
    )
    print(
        "Enabled before    :",
        result.enabled_before,
    )
    print(
        "Enabled after     :",
        result.enabled_after,
    )
    print(
        "Restore requested :",
        result.restore_requested,
    )
    print(
        "Restore performed :",
        result.restore_performed,
    )
    print(
        "Checks failed     :",
        len(result.failures),
    )

    for failure in result.failures:
        print(" -", failure)

    return (
        0
        if result.decision
        == "PRODUCTION_DISABLE_SUCCEEDED"
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
