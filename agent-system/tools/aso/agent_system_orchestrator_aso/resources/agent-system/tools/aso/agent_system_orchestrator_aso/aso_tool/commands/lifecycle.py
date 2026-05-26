"""Orchestrator-owned agent lifecycle event materializers."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .. import correction_routing
from .. import result_parser


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}


def _read_text(path: Path) -> tuple[str, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return "", str(exc)


def _parse_fields(text: str) -> dict[str, str]:
    parsed = result_parser.parse_result(text)
    fields: dict[str, str] = {}
    for key in parsed.fields:
        value = result_parser.as_string(parsed.fields, key)
        if value:
            fields[key] = value
    return fields


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


def _next_allowed_action(role: str, status: str = "") -> str:
    if role == "auditor":
        return "correction_required" if status in {"fail", "blocked", "gap"} else "checkpoint_preflight"
    return "audit_route"


def _result_received_event_name(role: str) -> str:
    return "AUDIT_RESULT_RECEIVED" if role == "auditor" else "RESULT_RECEIVED"


def _artifact_package_required(fields: dict[str, Any]) -> bool:
    value = result_parser.as_string(fields, "ARTIFACT_PACKAGE_REQUIRED").lower()
    return value in {"true", "yes", "required"}


def _result_receipt(root: Path, result_path: Path, parsed: result_parser.ParsedResult) -> dict[str, object]:
    result_ref = _rel(root, result_path)
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
        "artifact_package_required": _artifact_package_required(dict(parsed.fields)),
    }
    if parsed.result_type == "audit_result":
        receipt["audit_result"] = parsed.audit.to_json()
    return receipt


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


def _validate_request(root: Path, result_path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    text, error = _read_text(result_path)
    if error:
        findings.append(_error("LIFECYCLE_RESULT_IO_001", f"RESULT is unreadable: {error}", str(result_path), "Pass --from-result pointing at an existing RESULT Markdown file."))
        return {}, findings
    parsed = result_parser.parse_result(text, path=result_path)
    fields = parsed.fields
    task_id = parsed.task_id
    role = parsed.role
    agent_id = parsed.agent_instance_id
    status = parsed.status
    result_ref = _rel(root, result_path)
    receipt = _result_receipt(root, result_path, parsed)

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
    if role not in result_parser.VALID_ROLES:
        findings.append(_error("LIFECYCLE_RESULT_FORMAT_002", f"RESULT ROLE={role or 'MISSING'} is not a supported agent role.", result_ref, "Record a canonical profile role or auditor before termination."))
    if result_parser.as_string(fields, "REUSE_ALLOWED").lower() != "false":
        findings.append(_error("LIFECYCLE_RESULT_FORMAT_003", "RESULT must declare REUSE_ALLOWED: false.", result_ref, "Set REUSE_ALLOWED: false before terminating the agent instance."))
    if result_parser.as_string(fields, "AGENT_TERMINATION_REQUIRED").lower() != "true":
        findings.append(_error("LIFECYCLE_RESULT_FORMAT_004", "RESULT must declare AGENT_TERMINATION_REQUIRED: true.", result_ref, "Set AGENT_TERMINATION_REQUIRED: true before recording termination."))
    if not result_path.exists():
        findings.append(_error("LIFECYCLE_RESULT_IO_002", "RESULT path does not exist.", result_ref, "Write the RESULT artifact before recording termination."))

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
        "artifact_package_required": receipt["artifact_package_required"],
        "termination_reason": "result_submitted",
        "terminated_at": terminated_at,
        "timestamp_utc": terminated_at,
        "created_by": "orchestrator",
        "next_allowed_action": _next_allowed_action(role, status),
        "reuse_allowed": False,
    }
    return event, findings


def _validate_result_received_request(root: Path, result_path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    termination_event, findings = _validate_request(root, result_path)
    if not termination_event:
        return {}, findings
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
        "artifact_package_required": receipt["artifact_package_required"],
        "received_at": received_at,
        "timestamp_utc": received_at,
        "created_by": "orchestrator",
        "reuse_allowed": False,
    }
    return event, findings


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
    auditor_receipt_without_required_package = (
        str(event.get("role", "")) == "auditor"
        and str(event.get("result_type", "")) == "audit_result"
        and event.get("artifact_package_required") is not True
    )
    if not accepted_events and not auditor_receipt_without_required_package:
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


def run_receive_result(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    result_path = Path(args.from_result).expanduser()
    if not result_path.is_absolute():
        result_path = root / result_path
    event, findings = _validate_result_received_request(root, result_path)
    events_path = root / "project-runtime" / "agents" / "instances.jsonl"
    existing_events = _load_existing_events(events_path)
    if event and _duplicate_event(existing_events, event, {"RESULT_RECEIVED", "AUDIT_RESULT_RECEIVED", "agent_result_received"}):
        findings.append(_error("LIFECYCLE_RESULT_RECEIVED_001", "Agent instance already has a RESULT_RECEIVED event for this RESULT.", "project-runtime/agents/instances.jsonl", "Use one RESULT_RECEIVED event per RESULT artifact."))
    if not args.confirm_write:
        findings.append(_error("LIFECYCLE_CONFIRM_WRITE_REQUIRED", "writes require --confirm-write.", "project-runtime/agents/instances.jsonl", "Rerun with --confirm-write after reviewing the RESULT."))

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
    except OSError as exc:
        print(f"aso lifecycle receive-result: failed to write event: {exc}", file=sys.stderr)
        return EXIT_IO_ERROR
    report["mutations_performed"] = True
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT_OK


def run_terminate_agent(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    result_path = Path(args.from_result).expanduser()
    if not result_path.is_absolute():
        result_path = root / result_path
    event, findings = _validate_request(root, result_path)
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
                "artifact_ids": artifact_ids,
                "artifact_refs": artifact_refs,
                "artifact_receipt_refs": receipt_refs,
                "ready_at": ready_at,
                "timestamp_utc": ready_at,
                "created_by": "orchestrator",
                "previous_event_type": event["event_type"],
                "next_allowed_action": _next_allowed_action(str(event.get("role", "")), str(event.get("status", ""))),
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
    report["mutations_performed"] = True
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT_OK
