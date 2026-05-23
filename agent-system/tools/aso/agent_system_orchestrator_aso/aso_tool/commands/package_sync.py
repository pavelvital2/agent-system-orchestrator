"""Deprecated package-sync alias for package-layout verification."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import package_layout
from . import package_checks


SOURCE_TOOL_RELPATH = Path(package_checks.CANONICAL_TOOL_RELPATH) / "commands"
BUNDLED_TOOL_RELPATH = SOURCE_TOOL_RELPATH


def build_report(root: Path, strict: bool, command: str = "package-sync verify") -> tuple[dict[str, object], int]:
    """Build the delegated package-layout report for compatibility callers."""
    return package_layout.build_report(root, strict, command)


def run_verify(args: argparse.Namespace) -> int:
    """Run deprecated package-sync verify as a package-layout alias."""
    return package_layout.run_verify(args)
