#!/usr/bin/env python3
"""Read-only ASO command line scaffold."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from commands import archive_verify, lint, status


EXIT_USAGE = 2


def _existing_root(value: str) -> Path:
    root = Path(value).expanduser()
    if not root.exists() or not root.is_dir():
        raise argparse.ArgumentTypeError(f"project root is not a readable directory: {value}")
    return root


def _add_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        default=Path("."),
        type=_existing_root,
        help="Project root to inspect (default: current directory).",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aso",
        description="Read-only Agent System Orchestrator control-plane helper.",
    )
    parser.set_defaults(handler=None)

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    status_parser = subparsers.add_parser(
        "status",
        help="Summarize project runtime state.",
        description="Read project-runtime files and summarize the current ASO state.",
    )
    _add_root_argument(status_parser)
    status_parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Future read-only report output path; not implemented in this scaffold.",
    )
    status_parser.set_defaults(handler=status.run)

    lint_parser = subparsers.add_parser(
        "lint",
        help="Check runtime consistency rules.",
        description="Inspect runtime files for ASO consistency findings.",
    )
    _add_root_argument(lint_parser)
    lint_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat findings as a failing result when lint implementation is added.",
    )
    lint_parser.set_defaults(handler=lint.run)

    archive_parser = subparsers.add_parser(
        "archive",
        help="Archive inspection commands.",
        description="Read-only archive inspection commands.",
    )
    archive_subparsers = archive_parser.add_subparsers(dest="archive_command", metavar="COMMAND")
    verify_parser = archive_subparsers.add_parser(
        "verify",
        help="Verify packaged ASO archive structure.",
        description="Inspect an ASO archive for required project content.",
    )
    _add_root_argument(verify_parser)
    verify_parser.add_argument(
        "--archive",
        required=False,
        metavar="PATH",
        help="Archive to inspect (.zip, .tgz, .tar.gz, or .tar).",
    )
    verify_parser.set_defaults(handler=archive_verify.run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.handler is None:
        parser.print_help()
        return EXIT_USAGE
    return int(args.handler(args))


if __name__ == "__main__":
    sys.exit(main())
