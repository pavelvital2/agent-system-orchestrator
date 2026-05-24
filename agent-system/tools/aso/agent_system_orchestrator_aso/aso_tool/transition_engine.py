"""Canonical ASO runtime contract loader and transition engine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import resources
from . import runtime_contract_fallback


CONTRACT_RELATIVE_PATH = Path("agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json")
SCHEMA_RELATIVE_PATH = Path("agent-system/09_validators/schemas/orchestrator_runtime_contract.schema.json")
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}


class RuntimeContractError(ValueError):
    """Raised when the runtime contract cannot be loaded or validated."""


@dataclass(frozen=True)
class TransitionFinding:
    rule_id: str
    severity: str
    message: str
    evidence: str
    recommendation: str

    def to_json(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class ContractValidationResult:
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class TransitionDecision:
    inputs: dict[str, object]
    transition_selected: dict[str, object]
    findings: tuple[TransitionFinding, ...]
    next_action: dict[str, object]
    reference_docs_used: tuple[str, ...]
    allowed: bool
    current_state: str
    event: str
    next_state: str

    def to_json(self) -> dict[str, object]:
        return {
            "inputs": self.inputs,
            "transition_selected": self.transition_selected,
            "findings": [finding.to_json() for finding in self.findings],
            "next_action": self.next_action,
            "reference_docs_used": list(self.reference_docs_used),
            "allowed": self.allowed,
            "current_state": self.current_state,
            "event": self.event,
            "next_state": self.next_state,
        }


def _finding(
    rule_id: str,
    severity: str,
    message: str,
    evidence: str,
    recommendation: str,
) -> TransitionFinding:
    return TransitionFinding(rule_id, severity, message, evidence, recommendation)


def _is_none(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in NONE_VALUES)


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _contract_states(contract: Mapping[str, Any]) -> set[str]:
    transitions = _mapping(contract.get("state_transitions"))
    states = set(transitions)
    for event_map in transitions.values():
        if isinstance(event_map, Mapping):
            states.update(str(value) for value in event_map.values() if isinstance(value, str))
    states.update(_mapping(contract.get("next_actions_by_state")))
    states.update(_string_list(contract.get("terminal_states")))
    return states


def validate_runtime_contract(contract: Mapping[str, Any]) -> ContractValidationResult:
    """Validate the compact runtime contract with stdlib checks."""

    errors: list[str] = []
    required = (
        "contract_version",
        "package_version",
        "governance_ruleset_version",
        "runtime_schema_version",
        "artifact_package_schema_version",
        "allowed_roles",
        "forbidden_dispatch_roles",
        "allowed_events",
        "state_transitions",
        "forbidden_transitions",
        "next_actions_by_state",
        "required_docs_by_role",
        "reasoning_floor_by_role",
        "artifact_contracts",
        "audit_gate_rules",
        "checkpoint_rules",
        "routine_context_policy",
        "handoff_context_builder_contract",
    )
    for field in required:
        if field not in contract:
            errors.append(f"{field} is required")

    allowed_roles = _string_list(contract.get("allowed_roles"))
    forbidden_roles = _string_list(contract.get("forbidden_dispatch_roles"))
    allowed_events = _string_list(contract.get("allowed_events"))
    if not allowed_roles:
        errors.append("allowed_roles must contain at least one role")
    if not allowed_events:
        errors.append("allowed_events must contain at least one event")
    if len(set(allowed_roles)) != len(allowed_roles):
        errors.append("allowed_roles must not contain duplicates")
    if len(set(allowed_events)) != len(allowed_events):
        errors.append("allowed_events must not contain duplicates")
    if set(allowed_roles) & set(forbidden_roles):
        overlap = ", ".join(sorted(set(allowed_roles) & set(forbidden_roles)))
        errors.append(f"roles cannot be both allowed and forbidden for dispatch: {overlap}")

    transitions = _mapping(contract.get("state_transitions"))
    if not transitions:
        errors.append("state_transitions must be a non-empty object")
    states = _contract_states(contract)
    for from_state, event_map in transitions.items():
        if not isinstance(event_map, Mapping) or not event_map:
            errors.append(f"state_transitions.{from_state} must be a non-empty object")
            continue
        for event, to_state in event_map.items():
            if event not in allowed_events:
                errors.append(f"state_transitions.{from_state}.{event} is not in allowed_events")
            if not isinstance(to_state, str) or not to_state.strip():
                errors.append(f"state_transitions.{from_state}.{event} must name a target state")
            elif to_state not in states:
                errors.append(f"state_transitions.{from_state}.{event} targets unknown state {to_state}")

    next_actions = _mapping(contract.get("next_actions_by_state"))
    if not next_actions:
        errors.append("next_actions_by_state must be a non-empty object")
    for state, action in next_actions.items():
        action_map = _mapping(action)
        if not action_map:
            errors.append(f"next_actions_by_state.{state} must be an object")
            continue
        if not _text(action_map.get("recommended_next_action")):
            errors.append(f"next_actions_by_state.{state}.recommended_next_action is required")
        if not _text(action_map.get("action_type")):
            errors.append(f"next_actions_by_state.{state}.action_type is required")
        if not isinstance(action_map.get("dispatchable"), bool):
            errors.append(f"next_actions_by_state.{state}.dispatchable must be boolean")

    docs_by_role = _mapping(contract.get("required_docs_by_role"))
    reasoning_by_role = _mapping(contract.get("reasoning_floor_by_role"))
    for role in allowed_roles:
        if role not in docs_by_role:
            errors.append(f"required_docs_by_role missing role {role}")
        if role not in reasoning_by_role:
            errors.append(f"reasoning_floor_by_role missing role {role}")

    artifact_contracts = _mapping(contract.get("artifact_contracts"))
    if artifact_contracts.get("candidate_manifest_canonical") != "manifest.json":
        errors.append("artifact_contracts.candidate_manifest_canonical must be manifest.json")
    if artifact_contracts.get("accepted_manifest_canonical") != "manifest.json":
        errors.append("artifact_contracts.accepted_manifest_canonical must be manifest.json")

    routine_policy = _mapping(contract.get("routine_context_policy"))
    for field in (
        "orchestrator_must_read",
        "orchestrator_must_not_read_routinely",
        "reference_docs_allowed_only_for",
    ):
        if not isinstance(routine_policy.get(field), list):
            errors.append(f"routine_context_policy.{field} must be a list")

    handoff_context = _mapping(contract.get("handoff_context_builder_contract"))
    if handoff_context.get("normal_context_mode") != "routine":
        errors.append("handoff_context_builder_contract.normal_context_mode must be routine")
    allowed_context_modes = set(_string_list(handoff_context.get("allowed_context_modes")))
    for required_mode in ("routine", "debug", "explain", "violation_recovery"):
        if required_mode not in allowed_context_modes:
            errors.append(f"handoff_context_builder_contract.allowed_context_modes missing {required_mode}")
    for field in (
        "runtime_contract_required_sections",
        "routine_handoff_includes",
        "routine_handoff_excludes",
    ):
        if not isinstance(handoff_context.get(field), list) or not _string_list(handoff_context.get(field)):
            errors.append(f"handoff_context_builder_contract.{field} must be a non-empty list")
    if not _text(handoff_context.get("reference_doc_inclusion_rule")):
        errors.append("handoff_context_builder_contract.reference_doc_inclusion_rule is required")
    target_role_doc_map = _mapping(handoff_context.get("target_role_doc_map"))
    for role in allowed_roles:
        if role not in target_role_doc_map:
            errors.append(f"handoff_context_builder_contract.target_role_doc_map missing role {role}")

    return ContractValidationResult(tuple(errors))


def load_runtime_contract(contract_path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate the runtime contract from an explicit path or packaged resource."""

    if contract_path is None:
        try:
            resource = resources.read_resource_text(CONTRACT_RELATIVE_PATH, anchor_file=__file__)
            raw_text = resource.text
            origin = resource.origin
        except FileNotFoundError:
            raw_text = runtime_contract_fallback.ORCHESTRATOR_RUNTIME_CONTRACT_JSON
            origin = runtime_contract_fallback.ORIGIN
    else:
        path = Path(contract_path)
        raw_text = path.read_text(encoding="utf-8")
        origin = str(path)

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeContractError(f"{origin}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise RuntimeContractError(f"{origin}: runtime contract root must be an object")

    validation = validate_runtime_contract(payload)
    if not validation.passed:
        joined = "; ".join(validation.errors)
        raise RuntimeContractError(f"{origin}: invalid runtime contract: {joined}")
    return payload


load_contract = load_runtime_contract


def _reference_docs(contract: Mapping[str, Any], target_role: str) -> tuple[str, ...]:
    docs = [CONTRACT_RELATIVE_PATH.as_posix()]
    by_role = _mapping(contract.get("required_docs_by_role"))
    for doc in _string_list(by_role.get(target_role)):
        docs.append(doc)
    return tuple(dict.fromkeys(docs))


def _reasoning_floor(contract: Mapping[str, Any], target_role: str) -> str:
    floors = _mapping(contract.get("reasoning_floor_by_role"))
    value = floors.get(target_role)
    return value if isinstance(value, str) else ""


def _normalize_event(contract: Mapping[str, Any], event: object) -> str:
    status = ""
    raw_event: object = event
    if isinstance(event, Mapping):
        raw_event = event.get("event_type") or event.get("event") or event.get("type")
        status = _text(event.get("status") or event.get("result_status") or event.get("audit_status")).lower()

    event_text = _text(raw_event)
    aliases = _mapping(contract.get("event_aliases"))
    alias = aliases.get(event_text)
    if isinstance(alias, str):
        return alias
    if isinstance(alias, Mapping):
        resolved = alias.get(status)
        if isinstance(resolved, str):
            return resolved
    return event_text


def _state_from_input(current_state: object) -> str:
    if isinstance(current_state, str):
        return current_state.strip()
    if isinstance(current_state, Mapping):
        for key in ("contract_state", "state", "current_state", "lifecycle_state"):
            value = current_state.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def allowed_events_for_state(contract: Mapping[str, Any], current_state: object) -> list[str]:
    state = _state_from_input(current_state)
    event_map = _mapping(_mapping(contract.get("state_transitions")).get(state))
    return sorted(event_map)


def _forbidden_transition_findings(
    contract: Mapping[str, Any],
    current_state: str,
    event_name: str,
    *,
    same_task: bool,
) -> list[TransitionFinding]:
    findings: list[TransitionFinding] = []
    forbidden = contract.get("forbidden_transitions")
    if not isinstance(forbidden, list):
        return findings
    for item in forbidden:
        rule = _mapping(item)
        if current_state not in _string_list(rule.get("from_states")):
            continue
        if rule.get("event") != event_name:
            continue
        if rule.get("same_task") is True and not same_task:
            continue
        findings.append(
            _finding(
                "RUNTIME_TRANSITION_FORBIDDEN",
                "error",
                str(rule.get("reason") or "Transition is forbidden by the runtime contract."),
                f"from_state={current_state}; event={event_name}; same_task={str(same_task).lower()}",
                "Route through the canonical correction or audit/checkpoint path before continuing.",
            )
        )
    return findings


def _next_action_for_state(
    contract: Mapping[str, Any],
    state: str,
    *,
    target_role: str = "",
    task_id: str = "",
    task_packet: str = "",
) -> dict[str, object]:
    actions = _mapping(contract.get("next_actions_by_state"))
    action = _mapping(actions.get(state))
    if not action:
        return {
            "recommended_next_action": "NONE",
            "action_type": "update_state",
            "target_role": "orchestrator",
            "dispatchable": False,
        }

    result = dict(action)
    if result.get("target_role_source") == "task_or_gate":
        result["target_role"] = target_role or "NONE"
    result.setdefault("target_role", target_role or "NONE")
    if task_id:
        result["task_id"] = task_id
    if task_packet:
        result["task_packet"] = task_packet
    role = _text(result.get("target_role"))
    if role:
        result["reasoning_floor"] = _reasoning_floor(contract, role)
        result["required_docs"] = _string_list(_mapping(contract.get("required_docs_by_role")).get(role))
    return result


def derive_transition(
    contract: Mapping[str, Any],
    current_state: object,
    event: object,
    *,
    same_task: bool = True,
    target_role: str = "",
    task_id: str = "",
    task_packet: str = "",
) -> TransitionDecision:
    """Derive a canonical transition decision and explain/debug payload."""

    state = _state_from_input(current_state)
    event_name = _normalize_event(contract, event)
    findings: list[TransitionFinding] = []
    allowed_events = set(_string_list(contract.get("allowed_events")))

    if not state:
        findings.append(
            _finding(
                "RUNTIME_STATE_MISSING",
                "error",
                "Current contract state is missing.",
                repr(current_state),
                "Pass the current lifecycle state or sidecar-derived contract state to the transition engine.",
            )
        )
    if not event_name:
        findings.append(
            _finding(
                "RUNTIME_EVENT_MISSING",
                "error",
                "Runtime event is missing.",
                repr(event),
                "Pass a canonical event name or event object with event_type.",
            )
        )
    elif event_name not in allowed_events:
        findings.append(
            _finding(
                "RUNTIME_EVENT_NOT_ALLOWED",
                "error",
                "Runtime event is not in the contract allowed_events set.",
                f"event={event_name}",
                "Use a canonical runtime event from ORCHESTRATOR_RUNTIME_CONTRACT.json.",
            )
        )

    normalized_target_role = target_role.strip()
    if event_name == "CREATE_AGENT_DISPATCHED" and normalized_target_role in _string_list(contract.get("forbidden_dispatch_roles")):
        findings.append(
            _finding(
                "RUNTIME_FORBIDDEN_DISPATCH_ROLE",
                "error",
                "Runtime contract forbids dispatching this role.",
                f"target_role={normalized_target_role}",
                "Dispatch only allowed profile roles; route control/orchestrator work as non-dispatch correction/update_state.",
            )
        )

    findings.extend(_forbidden_transition_findings(contract, state, event_name, same_task=same_task))

    transitions = _mapping(contract.get("state_transitions"))
    event_map = _mapping(transitions.get(state))
    next_state = _text(event_map.get(event_name))
    if state and event_name and not next_state:
        findings.append(
            _finding(
                "RUNTIME_TRANSITION_NOT_ALLOWED",
                "error",
                "No state transition is defined for current state plus event.",
                f"from_state={state}; event={event_name}",
                "Use the transition table from ORCHESTRATOR_RUNTIME_CONTRACT.json as the routing authority.",
            )
        )

    selected = {
        "from_state": state,
        "event": event_name,
        "to_state": next_state or "NONE",
    }
    has_error = any(finding.severity == "error" for finding in findings)
    action_state = next_state or state
    next_action = _next_action_for_state(
        contract,
        action_state,
        target_role=normalized_target_role,
        task_id=task_id,
        task_packet=task_packet,
    )

    refs = _reference_docs(contract, _text(next_action.get("target_role")))
    return TransitionDecision(
        inputs={
            "current_state": state,
            "event": event_name,
            "same_task": same_task,
            "target_role": normalized_target_role,
            "task_id": task_id,
            "task_packet": task_packet,
        },
        transition_selected=selected,
        findings=tuple(findings),
        next_action=next_action,
        reference_docs_used=refs,
        allowed=not has_error,
        current_state=state,
        event=event_name,
        next_state=next_state,
    )


def derive_next_action(
    contract: Mapping[str, Any],
    current_state: object,
    event: object | None = None,
    *,
    same_task: bool = True,
    target_role: str = "",
    task_id: str = "",
    task_packet: str = "",
) -> dict[str, object]:
    """Return only the derived next action for callers that do not need the full explanation."""

    if event is not None:
        return derive_transition(
            contract,
            current_state,
            event,
            same_task=same_task,
            target_role=target_role,
            task_id=task_id,
            task_packet=task_packet,
        ).next_action
    return _next_action_for_state(
        contract,
        _state_from_input(current_state),
        target_role=target_role,
        task_id=task_id,
        task_packet=task_packet,
    )


def _state_route_decision(
    contract: Mapping[str, Any],
    state: str,
    *,
    result_type: str,
    status: str,
    derivation: str,
    target_role: str = "",
    task_id: str = "",
    task_packet: str = "",
    findings: Iterable[TransitionFinding] = (),
) -> TransitionDecision:
    route_findings = tuple(findings)
    next_action = _next_action_for_state(
        contract,
        state,
        target_role=target_role,
        task_id=task_id,
        task_packet=task_packet,
    )
    refs = _reference_docs(contract, _text(next_action.get("target_role")))
    return TransitionDecision(
        inputs={
            "result_type": result_type,
            "status": status,
            "task_id": task_id,
            "task_packet": task_packet,
            "target_role": target_role,
        },
        transition_selected={
            "derivation": derivation,
            "state": state,
        },
        findings=route_findings,
        next_action=next_action,
        reference_docs_used=refs,
        allowed=not any(finding.severity == "error" for finding in route_findings),
        current_state=state,
        event="",
        next_state=state,
    )


def derive_result_route(
    contract: Mapping[str, Any],
    result_type: str,
    status: str,
    *,
    task_id: str = "",
    task_packet: str = "",
) -> TransitionDecision:
    """Derive the canonical record-result route from the runtime contract."""

    normalized_result_type = _text(result_type)
    normalized_status = _text(status).lower()
    if normalized_result_type == "audit_result":
        return derive_transition(
            contract,
            "AUDIT_PENDING",
            {"event_type": "AUDIT_RESULT_RECEIVED", "status": normalized_status},
            target_role="auditor",
            task_id=task_id,
            task_packet=task_packet,
        )

    if normalized_result_type == "profile_result":
        if normalized_status == "pass":
            return _state_route_decision(
                contract,
                "AGENT_TERMINATED",
                result_type=normalized_result_type,
                status=normalized_status,
                derivation="profile_result_pass_after_agent_termination",
                target_role="auditor",
                task_id=task_id,
                task_packet=task_packet,
            )
        if normalized_status == "fail":
            return _state_route_decision(
                contract,
                "CORRECTION_REQUIRED",
                result_type=normalized_result_type,
                status=normalized_status,
                derivation="profile_result_fail",
                task_id=task_id,
                task_packet=task_packet,
            )

    findings = (
        _finding(
            "RUNTIME_RESULT_ROUTE_NOT_ALLOWED",
            "error",
            "Runtime contract does not define a record-result route for this result type and status.",
            f"result_type={normalized_result_type or 'NONE'}; status={normalized_status or 'NONE'}",
            "Add the route to ORCHESTRATOR_RUNTIME_CONTRACT.json or hold the RESULT for explicit correction routing.",
        ),
    )
    return _state_route_decision(
        contract,
        "",
        result_type=normalized_result_type,
        status=normalized_status,
        derivation="record_result_unroutable",
        task_id=task_id,
        task_packet=task_packet,
        findings=findings,
    )


def _content(sidecars: Mapping[str, Mapping[str, object]], sidecar_type: str) -> dict[str, Any]:
    payload = sidecars.get(sidecar_type, {})
    if not isinstance(payload, Mapping):
        return {}
    content = payload.get("content")
    if isinstance(content, Mapping):
        return dict(content)
    return dict(payload)


def _tasks_by_id(sidecars: Mapping[str, Mapping[str, object]]) -> dict[str, dict[str, Any]]:
    tasks = _content(sidecars, "TASK_REGISTRY").get("tasks")
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(tasks, list):
        return result
    for item in tasks:
        if isinstance(item, Mapping) and isinstance(item.get("task_id"), str):
            result[item["task_id"]] = dict(item)
    return result


def _active_task_id(
    project_state: Mapping[str, object],
    current_gate: Mapping[str, object],
    next_action: Mapping[str, object],
) -> str:
    for value in (next_action.get("task_id"), current_gate.get("task_id")):
        if isinstance(value, str) and not _is_none(value):
            return value.strip()
    branches = project_state.get("active_branches")
    if isinstance(branches, list):
        for branch in branches:
            if isinstance(branch, Mapping):
                task_id = branch.get("current_task")
                if isinstance(task_id, str) and not _is_none(task_id):
                    return task_id.strip()
    return ""


def _truthy_refs(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and not _is_none(item)]


def _has_audit_evidence(task: Mapping[str, object], sidecars: Mapping[str, Mapping[str, object]], task_id: str) -> bool:
    if _truthy_refs(task.get("audit_refs")):
        return True
    accepted = _content(sidecars, "ACCEPTED_ARTIFACTS").get("artifacts")
    if isinstance(accepted, list):
        for artifact in accepted:
            if not isinstance(artifact, Mapping):
                continue
            if artifact.get("source_task") != task_id and artifact.get("task_id") != task_id:
                continue
            audit_ref = artifact.get("audit_ref")
            if isinstance(audit_ref, str) and not _is_none(audit_ref):
                return True
    return False


def _infer_contract_state(
    sidecars: Mapping[str, Mapping[str, object]],
) -> tuple[str, dict[str, object]]:
    project_state = _content(sidecars, "PROJECT_STATE")
    current_gate = _content(sidecars, "CURRENT_GATE")
    next_action = _content(sidecars, "NEXT_ACTION")
    tasks = _tasks_by_id(sidecars)
    task_id = _active_task_id(project_state, current_gate, next_action)
    task = tasks.get(task_id, {})
    task_status = _text(task.get("status"))
    action_type = _text(next_action.get("action_type"))
    target_role = _text(next_action.get("target_role"))
    checkpoint_policy = _text(next_action.get("checkpoint_policy"))
    checkpoint_preflight_required = next_action.get("checkpoint_preflight_required") is True
    current_phase = _text(project_state.get("current_phase"))
    project_status = _text(project_state.get("project_status"))

    signals: dict[str, object] = {
        "task_id": task_id,
        "task_status": task_status,
        "next_action_type": action_type,
        "target_role": target_role,
        "checkpoint_policy": checkpoint_policy,
        "current_phase": current_phase,
        "project_status": project_status,
    }

    if project_status in {"completed", "archived"} or current_phase == "completed":
        return "TERMINAL_STOP", signals
    if current_phase == "correction":
        return "CORRECTION_REQUIRED", signals
    if project_status == "blocked" and action_type == "wait_for_owner":
        return "OWNER_INPUT_REQUIRED", signals
    if project_status == "blocked" and action_type == "correction":
        return "CORRECTION_REQUIRED", signals
    if task_status in {"failed", "blocked"}:
        return "CORRECTION_REQUIRED", signals
    if task_status in {"audit_passed", "checkpoint_done", "completed"} or _has_audit_evidence(task, sidecars, task_id):
        return "CHECKPOINT_ELIGIBLE", signals
    if checkpoint_policy in {"local_only", "commit_and_push"} or checkpoint_preflight_required:
        return "CHECKPOINT_ELIGIBLE", signals
    if task_status == "audit_pending":
        return "AUDIT_PENDING", signals
    if task_status == "running":
        if _truthy_refs(task.get("result_refs")):
            return "RESULT_PENDING_ARTIFACT_ACCEPTANCE", signals
        return "AGENT_RUNNING", signals
    if task_status in {"ready", "pending"}:
        return "TASK_READY", signals
    if action_type == "wait_for_owner":
        return "OWNER_INPUT_REQUIRED", signals
    if action_type == "stop":
        return "TERMINAL_STOP", signals
    if action_type == "correction":
        return "CORRECTION_REQUIRED", signals
    if action_type == "create_agent" and target_role == "auditor":
        return "AGENT_TERMINATED", signals
    if action_type == "create_agent":
        return "TASK_READY", signals
    if action_type == "route_result" and target_role == "auditor":
        return "AUDIT_PENDING", signals
    if action_type == "route_result":
        return "AGENT_RUNNING", signals
    if action_type == "finalize":
        return "CHECKPOINT_ELIGIBLE", signals
    if action_type == "update_state":
        return "RESULT_PENDING_ARTIFACT_ACCEPTANCE", signals
    return "CORRECTION_REQUIRED", signals


def infer_contract_state_from_sidecars(sidecars: Mapping[str, Mapping[str, object]]) -> str:
    state, _signals = _infer_contract_state(sidecars)
    return state


def recommendation_from_next_action_content(next_action: Mapping[str, object]) -> str:
    action_type = _text(next_action.get("action_type"))
    target_role = _text(next_action.get("target_role"))
    checkpoint_policy = _text(next_action.get("checkpoint_policy"))
    if checkpoint_policy in {"local_only", "commit_and_push"} or next_action.get("checkpoint_preflight_required") is True:
        return "CHECKPOINT_PREFLIGHT"
    if action_type == "create_agent":
        return "CREATE_AUDITOR" if target_role == "auditor" else "CREATE_AGENT"
    if action_type == "correction":
        return "CORRECTION_REQUIRED"
    if action_type == "wait_for_owner":
        return "ASK_OWNER"
    if action_type == "route_result":
        return "ROUTE_RESULT"
    if action_type == "update_state":
        return "UPDATE_STATE"
    if action_type == "finalize":
        return "FINALIZE"
    if action_type == "stop":
        return "STOP"
    return "NONE"


def _recommendations_match(contract: Mapping[str, Any], expected: str, actual: str) -> bool:
    if expected == actual:
        return True
    aliases = _mapping(contract.get("next_action_aliases"))
    expected_aliases = _string_list(aliases.get(expected))
    return actual in expected_aliases


def explain_next_action_from_sidecars(
    contract: Mapping[str, Any],
    sidecars: Mapping[str, Mapping[str, object]],
) -> TransitionDecision:
    state, signals = _infer_contract_state(sidecars)
    next_action_content = _content(sidecars, "NEXT_ACTION")
    task_id = _text(signals.get("task_id"))
    task_packet = _text(next_action_content.get("task_packet"))
    target_role = _text(next_action_content.get("target_role"))
    derived_action = derive_next_action(
        contract,
        state,
        target_role=target_role,
        task_id=task_id,
        task_packet=task_packet,
    )
    expected = _text(derived_action.get("recommended_next_action"))
    actual = recommendation_from_next_action_content(next_action_content)

    findings: list[TransitionFinding] = []
    if not _recommendations_match(contract, expected, actual):
        findings.append(
            _finding(
                "RUNTIME_NEXT_ACTION_STALE",
                "error",
                "Stored NEXT_ACTION differs from the transition engine derived next action.",
                f"contract_state={state}; expected={expected or 'NONE'}; actual={actual or 'NONE'}",
                "Regenerate NEXT_ACTION from the runtime contract and current state sidecars.",
            )
        )
    if actual in {"CREATE_AGENT", "CREATE_AUDITOR"} and target_role in _string_list(contract.get("forbidden_dispatch_roles")):
        findings.append(
            _finding(
                "RUNTIME_FORBIDDEN_DISPATCH_ROLE",
                "error",
                "Stored NEXT_ACTION targets a role that the runtime contract forbids for dispatch.",
                f"target_role={target_role}",
                "Use a non-dispatch correction/update_state action for control roles.",
            )
        )

    refs = _reference_docs(contract, _text(derived_action.get("target_role")))
    return TransitionDecision(
        inputs={
            "sidecar_state_signals": signals,
            "stored_next_action": {
                "action_type": next_action_content.get("action_type", ""),
                "target_role": target_role,
                "task_id": next_action_content.get("task_id", ""),
                "task_packet": task_packet,
                "checkpoint_policy": next_action_content.get("checkpoint_policy", ""),
            },
            "stored_recommended_next_action": actual,
        },
        transition_selected={
            "derivation": "sidecars",
            "state": state,
            "expected_recommended_next_action": expected,
        },
        findings=tuple(findings),
        next_action=derived_action,
        reference_docs_used=refs,
        allowed=not any(finding.severity == "error" for finding in findings),
        current_state=state,
        event="",
        next_state=state,
    )


def validate_next_action_consistency(
    contract: Mapping[str, Any],
    sidecars: Mapping[str, Mapping[str, object]],
) -> list[TransitionFinding]:
    return list(explain_next_action_from_sidecars(contract, sidecars).findings)


def findings_to_json(findings: Iterable[TransitionFinding]) -> list[dict[str, str]]:
    return [finding.to_json() for finding in findings]
