"""Deprecated package-sync alias for canonical package-layout verification."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_system_orchestrator_aso.aso_tool.commands import package_checks, package_layout


SOURCE_TOOL_RELPATH = Path("agent-system/tools/aso/commands")
BUNDLED_TOOL_RELPATH = Path(package_checks.CANONICAL_TOOL_RELPATH) / "commands"


def build_report(root: Path, strict: bool, command: str = "package-sync verify") -> tuple[dict[str, object], int]:
    """Return the package-layout report for legacy direct-module callers."""
    return package_layout.build_report(root, strict, command)


def run_verify(args: argparse.Namespace) -> int:
    """Run deprecated package-sync verify as a package-layout alias."""
    return package_layout.run_verify(args)
