"""P3 next-task proposal command."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import proposal_contracts
from . import output_policy, plan_next, state_verify


EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_IO_ERROR = 3

RELEVANT_SIDECARS = (
    "PROJECT_STATE.json",
    "TASK_REGISTRY.json",
    "NEXT_ACTION.json",
    "CURRENT_GATE.json",
    "WORKSPACE_IDENTITY.json",
    "REPOSITORY_LOCK.json",
    "ACCEPTED_ARTIFACTS.json",
    "CHECKPOINT_STATE.json",
    "SCHEMA_MANIFEST.json",
)
REQUIRED_VALIDATORS = (
    "proposal_schema",
    "state_verify_before_apply",
    "workspace_identity",
    "base_hash_staleness",
    "next_action_allowed",
    "no_agent_dispatch",
)
PROPOSAL_ID_SAFE_RE = re.compile(r"[^A-Za-z0-9_.:-]+")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _proposal_id_part(value: str) -> str:
    clean = PROPOSAL_ID_SAFE_RE.sub("-", value.strip()).strip("-")
    return clean or "NONE"


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_for_path(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        data = raw
    else:
        data = _canonical_json_bytes(payload)
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _base_state_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for filename in RELEVANT_SIDECARS:
        relpath = f"project-runtime/state/{filename}"
        digest = _sha256_for_path(root / relpath)
        if digest is not None:
            hashes[relpath] = digest
    return hashes


def _content(sidecars: dict[str, dict[str, object]], sidecar_type: str) -> dict[str, object]:
    payload = sidecars.get(sidecar_type, {})
    content = payload.get("content")
    return content if isinstance(content, dict) else {}


def _blocked_reasons(plan_report: dict[str, object], verify_report: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    blocking_rules = plan_report.get("blocking_rules")
    if isinstance(blocking_rules, list):
        for rule in blocking_rules:
            if isinstance(rule, dict):
                rule_id = str(rule.get("rule_id", "")).strip()
                message = str(rule.get("message", "")).strip()
                if rule_id or message:
                    reasons.append(": ".join(part for part in (rule_id, message) if part))
    findings = verify_report.get("findings")
    if isinstance(findings, list):
        for finding in findings:
            if isinstance(finding, dict) and finding.get("severity") == "error":
                rule_id = str(finding.get("rule_id", "")).strip()
                title = str(finding.get("title", "")).strip()
                if rule_id or title:
                    reasons.append(": ".join(part for part in (rule_id, title) if part))
    return sorted(set(reasons))


def _operation_for_plan(plan_report: dict[str, object], status: str, reasons: list[str]) -> dict[str, object]:
    task_id = str(plan_report.get("task_id") or "NONE")
    task_packet = str(plan_report.get("task_packet") or "NONE")
    target_role = str(plan_report.get("target_role") or "NONE")
    recommendation = str(plan_report.get("recommended_next_action") or "NONE")
    if status == "blocked":
        reason_text = "; ".join(reasons) if reasons else "NEXT_ACTION is blocked or state verification did not pass."
        description = (
            f"Blocked next-task proposal for task_id={task_id}, target_role={target_role}, "
            f"task_packet={task_packet}. Reason: {reason_text}"
        )
    else:
        description = (
            f"Propose next task from NEXT_ACTION: recommendation={recommendation}, "
            f"task_id={task_id}, target_role={target_role}, task_packet={task_packet}. "
            "This proposal does not dispatch or reuse an agent."
        )
    return {
        "operation_id": "op-001",
        "operation_type": "report_write",
        "target": "project-runtime/reports/next-task-proposal.json",
        "description": description,
        "fields": [
            "NEXT_ACTION.content.action_type",
            "NEXT_ACTION.content.target_role",
            "NEXT_ACTION.content.task_id",
            "NEXT_ACTION.content.task_packet",
            "TASK_REGISTRY.content.tasks",
            "CURRENT_GATE.content.status",
        ],
    }


def _build_proposal(root: Path, strict: bool, now: datetime) -> tuple[dict[str, Any], dict[str, object], int]:
    verify_report, verify_exit_code = state_verify._report(root, strict)
    sidecars = plan_next._load_sidecars(root)
    rules, rules_evidence = plan_next._load_governance_rules(root)
    plan_report = plan_next._plan(root, strict, verify_report, verify_exit_code, sidecars, rules, rules_evidence)
    workspace_identity = _content(sidecars, "WORKSPACE_IDENTITY")
    reasons = _blocked_reasons(plan_report, verify_report)
    status = "blocked" if verify_exit_code != 0 or plan_report.get("status") != "ready" else "proposed"
    created_at = _timestamp(now)
    task_id = str(plan_report.get("task_id") or "NONE")
    proposal_id = f"PROPOSAL-{now.strftime('%Y%m%dT%H%M%SZ')}-next-task-{_proposal_id_part(task_id)}"
    summary = (
        _operation_for_plan(plan_report, status, reasons)["description"]
        if status == "blocked"
        else f"Next task proposal for task_id={task_id}; no agent dispatch is performed."
    )
    operation = _operation_for_plan(plan_report, status, reasons)
    proposal: dict[str, Any] = {
        "proposal_id": proposal_id,
        "proposal_type": "next_task",
        "schema_version": proposal_contracts.CONTRACT_SCHEMA_VERSION,
        "package_version": proposal_contracts.PACKAGE_VERSION,
        "runtime_schema_version": proposal_contracts.RUNTIME_SCHEMA_VERSION,
        "created_at": created_at,
        "created_by": "aso propose next-task",
        "target_root": str(root.resolve(strict=False)),
        "target_workspace_identity": workspace_identity,
        "base_state_hashes": _base_state_hashes(root),
        "required_validators": list(REQUIRED_VALIDATORS),
        "operations": [operation],
        "safety_class": "read_only_plan",
        "status": status,
        "human_summary": summary,
    }
    contract_result = proposal_contracts.validate_proposal_artifact(proposal)
    report = {
        "tool": "aso",
        "command": "propose next-task",
        "status": status,
        "root": str(root),
        "strict": strict,
        "dry_run": True,
        "read_only": True,
        "mutations_performed": False,
        "proposal_id": proposal_id,
        "proposal_type": "next_task",
        "blocked_reasons": reasons,
        "validators_run": ["state_verify", "plan_next", "proposal_schema"],
        "contract_errors": list(contract_result.errors),
        "evidence": {
            "state_verify": {
                "status": verify_report.get("status"),
                "summary": verify_report.get("summary"),
                "findings": verify_report.get("findings", []),
            },
            "plan_next": plan_report,
        },
    }
    if not contract_result.passed:
        report["status"] = "failed"
        proposal["status"] = "blocked"
        return proposal, report, EXIT_BLOCKED
    return proposal, report, EXIT_OK if status == "proposed" else EXIT_BLOCKED


def _print_text(report: dict[str, object], files_written: list[str]) -> None:
    print(f"ASO propose next-task: {str(report['status']).upper()}")
    print(f"proposal_id: {report['proposal_id']}")
    print(f"proposal_type: {report['proposal_type']}")
    print(f"validators_run: {', '.join(str(item) for item in report['validators_run'])}")
    print(f"files_written: {len(files_written)}")
    for path in files_written:
        print(f"- {path}")
    reasons = report.get("blocked_reasons")
    if isinstance(reasons, list) and reasons:
        print("blocked_reasons:")
        for reason in reasons:
            print(f"- {reason}")


def _validate_json_out(root: Path, path_text: str) -> tuple[Path | None, str | None]:
    path = output_policy.resolve_output_path(path_text)
    error = output_policy.validate_generated_output_path(
        root,
        path,
        allowed_workspace_subdirs=("project-runtime/proposals", "project-runtime/reports"),
    )
    if error is not None:
        return None, f"{error.rule_id}: {error.message}: {error.evidence}"
    if not path.parent.exists():
        return None, f"json-out parent does not exist: {path.parent}"
    return path, None


def _is_workspace_proposal_output(root: Path, path: Path) -> bool:
    workspace = root.expanduser().resolve(strict=False)
    target = path.resolve(strict=False)
    try:
        target.relative_to((workspace / "project-runtime" / "proposals").resolve(strict=False))
    except ValueError:
        return False
    return True


def _confirm_write_path(root: Path, proposal_id: str) -> tuple[Path | None, str | None]:
    proposals_dir = (root / "project-runtime" / "proposals").resolve(strict=False)
    path = proposals_dir / f"{proposal_id}.json"
    error = output_policy.validate_generated_output_path(
        root,
        path,
        allowed_workspace_subdirs=("project-runtime/proposals",),
    )
    if error is not None:
        return None, f"{error.rule_id}: {error.message}: {error.evidence}"
    try:
        proposals_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return None, f"failed to create proposals directory: {exc}"
    return path, None


def _write_json(path: Path, payload: dict[str, Any]) -> tuple[bool, str]:
    try:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        return False, str(exc)
    return True, ""


def run_next_task(args: argparse.Namespace) -> int:
    """Run the P3 next-task proposal command."""

    root = Path(args.root).expanduser()
    strict = True
    proposal, report, exit_code = _build_proposal(root, strict, _utc_now())
    files_written: list[str] = []

    if args.confirm_write:
        path, error = _confirm_write_path(root, str(proposal["proposal_id"]))
        if error is not None or path is None:
            print(f"aso propose next-task: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
        ok, write_error = _write_json(path, proposal)
        if not ok:
            print(f"aso propose next-task: failed to write confirmed proposal: {write_error}", file=sys.stderr)
            return EXIT_IO_ERROR
        files_written.append(str(path))

    if args.json_out:
        path, error = _validate_json_out(root, str(args.json_out))
        if error is not None or path is None:
            print(f"aso propose next-task: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
        if _is_workspace_proposal_output(root, path) and not args.confirm_write:
            print(
                "aso propose next-task: --confirm-write is required for project-runtime/proposals writes",
                file=sys.stderr,
            )
            return EXIT_BLOCKED
        ok, write_error = _write_json(path, proposal)
        if not ok:
            print(f"aso propose next-task: failed to write json-out: {write_error}", file=sys.stderr)
            return EXIT_IO_ERROR
        files_written.append(str(path))

    if args.format == "json":
        print(json.dumps(proposal, indent=2, sort_keys=True))
    elif not args.json_out:
        _print_text(report, files_written)

    return exit_code
