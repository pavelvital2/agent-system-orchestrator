"""Structured runtime state reconciliation command."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .. import state_materialization


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3


def _print_text(report: dict[str, object]) -> None:
    print(f"ASO state reconcile: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    print(f"Dry run: {str(report['dry_run']).lower()}")
    print(f"Diff entries: {report['diff_count']}")
    print(f"Mutations performed: {str(report['mutations_performed']).lower()}")
    receipt_ref = str(report.get("receipt_ref", ""))
    if receipt_ref:
        print(f"Receipt: {receipt_ref}")
    findings = report.get("findings")
    if isinstance(findings, list) and findings:
        print(f"Findings: {len(findings)}")
        for finding in findings:
            if isinstance(finding, dict):
                print(f"- {finding.get('severity', 'error')} {finding.get('rule_id')}: {finding.get('message')}")
    planned_files = report.get("planned_files")
    if isinstance(planned_files, list) and planned_files:
        print("Planned files:")
        for item in planned_files:
            print(f"- {item}")
    files_written = report.get("files_written")
    if isinstance(files_written, list) and files_written:
        print("Files written:")
        for item in files_written:
            print(f"- {item}")


def _write_json(path_text: str, report: dict[str, object]) -> bool:
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso state reconcile: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso state reconcile: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    report = state_materialization.reconcile_state(
        root,
        confirm_write=bool(getattr(args, "confirm_write", False)),
        command="state reconcile",
    )
    if getattr(args, "format", "text") == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_text(report)
    if getattr(args, "json_out", None) and not _write_json(str(args.json_out), report):
        return EXIT_IO_ERROR
    status = str(report.get("status", "failed"))
    if status in {"blocked", "failed", "written_with_verify_findings"}:
        return EXIT_FINDINGS if status != "failed" else EXIT_IO_ERROR
    return EXIT_OK
