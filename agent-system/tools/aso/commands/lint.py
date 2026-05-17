"""Read-only lint command scaffold."""

from __future__ import annotations

import argparse


EXIT_OK = 0


def run(args: argparse.Namespace) -> int:
    """Run the lint command.

    Full lint rule evaluation is intentionally left to TASK_004.
    """
    print("ASO lint command scaffold")
    print(f"Root: {args.root}")
    print(f"Strict: {args.strict}")
    print("Findings: NOT_IMPLEMENTED")
    return EXIT_OK
