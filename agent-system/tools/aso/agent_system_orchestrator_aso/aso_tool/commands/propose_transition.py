"""P3 lifecycle transition proposal command."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import proposal_contracts, runtime_schema_contracts
from . import output_policy, plan_next, state_verify
from .propose_next_task import (
    EXIT_BLOCKED,
    EXIT_IO_ERROR,
    EXIT_OK,
    _base_state_hashes,
    _content,
    _proposal_id_part,
    _timestamp,
    _utc_now,
)


ALLOWED_LIFECYCLE_VALUES = tuple(runtime_schema_contracts.LIFECYCLE_STATUSES)
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "bootstrap": ("requirements", "design", "implementation"),
    "requirements": ("design",),
    "design": ("design_audit", "implementation"),
    "design_audit": ("implementation", "correction"),
    "implementation": ("implementation_audit", "audit", "testing", "correction"),
    "implementation_audit": ("testing", "correction"),
    "audit": ("testing", "correction", "finalization"),
    "testing": ("setup", "correction", "documentation"),
    "setup": ("run", "correction"),
    "run": ("launch", "correction"),
    "launch": ("documentation", "handover", "correction"),
    "documentation": ("handover", "correction"),
    "handover": ("finalization", "final_acceptance"),
    "correction": ("design", "implementation", "testing", "setup", "run", "documentation"),
    "blocked": ("correction",),
    "finalization": ("final_acceptance", "completed"),
    "final_acceptance": ("completed",),
}
TERMINAL_PHASES = {"completed"}
BLOCKED_GATE_STATUSES = {"blocked", "failed"}
PASSING_GATE_STATUSES = {"passed", "skipped"}
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}
REQUIRED_VALIDATORS = (
    "proposal_schema",
    "state_verify_before_apply",
    "workspace_identity",
    "base_hash_staleness",
    "lifecycle_transition_allowed",
    "current_gate_compatible",
    "transition_evidence_present",
    "runtime_sidecar_operations_only",
)


def _is_none(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in NONE_VALUES)


def _truthy_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and not _is_none(item)]


def _verify_errors(verify_report: dict[str, object]) -> list[str]:
    findings = verify_report.get("findings")
    if not isinstance(findings, list):
        return []
    reasons: list[str] = []
    for finding in findings:
        if not isinstance(finding, dict) or finding.get("severity") != "error":
            continue
        rule_id = str(finding.get("rule_id", "")).strip()
        title = str(finding.get("title", "")).strip()
        details = str(finding.get("details", "")).strip()
        text = ": ".join(part for part in (rule_id, title or details) if part)
        if text:
            reasons.append(text)
    return sorted(set(reasons))


def _task_evidence(sidecars: dict[str, dict[str, object]], task_id: str) -> list[str]:
    if _is_none(task_id):
        return []
    refs: list[str] = []
    tasks = _content(sidecars, "TASK_REGISTRY").get("tasks")
    if isinstance(tasks, list):
        for task in tasks:
            if not isinstance(task, dict) or task.get("task_id") != task_id:
                continue
            status = str(task.get("status", "")).strip()
            if status in {"audit_passed", "checkpoint_done", "completed"}:
                refs.append(f"TASK_REGISTRY:{task_id}:{status}")
            for key in ("audit_refs", "result_refs", "checkpoint_ref"):
                value = task.get(key)
                if isinstance(value, list):
                    refs.extend(f"TASK_REGISTRY:{task_id}:{item}" for item in _truthy_string_list(value))
                elif isinstance(value, str) and not _is_none(value):
                    refs.append(f"TASK_REGISTRY:{task_id}:{value.strip()}")
            break
    artifacts = _content(sidecars, "ACCEPTED_ARTIFACTS").get("artifacts")
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            if artifact.get("source_task") != task_id and artifact.get("task_id") != task_id:
                continue
            status = str(artifact.get("status", "")).strip()
            if status in {"accepted", "passed", "completed"}:
                refs.append(f"ACCEPTED_ARTIFACTS:{task_id}:{status}")
            for key in ("audit_ref", "source_result_ref", "checkpoint_ref"):
                value = artifact.get(key)
                if isinstance(value, str) and not _is_none(value):
                    refs.append(f"ACCEPTED_ARTIFACTS:{task_id}:{value.strip()}")
    return sorted(set(refs))


def _transition_reasons(
    sidecars: dict[str, dict[str, object]],
    verify_report: dict[str, object],
    verify_exit_code: int,
    target_stage: str,
) -> tuple[list[str], dict[str, object]]:
    reasons = _verify_errors(verify_report) if verify_exit_code != 0 else []
    project_state = _content(sidecars, "PROJECT_STATE")
    current_gate = _content(sidecars, "CURRENT_GATE")
    current_phase = project_state.get("current_phase")
    project_status = str(project_state.get("project_status", "")).strip()
    gate_status = str(current_gate.get("status", "")).strip()
    gate_type = str(current_gate.get("gate_type", "")).strip()
    gate_task_id = str(current_gate.get("task_id", "")).strip()
    gate_evidence = _truthy_string_list(current_gate.get("gate_evidence"))
    task_evidence = _task_evidence(sidecars, gate_task_id)

    if not isinstance(current_phase, str) or not current_phase.strip():
        reasons.append("ambiguous_state: PROJECT_STATE.content.current_phase is missing or non-string")
        current = ""
    else:
        current = current_phase.strip()
    if current and current not in ALLOWED_LIFECYCLE_VALUES:
        reasons.append(f"ambiguous_state: current lifecycle stage is not allowed: {current}")
    if target_stage not in ALLOWED_LIFECYCLE_VALUES:
        reasons.append(f"unknown_lifecycle_target: {target_stage}")
    elif current == target_stage:
        reasons.append(f"unknown_transition: current lifecycle stage is already {target_stage}")
    elif current in TERMINAL_PHASES:
        reasons.append(f"unknown_transition: terminal lifecycle stage cannot transition: {current}")
    elif current and target_stage not in ALLOWED_TRANSITIONS.get(current, ()):
        reasons.append(f"unknown_transition: {current} -> {target_stage}")

    if project_status == "blocked":
        reasons.append("blocked_state: PROJECT_STATE.content.project_status is blocked")
    if gate_status in BLOCKED_GATE_STATUSES:
        reasons.append(f"blocked_gate: CURRENT_GATE.content.status is {gate_status}")
    blocking_status = current_gate.get("blocking_status")
    if isinstance(blocking_status, dict) or not _is_none(blocking_status):
        reasons.append("blocked_gate: CURRENT_GATE.content.blocking_status is active")
    if current and gate_type and gate_type != current and gate_status not in PASSING_GATE_STATUSES:
        reasons.append(f"ambiguous_state: CURRENT_GATE gate_type {gate_type} does not match current phase {current}")
    if target_stage == "completed" and gate_type != "final_acceptance":
        reasons.append("missing_evidence: completed transition requires final_acceptance gate")
    if gate_status not in PASSING_GATE_STATUSES and not gate_evidence and not task_evidence:
        reasons.append("missing_evidence: transition requires passed/skipped gate, gate_evidence, or task audit/checkpoint evidence")

    evidence = {
        "current_phase": current,
        "target_stage": target_stage,
        "project_status": project_status,
        "current_gate": {
            "gate_id": current_gate.get("gate_id", ""),
            "gate_type": gate_type,
            "status": gate_status,
            "task_id": gate_task_id,
            "gate_evidence": gate_evidence,
            "blocking_status": blocking_status,
        },
        "task_evidence": task_evidence,
    }
    return sorted(set(reasons)), evidence


def _operation(target_stage: str, status: str, reasons: list[str], evidence: dict[str, object]) -> dict[str, object]:
    current_phase = str(evidence.get("current_phase") or "UNKNOWN")
    if status == "blocked":
        reason_text = "; ".join(reasons) if reasons else "transition validation did not pass"
        description = f"Blocked lifecycle transition proposal for {current_phase} -> {target_stage}. Reason: {reason_text}"
    else:
        description = (
            f"Propose guarded lifecycle transition from {current_phase} to {target_stage}. "
            "Apply may update only runtime sidecars after base-hash and validator checks."
        )
    return {
        "operation_id": "op-001",
        "operation_type": "sidecar_patch",
        "target": "project-runtime/state/PROJECT_STATE.json",
        "description": description,
        "fields": [
            "PROJECT_STATE.content.current_phase",
            "PROJECT_STATE.content.semantic_reason",
            "CURRENT_GATE.content.gate_type",
            "CURRENT_GATE.content.status",
            "NEXT_ACTION.content.action_type",
            "NEXT_ACTION.content.action_semantic",
        ],
    }


def _build_proposal(root: Path, target_stage: str, now: datetime) -> tuple[dict[str, Any], dict[str, object], int]:
    verify_report, verify_exit_code = state_verify._report(root, True)
    sidecars = plan_next._load_sidecars(root)
    workspace_identity = _content(sidecars, "WORKSPACE_IDENTITY")
    reasons, evidence = _transition_reasons(sidecars, verify_report, verify_exit_code, target_stage)
    status = "blocked" if reasons else "proposed"
    created_at = _timestamp(now)
    current_phase = str(evidence.get("current_phase") or "UNKNOWN")
    proposal_id = (
        f"PROPOSAL-{now.strftime('%Y%m%dT%H%M%SZ')}-transition-"
        f"{_proposal_id_part(current_phase)}-to-{_proposal_id_part(target_stage)}"
    )
    operation = _operation(target_stage, status, reasons, evidence)
    summary = (
        operation["description"]
        if status == "blocked"
        else f"Lifecycle transition proposal for {current_phase} -> {target_stage}; no state is mutated by proposal creation."
    )
    proposal: dict[str, Any] = {
        "proposal_id": proposal_id,
        "proposal_type": "transition",
        "schema_version": proposal_contracts.CONTRACT_SCHEMA_VERSION,
        "package_version": proposal_contracts.PACKAGE_VERSION,
        "runtime_schema_version": proposal_contracts.RUNTIME_SCHEMA_VERSION,
        "created_at": created_at,
        "created_by": "aso propose transition",
        "target_root": str(root.resolve(strict=False)),
        "target_workspace_identity": workspace_identity,
        "base_state_hashes": _base_state_hashes(root),
        "required_validators": list(REQUIRED_VALIDATORS),
        "operations": [operation],
        "safety_class": "runtime_state_only",
        "status": status,
        "human_summary": summary,
    }
    contract_result = proposal_contracts.validate_proposal_artifact(proposal)
    report = {
        "tool": "aso",
        "command": "propose transition",
        "status": status,
        "root": str(root),
        "dry_run": True,
        "read_only": True,
        "mutations_performed": False,
        "proposal_id": proposal_id,
        "proposal_type": "transition",
        "blocked_reasons": reasons,
        "validators_run": [
            "state_verify",
            "lifecycle_transition_allowed",
            "current_gate_compatible",
            "transition_evidence_present",
            "proposal_schema",
        ],
        "contract_errors": list(contract_result.errors),
        "evidence": {
            "transition": evidence,
            "state_verify": {
                "status": verify_report.get("status"),
                "summary": verify_report.get("summary"),
                "findings": verify_report.get("findings", []),
            },
        },
    }
    if not contract_result.passed:
        report["status"] = "failed"
        proposal["status"] = "blocked"
        return proposal, report, EXIT_BLOCKED
    return proposal, report, EXIT_OK if status == "proposed" else EXIT_BLOCKED


def _print_text(report: dict[str, object], files_written: list[str]) -> None:
    print(f"ASO propose transition: {str(report['status']).upper()}")
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


def run_transition(args: argparse.Namespace) -> int:
    """Run the P3 lifecycle transition proposal command."""

    root = Path(args.root).expanduser()
    proposal, report, exit_code = _build_proposal(root, str(args.to), _utc_now())
    files_written: list[str] = []

    if args.confirm_write:
        path, error = _confirm_write_path(root, str(proposal["proposal_id"]))
        if error is not None or path is None:
            print(f"aso propose transition: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
        ok, write_error = _write_json(path, proposal)
        if not ok:
            print(f"aso propose transition: failed to write confirmed proposal: {write_error}", file=sys.stderr)
            return EXIT_IO_ERROR
        files_written.append(str(path))

    if args.json_out:
        path, error = _validate_json_out(root, str(args.json_out))
        if error is not None or path is None:
            print(f"aso propose transition: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
        ok, write_error = _write_json(path, proposal)
        if not ok:
            print(f"aso propose transition: failed to write json-out: {write_error}", file=sys.stderr)
            return EXIT_IO_ERROR
        files_written.append(str(path))

    if args.format == "json":
        print(json.dumps(proposal, indent=2, sort_keys=True))
    elif not args.json_out:
        _print_text(report, files_written)

    return exit_code
