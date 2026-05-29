"""Orchestrator-owned agent lifecycle event materializers."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .. import correction_routing
from .. import result_parser
from .. import state_materialization
from .. import transition_engine
from ..timestamps import utc_timestamp
from . import state_verify


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}
STATE_ROOT = Path("project-runtime/state")
FINALIZATION_RECEIPT_RELATIVE_PATH = Path("project-runtime/receipts/lifecycle/PROJECT_FINALIZATION_RECEIPT.json")


def _read_text(path: Path) -> tuple[str, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return "", str(exc)


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _is_none(value: str | None) -> bool:
    return value is None or value.strip() in NONE_VALUES


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _event_name(role: str) -> str:
    return "AUDITOR_AGENT_TERMINATED" if role == "auditor" else "AGENT_TERMINATED"


def _legacy_event_name(role: str) -> str:
    return "auditor_agent_terminated" if role == "auditor" else "agent_instance_terminated"


def _next_allowed_action(decision: Mapping[str, object]) -> str:
    if decision.get("allowed") is not True:
        return "NONE"
    next_action = decision.get("next_action")
    if not isinstance(next_action, Mapping):
        return "NONE"
    recommended = str(next_action.get("recommended_next_action", "")).strip()
    aliases = {
        "CREATE_AUDITOR": "audit_route",
        "CHECKPOINT_PREFLIGHT": "checkpoint_preflight",
        "CORRECTION_REQUIRED": "correction_required",
    }
    return aliases.get(recommended, "NONE")


def _result_received_event_name(role: str) -> str:
    return "AUDIT_RESULT_RECEIVED" if role == "auditor" else "RESULT_RECEIVED"


def _result_acceptance_metadata(parsed: result_parser.ParsedResult) -> dict[str, object]:
    return result_parser.result_acceptance_metadata(parsed.fields, parsed.result_type)


def _result_receipt(root: Path, result_path: Path, parsed: result_parser.ParsedResult) -> dict[str, object]:
    result_ref = _rel(root, result_path)
    acceptance = _result_acceptance_metadata(parsed)
    receipt: dict[str, object] = {
        "receipt_type": "AUDIT_RESULT_RECEIPT" if parsed.result_type == "audit_result" else "RESULT_RECEIPT",
        "result_ref": result_ref,
        "result_type": parsed.result_type,
        "task_id": parsed.task_id,
        "agent_instance_id": parsed.agent_instance_id,
        "role": parsed.role,
        "status": parsed.status,
        "reuse_allowed": parsed.bool_field("REUSE_ALLOWED"),
        "agent_termination_required": parsed.bool_field("AGENT_TERMINATION_REQUIRED") is True,
        "result_acceptance_mode": acceptance["result_acceptance_mode"],
        "artifact_package_required": acceptance["artifact_package_required"],
    }
    if parsed.result_type == "audit_result":
        receipt["audit_result"] = parsed.audit.to_json()
    return receipt


def _transition_not_run(reason: str) -> dict[str, object]:
    return {
        "allowed": False,
        "findings": [],
        "reference_docs_used": [transition_engine.CONTRACT_RELATIVE_PATH.as_posix()],
        "candidate_recommended_next_action": "NONE",
        "canonical_recommended_next_action": "NONE",
        "contract_authoritative": True,
        "route_suppressed_by": reason,
    }


def _transition_load_failure(exc: BaseException) -> dict[str, object]:
    return {
        "allowed": False,
        "findings": [
            {
                "rule_id": "RUNTIME_CONTRACT_LOAD_FAILED",
                "severity": "error",
                "message": "Runtime contract could not be loaded.",
                "evidence": str(exc),
                "recommendation": "Restore ORCHESTRATOR_RUNTIME_CONTRACT.json before lifecycle routing.",
            }
        ],
        "reference_docs_used": [transition_engine.CONTRACT_RELATIVE_PATH.as_posix()],
        "candidate_recommended_next_action": "NONE",
        "canonical_recommended_next_action": "NONE",
        "contract_authoritative": True,
    }


def _transition_finding_as_lifecycle_error(finding: transition_engine.TransitionFinding) -> dict[str, str]:
    return {
        "rule_id": finding.rule_id,
        "severity": finding.severity,
        "message": finding.message,
        "path": transition_engine.CONTRACT_RELATIVE_PATH.as_posix(),
        "evidence": finding.evidence,
        "recommendation": finding.recommendation,
    }


def _result_transition_decision(
    parsed: result_parser.ParsedResult,
    result_ref: str,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    try:
        contract = transition_engine.load_runtime_contract()
    except (OSError, transition_engine.RuntimeContractError) as exc:
        report = _transition_load_failure(exc)
        return report, [
            {
                "rule_id": "RUNTIME_CONTRACT_LOAD_FAILED",
                "severity": "error",
                "message": "Runtime contract could not be loaded.",
                "path": transition_engine.CONTRACT_RELATIVE_PATH.as_posix(),
                "evidence": str(exc),
                "recommendation": "Restore ORCHESTRATOR_RUNTIME_CONTRACT.json before lifecycle routing.",
            }
        ]

    decision = transition_engine.derive_result_route(
        contract,
        parsed.result_type,
        parsed.status,
        task_id=parsed.task_id,
    )
    report = decision.to_json()
    candidate = str(decision.next_action.get("recommended_next_action") or "NONE").strip() or "NONE"
    lifecycle_findings: list[dict[str, str]] = []
    if parsed.result_type == "audit_result":
        supported = set(transition_engine.lifecycle_status_contract(contract)["audit_result_statuses"])
        if parsed.status not in supported:
            lifecycle_findings.append(
                _error(
                    "LIFECYCLE_AUDIT_RESULT_STATUS_UNSUPPORTED",
                    f"AUDIT_RESULT STATUS={parsed.status or 'MISSING'} is not supported for lifecycle routing.",
                    result_ref,
                    "Use a canonical AUDIT_RESULT STATUS of pass or fail; route blocked/gap through explicit correction or owner handling.",
                    reason_code="unsupported_audit_result_status",
                )
            )
    if not decision.allowed:
        lifecycle_findings.extend(
            _transition_finding_as_lifecycle_error(finding)
            for finding in decision.findings
            if finding.severity == "error"
        )
    allowed = decision.allowed and not lifecycle_findings
    report["allowed"] = allowed
    report["candidate_recommended_next_action"] = candidate
    report["canonical_recommended_next_action"] = candidate if allowed else "NONE"
    report["contract_authoritative"] = True
    return report, lifecycle_findings


def _error(
    rule_id: str,
    message: str,
    path: str,
    recommendation: str,
    *,
    reason_code: str = "",
) -> dict[str, str]:
    payload = {
        "rule_id": rule_id,
        "severity": "error",
        "message": message,
        "path": path,
        "recommendation": recommendation,
    }
    if reason_code:
        payload["reason_code"] = reason_code
    return payload


def _load_existing_events(path: Path) -> list[dict[str, Any]]:
    text, error = _read_text(path)
    if error:
        return []
    events: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _payload_event_types(payload: dict[str, Any]) -> set[str]:
    event = str(payload.get("event", "")).strip()
    event_type = str(payload.get("event_type", "")).strip()
    return {value for value in (event, event_type) if value}


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _validate_request(root: Path, result_path: Path) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, object]]:
    findings: list[dict[str, str]] = []
    text, error = _read_text(result_path)
    if error:
        findings.append(_error("LIFECYCLE_RESULT_IO_001", f"RESULT is unreadable: {error}", str(result_path), "Pass --from-result pointing at an existing RESULT Markdown file."))
        return {}, findings, _transition_not_run("result_unreadable")
    parsed = result_parser.parse_result(text, path=result_path)
    fields = parsed.fields
    task_id = parsed.task_id
    role = parsed.role
    agent_id = parsed.agent_instance_id
    status = parsed.status
    result_ref = _rel(root, result_path)
    receipt = _result_receipt(root, result_path, parsed)
    transition_report, transition_findings = _result_transition_decision(parsed, result_ref)

    identity_fields = (
        ("TASK_ID", task_id, result_parser.REASON_MISSING_TASK_ID),
        ("ROLE", role, result_parser.REASON_MISSING_ROLE),
        ("AGENT_INSTANCE_ID", agent_id, result_parser.REASON_MISSING_AGENT_INSTANCE_ID),
        ("STATUS", status, result_parser.REASON_MISSING_STATUS),
    )
    for field_name, value, reason_code in identity_fields:
        if _is_none(value):
            findings.append(
                _error(
                    "LIFECYCLE_RESULT_FORMAT_001",
                    f"RESULT is missing {field_name}.",
                    result_ref,
                    "Use a complete AGENT_RESULT_TEMPLATE.md or AUDIT_RESULT template.",
                    reason_code=reason_code,
                )
            )
    for issue in result_parser.result_acceptance_issues(fields, parsed.result_type):
        findings.append(
            _error(
                issue.rule_id,
                issue.message,
                result_ref,
                "Use RESULT_ACCEPTANCE_MODE: result_only with ARTIFACT_PACKAGE_REQUIRED: false, or artifact_package with true.",
                reason_code=issue.reason_code,
            )
        )
    if role not in result_parser.VALID_ROLES:
        findings.append(_error("LIFECYCLE_RESULT_FORMAT_002", f"RESULT ROLE={role or 'MISSING'} is not a supported agent role.", result_ref, "Record a canonical profile role or auditor before termination."))
    if result_parser.as_string(fields, "REUSE_ALLOWED").lower() != "false":
        findings.append(_error("LIFECYCLE_RESULT_FORMAT_003", "RESULT must declare REUSE_ALLOWED: false.", result_ref, "Set REUSE_ALLOWED: false before terminating the agent instance."))
    if result_parser.as_string(fields, "AGENT_TERMINATION_REQUIRED").lower() != "true":
        findings.append(_error("LIFECYCLE_RESULT_FORMAT_004", "RESULT must declare AGENT_TERMINATION_REQUIRED: true.", result_ref, "Set AGENT_TERMINATION_REQUIRED: true before recording termination."))
    if not result_path.exists():
        findings.append(_error("LIFECYCLE_RESULT_IO_002", "RESULT path does not exist.", result_ref, "Write the RESULT artifact before recording termination."))
    findings.extend(transition_findings)
    if transition_report.get("allowed") is not True:
        return {}, findings, transition_report

    terminated_at = _now_utc()
    event = {
        "event": _legacy_event_name(role),
        "event_type": _event_name(role),
        "task_id": task_id,
        "agent_role": role,
        "role": role,
        "agent_instance_id": agent_id,
        "result_ref": result_ref,
        "result_type": parsed.result_type,
        "status": status,
        "result_status": status,
        "receipt_type": receipt["receipt_type"],
        "result_receipt": receipt,
        "result_acceptance_mode": receipt["result_acceptance_mode"],
        "artifact_package_required": receipt["artifact_package_required"],
        "termination_reason": "result_submitted",
        "terminated_at": terminated_at,
        "timestamp_utc": terminated_at,
        "created_by": "orchestrator",
        "next_allowed_action": _next_allowed_action(transition_report),
        "reuse_allowed": False,
    }
    return event, findings, transition_report


def _validate_result_received_request(root: Path, result_path: Path) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, object]]:
    termination_event, findings, transition_report = _validate_request(root, result_path)
    if not termination_event:
        return {}, findings, transition_report
    received_at = _now_utc()
    receipt = dict(termination_event.get("result_receipt", {}))
    event = {
        "event": "agent_result_received",
        "event_type": _result_received_event_name(str(termination_event.get("role", ""))),
        "task_id": termination_event["task_id"],
        "agent_role": termination_event["agent_role"],
        "role": termination_event["role"],
        "agent_instance_id": termination_event["agent_instance_id"],
        "result_ref": termination_event["result_ref"],
        "result_type": termination_event["result_type"],
        "status": termination_event["status"],
        "result_status": termination_event["result_status"],
        "receipt_type": receipt["receipt_type"],
        "result_receipt": receipt,
        "result_acceptance_mode": receipt["result_acceptance_mode"],
        "artifact_package_required": receipt["artifact_package_required"],
        "received_at": received_at,
        "timestamp_utc": received_at,
        "created_by": "orchestrator",
        "reuse_allowed": False,
    }
    return event, findings, transition_report


def _result_only_acceptance_events(received_event: dict[str, Any]) -> list[dict[str, Any]]:
    if received_event.get("result_type") == "audit_result":
        return []
    if received_event.get("result_acceptance_mode") != "result_only":
        return []
    if received_event.get("artifact_package_required") is True:
        return []

    received_at = str(received_event.get("timestamp_utc") or received_event.get("received_at") or _now_utc())
    try:
        validated_at = (
            datetime.fromisoformat(received_at.replace("Z", "+00:00")) + timedelta(seconds=1)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        accepted_at = (
            datetime.fromisoformat(received_at.replace("Z", "+00:00")) + timedelta(seconds=2)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except ValueError:
        validated_at = _now_utc()
        accepted_at = _now_utc()

    base = {
        "task_id": received_event["task_id"],
        "agent_role": received_event["agent_role"],
        "role": received_event["role"],
        "agent_instance_id": received_event["agent_instance_id"],
        "result_ref": received_event["result_ref"],
        "result_type": received_event["result_type"],
        "status": received_event["status"],
        "result_status": received_event["result_status"],
        "receipt_type": received_event["receipt_type"],
        "result_receipt": received_event["result_receipt"],
        "result_acceptance_mode": "result_only",
        "artifact_package_required": False,
        "created_by": "orchestrator",
        "reuse_allowed": False,
    }
    return [
        {
            **base,
            "event": "result_validated",
            "event_type": "RESULT_VALIDATED",
            "validated_at": validated_at,
            "timestamp_utc": validated_at,
            "previous_event_type": received_event["event_type"],
        },
        {
            **base,
            "event": "result_accepted",
            "event_type": "RESULT_ACCEPTED",
            "accepted_at": accepted_at,
            "timestamp_utc": accepted_at,
            "previous_event_type": "RESULT_VALIDATED",
        },
    ]


def _duplicate_termination(events: list[dict[str, Any]], event: dict[str, Any]) -> bool:
    agent_id = event.get("agent_instance_id")
    for existing in events:
        if existing.get("agent_instance_id") != agent_id:
            continue
        existing_type = existing.get("event_type") or existing.get("event")
        if existing_type in {"AGENT_TERMINATED", "AUDITOR_AGENT_TERMINATED", "agent_instance_terminated", "auditor_agent_terminated"}:
            return True
    return False


def _duplicate_event(events: list[dict[str, Any]], event: dict[str, Any], event_types: set[str]) -> bool:
    agent_id = event.get("agent_instance_id")
    task_id = event.get("task_id")
    result_ref = event.get("result_ref")
    for existing in events:
        if existing.get("agent_instance_id") != agent_id:
            continue
        if existing.get("task_id") != task_id:
            continue
        if result_ref is not None and existing.get("result_ref") != result_ref:
            continue
        if _payload_event_types(existing) & event_types:
            return True
    return False


def _matching_received_event(events: list[dict[str, Any]], event: dict[str, Any]) -> dict[str, Any] | None:
    for existing in events:
        if not (_payload_event_types(existing) & {"RESULT_RECEIVED", "AUDIT_RESULT_RECEIVED", "agent_result_received"}):
            continue
        if existing.get("agent_instance_id") != event.get("agent_instance_id"):
            continue
        if existing.get("task_id") != event.get("task_id"):
            continue
        if existing.get("result_ref") != event.get("result_ref"):
            continue
        if str(existing.get("reuse_allowed", "")).lower() != "false":
            continue
        return existing
    return None


def _matching_accepted_events(events: list[dict[str, Any]], event: dict[str, Any]) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    for existing in events:
        if not (_payload_event_types(existing) & {"ARTIFACT_ACCEPTED", "artifact_accepted"}):
            continue
        if existing.get("agent_instance_id") != event.get("agent_instance_id"):
            continue
        if existing.get("task_id") != event.get("task_id"):
            continue
        if _is_none(str(existing.get("artifact_id", ""))):
            continue
        if _is_none(str(existing.get("artifact_ref", ""))):
            continue
        if _is_none(str(existing.get("receipt_ref", ""))):
            continue
        accepted.append(existing)
    return accepted


def _matching_result_accepted_event(events: list[dict[str, Any]], event: dict[str, Any]) -> dict[str, Any] | None:
    for existing in events:
        if not (_payload_event_types(existing) & {"RESULT_ACCEPTED", "result_accepted"}):
            continue
        if existing.get("agent_instance_id") != event.get("agent_instance_id"):
            continue
        if existing.get("task_id") != event.get("task_id"):
            continue
        if existing.get("result_ref") != event.get("result_ref"):
            continue
        if existing.get("result_acceptance_mode") != "result_only":
            continue
        if existing.get("artifact_package_required") is True:
            continue
        return existing
    return None


def _sequence_findings(events: list[dict[str, Any]], event: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    received = _matching_received_event(events, event)
    if received is None:
        findings.append(
            _error(
                "LIFECYCLE_SEQUENCE_001",
                "RESULT_RECEIVED event is required before AGENT_TERMINATED.",
                "project-runtime/agents/instances.jsonl",
                "Run lifecycle receive-result for this RESULT before terminating the agent.",
            )
        )
        return findings

    accepted_events = _matching_accepted_events(events, event)
    audit_receipt_without_required_package = (
        str(event.get("result_type", "")) == "audit_result"
        and event.get("artifact_package_required") is not True
    )
    result_only_accepted = (
        event.get("result_acceptance_mode") == "result_only"
        and event.get("artifact_package_required") is not True
        and _matching_result_accepted_event(events, event) is not None
    )
    if not accepted_events and not audit_receipt_without_required_package and not result_only_accepted:
        if event.get("result_acceptance_mode") == "result_only" and event.get("artifact_package_required") is not True:
            findings.append(
                _error(
                    "LIFECYCLE_SEQUENCE_002",
                    "RESULT_ACCEPTED event is required before AGENT_TERMINATED for result-only output.",
                    "project-runtime/agents/instances.jsonl",
                    "Run lifecycle receive-result for this result-only RESULT before terminating the agent.",
                )
            )
            return findings
        findings.append(
            _error(
                "LIFECYCLE_SEQUENCE_002",
                "ARTIFACT_ACCEPTED event with artifact_id and receipt_ref is required before AGENT_TERMINATED.",
                "project-runtime/agents/instances.jsonl",
                "Accept the candidate artifact package before terminating the agent.",
            )
        )
        return findings

    received_at = _parse_timestamp(received.get("timestamp_utc") or received.get("received_at"))
    for accepted in accepted_events:
        accepted_at = _parse_timestamp(accepted.get("timestamp_utc") or accepted.get("accepted_at"))
        if received_at is not None and accepted_at is not None and accepted_at < received_at:
            findings.append(
                _error(
                    "LIFECYCLE_SEQUENCE_003",
                    "ARTIFACT_ACCEPTED must not precede RESULT_RECEIVED.",
                    "project-runtime/agents/instances.jsonl",
                    "Record lifecycle events in RESULT_RECEIVED -> ARTIFACT_ACCEPTED order.",
                )
            )
            break
    return findings


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _content(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    content = payload.get("content")
    return dict(content) if isinstance(content, Mapping) else {}


def _load_state_sidecars(root: Path) -> dict[str, dict[str, Any]]:
    sidecars: dict[str, dict[str, Any]] = {}
    for sidecar_type in ("PROJECT_STATE", "CURRENT_GATE", "NEXT_ACTION", "TASK_REGISTRY"):
        payload = _read_json(root / STATE_ROOT / f"{sidecar_type}.json")
        if payload is not None:
            sidecars[sidecar_type] = payload
    return sidecars


def _transition_authority(root: Path, sidecars: dict[str, dict[str, Any]]) -> dict[str, object]:
    try:
        contract = transition_engine.load_runtime_contract()
        return transition_engine.routing_authority_report(contract, sidecars, root=root)
    except (OSError, transition_engine.RuntimeContractError) as exc:
        return {
            "allowed": False,
            "contract_authoritative": True,
            "canonical_recommended_next_action": "NONE",
            "findings": [
                {
                    "rule_id": "RUNTIME_CONTRACT_LOAD_FAILED",
                    "severity": "error",
                    "message": "Runtime contract could not be loaded.",
                    "evidence": str(exc),
                    "recommendation": "Restore ORCHESTRATOR_RUNTIME_CONTRACT.json before lifecycle routing.",
                }
            ],
            "reference_docs_used": [transition_engine.CONTRACT_RELATIVE_PATH.as_posix()],
        }


def _object_is_none(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in NONE_VALUES)


def _terminal_blockers(value: object) -> list[str]:
    if isinstance(value, list):
        blockers: list[str] = []
        for item in value:
            if isinstance(item, str) and not _object_is_none(item):
                blockers.append(item.strip())
            elif isinstance(item, Mapping) and item:
                blocker_id = item.get("blocker_id")
                blockers.append(str(blocker_id or json.dumps(dict(item), sort_keys=True)))
        return blockers
    if isinstance(value, str) and not _object_is_none(value):
        return [value.strip()]
    if isinstance(value, Mapping) and value:
        return [json.dumps(dict(value), sort_keys=True)]
    return []


def _finalization_error(rule_id: str, message: str, path: str, recommendation: str) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "severity": "error",
        "message": message,
        "path": path,
        "recommendation": recommendation,
    }


def _finalization_findings(sidecars: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    missing = sorted(set(("PROJECT_STATE", "CURRENT_GATE", "NEXT_ACTION", "TASK_REGISTRY")) - set(sidecars))
    if missing:
        findings.append(
            _finalization_error(
                "LIFECYCLE_FINALIZE_STATE_MISSING",
                f"Required state sidecars are missing: {', '.join(missing)}.",
                "project-runtime/state",
                "Initialize or restore runtime sidecars before finalization.",
            )
        )
        return findings

    project_state = _content(sidecars["PROJECT_STATE"])
    current_gate = _content(sidecars["CURRENT_GATE"])
    next_action = _content(sidecars["NEXT_ACTION"])
    task_registry = _content(sidecars["TASK_REGISTRY"])

    unresolved: list[str] = []
    tasks = task_registry.get("tasks")
    if isinstance(tasks, list):
        for task in tasks:
            if not isinstance(task, Mapping):
                continue
            status = task.get("status")
            if status in {"failed", "blocked", "audit_pending"}:
                unresolved.append(f"{task.get('task_id', 'UNKNOWN')}:{status}")
    if unresolved:
        findings.append(
            _finalization_error(
                "LIFECYCLE_FINALIZE_UNRESOLVED_TASKS",
                "Cannot finalize with unresolved failed/blocked/audit_pending tasks: " + ", ".join(unresolved),
                "project-runtime/state/TASK_REGISTRY.json",
                "Resolve, supersede, or correct unresolved tasks before project completion.",
            )
        )

    blockers = sorted(
        set(
            _terminal_blockers(project_state.get("active_blockers"))
            + _terminal_blockers(project_state.get("active_gaps"))
            + _terminal_blockers(project_state.get("checkpoint_blocked_by"))
            + _terminal_blockers(next_action.get("blocked_by"))
            + _terminal_blockers(current_gate.get("blocking_status"))
        )
    )
    if blockers:
        findings.append(
            _finalization_error(
                "LIFECYCLE_FINALIZE_STALE_BLOCKERS",
                "Cannot finalize with active or stale blockers: " + ", ".join(blockers),
                "project-runtime/state/PROJECT_STATE.json",
                "Clear active blockers, GAPs, and checkpoint blockers before finalization.",
            )
        )

    audit_status = str(project_state.get("audit_status", "")).strip()
    if audit_status not in {"passed", "not_applicable"}:
        findings.append(
            _finalization_error(
                "LIFECYCLE_FINALIZE_AUDIT_NOT_PASSED",
                f"Cannot finalize with audit_status={audit_status or 'NONE'}.",
                "project-runtime/state/PROJECT_STATE.json",
                "Record final audit pass evidence before finalization.",
            )
        )

    checkpoint_status = str(project_state.get("project_checkpoint_status", "")).strip()
    if checkpoint_status not in {"passed", "not_required"}:
        findings.append(
            _finalization_error(
                "LIFECYCLE_FINALIZE_CHECKPOINT_NOT_COMPLETE",
                f"Cannot finalize with project_checkpoint_status={checkpoint_status or 'NONE'}.",
                "project-runtime/state/PROJECT_STATE.json",
                "Complete the final checkpoint or explicitly mark it not_required before finalization.",
            )
        )

    action_type = str(next_action.get("action_type", "")).strip()
    current_phase = str(project_state.get("current_phase", "")).strip()
    if action_type != "finalize" and current_phase not in {"finalization", "final_acceptance"}:
        findings.append(
            _finalization_error(
                "LIFECYCLE_FINALIZE_ROUTE_NOT_READY",
                "Finalization must be routed by NEXT_ACTION action_type=finalize or a finalization phase.",
                "project-runtime/state/NEXT_ACTION.json",
                "Route FINAL_CHECKPOINT_COMPLETE to FINALIZE before confirming project completion.",
            )
        )
    return findings


def _is_project_completed(sidecars: dict[str, dict[str, Any]]) -> bool:
    project_state = _content(sidecars.get("PROJECT_STATE"))
    next_action = _content(sidecars.get("NEXT_ACTION"))
    current_gate = _content(sidecars.get("CURRENT_GATE"))
    return (
        project_state.get("project_status") == "completed"
        and project_state.get("current_phase") == "completed"
        and current_gate.get("gate_type") == "terminal"
        and current_gate.get("status") == "passed"
        and next_action.get("action_type") == "stop"
        and next_action.get("target_role") == "none"
        and next_action.get("action_semantic") == "stop_terminal"
    )


def _touch_sidecar(payload: dict[str, Any], timestamp: str) -> None:
    state_revision = payload.get("state_revision")
    if isinstance(state_revision, int) and not isinstance(state_revision, bool):
        payload["state_revision"] = state_revision + 1
    payload["updated_at"] = timestamp
    payload["updated_by"] = "orchestrator"


def _markdown_value(value: object) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return "NONE" if not value else ", ".join(str(item) for item in value)
    if isinstance(value, Mapping):
        return "NONE" if not value else json.dumps(dict(value), sort_keys=True)
    return str(value)


def _sync_markdown(root: Path, payload: Mapping[str, Any]) -> str:
    markdown_source = str(payload.get("markdown_source", "")).strip()
    if not markdown_source:
        return ""
    path = root / markdown_source
    if not path.is_file():
        return ""
    content = _content(payload)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    changed = False
    for key, value in content.items():
        if isinstance(value, (list, dict)):
            continue
        prefix = f"{key.upper()}:"
        replacement = f"{prefix} {_markdown_value(value)}"
        for index, line in enumerate(lines):
            if line.startswith(prefix):
                if line != replacement:
                    lines[index] = replacement
                    changed = True
                break
    if not changed:
        return ""
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return markdown_source


def _append_unique(values: object, value: str) -> list[str]:
    result = [item for item in values if isinstance(item, str)] if isinstance(values, list) else []
    if value and value not in result:
        result.append(value)
    return result


def _finalization_receipt(root: Path, timestamp: str, pre_verify: dict[str, object]) -> dict[str, object]:
    return {
        "receipt_type": "PROJECT_FINALIZATION_RECEIPT",
        "receipt_version": "1.0.0",
        "command": "lifecycle finalize",
        "root": str(root),
        "finalized_at": timestamp,
        "created_by": "orchestrator",
        "from_state": "FINAL_CHECKPOINT_COMPLETE",
        "terminal_state": "PROJECT_COMPLETED",
        "terminal_route": "NO_NEXT_ACTION",
        "state_verify_before_status": pre_verify.get("status", "unknown"),
        "state_verify_before_summary": pre_verify.get("summary", {}),
    }


def _apply_finalization(
    root: Path,
    sidecars: dict[str, dict[str, Any]],
    timestamp: str,
    receipt_ref: str,
) -> list[str]:
    files_written: list[str] = []
    changed: dict[str, dict[str, Any]] = {}

    project_state = sidecars["PROJECT_STATE"]
    project_content = _content(project_state)
    project_content.update(
        {
            "audit_status": "passed" if project_content.get("audit_status") != "not_applicable" else "not_applicable",
            "checkpoint_eligibility": "not_applicable",
            "checkpoint_eligibility_status": "eligible",
            "checkpoint_preflight_status": "passed",
            "project_checkpoint_status": "passed" if project_content.get("project_checkpoint_status") != "not_required" else "not_required",
            "checkpoint_blocked_by": [],
            "last_checkpoint_failure_reason": "NONE",
            "current_phase": "completed",
            "project_status": "completed",
            "action_semantic": "completed_state_transition",
            "semantic_reason": "Project completed by lifecycle finalize.",
            "active_blockers": [],
            "active_gaps": [],
        }
    )
    branches = project_content.get("active_branches")
    if isinstance(branches, list):
        for branch in branches:
            if isinstance(branch, dict):
                branch["status"] = "completed"
                branch["blocked_by"] = ""
    project_state["content"] = project_content
    changed["PROJECT_STATE"] = project_state

    task_registry = sidecars["TASK_REGISTRY"]
    registry_content = _content(task_registry)
    tasks = registry_content.get("tasks")
    registry_changed = False
    if isinstance(tasks, list):
        for task in tasks:
            if not isinstance(task, dict):
                continue
            if task.get("status") in {"audit_passed", "checkpoint_done"}:
                task["status"] = "completed"
                task["updated_at"] = timestamp
                registry_changed = True
            if isinstance(task.get("checkpoint_ref"), str) and task.get("checkpoint_ref") == "NONE":
                task["checkpoint_ref"] = receipt_ref
                registry_changed = True
    if registry_changed:
        if isinstance(registry_content.get("registry_revision"), int):
            registry_content["registry_revision"] = int(registry_content["registry_revision"]) + 1
        task_registry["content"] = registry_content
        changed["TASK_REGISTRY"] = task_registry

    current_gate = sidecars["CURRENT_GATE"]
    gate_content = _content(current_gate)
    evidence = _append_unique(gate_content.get("gate_evidence"), receipt_ref)
    gate_content.update(
        {
            "gate_id": "GATE-PROJECT-COMPLETED",
            "gate_name": "Project completed",
            "gate_type": "terminal",
            "status": "passed",
            "owner_role": "orchestrator",
            "task_id": "NONE",
            "task_packet": "NONE",
            "action_semantic": "stop_terminal",
            "checkpoint_eligibility": "not_applicable",
            "checkpoint_eligibility_status": "eligible",
            "project_checkpoint_status": project_content.get("project_checkpoint_status", "passed"),
            "required_next_role": "none",
            "gate_evidence": evidence,
            "blocking_status": "NONE",
        }
    )
    current_gate["content"] = gate_content
    changed["CURRENT_GATE"] = current_gate

    next_action = sidecars["NEXT_ACTION"]
    next_content = _content(next_action)
    checkpoint_receipt_ref = str(project_content.get("checkpoint_receipt_ref", "NONE")).strip() or "NONE"
    next_content.update(
        {
            "action_id": "ACTION-NO-NEXT-ACTION-PROJECT-COMPLETED",
            "action_type": "stop",
            "target_role": "none",
            "task_id": "NONE",
            "task_packet": "NONE",
            "dependency_status": "completed",
            "blocked_by": [],
            "action_semantic": "stop_terminal",
            "workspace_identity_required": False,
            "repository_lock_required": False,
            "checkpoint_policy": "no_checkpoint",
            "checkpoint_preflight_required": False,
            "checkpoint_receipt_required": False,
            "checkpoint_receipt_ref": checkpoint_receipt_ref,
            "requester_return_context": "NONE",
            "blocking_or_resume_context": "NONE",
            "required_universal_docs": [],
            "required_project_docs": [],
            "expected_result": [],
            "instruction_for_orchestrator": "NO_NEXT_ACTION: project is completed.",
        }
    )
    next_action["content"] = next_content
    changed["NEXT_ACTION"] = next_action

    for sidecar_type, payload in changed.items():
        _touch_sidecar(payload, timestamp)
        path = root / STATE_ROOT / f"{sidecar_type}.json"
        _write_json(path, payload)
        files_written.append(path.relative_to(root).as_posix())
        markdown = _sync_markdown(root, payload)
        if markdown:
            files_written.append(markdown)
    return sorted(dict.fromkeys(files_written))


def _write_report(path_text: str | None, report: dict[str, object]) -> bool:
    if not path_text:
        return True
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso lifecycle finalize: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso lifecycle finalize: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def _emit_finalize_report(args: argparse.Namespace, report: dict[str, object], exit_code: int) -> int:
    print(json.dumps(report, indent=2, sort_keys=True))
    if not _write_report(getattr(args, "json_out", None), report):
        return EXIT_IO_ERROR
    return exit_code


def run_receive_result(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    result_path = Path(args.from_result).expanduser()
    if not result_path.is_absolute():
        result_path = root / result_path
    event, findings, transition_report = _validate_result_received_request(root, result_path)
    events_path = root / "project-runtime" / "agents" / "instances.jsonl"
    existing_events = _load_existing_events(events_path)
    if event and _duplicate_event(existing_events, event, {"RESULT_RECEIVED", "AUDIT_RESULT_RECEIVED", "agent_result_received"}):
        findings.append(_error("LIFECYCLE_RESULT_RECEIVED_001", "Agent instance already has a RESULT_RECEIVED event for this RESULT.", "project-runtime/agents/instances.jsonl", "Use one RESULT_RECEIVED event per RESULT artifact."))
    if not args.confirm_write:
        findings.append(_error("LIFECYCLE_CONFIRM_WRITE_REQUIRED", "writes require --confirm-write.", "project-runtime/agents/instances.jsonl", "Rerun with --confirm-write after reviewing the RESULT."))
    acceptance_events = _result_only_acceptance_events(event) if event else []

    correction_route = {}
    if event and event.get("result_type") == "audit_result" and event.get("status") == "fail":
        parsed = result_parser.parse_result_file(result_path)
        correction_route = correction_routing.from_parsed_audit_result(
            root=root,
            result_path=result_path,
            parsed=parsed,
        )

    report = {
        "tool": "aso",
        "command": "lifecycle receive-result",
        "root": str(root),
        "status": "blocked" if findings else "written",
        "event": event,
        "result_acceptance_events": acceptance_events,
        "transition_engine": transition_report,
        "correction_routing": correction_route,
        "event_log": "project-runtime/agents/instances.jsonl",
        "findings": findings,
        "mutations_performed": False,
    }
    if findings:
        print(json.dumps(report, indent=2, sort_keys=True))
        return EXIT_FINDINGS

    try:
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            for acceptance_event in acceptance_events:
                handle.write(json.dumps(acceptance_event, sort_keys=True) + "\n")
    except OSError as exc:
        print(f"aso lifecycle receive-result: failed to write event: {exc}", file=sys.stderr)
        return EXIT_IO_ERROR
    materialization = state_materialization.materialize_after_confirmed_write(root)
    report["state_materialization"] = materialization.to_json()
    if not materialization.ok:
        print(json.dumps(report, indent=2, sort_keys=True))
        return EXIT_IO_ERROR
    report["mutations_performed"] = True
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT_OK


def run_terminate_agent(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    result_path = Path(args.from_result).expanduser()
    if not result_path.is_absolute():
        result_path = root / result_path
    event, findings, transition_report = _validate_request(root, result_path)
    events_path = root / "project-runtime" / "agents" / "instances.jsonl"
    existing_events = _load_existing_events(events_path)
    if event and _duplicate_termination(existing_events, event):
        findings.append(_error("LIFECYCLE_TERMINATION_001", "Agent instance already has a termination event.", "project-runtime/agents/instances.jsonl", "Use one termination event per agent instance."))
    if event:
        findings.extend(_sequence_findings(existing_events, event))
    if not args.confirm_write:
        findings.append(_error("LIFECYCLE_CONFIRM_WRITE_REQUIRED", "writes require --confirm-write.", "project-runtime/agents/instances.jsonl", "Rerun with --confirm-write after reviewing the RESULT."))

    accepted_events = _matching_accepted_events(existing_events, event) if event else []
    artifact_ids = [str(item["artifact_id"]) for item in accepted_events]
    artifact_refs = [str(item["artifact_ref"]) for item in accepted_events]
    receipt_refs = [str(item["receipt_ref"]) for item in accepted_events]
    correction_route = {}
    if event:
        event["artifact_ids"] = artifact_ids
        event["artifact_refs"] = artifact_refs
        event["artifact_receipt_refs"] = receipt_refs
        if event.get("result_type") == "audit_result" and event.get("status") == "fail":
            parsed = result_parser.parse_result_file(result_path)
            correction_route = correction_routing.from_parsed_audit_result(
                root=root,
                result_path=result_path,
                parsed=parsed,
            )
        terminated_at = str(event["timestamp_utc"])
        ready_at = (
            datetime.fromisoformat(terminated_at.replace("Z", "+00:00")) + timedelta(seconds=1)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if event.get("role") == "auditor" and event.get("status") == "fail":
            audit_ready_event = {}
        else:
            audit_ready_event = {
                "event": "audit_route_ready",
                "event_type": "AUDIT_ROUTE_READY",
                "task_id": event["task_id"],
                "agent_role": event["agent_role"],
                "role": event["role"],
                "agent_instance_id": event["agent_instance_id"],
                "result_ref": event["result_ref"],
                "result_acceptance_mode": event["result_acceptance_mode"],
                "artifact_package_required": event["artifact_package_required"],
                "artifact_ids": artifact_ids,
                "artifact_refs": artifact_refs,
                "artifact_receipt_refs": receipt_refs,
                "ready_at": ready_at,
                "timestamp_utc": ready_at,
                "created_by": "orchestrator",
                "previous_event_type": event["event_type"],
                "next_allowed_action": _next_allowed_action(transition_report),
            }
    else:
        audit_ready_event = {}

    report = {
        "tool": "aso",
        "command": "lifecycle terminate-agent",
        "root": str(root),
        "status": "blocked" if findings else "written",
        "event": event,
        "audit_route_ready_event": audit_ready_event,
        "transition_engine": transition_report,
        "correction_routing": correction_route,
        "event_log": "project-runtime/agents/instances.jsonl",
        "findings": findings,
        "mutations_performed": False,
    }
    if findings:
        print(json.dumps(report, indent=2, sort_keys=True))
        return EXIT_FINDINGS

    try:
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            if audit_ready_event:
                handle.write(json.dumps(audit_ready_event, sort_keys=True) + "\n")
    except OSError as exc:
        print(f"aso lifecycle terminate-agent: failed to write event: {exc}", file=sys.stderr)
        return EXIT_IO_ERROR
    materialization = state_materialization.materialize_after_confirmed_write(root)
    report["state_materialization"] = materialization.to_json()
    if not materialization.ok:
        print(json.dumps(report, indent=2, sort_keys=True))
        return EXIT_IO_ERROR
    report["mutations_performed"] = True
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT_OK


def run_finalize(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    dry_run = bool(getattr(args, "dry_run", False)) or not bool(getattr(args, "confirm_write", False))
    sidecars = _load_state_sidecars(root)
    transition_authority = _transition_authority(root, sidecars)
    pre_verify, pre_exit_code = state_verify._report(root, True)
    receipt_ref = FINALIZATION_RECEIPT_RELATIVE_PATH.as_posix()
    timestamp = utc_timestamp()
    receipt = _finalization_receipt(root, timestamp, pre_verify)
    already_completed = _is_project_completed(sidecars)
    findings: list[dict[str, str]] = []

    if pre_exit_code != 0:
        findings.extend(
            [
                {
                    "rule_id": str(finding.get("rule_id", "STATE_VERIFY_FAILED")),
                    "severity": str(finding.get("severity", "error")),
                    "message": str(finding.get("message", finding.get("details", ""))),
                    "path": str(finding.get("path", "")),
                    "recommendation": str(finding.get("recommendation", "Repair state verify findings before finalization.")),
                }
                for finding in pre_verify.get("findings", [])
                if isinstance(finding, dict) and finding.get("severity") == "error"
            ]
        )

    if already_completed and not findings:
        report = {
            "tool": "aso",
            "command": "lifecycle finalize",
            "root": str(root),
            "status": "already_finalized",
            "dry_run": dry_run,
            "receipt_ref": receipt_ref,
            "receipt": receipt if not (root / FINALIZATION_RECEIPT_RELATIVE_PATH).is_file() else _read_json(root / FINALIZATION_RECEIPT_RELATIVE_PATH),
            "state_verify_before": pre_verify,
            "state_verify_after": pre_verify,
            "transition_engine": transition_authority,
            "findings": [],
            "files_written": [],
            "mutations_performed": False,
            "terminal_state": "PROJECT_COMPLETED",
            "recommended_next_action": "NO_NEXT_ACTION",
        }
        return _emit_finalize_report(args, report, EXIT_OK)

    if not findings:
        findings.extend(_finalization_findings(sidecars))
    if (
        not findings
        and not already_completed
        and transition_authority.get("canonical_recommended_next_action") != "FINALIZE"
    ):
        findings.append(
            _finalization_error(
                "LIFECYCLE_FINALIZE_TRANSITION_NOT_ALLOWED",
                (
                    "Transition engine does not route this workspace to FINALIZE; "
                    f"recommended={transition_authority.get('canonical_recommended_next_action', 'NONE')}."
                ),
                "project-runtime/state/NEXT_ACTION.json",
                "Route FINAL_CHECKPOINT_COMPLETE to FINALIZE before confirming project completion.",
            )
        )

    base_report = {
        "tool": "aso",
        "command": "lifecycle finalize",
        "root": str(root),
        "dry_run": dry_run,
        "receipt_ref": receipt_ref,
        "receipt": receipt,
        "state_verify_before": pre_verify,
        "transition_engine": transition_authority,
        "findings": findings,
        "files_written": [],
        "mutations_performed": False,
        "terminal_state": "PROJECT_COMPLETED",
        "recommended_next_action": "NO_NEXT_ACTION",
    }
    if findings:
        base_report["status"] = "blocked"
        return _emit_finalize_report(args, base_report, EXIT_FINDINGS)
    if dry_run:
        base_report["status"] = "dry_run"
        base_report["planned_files"] = [
            "project-runtime/state/PROJECT_STATE.json",
            "project-runtime/state/CURRENT_GATE.json",
            "project-runtime/state/NEXT_ACTION.json",
            "project-runtime/state/TASK_REGISTRY.json",
            receipt_ref,
        ]
        return _emit_finalize_report(args, base_report, EXIT_OK)

    try:
        files_written = _apply_finalization(root, sidecars, timestamp, receipt_ref)
        _write_json(root / FINALIZATION_RECEIPT_RELATIVE_PATH, receipt)
        files_written.append(receipt_ref)
    except OSError as exc:
        base_report["status"] = "io_error"
        base_report["findings"] = [
            _finalization_error(
                "LIFECYCLE_FINALIZE_WRITE_FAILED",
                f"Finalization write failed: {exc}",
                "project-runtime",
                "Repair workspace permissions and rerun lifecycle finalize.",
            )
        ]
        return _emit_finalize_report(args, base_report, EXIT_IO_ERROR)

    post_verify, post_exit_code = state_verify._report(root, True)
    base_report["status"] = "written" if post_exit_code == 0 else "written_with_verify_findings"
    base_report["files_written"] = sorted(dict.fromkeys(files_written))
    base_report["mutations_performed"] = True
    base_report["state_verify_after"] = post_verify
    if post_exit_code != 0:
        base_report["findings"] = [
            _finalization_error(
                "LIFECYCLE_FINALIZE_POST_VERIFY_FAILED",
                "State verify failed after finalization write.",
                "project-runtime/state",
                "Inspect state_verify_after findings and repair terminal completion state.",
            )
        ]
        return _emit_finalize_report(args, base_report, EXIT_FINDINGS)
    return _emit_finalize_report(args, base_report, EXIT_OK)
