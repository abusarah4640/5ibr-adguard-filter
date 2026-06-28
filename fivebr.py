#!/usr/bin/env python3

"""
5ibr Development Toolkit
Command Line Interface
"""

import argparse
import subprocess
import sys


COMMANDS = {
    "build": "scripts/build.py",
    "validate": "scripts/validate.py",
    "fix": "scripts/fix.py",
    "analyze": "scripts/analyze_querylog.py",
    "report": "scripts/report.py",
    "html": "scripts/html_report.py",
}


def run(script):

    print()
    print("=" * 50)
    print(f"Running: {script}")
    print("=" * 50)
    print()

    result = subprocess.run(
        [sys.executable, script]
    )

    sys.exit(result.returncode)


def main():

    parser = argparse.ArgumentParser(
        prog="fivebr",
        description="5ibr Development Toolkit"
    )

    parser.add_argument(
        "command",
        choices=COMMANDS.keys()
    )

    args = parser.parse_args()

    run(COMMANDS[args.command])


if __name__ == "__main__":
    main()