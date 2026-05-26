"""Read-only dry-run planner for the next orchestrator action."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from . import state_init, state_verify
from .. import correction_routing
from .. import dispatch_receipts
from .. import handoff_artifacts
from .. import role_registry
from .. import result_parser
from .. import resources
from .. import transition_engine


EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_RUNTIME_ERROR = 2
EXIT_INVALID_STATE = 3
EXIT_IO_ERROR = EXIT_RUNTIME_ERROR

RULES_RELATIVE_PATH = Path("agent-system/09_validators/rules/governance_rules.json")
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}
PROFILE_EXECUTION_ROLES = set(role_registry.dispatchable_roles())
LIFECYCLE_SYSTEM_ROLES = set(role_registry.legacy_lifecycle_system_roles())
DEPRECATED_PROFILE_ROLE_ALIASES: dict[str, str] = {}
CONTROL_OR_PSEUDO_ROLES = set(role_registry.control_or_pseudo_roles())
NON_DISPATCH_ACTION_TYPES = {
    "correction": "CORRECTION_REQUIRED",
    "update_state": "UPDATE_STATE",
    "wait_for_owner": "ASK_OWNER",
    "finalize": "FINALIZE",
    "stop": "STOP",
    "route_result": "ROUTE_RESULT",
}
TASK_PACKET_REQUIRED_FIELDS = {"TASK_ID", "TASK_KIND", "TASK_TYPE", "TARGET_ROLE"}
BOOTSTRAP_TASK_PACKET_REQUIRED_FIELDS = {
    "TASK_COMPLEXITY",
    "REASONING_LEVEL_REQUIRED",
    "AGENT_LIFECYCLE_POLICY",
    "RESULT_CONTRACT",
    "EVIDENCE_REQUIREMENTS",
    "EXPECTED_ARTIFACT_PACKAGE",
}
TASK_COMPLEXITY_FLOORS = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "xhigh",
}
INCIDENT_MARKERS = {
    "incident",
    "incident_recovery",
    "wrong_remote_push",
    "wrong_branch_push",
    "invalid_task_packet_commit",
    "forbidden_files",
    "secret_exposure",
    "runtime_corruption",
    "audit_false_pass",
    "AUDIT_FALSE_PASS_DETECTED",
}
CHECKPOINT_PREFLIGHT_POLICIES = {"local_only", "commit_and_push"}
BOOTSTRAP_INPUTS = (Path("project-input/TZ.md"),)
PROJECT_STATE_READY_IDENTITY_STATUSES = {"passed"}
PROJECT_STATE_READY_REPOSITORY_LOCK_STATUSES = {"accepted"}
PROJECT_STATE_READY_BASELINE_STATUSES = {"passed"}
PROJECT_STATE_IDENTITY_STATUSES = state_verify.ENUM_FIELDS[("PROJECT_STATE", "identity_validation_status")]
PROJECT_STATE_REPOSITORY_LOCK_STATUSES = state_verify.ENUM_FIELDS[("PROJECT_STATE", "repository_lock_status")]
INVALID_STATE_RULE_IDS = {
    "SIDECAR_JSON_PARSE_ERROR",
    "SIDECAR_TOP_LEVEL_NOT_OBJECT",
    "SIDECAR_REQUIRED_SIDECAR_MISSING",
    "SIDECAR_SCHEMA_VERSION_MISSING_OR_INVALID",
    "RUNTIME_LIFECYCLE_LOG_JSON_INVALID",
    "RUNTIME_LIFECYCLE_LOG_EVENT_INVALID",
    "RUNTIME_LIFECYCLE_LOG_UNREADABLE",
}


def _is_none(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in NONE_VALUES)


def _as_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _content(sidecars: dict[str, dict[str, object]], sidecar_type: str) -> dict[str, object]:
    payload = sidecars.get(sidecar_type, {})
    content = payload.get("content")
    return content if isinstance(content, dict) else {}


def _load_governance_rules(workspace_root: Path) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    try:
        resource = resources.read_resource_text(RULES_RELATIVE_PATH, anchor_file=__file__)
        payload = json.loads(resource.text)
    except (OSError, json.JSONDecodeError) as exc:
        return {}, {
            "path": RULES_RELATIVE_PATH.as_posix(),
            "origin": "",
            "attempted_paths": getattr(exc, "filename", "") or str(exc),
            "registry_id": "",
            "rule_count": 0,
            "load_error": (
                f"Governance rule registry could not be loaded. {exc}. "
                "Reinstall agent-system-orchestrator from a complete source archive, or run the direct script from "
                "an ASO source checkout."
            ),
        }

    rules: dict[str, dict[str, object]] = {}
    raw_rules = payload.get("rules") if isinstance(payload, dict) else None
    if isinstance(raw_rules, list):
        for item in raw_rules:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                rules[item["id"]] = item
    return rules, {
        "path": resource.relative_path,
        "origin": resource.origin,
        "attempted_paths": list(resource.attempted_paths),
        "registry_id": payload.get("registry_id", "") if isinstance(payload, dict) else "",
        "rule_count": len(rules),
        "load_error": "",
    }


def _load_sidecars(root: Path) -> dict[str, dict[str, object]]:
    sidecars: dict[str, dict[str, object]] = {}
    for spec in state_verify.SIDECARS:
        path = root / "project-runtime" / "state" / spec.filename
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            sidecars[spec.sidecar_type] = payload
    lifecycle_log = transition_engine.load_lifecycle_log(root)
    if lifecycle_log.get("events") or lifecycle_log.get("findings"):
        sidecars["LIFECYCLE_LOG"] = lifecycle_log
    return sidecars


def _tasks_by_id(sidecars: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    content = _content(sidecars, "TASK_REGISTRY")
    tasks = content.get("tasks")
    result: dict[str, dict[str, object]] = {}
    if isinstance(tasks, list):
        for task in tasks:
            if isinstance(task, dict) and isinstance(task.get("task_id"), str):
                result[task["task_id"]] = task
    return result


def _truthy_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    refs: list[str] = []
    for item in value:
        if isinstance(item, str) and not _is_none(item):
            refs.append(item.strip())
    return refs


def _active_blockers(project_state: dict[str, object], next_action: dict[str, object]) -> list[str]:
    blockers: list[str] = []
    for key in ("active_blockers", "checkpoint_blocked_by"):
        value = project_state.get(key)
        if isinstance(value, list):
            blockers.extend(str(item).strip() for item in value if not _is_none(item))
    value = next_action.get("blocked_by")
    if isinstance(value, list):
        blockers.extend(str(item).strip() for item in value if not _is_none(item))
    return sorted(set(blocker for blocker in blockers if blocker))


def _has_incident(project_state: dict[str, object], blockers: list[str]) -> bool:
    values = [
        _as_text(project_state.get("current_phase")),
        _as_text(project_state.get("project_status")),
    ]
    values.extend(_as_text(blocker) for blocker in blockers)
    joined = " ".join(values).lower()
    return any(marker.lower() in joined for marker in INCIDENT_MARKERS)


def _has_owner_or_gap_blocker(blockers: list[str]) -> bool:
    joined = " ".join(blockers).lower()
    return any(token in joined for token in ("gap", "owner", "decision", "question"))


def _accepted_artifact_audit_refs(sidecars: dict[str, dict[str, object]], task_id: str) -> list[str]:
    accepted = _content(sidecars, "ACCEPTED_ARTIFACTS")
    artifacts = accepted.get("artifacts")
    refs: list[str] = []
    if not isinstance(artifacts, list):
        return refs
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        if artifact.get("source_task") != task_id and artifact.get("task_id") != task_id:
            continue
        audit_ref = artifact.get("audit_ref")
        if isinstance(audit_ref, str) and not _is_none(audit_ref):
            refs.append(audit_ref.strip())
    return refs


def _current_gate_audit_evidence(sidecars: dict[str, dict[str, object]]) -> list[str]:
    refs: list[str] = []
    for item in _truthy_string_list(_content(sidecars, "CURRENT_GATE").get("gate_evidence")):
        if "audit" in item.lower():
            refs.append(item)
    return refs


def _audit_pass_evidence(
    root: Path,
    sidecars: dict[str, dict[str, object]],
    task: dict[str, object],
    task_id: str,
) -> dict[str, object]:
    task_status = _as_text(task.get("status"))
    task_audit_refs = _truthy_string_list(task.get("audit_refs"))
    artifact_audit_refs = _accepted_artifact_audit_refs(sidecars, task_id)
    current_gate_refs = _current_gate_audit_evidence(sidecars)
    audit_refs = [*task_audit_refs, *artifact_audit_refs, *current_gate_refs]
    parsed_evidence = result_parser.inspect_audit_references(root, audit_refs, task_id=task_id, strict=True)
    invalid_refs = parsed_evidence["invalid_refs"]
    unparsed_refs = parsed_evidence["unparsed_refs"]
    passed_refs = parsed_evidence["passed_refs"]
    present = bool(passed_refs) and not invalid_refs and not unparsed_refs
    return {
        "present": present,
        "task_status": task_status,
        "task_audit_refs": task_audit_refs,
        "accepted_artifact_audit_refs": artifact_audit_refs,
        "current_gate_audit_evidence_refs": current_gate_refs,
        "parsed_audit_results": parsed_evidence["parsed_refs"],
        "passed_audit_refs": passed_refs,
        "invalid_audit_results": invalid_refs,
        "unparsed_audit_refs": unparsed_refs,
    }


def _audit_fail_correction_route(
    root: Path,
    audit_evidence: dict[str, object],
    transition_evidence: dict[str, object],
) -> dict[str, object]:
    route = correction_routing.from_audit_inspection(root, audit_evidence.get("invalid_audit_results"))
    if route:
        return route
    return correction_routing.from_transition_evidence(root, transition_evidence)


def _rule(
    rules: dict[str, dict[str, object]],
    rule_id: str,
    message: str,
    evidence: str,
) -> dict[str, object]:
    rule = rules.get(rule_id, {})
    return {
        "rule_id": rule_id,
        "severity": rule.get("severity", "error"),
        "check_target": rule.get("check_target", ""),
        "expected_action": rule.get("expected_action", []),
        "message": message,
        "evidence": evidence,
    }


def _state_verify_blockers(
    rules: dict[str, dict[str, object]],
    verify_report: dict[str, object],
) -> list[dict[str, object]]:
    findings = verify_report.get("findings")
    if not isinstance(findings, list):
        return []
    blockers: list[dict[str, object]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        rule_id = finding.get("rule_id")
        if rule_id == "SIDECAR_CHECKPOINT_POLICY_INVALID":
            blockers.append(
                _rule(
                    rules,
                    "GOV-CHECKPOINT-AUDIT-GATE",
                    "Checkpoint planning is blocked until audit-pass evidence exists in state.",
                    str(finding.get("details", "")),
                )
            )
        elif str(finding.get("severity", "")) == "error":
            blockers.append(
                _rule(
                    rules,
                    "GOV-ACTION-SEMANTICS",
                    "Verified state has blocking findings; planner will not recommend a mutating action.",
                    f"{rule_id}: {finding.get('details', '')}",
                )
            )
    return blockers


def _workspace_relative_path(value: str) -> Path | None:
    if not value or value in NONE_VALUES:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def _placeholder_tz_blockers(
    root: Path,
    rules: dict[str, dict[str, object]],
    project_state: dict[str, object],
    next_action: dict[str, object],
) -> list[dict[str, object]]:
    candidates: list[Path] = []
    state_tz = _workspace_relative_path(_as_text(project_state.get("tz_path")))
    if state_tz is not None:
        candidates.append(state_tz)
    required_docs = next_action.get("required_project_docs")
    if isinstance(required_docs, list):
        for item in required_docs:
            if isinstance(item, str):
                relpath = _workspace_relative_path(item.strip())
                if relpath is not None:
                    candidates.append(relpath)
    candidates.extend(BOOTSTRAP_INPUTS)

    blockers: list[dict[str, object]] = []
    seen: set[str] = set()
    for relpath in candidates:
        relpath_text = relpath.as_posix()
        if relpath_text in seen or not (root / relpath).is_file():
            continue
        seen.add(relpath_text)
        placeholder, detail = state_init.tz_placeholder_status(root, relpath)
        if placeholder:
            blockers.append(
                _rule(
                    rules,
                    "GOV-ACTION-SEMANTICS",
                    "Placeholder TZ input cannot be used for lifecycle planning.",
                    detail,
                )
            )
    return blockers


def _dedupe_rules(blockers: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[tuple[object, object]] = set()
    deduped: list[dict[str, object]] = []
    for blocker in blockers:
        key = (blocker.get("rule_id"), blocker.get("evidence"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(blocker)
    return deduped


def _transition_engine_evidence(sidecars: dict[str, dict[str, object]]) -> dict[str, object]:
    try:
        contract = transition_engine.load_runtime_contract()
        return transition_engine.explain_next_action_from_sidecars(contract, sidecars).to_json()
    except (OSError, transition_engine.RuntimeContractError) as exc:
        return {
            "allowed": False,
            "findings": [
                {
                    "rule_id": "RUNTIME_CONTRACT_LOAD_FAILED",
                    "severity": "error",
                    "message": "Runtime contract could not be loaded.",
                    "evidence": str(exc),
                    "recommendation": "Restore ORCHESTRATOR_RUNTIME_CONTRACT.json before routing.",
                }
            ],
            "reference_docs_used": [transition_engine.CONTRACT_RELATIVE_PATH.as_posix()],
        }


def _is_checkpoint_attempt(next_action: dict[str, object]) -> bool:
    return next_action.get("checkpoint_policy") in CHECKPOINT_PREFLIGHT_POLICIES


def _reason(reason_code: str, message: str, input_ref: str) -> dict[str, object]:
    return {
        "reason_code": reason_code,
        "message": message,
        "input_ref": input_ref,
    }


def _gate_check(
    checks: list[dict[str, object]],
    reasons: list[dict[str, object]],
    check_id: str,
    passed: bool,
    reason_code: str,
    evidence: str,
    message: str,
    input_ref: str,
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "passed": passed,
            "severity": "info" if passed else "error",
            "reason_code": "none" if passed else reason_code,
            "evidence": evidence,
        }
    )
    if not passed:
        reasons.append(_reason(reason_code, message, input_ref))


def _role_class(target_role: str) -> str:
    role = _normalize_profile_role(target_role).lower()
    if role in CONTROL_OR_PSEUDO_ROLES or _is_none(role):
        return "control_or_pseudo"
    if role in PROFILE_EXECUTION_ROLES:
        return "profile_execution"
    if role in LIFECYCLE_SYSTEM_ROLES:
        return "unknown"
    return "unknown"


def _normalize_profile_role(role: str) -> str:
    normalized = role.strip()
    return DEPRECATED_PROFILE_ROLE_ALIASES.get(normalized, normalized)


def _action_class(action_type: str, target_role: str) -> str:
    if action_type == "create_agent" and target_role == "auditor":
        return "audit_dispatch"
    if action_type == "create_agent":
        return "dispatch"
    if action_type == "correction":
        return "internal_correction"
    if action_type == "update_state":
        return "state_update"
    if action_type == "wait_for_owner":
        return "owner_wait"
    if action_type == "route_result":
        return "result_routing"
    if action_type == "finalize":
        return "finalization"
    if action_type == "stop":
        return "terminal_stop"
    return "unknown"


def _non_dispatch_status(action_type: str, recommended_next_action: str) -> str:
    if recommended_next_action == "ASK_OWNER" or action_type == "wait_for_owner":
        return "owner_input_required"
    if recommended_next_action == "FREEZE":
        return "frozen"
    if recommended_next_action == "BOOTSTRAP_PREP":
        return "bootstrap_required"
    if recommended_next_action == "STOP" or action_type == "stop":
        return "stopped"
    if recommended_next_action == "CORRECTION_REQUIRED" or action_type == "correction":
        return "correction_required"
    return "blocked"


def _task_packet_path(root: Path, task_packet: str) -> Path | None:
    if _is_none(task_packet):
        return None
    relpath = Path(task_packet)
    if relpath.is_absolute() or ".." in relpath.parts:
        return None
    return root / relpath


def _read_task_packet_fields(root: Path, task_packet: str) -> tuple[dict[str, str], str]:
    path = _task_packet_path(root, task_packet)
    if path is None:
        return {}, "task packet path is empty, absolute, or escapes the workspace"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, str(exc)
    fields: dict[str, str] = {}
    for match in re.finditer(r"^([A-Z][A-Z0-9_]*):\s*(.*?)\s*$", text, flags=re.MULTILINE):
        fields.setdefault(match.group(1), match.group(2))
    return fields, ""


def _task_packet_exists(root: Path, task_packet: str) -> bool:
    path = _task_packet_path(root, task_packet)
    return path is not None and path.is_file()


def _task_packet_dispatch_valid(
    root: Path,
    task_packet: str,
    task_id: str,
    target_role: str,
) -> tuple[bool, str]:
    fields, error = _read_task_packet_fields(root, task_packet)
    if error:
        return False, error
    missing = sorted(TASK_PACKET_REQUIRED_FIELDS - set(fields))
    if missing:
        return False, f"missing task packet fields: {', '.join(missing)}"
    if fields.get("TASK_ID") != task_id:
        return False, f"TASK_ID={fields.get('TASK_ID', '') or 'NONE'} does not match NEXT_ACTION task_id={task_id}"
    packet_role = fields.get("TARGET_ROLE", "")
    if packet_role not in PROFILE_EXECUTION_ROLES:
        return False, f"TARGET_ROLE={packet_role or 'NONE'} is not a profile execution role"
    target_role = _normalize_profile_role(target_role)
    packet_role = _normalize_profile_role(packet_role)
    if packet_role != target_role:
        return False, f"TARGET_ROLE={fields.get('TARGET_ROLE', '') or 'NONE'} does not match normalized target_role={target_role}"
    if target_role == "auditor" and fields.get("TASK_KIND") != "audit":
        return False, f"TASK_KIND={fields.get('TASK_KIND', '') or 'NONE'} is not an audit task packet"
    return True, "task packet has dispatch identity fields"


def _safe_runtime_contract() -> dict[str, Any]:
    try:
        return transition_engine.load_runtime_contract()
    except (OSError, transition_engine.RuntimeContractError):
        return {}


def _level_rank(level: str) -> int:
    return dispatch_receipts.LEVEL_RANK.get(level, -1)


def _reasoning_resolution(
    target_role: str,
    packet_fields: dict[str, str],
) -> dict[str, object]:
    contract = _safe_runtime_contract()
    target_role = _normalize_profile_role(target_role)
    reasoning_by_role = contract.get("reasoning_floor_by_role")
    role_floor = ""
    if isinstance(reasoning_by_role, dict):
        role_value = reasoning_by_role.get(target_role)
        if isinstance(role_value, str):
            role_floor = role_value.strip()
    complexity = packet_fields.get("TASK_COMPLEXITY", "").strip()
    complexity_floor = TASK_COMPLEXITY_FLOORS.get(complexity, "")
    packet_required = packet_fields.get("REASONING_LEVEL_REQUIRED", "").strip()

    candidates: list[tuple[int, int, str, str]] = []
    for priority, source, level in (
        (1, "runtime_contract.reasoning_floor_by_role", role_floor),
        (2, "task_packet.TASK_COMPLEXITY", complexity_floor),
        (3, "task_packet.REASONING_LEVEL_REQUIRED", packet_required),
    ):
        rank = _level_rank(level)
        if rank >= 0:
            candidates.append((rank, priority, level, source))
    if candidates:
        _, _, resolved, source = max(candidates)
    else:
        resolved = "NONE"
        source = "unresolved"
    return {
        "resolved_reasoning_level": resolved,
        "reasoning_source": source,
        "reasoning_inputs": {
            "role": target_role or "NONE",
            "role_floor": role_floor or "NONE",
            "task_complexity": complexity or "NONE",
            "task_complexity_floor": complexity_floor or "NONE",
            "task_packet_required": packet_required or "NONE",
        },
    }


def _bootstrap_reasoning_fields_present(task_packet: str, packet_fields: dict[str, str]) -> tuple[bool, str]:
    is_bootstrap = task_packet.startswith("project-runtime/bootstrap/")
    if not is_bootstrap:
        return True, "non-bootstrap task packet; bootstrap-only metadata check not applicable"
    missing = sorted(field for field in BOOTSTRAP_TASK_PACKET_REQUIRED_FIELDS if _is_none(packet_fields.get(field)))
    if missing:
        return False, f"missing bootstrap task packet fields: {', '.join(missing)}"
    return True, "bootstrap task packet includes reasoning, lifecycle, result, evidence, and artifact metadata"


def _task_registry_compatible(
    task: dict[str, object],
    task_id: str,
    task_packet: str,
    target_role: str,
    packet_fields: dict[str, str],
) -> tuple[bool, str]:
    if not task:
        return False, f"TASK_REGISTRY has no entry for task_id={task_id or 'NONE'}"
    if _as_text(task.get("task_id")) not in {"", task_id}:
        return False, f"registry task_id={task.get('task_id')} does not match NEXT_ACTION task_id={task_id}"
    registry_packet = _as_text(task.get("task_packet"))
    if registry_packet and registry_packet != task_packet:
        return False, f"registry task_packet={registry_packet} does not match NEXT_ACTION task_packet={task_packet}"
    if packet_fields:
        registry_kind = _as_text(task.get("task_kind"))
        packet_kind = packet_fields.get("TASK_KIND", "")
        if registry_kind and packet_kind and registry_kind != packet_kind:
            return False, f"registry task_kind={registry_kind} does not match packet TASK_KIND={packet_kind}"
    compatible_roles = {
        _normalize_profile_role(_as_text(task.get("task_type"))),
        _normalize_profile_role(_as_text(task.get("owner_role"))),
    }
    target_role = _normalize_profile_role(target_role)
    if target_role not in compatible_roles:
        return False, f"registry roles={sorted(role for role in compatible_roles if role)} do not include normalized target_role={target_role}"
    return True, "registry entry matches NEXT_ACTION and task packet"


def _current_gate_permits_dispatch(
    current_gate: dict[str, object],
    task_id: str,
    task_packet: str,
    target_role: str,
    audit_route_required: bool,
) -> tuple[bool, str]:
    status = _as_text(current_gate.get("status"))
    if status not in {"open", "passed"}:
        return False, f"CURRENT_GATE.content.status={status or 'NONE'}"
    gate_task_id = _as_text(current_gate.get("task_id"))
    if not _is_none(gate_task_id) and gate_task_id != task_id:
        return False, f"CURRENT_GATE.content.task_id={gate_task_id} does not match NEXT_ACTION task_id={task_id}"
    gate_task_packet = _as_text(current_gate.get("task_packet"))
    if not _is_none(gate_task_packet) and gate_task_packet != task_packet:
        return False, f"CURRENT_GATE.content.task_packet={gate_task_packet} does not match NEXT_ACTION task_packet={task_packet}"
    required_next_role = _normalize_profile_role(_as_text(current_gate.get("required_next_role")))
    target_role = _normalize_profile_role(target_role)
    if (
        not _is_none(required_next_role)
        and required_next_role != target_role
    ):
        return False, f"CURRENT_GATE.content.required_next_role={required_next_role} does not match target_role={target_role}"
    if target_role == "auditor" and not audit_route_required:
        return False, "auditor dispatch recommendation is only valid when an audit route is required"
    return True, f"CURRENT_GATE.content.status={status}; task and role are compatible"


def _workspace_identity_ready(project_state: dict[str, object], next_action: dict[str, object]) -> tuple[bool, str]:
    status = _as_text(project_state.get("identity_validation_status"))
    if status not in PROJECT_STATE_IDENTITY_STATUSES:
        return False, f"PROJECT_STATE.content.identity_validation_status={status or 'NONE'} is invalid"
    if next_action.get("workspace_identity_required") is False:
        return True, "NEXT_ACTION.content.workspace_identity_required=false"
    return (
        status in PROJECT_STATE_READY_IDENTITY_STATUSES,
        f"PROJECT_STATE.content.identity_validation_status={status or 'NONE'}",
    )


def _repository_lock_ready(project_state: dict[str, object], next_action: dict[str, object]) -> tuple[bool, str]:
    status = _as_text(project_state.get("repository_lock_status"))
    if status not in PROJECT_STATE_REPOSITORY_LOCK_STATUSES:
        return False, f"PROJECT_STATE.content.repository_lock_status={status or 'NONE'} is invalid"
    if next_action.get("repository_lock_required") is False:
        return True, "NEXT_ACTION.content.repository_lock_required=false"
    return (
        status in PROJECT_STATE_READY_REPOSITORY_LOCK_STATUSES,
        f"PROJECT_STATE.content.repository_lock_status={status or 'NONE'}",
    )


def _baseline_ready(root: Path, project_state: dict[str, object]) -> tuple[bool, str]:
    status = _as_text(project_state.get("baseline_tracking_status"))
    if status in PROJECT_STATE_READY_BASELINE_STATUSES:
        return True, f"PROJECT_STATE.content.baseline_tracking_status={status}"
    if project_state.get("current_phase") == "bootstrap" and not _first_dispatch_recorded(root):
        return True, "first-bootstrap exception: no agent_task_dispatched record exists"
    return False, f"PROJECT_STATE.content.baseline_tracking_status={status or 'NONE'}"


def _non_dispatch_recommendation(action_type: str) -> str:
    if action_type == "create_agent":
        return "CORRECTION_REQUIRED"
    return NON_DISPATCH_ACTION_TYPES.get(action_type, "ASK_OWNER")


def can_dispatch_agent(
    root: Path,
    action_type: str,
    target_role: str,
    task_id: str,
    task_packet: str,
    next_action: dict[str, object],
    project_state: dict[str, object],
    current_gate: dict[str, object],
    task: dict[str, object],
    blocking_rules: list[dict[str, object]],
) -> dict[str, object]:
    """Evaluate the single P5.4 dry-run dispatchability gate."""

    target_role = _normalize_profile_role(target_role)
    checks: list[dict[str, object]] = []
    reasons: list[dict[str, object]] = []

    _gate_check(
        checks,
        reasons,
        "DG54_ACTION_TYPE_DISPATCH_CAPABLE",
        action_type == "create_agent",
        "action_type_not_dispatch_capable",
        f"NEXT_ACTION.content.action_type={action_type or 'NONE'}",
        f"{action_type or 'NONE'} is not a dispatch-capable action type",
        "NEXT_ACTION.content.action_type",
    )
    _gate_check(
        checks,
        reasons,
        "DG54_TARGET_ROLE_PROFILE_EXECUTION",
        target_role in PROFILE_EXECUTION_ROLES,
        "target_role_not_profile_execution",
        f"NEXT_ACTION.content.target_role={target_role or 'NONE'}",
        f"{target_role or 'NONE'} is not a profile execution role",
        "NEXT_ACTION.content.target_role",
    )
    _gate_check(
        checks,
        reasons,
        "DG54_TARGET_ROLE_NOT_CONTROL",
        target_role.lower() not in CONTROL_OR_PSEUDO_ROLES and not _is_none(target_role),
        "target_role_control_or_pseudo",
        f"NEXT_ACTION.content.target_role={target_role or 'NONE'}",
        f"{target_role or 'NONE'} is a control or pseudo role",
        "NEXT_ACTION.content.target_role",
    )
    _gate_check(
        checks,
        reasons,
        "DG54_TASK_ID_PRESENT",
        not _is_none(task_id),
        "task_id_none",
        f"NEXT_ACTION.content.task_id={task_id or 'NONE'}",
        "NEXT_ACTION task_id is absent or NONE",
        "NEXT_ACTION.content.task_id",
    )
    _gate_check(
        checks,
        reasons,
        "DG54_TASK_PACKET_PRESENT",
        not _is_none(task_packet),
        "task_packet_none",
        f"NEXT_ACTION.content.task_packet={task_packet or 'NONE'}",
        "NEXT_ACTION task_packet is absent or NONE",
        "NEXT_ACTION.content.task_packet",
    )

    packet_exists = _task_packet_exists(root, task_packet)
    _gate_check(
        checks,
        reasons,
        "DG54_TASK_PACKET_EXISTS",
        packet_exists,
        "task_packet_missing",
        f"NEXT_ACTION.content.task_packet={task_packet or 'NONE'}",
        "Referenced task packet file does not exist",
        "NEXT_ACTION.content.task_packet",
    )

    packet_fields: dict[str, str] = {}
    packet_valid = False
    packet_valid_evidence = "task packet was not read because the path is absent"
    if packet_exists:
        packet_fields, _ = _read_task_packet_fields(root, task_packet)
        packet_valid, packet_valid_evidence = _task_packet_dispatch_valid(root, task_packet, task_id, target_role)
    _gate_check(
        checks,
        reasons,
        "DG54_TASK_PACKET_DISPATCH_VALID",
        packet_valid,
        "task_packet_not_dispatch_valid",
        packet_valid_evidence,
        "Referenced task packet is not valid for dispatch",
        "NEXT_ACTION.content.task_packet",
    )

    reasoning = _reasoning_resolution(target_role, packet_fields)
    _gate_check(
        checks,
        reasons,
        "DG54_REASONING_FLOOR_RESOLVED",
        str(reasoning["resolved_reasoning_level"]) in dispatch_receipts.LEVEL_RANK,
        "reasoning_floor_unresolved",
        json.dumps(reasoning, sort_keys=True),
        "Dispatch reasoning floor could not be resolved from the runtime contract and task packet",
        "ORCHESTRATOR_RUNTIME_CONTRACT.reasoning_floor_by_role",
    )
    bootstrap_fields_present, bootstrap_fields_evidence = _bootstrap_reasoning_fields_present(task_packet, packet_fields)
    _gate_check(
        checks,
        reasons,
        "DG54_BOOTSTRAP_REASONING_FIELDS_PRESENT",
        bootstrap_fields_present,
        "bootstrap_reasoning_fields_missing",
        bootstrap_fields_evidence,
        "Bootstrap task packet lacks required dispatch reasoning, lifecycle, result, evidence, or artifact metadata",
        "NEXT_ACTION.content.task_packet",
    )

    registry_compatible, registry_evidence = _task_registry_compatible(
        task,
        task_id,
        task_packet,
        target_role,
        packet_fields,
    )
    _gate_check(
        checks,
        reasons,
        "DG54_TASK_REGISTRY_COMPATIBLE",
        registry_compatible,
        "task_registry_incompatible",
        registry_evidence,
        "Task registry entry is missing or incompatible with the dispatch candidate",
        "TASK_REGISTRY.content.tasks[task_id]",
    )

    gate_permits, gate_evidence = _current_gate_permits_dispatch(
        current_gate,
        task_id,
        task_packet,
        target_role,
        _is_checkpoint_attempt(next_action),
    )
    _gate_check(
        checks,
        reasons,
        "DG54_CURRENT_GATE_PERMITS_DISPATCH",
        gate_permits,
        "current_gate_blocks_dispatch",
        gate_evidence,
        "Current gate does not permit dispatch",
        "CURRENT_GATE.content.status",
    )

    _gate_check(
        checks,
        reasons,
        "DG54_NO_BLOCKING_RULES",
        not blocking_rules,
        "blocking_rules_present",
        f"blocking_rules={len(blocking_rules)}",
        "Blocking rules prevent dispatch",
        "plan-next.blocking_rules",
    )

    identity_ready, identity_evidence = _workspace_identity_ready(project_state, next_action)
    _gate_check(
        checks,
        reasons,
        "DG54_WORKSPACE_IDENTITY_READY",
        identity_ready,
        "workspace_identity_not_ready",
        identity_evidence,
        "Workspace identity is not ready for dispatch",
        "PROJECT_STATE.content.identity_validation_status",
    )

    lock_ready, lock_evidence = _repository_lock_ready(project_state, next_action)
    _gate_check(
        checks,
        reasons,
        "DG54_REPOSITORY_LOCK_READY",
        lock_ready,
        "repository_lock_not_ready",
        lock_evidence,
        "Repository lock is not ready for dispatch",
        "PROJECT_STATE.content.repository_lock_status",
    )

    baseline_ready, baseline_evidence = _baseline_ready(root, project_state)
    _gate_check(
        checks,
        reasons,
        "DG54_BASELINE_READY_OR_BOOTSTRAP_EXCEPTION",
        baseline_ready,
        "baseline_not_ready",
        baseline_evidence,
        "Baseline tracking is not ready and no bootstrap exception applies",
        "PROJECT_STATE.content.baseline_tracking_status",
    )

    dispatchable = all(bool(check["passed"]) for check in checks)
    if dispatchable:
        recommended_next_action = "CREATE_AUDITOR" if target_role == "auditor" else "CREATE_AGENT"
        status = "ready"
    else:
        recommended_next_action = _non_dispatch_recommendation(action_type)
        status = "blocked" if action_type == "create_agent" else _non_dispatch_status(action_type, recommended_next_action)

    return {
        "contract_id": "ASO_PLANNER_DISPATCHABILITY_GATE_P5_4",
        "contract_version": "1.0.0",
        "dispatchable": dispatchable,
        "verdict": "dispatchable" if dispatchable else "not_dispatchable",
        "recommended_next_action": recommended_next_action,
        "status": status,
        "target_role": target_role or "NONE",
        "role_class": _role_class(target_role),
        "action_type": action_type or "NONE",
        "action_class": _action_class(action_type, target_role),
        "task_id": task_id or "NONE",
        "task_packet": task_packet or "NONE",
        "checks": checks,
        "reasons": reasons,
        "live_dispatch_performed": False,
        "resolved_reasoning_level": reasoning["resolved_reasoning_level"],
        "reasoning_source": reasoning["reasoning_source"],
        "reasoning_inputs": reasoning["reasoning_inputs"],
        "dispatch_receipt_required": dispatchable,
        "dispatch_receipt_schema_ref": dispatch_receipts.SCHEMA_RELATIVE_PATH,
        "dispatch_receipt_ref_template": dispatch_receipts.RECEIPT_REF_TEMPLATE,
        "handoff_artifact_schema_ref": handoff_artifacts.SCHEMA_RELATIVE_PATH,
        "handoff_ref_template": handoff_artifacts.HANDOFF_REF_TEMPLATE,
        "prompt_ref_template": handoff_artifacts.PROMPT_REF_TEMPLATE,
        "external_runner_command_template": dispatch_receipts.EXTERNAL_RUNNER_COMMAND_TEMPLATE,
        "receipt_writer_command_template": dispatch_receipts.WRITER_COMMAND_TEMPLATE,
        "runner_semantics": dispatch_receipts.RUNNER_SEMANTICS,
    }


def _non_dispatchability(
    action_type: str,
    target_role: str,
    task_id: str,
    task_packet: str,
    recommended_next_action: str,
    status: str,
    reasons: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "contract_id": "ASO_PLANNER_DISPATCHABILITY_GATE_P5_4",
        "contract_version": "1.0.0",
        "dispatchable": False,
        "verdict": "not_dispatchable",
        "recommended_next_action": recommended_next_action,
        "status": status,
        "target_role": target_role or "NONE",
        "role_class": _role_class(target_role),
        "action_type": action_type or "NONE",
        "action_class": _action_class(action_type, target_role),
        "task_id": task_id or "NONE",
        "task_packet": task_packet or "NONE",
        "checks": [
            {
                "check_id": "DG54_ACTION_TYPE_DISPATCH_CAPABLE",
                "passed": False,
                "severity": "info",
                "reason_code": "action_type_not_dispatch_capable",
                "evidence": f"plan-next recommended non-dispatch route {recommended_next_action}",
            }
        ],
        "reasons": reasons
        or [
            _reason(
                "action_type_not_dispatch_capable",
                f"{recommended_next_action} is a non-dispatch planner route",
                "plan-next.recommended_next_action",
            )
        ],
        "live_dispatch_performed": False,
        "resolved_reasoning_level": "NONE",
        "reasoning_source": "not_dispatchable",
        "reasoning_inputs": {},
        "dispatch_receipt_required": False,
        "dispatch_receipt_schema_ref": dispatch_receipts.SCHEMA_RELATIVE_PATH,
        "dispatch_receipt_ref_template": dispatch_receipts.RECEIPT_REF_TEMPLATE,
        "handoff_artifact_schema_ref": handoff_artifacts.SCHEMA_RELATIVE_PATH,
        "handoff_ref_template": handoff_artifacts.HANDOFF_REF_TEMPLATE,
        "prompt_ref_template": handoff_artifacts.PROMPT_REF_TEMPLATE,
        "external_runner_command_template": dispatch_receipts.EXTERNAL_RUNNER_COMMAND_TEMPLATE,
        "receipt_writer_command_template": dispatch_receipts.WRITER_COMMAND_TEMPLATE,
        "runner_semantics": dispatch_receipts.RUNNER_SEMANTICS,
    }


def _bootstrap_inputs_present(root: Path) -> bool:
    return any((root / relpath).is_file() for relpath in BOOTSTRAP_INPUTS)


def _first_dispatch_recorded(root: Path) -> bool:
    instances_path = root / "project-runtime" / "agents" / "instances.jsonl"
    try:
        text = instances_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "agent_task_dispatched" in text


def _needs_bootstrap_reconciliation(
    root: Path,
    project_state: dict[str, object],
    current_gate: dict[str, object],
    next_action: dict[str, object],
) -> bool:
    terminal_next_action = (
        next_action.get("action_semantic") == "stop_terminal"
        or next_action.get("action_type") == "stop"
    )
    return (
        project_state.get("current_phase") == "bootstrap"
        and project_state.get("project_status") == "active"
        and current_gate.get("status") == "open"
        and terminal_next_action
        and _bootstrap_inputs_present(root)
        and not _first_dispatch_recorded(root)
    )


def _plan(
    root: Path,
    strict: bool,
    verify_report: dict[str, object],
    verify_exit_code: int,
    sidecars: dict[str, dict[str, object]],
    rules: dict[str, dict[str, object]],
    rules_evidence: dict[str, object],
) -> dict[str, object]:
    project_state = _content(sidecars, "PROJECT_STATE")
    current_gate = _content(sidecars, "CURRENT_GATE")
    next_action = _content(sidecars, "NEXT_ACTION")
    tasks = _tasks_by_id(sidecars)
    task_id = _as_text(next_action.get("task_id"))
    task = tasks.get(task_id, {})
    action_type = _as_text(next_action.get("action_type"))
    dependency_status = _as_text(next_action.get("dependency_status"))
    target_role = _as_text(next_action.get("target_role"))
    task_packet = _as_text(next_action.get("task_packet"))
    blockers = _active_blockers(project_state, next_action)
    audit_evidence = _audit_pass_evidence(root, sidecars, task, task_id)

    blocking_rules = _state_verify_blockers(rules, verify_report)
    blocking_rules.extend(_placeholder_tz_blockers(root, rules, project_state, next_action))
    recommended_next_action = "NONE"
    dispatchability: dict[str, object] = _non_dispatchability(
        action_type,
        target_role,
        task_id,
        task_packet,
        "NONE",
        "blocked",
    )
    transition_evidence = _transition_engine_evidence(sidecars)
    transition_selected = transition_evidence.get("transition_selected")
    derived_next_action = transition_evidence.get("next_action")
    correction_route: dict[str, object] = {}
    lifecycle_derived = (
        isinstance(transition_selected, dict)
        and transition_selected.get("derivation") == "lifecycle_log"
        and isinstance(derived_next_action, dict)
    )
    routing_next_action = dict(next_action)

    if rules_evidence.get("load_error"):
        blocking_rules.append(
            _rule(
                rules,
                "GOV-ACTION-SEMANTICS",
                "Governance rule registry could not be loaded.",
                str(rules_evidence["load_error"]),
            )
        )

    if _has_incident(project_state, blockers):
        recommended_next_action = "FREEZE"
        dispatchability = _non_dispatchability(
            action_type,
            target_role,
            task_id,
            task_packet,
            recommended_next_action,
            "frozen",
        )
        blocking_rules.append(
            _rule(
                rules,
                "GOV-ACTION-SEMANTICS",
                "Incident or recovery state freezes normal dispatch and checkpoint planning.",
                ", ".join(blockers) or _as_text(project_state.get("current_phase")),
            )
        )
    elif _has_owner_or_gap_blocker(blockers) or dependency_status == "blocked":
        recommended_next_action = "ASK_OWNER"
        dispatchability = _non_dispatchability(
            action_type,
            target_role,
            task_id,
            task_packet,
            recommended_next_action,
            "owner_input_required",
        )
        blocking_rules.append(
            _rule(
                rules,
                "GOV-ACTION-SEMANTICS",
                "Blocked owner/GAP state requires owner-facing routing before dependent work continues.",
                ", ".join(blockers) or dependency_status,
            )
        )
    elif _needs_bootstrap_reconciliation(root, project_state, current_gate, next_action):
        recommended_next_action = "BOOTSTRAP_PREP"
        target_role = "orchestrator"
        dispatchability = _non_dispatchability(
            action_type,
            target_role,
            task_id,
            task_packet,
            recommended_next_action,
            "bootstrap_required",
        )
        blocking_rules.append(
            _rule(
                rules,
                "GOV-ACTION-SEMANTICS",
                "Active/open bootstrap with mandatory inputs cannot route to terminal STOP before first dispatch.",
                "route=repair_bootstrap_state/create_or_reference_bootstrap_task_packet",
            )
        )
    elif lifecycle_derived and isinstance(derived_next_action, dict):
        routing_next_action.update(derived_next_action)
        action_type = _as_text(routing_next_action.get("action_type"))
        target_role = _as_text(routing_next_action.get("target_role"))
        task_id = _as_text(routing_next_action.get("task_id")) or task_id
        task_packet = _as_text(routing_next_action.get("task_packet")) or task_packet
        task = tasks.get(task_id, {})
        audit_evidence = _audit_pass_evidence(root, sidecars, task, task_id)
        recommended_next_action = (
            _as_text(derived_next_action.get("recommended_next_action"))
            or transition_engine.recommendation_from_next_action_content(routing_next_action)
        )
        if recommended_next_action == "CORRECTION_REQUIRED":
            correction_route = _audit_fail_correction_route(root, audit_evidence, transition_evidence)
        if action_type == "create_agent":
            dispatchability = can_dispatch_agent(
                root,
                action_type,
                target_role,
                task_id,
                task_packet,
                routing_next_action,
                project_state,
                current_gate,
                task,
                blocking_rules,
            )
            target_role = str(dispatchability["target_role"])
        else:
            dispatchability = _non_dispatchability(
                action_type,
                target_role,
                task_id,
                task_packet,
                recommended_next_action,
                _non_dispatch_status(action_type, recommended_next_action),
            )
    elif _is_checkpoint_attempt(next_action):
        if audit_evidence["present"]:
            recommended_next_action = "CHECKPOINT_PREFLIGHT"
            dispatchability = _non_dispatchability(
                action_type,
                target_role,
                task_id,
                task_packet,
                recommended_next_action,
                "blocked",
            )
        else:
            correction_route = _audit_fail_correction_route(root, audit_evidence, transition_evidence)
            if correction_route:
                recommended_next_action = "CORRECTION_REQUIRED"
                target_role = "orchestrator"
                dispatchability = _non_dispatchability(
                    "correction",
                    target_role,
                    task_id,
                    "NONE",
                    recommended_next_action,
                    "correction_required",
                    reasons=[
                        _reason(
                            "audit_result_status_fail",
                            "AUDIT_RESULT STATUS fail routes correction and blocks checkpoint preflight",
                            "TASK_REGISTRY.content.tasks[].audit_refs",
                        )
                    ],
                )
                blocking_rules.append(
                    _rule(
                        rules,
                        "GOV-AUDIT-FAIL-NO-CHECKPOINT",
                        "AUDIT_RESULT STATUS fail routes correction and blocks checkpoint preflight.",
                        str(correction_route.get("source_audit_result_ref", "NONE")),
                    )
                )
            else:
                target_role = "auditor"
                dispatchability = can_dispatch_agent(
                    root,
                    "create_agent",
                    target_role,
                    task_id,
                    task_packet,
                    next_action,
                    project_state,
                    current_gate,
                    task,
                    [],
                )
                recommended_next_action = str(dispatchability["recommended_next_action"])
                target_role = str(dispatchability["target_role"])
            blocking_rules.append(
                _rule(
                    rules,
                    "GOV-CHECKPOINT-AUDIT-GATE",
                    "Checkpoint preflight is blocked because audit-pass evidence is absent.",
                    f"task_id={task_id or 'NONE'}",
                )
            )
            if audit_evidence["invalid_audit_results"]:
                blocking_rules.append(
                    _rule(
                        rules,
                        "GOV-CHECKPOINT-AUDIT-GATE",
                        "Parsed AUDIT_RESULT evidence is not a pass for this task.",
                        json.dumps(audit_evidence["invalid_audit_results"], sort_keys=True),
                    )
                )
            if audit_evidence["unparsed_audit_refs"]:
                blocking_rules.append(
                    _rule(
                        rules,
                        "GOV-CHECKPOINT-AUDIT-GATE",
                        "AUDIT_RESULT evidence references are missing or unreadable.",
                        json.dumps(audit_evidence["unparsed_audit_refs"], sort_keys=True),
                    )
                )
    elif verify_exit_code != 0 and action_type != "create_agent":
        recommended_next_action = "NONE"
        dispatchability = _non_dispatchability(
            action_type,
            target_role,
            task_id,
            task_packet,
            recommended_next_action,
            "blocked",
        )
    elif action_type == "wait_for_owner":
        recommended_next_action = "ASK_OWNER"
        dispatchability = _non_dispatchability(
            action_type,
            target_role,
            task_id,
            task_packet,
            recommended_next_action,
            "owner_input_required",
        )
        blocking_rules.append(
            _rule(
                rules,
                "GOV-ACTION-SEMANTICS",
                "NEXT_ACTION requires owner-facing routing before dependent work continues.",
                f"action_type={action_type}",
            )
        )
    elif action_type in {"create_agent", "route_result", "update_state", "correction", "finalize", "stop"}:
        dispatchability = can_dispatch_agent(
            root,
            action_type,
            target_role,
            task_id,
            task_packet,
            next_action,
            project_state,
            current_gate,
            task,
            blocking_rules,
        )
        recommended_next_action = str(dispatchability["recommended_next_action"])
        target_role = str(dispatchability["target_role"])

    blocking_rules = _dedupe_rules(blocking_rules)
    if blocking_rules:
        status = "blocked"
    elif recommended_next_action == "CORRECTION_REQUIRED":
        status = str(dispatchability["status"])
    else:
        status = "ready"
    resolved_reasoning_level = str(dispatchability.get("resolved_reasoning_level") or "NONE")
    reasoning_source = str(dispatchability.get("reasoning_source") or "NONE")
    dispatch_receipt = dispatch_receipts.dispatch_receipt_plan(
        task_id=task_id,
        role=target_role,
        reasoning_effort=resolved_reasoning_level,
        required=bool(dispatchability.get("dispatchable")),
    )
    handoff_packet_fields: dict[str, str] = {}
    if task_packet:
        handoff_packet_fields, _ = _read_task_packet_fields(root, task_packet)
    handoff_artifact = handoff_artifacts.handoff_plan(
        contract=_safe_runtime_contract(),
        task_id=task_id,
        role=target_role,
        resolved_reasoning_level=resolved_reasoning_level,
        task_packet=task_packet,
        packet_fields=handoff_packet_fields,
        dispatchable=bool(dispatchability.get("dispatchable")),
    )
    return {
        "tool": "aso",
        "command": "plan-next",
        "mode": "workspace",
        "status": status,
        "root": str(root),
        "strict": strict,
        "dry_run": True,
        "read_only": True,
        "mutations_performed": False,
        "recommended_next_action": recommended_next_action,
        "dispatchable": bool(dispatchability.get("dispatchable")),
        "dispatchability": dispatchability,
        "target_role": target_role,
        "task_id": task_id,
        "task_packet": task_packet,
        "resolved_reasoning_level": resolved_reasoning_level,
        "reasoning_source": reasoning_source,
        "dispatch_receipt": dispatch_receipt,
        "handoff_artifact": handoff_artifact,
        "correction_routing": correction_route,
        "blocking_rules": blocking_rules,
        "evidence": {
            "state_verify": {
                "status": verify_report.get("status"),
                "summary": verify_report.get("summary"),
                "findings": verify_report.get("findings", []),
            },
            "governance_rules": rules_evidence,
            "project_state": {
                "current_phase": project_state.get("current_phase", ""),
                "project_status": project_state.get("project_status", ""),
                "identity_validation_status": project_state.get("identity_validation_status", ""),
                "repository_lock_status": project_state.get("repository_lock_status", ""),
                "checkpoint_eligibility": project_state.get("checkpoint_eligibility", ""),
                "active_blockers": blockers,
            },
            "next_action": {
                "action_type": action_type,
                "dependency_status": dependency_status,
                "action_semantic": next_action.get("action_semantic", ""),
                "checkpoint_policy": next_action.get("checkpoint_policy", ""),
                "blocked_by": next_action.get("blocked_by", []),
                "routing_source": "transition_engine" if lifecycle_derived else "stored",
                "stored_action_type": next_action.get("action_type", ""),
                "stored_target_role": next_action.get("target_role", ""),
                "routing_action_type": routing_next_action.get("action_type", ""),
                "routing_target_role": routing_next_action.get("target_role", ""),
            },
            "task": {
                "task_id": task_id,
                "status": task.get("status", ""),
                "result_refs": task.get("result_refs", []),
                "audit_refs": task.get("audit_refs", []),
            },
            "audit_pass_evidence": audit_evidence,
            "correction_routing": correction_route,
            "transition_engine": transition_evidence,
        },
    }


def _print_text(report: dict[str, object]) -> None:
    print(f"ASO plan-next: {str(report['status']).upper()} (dry-run/read-only)")
    print(f"Root: {report['root']}")
    print(f"Strict: {report['strict']}")
    print(f"Recommended next action: {report['recommended_next_action']}")
    print(f"Target role: {report['target_role'] or 'NONE'}")
    print(f"Task packet: {report['task_packet'] or 'NONE'}")
    print(f"Resolved reasoning level: {report.get('resolved_reasoning_level') or 'NONE'}")
    blocking_rules = report.get("blocking_rules", [])
    count = len(blocking_rules) if isinstance(blocking_rules, list) else 0
    print(f"Blocking rules: {count}")
    if isinstance(blocking_rules, list):
        for blocker in blocking_rules:
            if isinstance(blocker, dict):
                print(f"- {blocker.get('rule_id')}: {blocker.get('message')}")


def _write_json(path_text: str, report: dict[str, object]) -> bool:
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso plan-next: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso plan-next: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def _state_verify_findings(report: dict[str, object]) -> list[dict[str, object]]:
    evidence = report.get("evidence")
    if not isinstance(evidence, dict):
        return []
    state_verify_evidence = evidence.get("state_verify")
    if not isinstance(state_verify_evidence, dict):
        return []
    findings = state_verify_evidence.get("findings")
    return [dict(item) for item in findings if isinstance(item, dict)] if isinstance(findings, list) else []


def _has_invalid_state(report: dict[str, object]) -> bool:
    for finding in _state_verify_findings(report):
        if finding.get("severity") != "error":
            continue
        rule_id = str(finding.get("rule_id") or "")
        if rule_id in INVALID_STATE_RULE_IDS:
            return True
    return False


def _has_valid_correction_route(report: dict[str, object]) -> bool:
    if report.get("recommended_next_action") != "CORRECTION_REQUIRED":
        return False
    correction_route = report.get("correction_routing")
    if isinstance(correction_route, dict) and correction_route.get("route") == "CORRECTION_REQUIRED":
        return True
    dispatchability = report.get("dispatchability")
    if isinstance(dispatchability, dict) and dispatchability.get("action_type") == "correction":
        return report.get("status") == "correction_required"
    evidence = report.get("evidence")
    if isinstance(evidence, dict):
        next_action = evidence.get("next_action")
        if isinstance(next_action, dict) and next_action.get("routing_action_type") == "correction":
            return True
    return False


def _route_exit_contract(report: dict[str, object], verify_exit_code: int) -> tuple[str, bool, int]:
    if _has_invalid_state(report):
        return "invalid_state", True, EXIT_INVALID_STATE
    if verify_exit_code == state_verify.EXIT_IO_ERROR:
        return "runtime_error", True, EXIT_RUNTIME_ERROR
    if _has_valid_correction_route(report):
        return "ready", False, EXIT_OK
    if report.get("status") == "ready":
        return "ready", False, EXIT_OK
    return "governance_blocked", False, EXIT_BLOCKED


def run(args: argparse.Namespace) -> int:
    """Run the dry-run planner."""

    root = Path(args.root).expanduser()
    verify_report, verify_exit_code = state_verify._report(root, bool(args.strict))
    sidecars = _load_sidecars(root)
    rules, rules_evidence = _load_governance_rules(root)
    report = _plan(root, bool(args.strict), verify_report, verify_exit_code, sidecars, rules, rules_evidence)
    route_status, fatal, exit_code = _route_exit_contract(report, verify_exit_code)
    report["route_status"] = route_status
    report["fatal"] = fatal
    report["exit_code"] = exit_code
    _print_text(report)
    if args.json_out and not _write_json(str(args.json_out), report):
        return EXIT_RUNTIME_ERROR
    return exit_code
