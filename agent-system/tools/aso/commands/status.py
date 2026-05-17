"""Read-only status command scaffold."""

from __future__ import annotations

import argparse


EXIT_OK = 0


def run(args: argparse.Namespace) -> int:
    """Run the status command.

    Full runtime-state parsing is intentionally left to TASK_003.
    """
    print("ASO status command scaffold")
    print(f"Root: {args.root}")
    print("Runtime consistency: NOT_IMPLEMENTED")
    return EXIT_OK
