"""Read-only package layout verification for ASO."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import package_checks


EXIT_OK = 0
EXIT_FINDINGS = 1


def build_report(root: Path, strict: bool, command: str = "package-layout verify") -> tuple[dict[str, object], int]:
    inspection = package_checks.inspect_package(root)
    findings = inspection.findings
    status = package_checks.consistency(findings).lower()
    exit_code = EXIT_OK if status == "pass" else EXIT_FINDINGS

    return {
        "tool": "aso",
        "command": command,
        "status": "passed" if status == "pass" else status,
        "root": str(root),
        "strict": strict,
        "canonical_package": package_checks.CANONICAL_PACKAGE_RELPATH,
        "root_duplicate_package": package_checks.ROOT_PACKAGE_RELPATH,
        "summary": {
            "findings": len(findings),
            "errors": sum(1 for finding in findings if finding.severity == "error"),
            "warnings": sum(1 for finding in findings if finding.severity == "warning"),
        },
        "findings": [finding.to_json("package") for finding in findings],
    }, exit_code


def _print_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    if not isinstance(summary, dict):
        raise TypeError("internal package layout report summary must be a dictionary")

    print(f"ASO {report['command']}: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    print(f"Strict: {report['strict']}")
    print(f"Canonical package: {report['canonical_package']}")
    print(f"Root duplicate package: {report['root_duplicate_package']}")
    print(f"Findings: {summary['findings']}")
    for finding in report["findings"]:
        if not isinstance(finding, dict):
            continue
        print(f"- {finding['severity']} {finding['rule_id']}: {finding['title']}")


def run_verify(args: argparse.Namespace) -> int:
    """Run read-only package layout verification."""
    command = f"{getattr(args, 'command', 'package-layout')} verify"
    report, exit_code = build_report(args.root, args.strict, command)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_text(report)
    return exit_code
