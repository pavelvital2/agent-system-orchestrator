"""Read-only archive verify command scaffold."""

from __future__ import annotations

import argparse


EXIT_OK = 0


def run(args: argparse.Namespace) -> int:
    """Run the archive verify command.

    Full archive inspection is intentionally left to TASK_005.
    """
    print("ASO archive verify command scaffold")
    print(f"Root: {args.root}")
    print(f"Archive: {args.archive or 'NOT_PROVIDED'}")
    print("Archive verification: NOT_IMPLEMENTED")
    return EXIT_OK
