"""Read-only design contract and traceability validator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..rules.design import validate_design_file


EXIT_IO_ERROR = 3


def _resolve_design_path(root: Path, design_path: str) -> Path:
    path = Path(design_path).expanduser()
    if path.is_absolute():
        return path
    root_candidate = root / path
    if root_candidate.exists():
        return root_candidate
    return path


def _report(path: Path, root: Path, strict: bool) -> tuple[dict[str, object], int]:
    result = validate_design_file(path, root=root, strict=strict)
    report = {
        "tool": "aso",
        "command": "validate-design",
        "status": result.status,
        "root": str(root),
        "path": str(path),
        "strict": strict,
        "summary": result.summary,
        "findings": [finding.to_json() for finding in result.findings],
        "design": result.document,
        "rubric": {
            "DESIGN_OUTPUT_CONTRACT_STATUS": "failed" if result.summary["errors"] else "passed",
            "DESIGN_TRACEABILITY_STATUS": "failed" if result.summary["errors"] else "passed",
            "DESIGN_REVIEW_RUBRIC_SCORE": result.score,
            "DESIGN_REVIEW_RUBRIC_STATUS": "passed" if result.score >= 90 and not result.summary["errors"] else "failed",
            "DESIGN_REVIEW_FAIL_CONDITIONS": sorted(
                {
                    finding.rule_id
                    for finding in result.findings
                    if finding.rule_id.startswith("DRF-")
                }
            )
            or ["NONE"],
        },
    }
    return report, result.exit_code


def _print_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    if not isinstance(summary, dict):
        raise TypeError("internal validate-design report summary must be a dictionary")

    print(f"ASO validate-design: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    print(f"Path: {report['path']}")
    print(f"Strict: {report['strict']}")
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Info: {summary['info']}")
    print(f"Findings: {len(report['findings'])}")
    for finding in report["findings"]:
        if not isinstance(finding, dict):
            continue
        print(f"- {finding['severity']} {finding['rule_id']}: {finding['title']}")


def _write_json(path_text: str, report: dict[str, object]) -> bool:
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso validate-design: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso validate-design: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def run(args: argparse.Namespace) -> int:
    """Run the validate-design command."""

    root = Path(args.root).expanduser()
    design_path = _resolve_design_path(root, args.design_path)
    report, exit_code = _report(design_path, root, args.strict)
    _print_text(report)
    if args.json_out and not _write_json(args.json_out, report):
        return EXIT_IO_ERROR
    return exit_code
