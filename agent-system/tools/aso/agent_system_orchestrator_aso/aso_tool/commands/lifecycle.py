"""Orchestrator-owned agent lifecycle event materializers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    fields: dict[str, str] = {}
    pending_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.match(r"^([A-Z0-9_]+):\s*(.*?)\s*$", line)
        if match:
            key = match.group(1)
            value = match.group(2).strip()
            if value:
                fields.setdefault(key, value)
                pending_key = None
            else:
                pending_key = key
            continue
        if pending_key is not None and line and not line.startswith(("#", "- ", "```")):
            fields.setdefault(pending_key, line)
            pending_key = None
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


def _next_allowed_action(role: str) -> str:
    return "checkpoint_preflight" if role == "auditor" else "audit_route"


def _error(rule_id: str, message: str, path: str, recommendation: str) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "severity": "error",
        "message": message,
        "path": path,
        "recommendation": recommendation,
    }


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


def _validate_request(root: Path, result_path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    text, error = _read_text(result_path)
    if error:
        findings.append(_error("LIFECYCLE_RESULT_IO_001", f"RESULT is unreadable: {error}", str(result_path), "Pass --from-result pointing at an existing RESULT Markdown file."))
        return {}, findings
    fields = _parse_fields(text)
    task_id = fields.get("TASK_ID", "")
    role = fields.get("ROLE", "")
    agent_id = fields.get("AGENT_INSTANCE_ID", "")
    status = fields.get("STATUS", "")
    result_ref = _rel(root, result_path)

    for field_name, value in (("TASK_ID", task_id), ("ROLE", role), ("AGENT_INSTANCE_ID", agent_id), ("STATUS", status)):
        if _is_none(value):
            findings.append(_error("LIFECYCLE_RESULT_FORMAT_001", f"RESULT is missing {field_name}.", result_ref, "Use a complete AGENT_RESULT_TEMPLATE.md or AUDIT_RESULT template."))
    if role not in {
        "requirements_analyst",
        "solution_architect",
        "designer",
        "developer",
        "auditor",
        "tester",
        "technical_writer",
        "devops_setup_engineer",
        "release_manager",
    }:
        findings.append(_error("LIFECYCLE_RESULT_FORMAT_002", f"RESULT ROLE={role or 'MISSING'} is not a supported agent role.", result_ref, "Record a canonical profile role or auditor before termination."))
    if fields.get("REUSE_ALLOWED", "").lower() != "false":
        findings.append(_error("LIFECYCLE_RESULT_FORMAT_003", "RESULT must declare REUSE_ALLOWED: false.", result_ref, "Set REUSE_ALLOWED: false before terminating the agent instance."))
    if fields.get("AGENT_TERMINATION_REQUIRED", "").lower() != "true":
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
        "termination_reason": "result_submitted",
        "terminated_at": terminated_at,
        "timestamp_utc": terminated_at,
        "created_by": "orchestrator",
        "next_allowed_action": _next_allowed_action(role),
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
    if not args.confirm_write:
        findings.append(_error("LIFECYCLE_CONFIRM_WRITE_REQUIRED", "writes require --confirm-write.", "project-runtime/agents/instances.jsonl", "Rerun with --confirm-write after reviewing the RESULT."))

    report = {
        "tool": "aso",
        "command": "lifecycle terminate-agent",
        "root": str(root),
        "status": "blocked" if findings else "written",
        "event": event,
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
        print(f"aso lifecycle terminate-agent: failed to write event: {exc}", file=sys.stderr)
        return EXIT_IO_ERROR
    report["mutations_performed"] = True
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT_OK
