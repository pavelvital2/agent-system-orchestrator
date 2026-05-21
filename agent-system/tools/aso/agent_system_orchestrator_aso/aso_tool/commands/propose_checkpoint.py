"""P3 checkpoint proposal command."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import proposal_contracts
from . import checkpoint_preflight, output_policy, plan_next, state_verify
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


REQUIRED_VALIDATORS = (
    "proposal_schema",
    "state_verify_before_checkpoint_proposal",
    "workspace_identity",
    "base_hash_staleness",
    "checkpoint_preflight_read_only",
    "checkpoint_state_inspected",
    "accepted_artifacts_audit_evidence",
    "no_checkpoint_execution",
)


def _load_sidecar(root: Path, filename: str) -> dict[str, object]:
    path = root / "project-runtime" / "state" / filename
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_none(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in plan_next.NONE_VALUES)


def _as_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _truthy_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and not _is_none(item)]


def _tasks_by_id(sidecars: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    tasks = _content(sidecars, "TASK_REGISTRY").get("tasks")
    result: dict[str, dict[str, object]] = {}
    if isinstance(tasks, list):
        for task in tasks:
            if isinstance(task, dict) and isinstance(task.get("task_id"), str):
                result[task["task_id"]] = task
    return result


def _accepted_artifacts_for_task(sidecars: dict[str, dict[str, object]], task_id: str) -> list[dict[str, object]]:
    artifacts = _content(sidecars, "ACCEPTED_ARTIFACTS").get("artifacts")
    result: list[dict[str, object]] = []
    if not isinstance(artifacts, list):
        return result
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        if artifact.get("source_task") == task_id or artifact.get("task_id") == task_id:
            result.append(dict(artifact))
    return result


def _audit_evidence(sidecars: dict[str, dict[str, object]], task_id: str) -> dict[str, object]:
    task = _tasks_by_id(sidecars).get(task_id, {})
    artifacts = _accepted_artifacts_for_task(sidecars, task_id)
    accepted_artifact_audit_refs = [
        str(artifact["audit_ref"]).strip()
        for artifact in artifacts
        if isinstance(artifact.get("audit_ref"), str) and not _is_none(artifact.get("audit_ref"))
    ]
    current_gate_refs = [
        item
        for item in _truthy_string_list(_content(sidecars, "CURRENT_GATE").get("gate_evidence"))
        if "audit" in item.lower()
    ]
    task_audit_refs = _truthy_string_list(task.get("audit_refs"))
    task_status = _as_text(task.get("status"))
    return {
        "present": bool(task_audit_refs or accepted_artifact_audit_refs or current_gate_refs),
        "task_id": task_id,
        "task_status": task_status,
        "task_status_audit_passed": task_status in {"audit_passed", "checkpoint_done", "completed"},
        "task_audit_refs": task_audit_refs,
        "accepted_artifact_count": len(artifacts),
        "accepted_artifact_refs": [
            str(artifact.get("artifact_ref", "")).strip()
            for artifact in artifacts
            if isinstance(artifact.get("artifact_ref"), str) and not _is_none(artifact.get("artifact_ref"))
        ],
        "accepted_artifact_audit_refs": accepted_artifact_audit_refs,
        "current_gate_audit_evidence_refs": current_gate_refs,
    }


def _checkpoint_required(
    project_state: dict[str, object],
    next_action: dict[str, object],
    checkpoint_state: dict[str, object],
) -> bool:
    checkpoint_status = _as_text(checkpoint_state.get("checkpoint_status"))
    return (
        plan_next._is_checkpoint_attempt(next_action)
        or next_action.get("checkpoint_receipt_required") is True
        or bool(next_action.get("checkpoint_preflight_required"))
        or _as_text(project_state.get("project_checkpoint_status")) == "pending"
        or checkpoint_status in {"pending", "eligible"}
    )


def _reason_text(blocking_rules: object) -> list[str]:
    reasons: list[str] = []
    if isinstance(blocking_rules, list):
        for rule in blocking_rules:
            if not isinstance(rule, dict):
                continue
            rule_id = str(rule.get("rule_id", "")).strip()
            message = str(rule.get("message", "")).strip()
            evidence = str(rule.get("evidence", "")).strip()
            reason = ": ".join(part for part in (rule_id, message, evidence) if part)
            if reason:
                reasons.append(reason)
    return sorted(set(reasons))


def _active_blockers(project_state: dict[str, object], next_action: dict[str, object]) -> list[str]:
    blockers: list[str] = []
    for key in ("active_blockers", "checkpoint_blocked_by"):
        value = project_state.get(key)
        if isinstance(value, list):
            blockers.extend(str(item).strip() for item in value if not _is_none(item))
    value = next_action.get("blocked_by")
    if isinstance(value, list):
        blockers.extend(str(item).strip() for item in value if not _is_none(item))
    return sorted(set(item for item in blockers if item))


def _checkpoint_decision(
    required: bool,
    preflight_report: dict[str, object],
    verify_exit_code: int,
    project_state: dict[str, object],
    next_action: dict[str, object],
) -> tuple[str, list[str]]:
    preflight_reasons = _reason_text(preflight_report.get("blocking_rules"))
    blockers = _active_blockers(project_state, next_action)
    if verify_exit_code == checkpoint_preflight.EXIT_IO_ERROR or preflight_report.get("status") == "io_error":
        return "blocked", preflight_reasons or ["Workspace state sidecars are unavailable or unreadable."]
    if _as_text(project_state.get("project_status")) == "blocked" or blockers:
        reasons = list(preflight_reasons)
        if blockers:
            reasons.append("active_blockers: " + ", ".join(blockers))
        if _as_text(project_state.get("project_status")) == "blocked":
            reasons.append("project_status: blocked")
        return "blocked", sorted(set(reasons))
    if not required:
        return "not_required", []
    if preflight_report.get("eligible") is True:
        return "eligible", []
    return "ineligible", preflight_reasons or ["Checkpoint preflight did not mark the workspace eligible."]


def _operation(decision: str, reasons: list[str]) -> dict[str, object]:
    if decision == "eligible":
        description = (
            "Checkpoint is eligible according to read-only diagnostics. "
            "This proposal does not stage, commit, push, tag, or write a checkpoint receipt."
        )
    elif decision == "not_required":
        description = (
            "Checkpoint is not required by current runtime state. "
            "This proposal records that no checkpoint execution is proposed."
        )
    else:
        reason_text = "; ".join(reasons) if reasons else "checkpoint diagnostics did not pass"
        description = f"Checkpoint proposal is {decision}. Reason: {reason_text}"
    return {
        "operation_id": "op-001",
        "operation_type": "report_write",
        "target": "project-runtime/reports/checkpoint-proposal.json",
        "description": description,
        "fields": [
            "PROJECT_STATE.content.checkpoint_eligibility",
            "PROJECT_STATE.content.checkpoint_eligibility_status",
            "PROJECT_STATE.content.project_checkpoint_status",
            "NEXT_ACTION.content.checkpoint_policy",
            "NEXT_ACTION.content.checkpoint_preflight_required",
            "NEXT_ACTION.content.checkpoint_receipt_required",
            "CHECKPOINT_STATE.content.checkpoint_status",
            "ACCEPTED_ARTIFACTS.content.artifacts",
            "TASK_REGISTRY.content.tasks[].audit_refs",
        ],
    }


def _build_proposal(root: Path, now: datetime) -> tuple[dict[str, Any], dict[str, object], int]:
    verify_report, verify_exit_code = state_verify._report(root, True)
    sidecars = plan_next._load_sidecars(root)
    checkpoint_payload = _load_sidecar(root, "CHECKPOINT_STATE.json")
    if checkpoint_payload:
        sidecars["CHECKPOINT_STATE"] = checkpoint_payload
    workspace_identity = _content(sidecars, "WORKSPACE_IDENTITY")
    project_state = _content(sidecars, "PROJECT_STATE")
    next_action = _content(sidecars, "NEXT_ACTION")
    checkpoint_state = _content(sidecars, "CHECKPOINT_STATE")
    task_id = _as_text(next_action.get("task_id"))
    required = _checkpoint_required(project_state, next_action, checkpoint_state)
    preflight_report, preflight_exit_code = checkpoint_preflight._workspace_report(root, True)
    decision, reasons = _checkpoint_decision(required, preflight_report, verify_exit_code, project_state, next_action)
    proposal_status = "proposed" if decision in {"eligible", "not_required"} else "blocked"
    created_at = _timestamp(now)
    proposal_id = (
        f"PROPOSAL-{now.strftime('%Y%m%dT%H%M%SZ')}-checkpoint-"
        f"{_proposal_id_part(decision)}-{_proposal_id_part(task_id or 'NONE')}"
    )
    operation = _operation(decision, reasons)
    proposal: dict[str, Any] = {
        "proposal_id": proposal_id,
        "proposal_type": "checkpoint",
        "schema_version": proposal_contracts.CONTRACT_SCHEMA_VERSION,
        "package_version": proposal_contracts.PACKAGE_VERSION,
        "runtime_schema_version": proposal_contracts.RUNTIME_SCHEMA_VERSION,
        "created_at": created_at,
        "created_by": "aso propose checkpoint",
        "target_root": str(root.resolve(strict=False)),
        "target_workspace_identity": workspace_identity,
        "base_state_hashes": _base_state_hashes(root),
        "required_validators": list(REQUIRED_VALIDATORS),
        "operations": [operation],
        "safety_class": "checkpoint_proposal_only",
        "status": proposal_status,
        "human_summary": operation["description"],
        "checkpoint_decision": decision,
        "checkpoint_execution_performed": False,
        "checkpoint_receipt_created": False,
    }
    contract_result = proposal_contracts.validate_proposal_artifact(proposal)
    report = {
        "tool": "aso",
        "command": "propose checkpoint",
        "status": proposal_status,
        "checkpoint_decision": decision,
        "root": str(root),
        "dry_run": True,
        "read_only": True,
        "mutations_performed": False,
        "checkpoint_execution_performed": False,
        "checkpoint_receipt_created": False,
        "proposal_id": proposal_id,
        "proposal_type": "checkpoint",
        "blocked_reasons": reasons,
        "validators_run": [
            "state_verify",
            "checkpoint_preflight_read_only",
            "checkpoint_state_inspected",
            "accepted_artifacts_audit_evidence",
            "proposal_schema",
        ],
        "contract_errors": list(contract_result.errors),
        "evidence": {
            "checkpoint_required": required,
            "checkpoint_state": {
                "present": bool(checkpoint_payload),
                "content": checkpoint_state,
            },
            "audit_evidence": _audit_evidence(sidecars, task_id),
            "state_verify": {
                "status": verify_report.get("status"),
                "summary": verify_report.get("summary"),
                "findings": verify_report.get("findings", []),
            },
            "checkpoint_preflight": preflight_report,
        },
    }
    if not contract_result.passed:
        report["status"] = "failed"
        proposal["status"] = "blocked"
        return proposal, report, EXIT_BLOCKED
    if proposal_status == "proposed":
        return proposal, report, EXIT_OK
    if preflight_exit_code == checkpoint_preflight.EXIT_IO_ERROR:
        return proposal, report, EXIT_IO_ERROR
    return proposal, report, EXIT_BLOCKED


def _print_text(report: dict[str, object], files_written: list[str]) -> None:
    print(f"ASO propose checkpoint: {str(report['checkpoint_decision']).upper()}")
    print(f"status: {report['status']}")
    print(f"proposal_id: {report['proposal_id']}")
    print(f"proposal_type: {report['proposal_type']}")
    print(f"validators_run: {', '.join(str(item) for item in report['validators_run'])}")
    print("checkpoint_execution_performed: false")
    print("checkpoint_receipt_created: false")
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


def run_checkpoint(args: argparse.Namespace) -> int:
    """Run the P3 checkpoint proposal command."""

    root = Path(args.root).expanduser()
    proposal, report, exit_code = _build_proposal(root, _utc_now())
    files_written: list[str] = []

    if args.confirm_write:
        path, error = _confirm_write_path(root, str(proposal["proposal_id"]))
        if error is not None or path is None:
            print(f"aso propose checkpoint: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
        ok, write_error = _write_json(path, proposal)
        if not ok:
            print(f"aso propose checkpoint: failed to write confirmed proposal: {write_error}", file=sys.stderr)
            return EXIT_IO_ERROR
        files_written.append(str(path))

    if args.json_out:
        path, error = _validate_json_out(root, str(args.json_out))
        if error is not None or path is None:
            print(f"aso propose checkpoint: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
        ok, write_error = _write_json(path, proposal)
        if not ok:
            print(f"aso propose checkpoint: failed to write json-out: {write_error}", file=sys.stderr)
            return EXIT_IO_ERROR
        files_written.append(str(path))

    if args.format == "json":
        print(json.dumps(proposal, indent=2, sort_keys=True))
    elif not args.json_out:
        _print_text(report, files_written)

    return exit_code
