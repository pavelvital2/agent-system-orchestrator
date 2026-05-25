"""Dispatch receipt proposal and writer commands."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import dispatch_receipts
from . import output_policy


EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_IO_ERROR = 3


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _write_json(path: Path, payload: dict[str, Any]) -> tuple[bool, str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_json_bytes(payload), encoding="utf-8")
    except OSError as exc:
        return False, str(exc)
    return True, ""


def _validate_json_out(root: Path, path_text: str) -> tuple[Path | None, str | None]:
    path = output_policy.resolve_output_path(path_text)
    error = output_policy.validate_generated_output_path(
        root,
        path,
        allowed_workspace_subdirs=("project-runtime/reports",),
    )
    if error is not None:
        return None, f"{error.rule_id}: {error.message}: {error.evidence}"
    return path, None


def _report(
    *,
    root: Path,
    receipt: dict[str, Any],
    status: str,
    findings: list[dict[str, str]],
    mutations_performed: bool,
) -> dict[str, Any]:
    return {
        "tool": "aso",
        "command": "dispatch receipt",
        "root": str(root),
        "status": status,
        "receipt_ref": receipt.get("receipt_ref", "NONE"),
        "receipt_path": str(root / str(receipt.get("receipt_ref", "NONE")))
        if isinstance(receipt.get("receipt_ref"), str)
        else "NONE",
        "receipt": receipt,
        "schema_ref": dispatch_receipts.SCHEMA_RELATIVE_PATH,
        "runner_semantics": dispatch_receipts.RUNNER_SEMANTICS,
        "external_runner_command_template": dispatch_receipts.EXTERNAL_RUNNER_COMMAND_TEMPLATE,
        "findings": findings,
        "mutations_performed": mutations_performed,
        "live_dispatch_performed_by_aso": False,
    }


def _finding(rule_id: str, message: str, evidence: str, recommendation: str) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "severity": "error",
        "message": message,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def _print_text(report: dict[str, Any]) -> None:
    print(f"ASO dispatch receipt: {str(report['status']).upper()}")
    print(f"Receipt ref: {report['receipt_ref']}")
    print(f"Schema ref: {report['schema_ref']}")
    print(f"Live dispatch performed by ASO: {str(report['live_dispatch_performed_by_aso']).lower()}")
    findings = report.get("findings")
    if isinstance(findings, list) and findings:
        print("Findings:")
        for finding in findings:
            if isinstance(finding, dict):
                print(f"- {finding.get('rule_id')}: {finding.get('message')}")


def run_receipt(args: argparse.Namespace) -> int:
    """Build or write a dispatch receipt for an externally launched profile agent."""

    root = Path(args.root).expanduser().resolve(strict=False)
    started_at = args.started_at or _utc_now()
    receipt = dispatch_receipts.build_dispatch_receipt(
        agent_instance_id=str(args.agent_instance_id),
        task_id=str(args.task_id),
        role=str(args.role),
        runner=str(args.runner),
        model=str(args.model or "UNKNOWN"),
        reasoning_effort=str(args.reasoning_effort),
        prompt_ref=str(args.prompt_ref),
        handoff_ref=str(args.handoff_ref),
        started_at=started_at,
    )
    validation = dispatch_receipts.validate_dispatch_receipt(receipt)
    findings = [
        _finding(
            "DISPATCH_RECEIPT_CONTRACT_INVALID",
            "Dispatch receipt does not satisfy the machine-readable contract.",
            error,
            "Correct the receipt fields before profile-agent execution.",
        )
        for error in validation.errors
    ]

    status = "blocked" if findings else "proposed"
    mutations_performed = False
    exit_code = EXIT_BLOCKED if findings else EXIT_OK
    if args.confirm_write and not findings:
        path = dispatch_receipts.receipt_path(root, str(args.agent_instance_id))
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = None
            if existing != receipt:
                findings.append(
                    _finding(
                        "DISPATCH_RECEIPT_ALREADY_EXISTS",
                        "A different dispatch receipt already exists for this agent instance.",
                        dispatch_receipts.receipt_ref(str(args.agent_instance_id)),
                        "Use a fresh agent_instance_id for each bounded dispatch.",
                    )
                )
                status = "blocked"
                exit_code = EXIT_BLOCKED
            else:
                status = "already_exists"
        if not findings and status != "already_exists":
            ok, error = _write_json(path, receipt)
            if not ok:
                print(f"aso dispatch receipt: failed to write receipt: {error}", file=sys.stderr)
                return EXIT_IO_ERROR
            status = "written"
            mutations_performed = True

    report = _report(
        root=root,
        receipt=receipt,
        status=status,
        findings=findings,
        mutations_performed=mutations_performed,
    )
    if args.json_out:
        json_out, error = _validate_json_out(root, str(args.json_out))
        if error is not None or json_out is None:
            print(f"aso dispatch receipt: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
        ok, write_error = _write_json(json_out, report)
        if not ok:
            print(f"aso dispatch receipt: failed to write json-out: {write_error}", file=sys.stderr)
            return EXIT_IO_ERROR
    if args.format == "json":
        print(_json_bytes(report), end="")
    elif not args.json_out:
        _print_text(report)
    return exit_code
