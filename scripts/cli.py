"""Shared CLI helpers."""

from __future__ import annotations

import argparse


def parse_no_args(
    *,
    prog: str,
    description: str,
    argv: list[str] | None,
) -> None:
    """Parse a command that intentionally accepts no arguments."""

    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
    )
    parser.parse_args(argv)
