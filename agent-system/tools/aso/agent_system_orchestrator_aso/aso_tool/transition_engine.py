"""Canonical ASO runtime contract loader and transition engine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import dispatch_receipts
from . import result_parser
from . import role_registry
from . import resources
from . import runtime_contract_fallback


CONTRACT_RELATIVE_PATH = Path("agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json")
SCHEMA_RELATIVE_PATH = Path("agent-system/09_validators/schemas/orchestrator_runtime_contract.schema.json")
LIFECYCLE_LOG_RELATIVE_PATH = Path("project-runtime/agents/instances.jsonl")
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}
LIFECYCLE_EVENT_STATES = {
    "CREATE_AGENT_DISPATCHED": "AGENT_RUNNING",
    "RESULT_RECEIVED": "RESULT_PENDING_ARTIFACT_ACCEPTANCE",
    "RESULT_VALIDATED": "RESULT_VALIDATED",
    "RESULT_ACCEPTED": "RESULT_ACCEPTED",
    "ARTIFACT_PACKAGE_RECEIVED": "ARTIFACT_PACKAGE_RECEIVED",
    "ARTIFACT_VALIDATED": "ARTIFACT_VALIDATED",
    "ARTIFACT_ACCEPTED": "RESULT_ACCEPTED",
    "AGENT_TERMINATED": "AGENT_TERMINATED",
    "AUDIT_ROUTE_READY": "AUDIT_PENDING",
    "AUDIT_RESULT_RECEIVED_PASS": "CHECKPOINT_ELIGIBLE",
    "AUDIT_RESULT_RECEIVED_FAIL": "CORRECTION_REQUIRED",
    "CORRECTION_REQUIRED": "CORRECTION_REQUIRED",
    "CHECKPOINT_ELIGIBLE": "CHECKPOINT_ELIGIBLE",
    "CHECKPOINT_PREFLIGHT_PASS": "FINAL_AUDIT_PASS",
    "CHECKPOINT_COMMITTED_OR_ARCHIVED": "FINAL_CHECKPOINT_COMPLETE",
    "FINALIZE": "PROJECT_COMPLETED",
    "PROJECT_COMPLETED": "PROJECT_COMPLETED",
    "NO_NEXT_ACTION": "NO_NEXT_ACTION",
}
AUDIT_RESULT_EVENTS = {
    "AUDIT_RESULT_RECEIVED",
    "AUDIT_RESULT_RECEIVED_PASS",
    "AUDIT_RESULT_RECEIVED_FAIL",
}
AUDITOR_BOOKKEEPING_EVENTS = {
    "ARTIFACT_ACCEPTED",
    "AGENT_TERMINATED",
    "AUDIT_ROUTE_READY",
}
LIFECYCLE_PROGRESS_STATES = {
    "AGENT_RUNNING",
    "RESULT_PENDING_ARTIFACT_ACCEPTANCE",
    "RESULT_VALIDATED",
    "ARTIFACT_PACKAGE_RECEIVED",
    "ARTIFACT_VALIDATED",
    "RESULT_ACCEPTED",
    "AGENT_TERMINATED",
    "AUDIT_PENDING",
    "CORRECTION_REQUIRED",
    "CORRECTION_AGENT_RUNNING",
    "CHECKPOINT_ELIGIBLE",
    "FINAL_AUDIT_PASS",
    "FINAL_CHECKPOINT_COMPLETE",
}
LIFECYCLE_STATUS_CONTRACT = {
    "profile_result_statuses": ("pass", "fail"),
    "audit_result_statuses": ("pass", "fail"),
    "terminal_states": ("PROJECT_COMPLETED", "NO_NEXT_ACTION"),
}
DERIVED_NEXT_ACTION_CACHE_FIELDS = (
    "action_type",
    "target_role",
    "task_id",
    "task_packet",
    "dependency_status",
    "blocked_by",
    "action_semantic",
    "workspace_identity_required",
    "repository_lock_required",
    "checkpoint_policy",
    "checkpoint_preflight_required",
    "checkpoint_receipt_required",
)


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


def _truthy_refs(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and not _is_none(item)]


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _log_finding(
    rule_id: str,
    severity: str,
    message: str,
    evidence: str,
    recommendation: str,
) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def load_lifecycle_log(root: str | Path) -> dict[str, object]:
    """Load lifecycle events for reconciliation without mutating workspace state."""

    workspace_root = Path(root)
    path = workspace_root / LIFECYCLE_LOG_RELATIVE_PATH
    events: list[dict[str, Any]] = []
    findings: list[dict[str, str]] = []
    if not path.exists():
        return {
            "path": LIFECYCLE_LOG_RELATIVE_PATH.as_posix(),
            "exists": False,
            "events": events,
            "findings": findings,
        }
    if not path.is_file():
        return {
            "path": LIFECYCLE_LOG_RELATIVE_PATH.as_posix(),
            "exists": False,
            "events": events,
            "findings": [
                _log_finding(
                    "RUNTIME_LIFECYCLE_LOG_UNREADABLE",
                    "error",
                    "Lifecycle log path is not a regular file.",
                    LIFECYCLE_LOG_RELATIVE_PATH.as_posix(),
                    "Restore project-runtime/agents/instances.jsonl as a JSONL event log.",
                )
            ],
        }
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {
            "path": LIFECYCLE_LOG_RELATIVE_PATH.as_posix(),
            "exists": True,
            "events": events,
            "findings": [
                _log_finding(
                    "RUNTIME_LIFECYCLE_LOG_UNREADABLE",
                    "error",
                    "Lifecycle log could not be read.",
                    str(exc),
                    "Repair lifecycle log permissions before routing next actions.",
                )
            ],
        }

    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            findings.append(
                _log_finding(
                    "RUNTIME_LIFECYCLE_LOG_JSON_INVALID",
                    "error",
                    "Lifecycle log contains invalid JSON.",
                    f"{LIFECYCLE_LOG_RELATIVE_PATH.as_posix()}:{line_number}: {exc.msg}",
                    "Repair or remove the malformed lifecycle event before routing next actions.",
                )
            )
            continue
        if not isinstance(payload, dict):
            findings.append(
                _log_finding(
                    "RUNTIME_LIFECYCLE_LOG_EVENT_INVALID",
                    "error",
                    "Lifecycle log entry is not an object.",
                    f"{LIFECYCLE_LOG_RELATIVE_PATH.as_posix()}:{line_number}",
                    "Use one JSON object per lifecycle event line.",
                )
            )
            continue
        event = dict(payload)
        event["_line"] = line_number
        events.append(event)

        result_ref = _text(event.get("result_ref"))
        if result_ref and not _is_none(result_ref):
            result_path = workspace_root / result_ref
            if not result_path.is_file():
                findings.append(
                    _log_finding(
                        "RUNTIME_LIFECYCLE_RESULT_REF_MISSING",
                        "error",
                        "Lifecycle event references a missing RESULT.",
                        f"{LIFECYCLE_LOG_RELATIVE_PATH.as_posix()}:{line_number}; result_ref={result_ref}",
                        "Restore the referenced RESULT artifact or repair the lifecycle event.",
                    )
                )

        for ref_field in ("artifact_ref", "artifact_package_ref", "receipt_ref"):
            ref = _text(event.get(ref_field))
            if not ref or _is_none(ref):
                continue
            ref_path = workspace_root / ref
            if not ref_path.exists():
                findings.append(
                    _log_finding(
                        "RUNTIME_LIFECYCLE_ARTIFACT_REF_MISSING",
                        "error",
                        "Lifecycle event references a missing artifact or receipt.",
                        f"{LIFECYCLE_LOG_RELATIVE_PATH.as_posix()}:{line_number}; {ref_field}={ref}",
                        "Restore the referenced artifact/receipt or repair the lifecycle event.",
                    )
                )

    return {
        "path": LIFECYCLE_LOG_RELATIVE_PATH.as_posix(),
        "exists": True,
        "events": events,
        "findings": findings,
    }


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
        "dispatch_receipt_contract",
        "handoff_artifact_contract",
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

    dispatch_receipt = _mapping(contract.get("dispatch_receipt_contract"))
    if not dispatch_receipt:
        errors.append("dispatch_receipt_contract must be an object")
    else:
        if dispatch_receipt.get("receipt_ref_template") != "project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json":
            errors.append("dispatch_receipt_contract.receipt_ref_template must be project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json")
        if dispatch_receipt.get("runner") != "external_codex_cli":
            errors.append("dispatch_receipt_contract.runner must be external_codex_cli")
        if dispatch_receipt.get("live_dispatch_performed_by_aso") is not False:
            errors.append("dispatch_receipt_contract.live_dispatch_performed_by_aso must be false")
        for field in (
            "schema_ref",
            "template_ref",
            "runner_semantics",
            "external_runner_command_template",
            "writer_command_template",
        ):
            if not _text(dispatch_receipt.get(field)):
                errors.append(f"dispatch_receipt_contract.{field} is required")
        required_receipt_fields = set(_string_list(dispatch_receipt.get("required_fields")))
        for field in ("runner", "model", "reasoning_effort", "prompt_ref", "task_id", "role", "started_at", "handoff_ref"):
            if field not in required_receipt_fields:
                errors.append(f"dispatch_receipt_contract.required_fields missing {field}")

    handoff_artifact = _mapping(contract.get("handoff_artifact_contract"))
    if not handoff_artifact:
        errors.append("handoff_artifact_contract must be an object")
    else:
        expected_values = {
            "schema_ref": "agent-system/09_validators/schemas/orchestrator_handoff.schema.json",
            "template_ref": "agent-system/03_templates/orchestrator_handoff.template.json",
            "handoff_ref_template": "project-runtime/handoffs/<TASK_ID>.json",
            "prompt_ref_template": "project-runtime/handoffs/<TASK_ID>.prompt.md",
            "expected_result_ref_template": "project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_001.md",
            "expected_audit_result_ref_template": "project-runtime/results/audit/AUDIT_RESULT_<TASK_ID>_ATTEMPT_001.md",
            "expected_artifact_package_ref_template": "project-runtime/artifacts/candidates/<TASK_ID>/manifest.json",
            "runner": "external_codex_cli",
            "external_runner_command_template": dispatch_receipts.EXTERNAL_RUNNER_COMMAND_TEMPLATE,
        }
        for field, expected in expected_values.items():
            if handoff_artifact.get(field) != expected:
                errors.append(f"handoff_artifact_contract.{field} must be {expected}")
        if handoff_artifact.get("live_dispatch_performed_by_aso") is not False:
            errors.append("handoff_artifact_contract.live_dispatch_performed_by_aso must be false")
        for field in ("forbidden_governance_corpus_rule", "runner_semantics"):
            if not _text(handoff_artifact.get(field)):
                errors.append(f"handoff_artifact_contract.{field} is required")
        required_handoff_fields = set(_string_list(handoff_artifact.get("required_fields")))
        for field in (
            "task_id",
            "role",
            "resolved_reasoning_level",
            "required_docs",
            "forbidden_docs",
            "prompt_ref",
            "expected_result_path",
            "expected_artifact_package_path",
            "lifecycle_policy",
        ):
            if field not in required_handoff_fields:
                errors.append(f"handoff_artifact_contract.required_fields missing {field}")

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
    if event_name == "CREATE_AGENT_DISPATCHED" and not role_registry.is_dispatchable_role(normalized_target_role, contract):
        findings.append(
            _finding(
                "RUNTIME_FORBIDDEN_DISPATCH_ROLE",
                "error",
                "Runtime contract does not permit dispatching this role.",
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
) -> str:
    for value in (current_gate.get("task_id"),):
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


def _truthy_text(value: object) -> str:
    text = _text(value)
    return "" if _is_none(text) else text


def _single_active_task_id(tasks: Mapping[str, Mapping[str, Any]]) -> str:
    candidates = [
        task_id
        for task_id, task in tasks.items()
        if _text(task.get("status")) not in {"", "completed", "checkpoint_done", "superseded"}
    ]
    return candidates[0] if len(candidates) == 1 else ""


def _task_for_id(sidecars: Mapping[str, Mapping[str, object]], task_id: str) -> dict[str, Any]:
    if not task_id:
        return {}
    return _tasks_by_id(sidecars).get(task_id, {})


def _canonical_target_role(
    sidecars: Mapping[str, Mapping[str, object]],
    task_id: str,
) -> str:
    current_gate = _content(sidecars, "CURRENT_GATE")
    project_state = _content(sidecars, "PROJECT_STATE")
    gate_task_id = _truthy_text(current_gate.get("task_id"))
    required_next_role = _truthy_text(current_gate.get("required_next_role"))
    if required_next_role and (not task_id or (gate_task_id and gate_task_id == task_id)):
        return required_next_role

    task = _task_for_id(sidecars, task_id)
    for value in (task.get("owner_role"), task.get("task_type")):
        text = _truthy_text(value)
        if text:
            return text

    branches = project_state.get("active_branches")
    if isinstance(branches, list):
        for branch in branches:
            if not isinstance(branch, Mapping):
                continue
            if task_id and _text(branch.get("current_task")) != task_id:
                continue
            role = _truthy_text(branch.get("current_agent_role"))
            if role:
                return role

    owner_role = _truthy_text(current_gate.get("owner_role"))
    if owner_role and (not task_id or (gate_task_id and gate_task_id == task_id)):
        return owner_role
    return ""


def _canonical_task_packet(
    sidecars: Mapping[str, Mapping[str, object]],
    task_id: str,
) -> str:
    current_gate = _content(sidecars, "CURRENT_GATE")
    gate_task_id = _truthy_text(current_gate.get("task_id"))
    gate_packet = _truthy_text(current_gate.get("task_packet"))
    if gate_packet and (not task_id or not gate_task_id or gate_task_id == task_id):
        return gate_packet

    task = _task_for_id(sidecars, task_id)
    packet = _truthy_text(task.get("task_packet"))
    if packet:
        return packet

    return ""


def contract_roles(contract: Mapping[str, Any]) -> dict[str, object]:
    """Return canonical runtime roles used by routing and validation callers."""

    allowed_roles = _string_list(contract.get("allowed_roles"))
    forbidden_dispatch_roles = _string_list(contract.get("forbidden_dispatch_roles"))
    return {
        "allowed_roles": allowed_roles,
        "forbidden_dispatch_roles": forbidden_dispatch_roles,
        "dispatchable_roles": list(role_registry.dispatchable_roles(contract)),
        "control_or_pseudo_roles": list(role_registry.control_or_pseudo_roles(contract)),
    }


def lifecycle_status_contract(contract: Mapping[str, Any]) -> dict[str, object]:
    """Return lifecycle and terminal statuses derived from the runtime contract."""

    return {
        "profile_result_statuses": list(LIFECYCLE_STATUS_CONTRACT["profile_result_statuses"]),
        "audit_result_statuses": list(LIFECYCLE_STATUS_CONTRACT["audit_result_statuses"]),
        "terminal_states": _string_list(contract.get("terminal_states")),
        "progress_states": sorted(LIFECYCLE_PROGRESS_STATES),
    }


def checkpoint_policies(contract: Mapping[str, Any]) -> list[str]:
    """Return checkpoint policies declared by checkpoint next-action routes."""

    policies: list[str] = []
    actions = _mapping(contract.get("next_actions_by_state"))
    for action in actions.values():
        action_map = _mapping(action)
        if action_map.get("recommended_next_action") != "CHECKPOINT_PREFLIGHT":
            continue
        policy = _text(action_map.get("checkpoint_policy"))
        if policy:
            policies.append(policy)
    return sorted(dict.fromkeys(policies))


def is_checkpoint_next_action(contract: Mapping[str, Any], next_action: Mapping[str, object]) -> bool:
    """Return whether NEXT_ACTION is checkpoint preflight by contract-derived rules."""

    recommended = recommendation_from_next_action_content(next_action)
    if recommended == "CHECKPOINT_PREFLIGHT":
        return True
    if next_action.get("checkpoint_preflight_required") is True:
        return True
    policy = _text(next_action.get("checkpoint_policy"))
    return bool(policy and policy in set(checkpoint_policies(contract)))


def _accepted_artifact_audit_refs(
    sidecars: Mapping[str, Mapping[str, object]],
    task_id: str,
) -> list[str]:
    accepted = _content(sidecars, "ACCEPTED_ARTIFACTS").get("artifacts")
    refs: list[str] = []
    if not isinstance(accepted, list):
        return refs
    for artifact in accepted:
        if not isinstance(artifact, Mapping):
            continue
        if artifact.get("source_task") != task_id and artifact.get("task_id") != task_id:
            continue
        audit_ref = artifact.get("audit_ref")
        if isinstance(audit_ref, str) and not _is_none(audit_ref):
            refs.append(audit_ref.strip())
    return refs


def _current_gate_audit_refs(sidecars: Mapping[str, Mapping[str, object]]) -> list[str]:
    refs: list[str] = []
    for item in _truthy_refs(_content(sidecars, "CURRENT_GATE").get("gate_evidence")):
        if "audit" in item.lower():
            refs.append(item)
    return refs


def _lifecycle_audit_pass_refs(
    sidecars: Mapping[str, Mapping[str, object]],
    task_id: str,
) -> list[str]:
    refs: list[str] = []
    for event in _lifecycle_events(sidecars):
        if task_id and _event_task_id(event) != task_id:
            continue
        raw_event = _raw_event_type(event)
        status = _event_status(event)
        event_name = "AUDIT_RESULT_RECEIVED_PASS" if raw_event == "AUDIT_RESULT_RECEIVED" and status == "pass" else raw_event
        if event_name not in {"AUDIT_RESULT_RECEIVED_PASS", "audit_result_received_pass"}:
            continue
        result_ref = _event_result_ref(event)
        if result_ref and not _is_none(result_ref):
            refs.append(result_ref)
    return refs


def audit_pass_evidence_from_sidecars(
    root: str | Path,
    sidecars: Mapping[str, Mapping[str, object]],
    *,
    task_id: str = "",
) -> dict[str, object]:
    """Inspect audit-pass evidence from TASK_REGISTRY, artifacts, and CURRENT_GATE."""

    workspace_root = Path(root)
    project_state = _content(sidecars, "PROJECT_STATE")
    current_gate = _content(sidecars, "CURRENT_GATE")
    tasks = _tasks_by_id(sidecars)
    resolved_task_id = task_id or _active_task_id(project_state, current_gate) or _single_active_task_id(tasks)
    task = tasks.get(resolved_task_id, {})
    task_status = _text(task.get("status"))
    task_audit_refs = _truthy_refs(task.get("audit_refs"))
    artifact_audit_refs = _accepted_artifact_audit_refs(sidecars, resolved_task_id)
    gate_audit_refs = _current_gate_audit_refs(sidecars)
    lifecycle_audit_refs = _lifecycle_audit_pass_refs(sidecars, resolved_task_id)
    strict_audit_refs = list(dict.fromkeys([*task_audit_refs, *artifact_audit_refs, *gate_audit_refs]))
    lifecycle_only_refs = [ref for ref in lifecycle_audit_refs if ref not in set(strict_audit_refs)]
    parsed = result_parser.inspect_audit_references(
        workspace_root,
        strict_audit_refs,
        task_id=resolved_task_id,
        strict=True,
    )
    lifecycle_parsed = result_parser.inspect_audit_references(
        workspace_root,
        lifecycle_only_refs,
        task_id=resolved_task_id,
        strict=False,
    )
    invalid_refs = [*parsed["invalid_refs"], *lifecycle_parsed["invalid_refs"]]
    unparsed_refs = [*parsed["unparsed_refs"], *lifecycle_parsed["unparsed_refs"]]
    passed_refs = list(dict.fromkeys([*parsed["passed_refs"], *lifecycle_parsed["passed_refs"]]))
    present = bool(passed_refs) and not invalid_refs and not unparsed_refs
    return {
        "present": present,
        "task_id": resolved_task_id,
        "task_status": task_status,
        "task_status_audit_passed": task_status == "audit_passed",
        "task_audit_refs": task_audit_refs,
        "accepted_artifact_audit_refs": artifact_audit_refs,
        "current_gate_audit_evidence_refs": gate_audit_refs,
        "lifecycle_audit_pass_refs": lifecycle_audit_refs,
        "parsed_audit_results": [*parsed["parsed_refs"], *lifecycle_parsed["parsed_refs"]],
        "passed_audit_refs": passed_refs,
        "invalid_audit_results": invalid_refs,
        "unparsed_audit_refs": unparsed_refs,
    }


def active_blockers_from_sidecars(sidecars: Mapping[str, Mapping[str, object]]) -> list[str]:
    """Return active blockers that block routing or checkpoint by contract policy."""

    project_state = _content(sidecars, "PROJECT_STATE")
    blockers: list[str] = []
    for key in ("active_blockers", "checkpoint_blocked_by"):
        value = project_state.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and not _is_none(item):
                    blockers.append(item.strip())
                elif isinstance(item, Mapping) and item:
                    blocker_id = _text(item.get("blocker_id"))
                    blockers.append(blocker_id or json.dumps(dict(item), sort_keys=True))
        elif isinstance(value, str) and not _is_none(value):
            blockers.append(value.strip())
    return sorted(dict.fromkeys(blocker for blocker in blockers if blocker))


def routing_authority_report(
    contract: Mapping[str, Any],
    sidecars: Mapping[str, Mapping[str, object]],
    *,
    root: str | Path | None = None,
) -> dict[str, object]:
    """Return the canonical read-only validate -> route-next -> apply-transition report."""

    decision = explain_next_action_from_sidecars(contract, sidecars)
    payload = decision.to_json()
    recommended = _text(decision.next_action.get("recommended_next_action"))
    derived_cache = derived_next_action_cache_content(contract, sidecars, decision)
    blockers = active_blockers_from_sidecars(sidecars)
    audit_evidence: dict[str, object] = {}
    if root is not None:
        signals = decision.inputs.get("sidecar_state_signals")
        audit_task_id = _text(signals.get("task_id")) if isinstance(signals, Mapping) else ""
        audit_evidence = audit_pass_evidence_from_sidecars(root, sidecars, task_id=audit_task_id)
    checkpoint_rules = _mapping(contract.get("checkpoint_rules"))
    checkpoint_route = {
        "attempt": recommended == "CHECKPOINT_PREFLIGHT",
        "eligible": (
            recommended == "CHECKPOINT_PREFLIGHT"
            and (not checkpoint_rules.get("requires_audit_pass", True) or bool(audit_evidence.get("present")))
            and (not checkpoint_rules.get("requires_no_open_lifecycle_blockers", True) or not blockers)
        ),
        "requires_audit_pass": checkpoint_rules.get("requires_audit_pass", True),
        "requires_no_open_lifecycle_blockers": checkpoint_rules.get("requires_no_open_lifecycle_blockers", True),
        "active_blockers": blockers,
    }
    payload.update(
        {
            "contract_authoritative": True,
            "canonical_recommended_next_action": recommended or "NONE",
            "derived_next_action_cache": derived_cache,
            "audit_gate_rules": _mapping(contract.get("audit_gate_rules")),
            "checkpoint_rules": checkpoint_rules,
            "checkpoint_route": checkpoint_route,
            "allowed_events": _string_list(contract.get("allowed_events")),
            "roles": contract_roles(contract),
            "lifecycle_statuses": lifecycle_status_contract(contract),
            "routing_layers": {
                "validate": {
                    "status": "passed" if decision.allowed else "failed",
                    "read_only": True,
                    "mutations_performed": False,
                    "findings": [finding.to_json() for finding in decision.findings],
                },
                "route_next": {
                    "status": "routed",
                    "read_only": True,
                    "mutations_performed": False,
                    "current_state": decision.current_state,
                    "recommended_next_action": recommended or "NONE",
                    "next_action": decision.next_action,
                },
                "apply_transition": {
                    "status": "not_requested",
                    "mutating_authority": True,
                    "read_only": True,
                    "mutations_performed": False,
                    "requires_explicit_confirm_write": True,
                },
            },
        }
    )
    if audit_evidence:
        payload["audit_pass_evidence"] = audit_evidence
    return payload


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


def _lifecycle_payload(sidecars: Mapping[str, Mapping[str, object]]) -> dict[str, Any]:
    payload = sidecars.get("LIFECYCLE_LOG")
    if not isinstance(payload, Mapping):
        return {}
    content = payload.get("content")
    if isinstance(content, Mapping):
        return dict(content)
    return dict(payload)


def _lifecycle_events(sidecars: Mapping[str, Mapping[str, object]]) -> list[dict[str, Any]]:
    payload = _lifecycle_payload(sidecars)
    events = payload.get("events")
    if not isinstance(events, list):
        return []
    return [dict(event) for event in events if isinstance(event, Mapping)]


def _lifecycle_log_findings(sidecars: Mapping[str, Mapping[str, object]]) -> list[TransitionFinding]:
    payload = _lifecycle_payload(sidecars)
    raw_findings = payload.get("findings")
    if not isinstance(raw_findings, list):
        return []
    findings: list[TransitionFinding] = []
    for item in raw_findings:
        if not isinstance(item, Mapping):
            continue
        findings.append(
            _finding(
                _text(item.get("rule_id")) or "RUNTIME_LIFECYCLE_LOG_INVALID",
                _text(item.get("severity")) or "error",
                _text(item.get("message")) or "Lifecycle log is invalid.",
                _text(item.get("evidence")),
                _text(item.get("recommendation")) or "Repair lifecycle log before routing.",
            )
        )
    return findings


def _event_line(event: Mapping[str, object]) -> str:
    line = event.get("_line")
    return str(line) if isinstance(line, int) else "unknown"


def _event_task_id(event: Mapping[str, object]) -> str:
    return _text(event.get("task_id") or event.get("task") or event.get("TASK_ID"))


def _event_result_ref(event: Mapping[str, object]) -> str:
    return _text(event.get("result_ref") or event.get("source_result_ref"))


def _event_role(event: Mapping[str, object]) -> str:
    return _text(event.get("agent_role") or event.get("role") or event.get("ROLE")).lower()


def _event_status(event: Mapping[str, object]) -> str:
    return _text(event.get("status") or event.get("result_status") or event.get("audit_status")).lower()


def _event_acceptance_mode(event: Mapping[str, object]) -> str:
    mode = _text(event.get("result_acceptance_mode") or event.get("RESULT_ACCEPTANCE_MODE")).lower()
    if mode in {"result_only", "artifact_package"}:
        return mode
    required = event.get("artifact_package_required")
    if isinstance(required, bool):
        return "artifact_package" if required else "result_only"
    required_text = _text(required or event.get("ARTIFACT_PACKAGE_REQUIRED")).lower()
    if required_text in {"true", "yes", "required"}:
        return "artifact_package"
    if required_text in {"false", "no", "not_required"}:
        return "result_only"
    return ""


def _events_use_result_only_acceptance(events: Iterable[Mapping[str, object]]) -> bool:
    return any(_event_acceptance_mode(event) == "result_only" for event in events)


def _raw_event_type(event: Mapping[str, object]) -> str:
    return _text(event.get("event_type") or event.get("event") or event.get("type"))


def _is_auditor_event(event: Mapping[str, object], event_name: str) -> bool:
    role = _event_role(event)
    if role == "auditor":
        return True
    raw_event_type = _raw_event_type(event)
    if raw_event_type in {"AUDITOR_AGENT_TERMINATED", "auditor_agent_terminated"}:
        return True
    previous_event_type = _text(event.get("previous_event_type") or event.get("previous_event"))
    if previous_event_type in {"AUDITOR_AGENT_TERMINATED", "auditor_agent_terminated"}:
        return True
    agent_instance_id = _text(event.get("agent_instance_id"))
    if agent_instance_id.startswith("audit_"):
        return True
    return event_name in AUDIT_RESULT_EVENTS


def _is_auditor_bookkeeping_event(event: Mapping[str, object], event_name: str) -> bool:
    return event_name in AUDITOR_BOOKKEEPING_EVENTS and _is_auditor_event(event, event_name)


def _contract_transition_state(contract: Mapping[str, Any], state: str, event_name: str) -> str:
    transitions = _mapping(contract.get("state_transitions"))
    return _text(_mapping(transitions.get(state)).get(event_name))


def _relevant_lifecycle_events(
    contract: Mapping[str, Any],
    events: list[dict[str, Any]],
    task_id: str,
) -> list[dict[str, Any]]:
    if task_id:
        filtered = [
            event
            for event in events
            if _event_task_id(event) == task_id
        ]
        if filtered:
            return filtered
        return []
    return events


def _last_lifecycle_task_id(events: list[dict[str, Any]]) -> str:
    for event in reversed(events):
        task_id = _event_task_id(event)
        if task_id:
            return task_id
    return ""


def _accepted_artifact_entries(sidecars: Mapping[str, Mapping[str, object]]) -> list[dict[str, Any]]:
    artifacts = _content(sidecars, "ACCEPTED_ARTIFACTS").get("artifacts")
    if not isinstance(artifacts, list):
        return []
    return [dict(item) for item in artifacts if isinstance(item, Mapping)]


def _artifact_event_has_sidecar_entry(
    event: Mapping[str, object],
    entries: list[dict[str, Any]],
) -> bool:
    artifact_ref = _text(event.get("artifact_ref"))
    artifact_package_ref = _text(event.get("artifact_package_ref"))
    artifact_id = _text(event.get("artifact_id"))
    task_id = _event_task_id(event)
    for entry in entries:
        if entry.get("status") != "accepted":
            continue
        entry_refs = {
            _text(entry.get("artifact_ref")),
            _text(entry.get("artifact_package_ref")),
        }
        if artifact_ref and artifact_ref in entry_refs:
            return True
        if artifact_package_ref and artifact_package_ref in entry_refs:
            return True
        if artifact_id and artifact_id == _text(entry.get("artifact_id")):
            return True
        if task_id and task_id in {_text(entry.get("source_task")), _text(entry.get("task_id"))}:
            return True
    return False


def _lifecycle_sequence_findings(
    contract: Mapping[str, Any],
    events: list[dict[str, Any]],
    task_id: str,
) -> list[TransitionFinding]:
    profile_positions: dict[str, int] = {}
    auditor_positions: dict[str, int] = {}
    profile_events: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        event_name = _normalize_event(contract, event)
        if _is_auditor_event(event, event_name):
            auditor_positions.setdefault(event_name, index)
        else:
            profile_events.append(event)
            profile_positions.setdefault(event_name, index)

    findings: list[TransitionFinding] = []
    if "ARTIFACT_ACCEPTED" in profile_positions and "RESULT_RECEIVED" not in profile_positions:
        findings.append(
            _finding(
                "RUNTIME_LIFECYCLE_SEQUENCE_INVALID",
                "error",
                "ARTIFACT_ACCEPTED exists without a prior RESULT_RECEIVED lifecycle event.",
                f"task_id={task_id or 'NONE'}",
                "Record RESULT_RECEIVED before ARTIFACT_ACCEPTED.",
            )
        )
    if "RESULT_ACCEPTED" in profile_positions:
        if "RESULT_RECEIVED" not in profile_positions:
            findings.append(
                _finding(
                    "RUNTIME_LIFECYCLE_SEQUENCE_INVALID",
                    "error",
                    "RESULT_ACCEPTED exists without a prior RESULT_RECEIVED lifecycle event.",
                    f"task_id={task_id or 'NONE'}",
                    "Record RESULT_RECEIVED before RESULT_ACCEPTED.",
                )
            )
        if "RESULT_VALIDATED" not in profile_positions:
            findings.append(
                _finding(
                    "RUNTIME_LIFECYCLE_SEQUENCE_INVALID",
                    "error",
                    "RESULT_ACCEPTED exists without RESULT_VALIDATED.",
                    f"task_id={task_id or 'NONE'}",
                    "Record RESULT_VALIDATED before RESULT_ACCEPTED for result-only outputs.",
                )
            )
    if "AGENT_TERMINATED" in profile_positions:
        if "RESULT_RECEIVED" not in profile_positions:
            findings.append(
                _finding(
                    "RUNTIME_LIFECYCLE_SEQUENCE_INVALID",
                    "error",
                    "AGENT_TERMINATED exists without RESULT_RECEIVED.",
                    f"task_id={task_id or 'NONE'}",
                    "Record RESULT_RECEIVED before AGENT_TERMINATED.",
                )
            )
        result_only_acceptance = _events_use_result_only_acceptance(profile_events)
        if result_only_acceptance:
            if "RESULT_ACCEPTED" not in profile_positions:
                findings.append(
                    _finding(
                        "RUNTIME_LIFECYCLE_SEQUENCE_INVALID",
                        "error",
                        "AGENT_TERMINATED exists without RESULT_ACCEPTED for a result-only output.",
                        f"task_id={task_id or 'NONE'}",
                        "Record RESULT_VALIDATED and RESULT_ACCEPTED before terminating a result-only agent.",
                    )
                )
        elif "ARTIFACT_ACCEPTED" not in profile_positions:
            findings.append(
                _finding(
                    "RUNTIME_LIFECYCLE_SEQUENCE_INVALID",
                    "error",
                    "AGENT_TERMINATED exists without ARTIFACT_ACCEPTED.",
                    f"task_id={task_id or 'NONE'}",
                    "Accept the artifact package before AGENT_TERMINATED.",
                )
            )
    if "AUDIT_ROUTE_READY" in profile_positions and "AGENT_TERMINATED" not in profile_positions:
        findings.append(
            _finding(
                "RUNTIME_LIFECYCLE_SEQUENCE_INVALID",
                "error",
                "AUDIT_ROUTE_READY exists without AGENT_TERMINATED.",
                f"task_id={task_id or 'NONE'}",
                "Record AGENT_TERMINATED before AUDIT_ROUTE_READY.",
            )
        )
    audit_result_recorded = bool(AUDIT_RESULT_EVENTS & set(auditor_positions))
    if "ARTIFACT_ACCEPTED" in auditor_positions and not audit_result_recorded:
        findings.append(
            _finding(
                "RUNTIME_LIFECYCLE_SEQUENCE_INVALID",
                "error",
                "Auditor ARTIFACT_ACCEPTED exists without a prior AUDIT_RESULT_RECEIVED lifecycle event.",
                f"task_id={task_id or 'NONE'}",
                "Record AUDIT_RESULT_RECEIVED before accepting the auditor artifact package.",
            )
        )
    if "AGENT_TERMINATED" in auditor_positions:
        if not audit_result_recorded:
            findings.append(
                _finding(
                    "RUNTIME_LIFECYCLE_SEQUENCE_INVALID",
                    "error",
                    "AUDITOR_AGENT_TERMINATED exists without AUDIT_RESULT_RECEIVED.",
                    f"task_id={task_id or 'NONE'}",
                    "Record AUDIT_RESULT_RECEIVED before AUDITOR_AGENT_TERMINATED.",
                )
            )
    if "AUDIT_ROUTE_READY" in auditor_positions and "AGENT_TERMINATED" not in auditor_positions:
        findings.append(
            _finding(
                "RUNTIME_LIFECYCLE_SEQUENCE_INVALID",
                "error",
                "Auditor AUDIT_ROUTE_READY exists without AUDITOR_AGENT_TERMINATED.",
                f"task_id={task_id or 'NONE'}",
                "Record AUDITOR_AGENT_TERMINATED before auditor route readiness.",
            )
        )
    return findings


def _lifecycle_state(
    contract: Mapping[str, Any],
    sidecars: Mapping[str, Mapping[str, object]],
    task_id: str,
) -> tuple[str, dict[str, object], tuple[TransitionFinding, ...]]:
    events = _lifecycle_events(sidecars)
    findings = _lifecycle_log_findings(sidecars)
    if not events:
        return "", {}, tuple(findings)

    if not task_id:
        task_id = _last_lifecycle_task_id(events)
    if not task_id:
        return "", {}, tuple(findings)
    relevant_events = _relevant_lifecycle_events(contract, events, task_id)
    if not relevant_events:
        return "", {}, tuple(findings)

    event_summaries: list[dict[str, object]] = []
    state = ""
    for event in relevant_events:
        event_name = _normalize_event(contract, event)
        event_state = LIFECYCLE_EVENT_STATES.get(event_name)
        auditor_event = _is_auditor_event(event, event_name)
        applied = False
        ignored_reason = ""
        if _is_auditor_bookkeeping_event(event, event_name):
            ignored_reason = "auditor_bookkeeping_not_task_route_state"
        elif event_name in AUDIT_RESULT_EVENTS and event_state:
            transition_state = _contract_transition_state(contract, state, event_name) if state else ""
            state = transition_state or event_state
            applied = True
        elif event_state:
            transition_state = _contract_transition_state(contract, state, event_name) if state else ""
            if transition_state:
                state = transition_state
                applied = True
            elif not state:
                state = event_state
                applied = True
            else:
                ignored_reason = "no_contract_transition_from_current_state"
        event_summary = {
            "event": event_name,
            "line": _event_line(event),
            "task_id": _event_task_id(event),
            "result_ref": _event_result_ref(event),
            "role": _event_role(event),
            "status": _event_status(event),
            "auditor_event": auditor_event,
            "applied_to_state": applied,
            "state_after": state,
        }
        if ignored_reason:
            event_summary["ignored_reason"] = ignored_reason
        event_summaries.append(event_summary)

    findings.extend(_lifecycle_sequence_findings(contract, relevant_events, task_id))
    signals: dict[str, object] = {
        "state_source": "lifecycle_log",
        "task_id": task_id,
        "lifecycle_event_count": len(relevant_events),
        "latest_lifecycle_event": event_summaries[-1]["event"] if event_summaries else "",
        "lifecycle_events": event_summaries,
    }
    return state, signals, tuple(findings)


def _lifecycle_consistency_findings(
    state: str,
    sidecars: Mapping[str, Mapping[str, object]],
    task: Mapping[str, object],
    task_id: str,
) -> list[TransitionFinding]:
    if state not in LIFECYCLE_PROGRESS_STATES or not task_id:
        return []

    findings: list[TransitionFinding] = []
    task_status = _text(task.get("status"))
    if state in {
        "RESULT_PENDING_ARTIFACT_ACCEPTANCE",
        "RESULT_VALIDATED",
        "ARTIFACT_PACKAGE_RECEIVED",
        "ARTIFACT_VALIDATED",
        "RESULT_ACCEPTED",
        "AGENT_TERMINATED",
        "AUDIT_PENDING",
    }:
        if task_status in {"ready", "pending"}:
            findings.append(
                _finding(
                    "RUNTIME_LIFECYCLE_TASK_REGISTRY_STALE",
                    "error",
                    "Lifecycle log shows progress for this task but TASK_REGISTRY still marks it pre-dispatch.",
                    f"task_id={task_id}; lifecycle_state={state}; task_status={task_status}",
                    "Update TASK_REGISTRY from lifecycle events or route using the transition engine derived state.",
                )
            )
        if state in {"RESULT_PENDING_ARTIFACT_ACCEPTANCE", "RESULT_VALIDATED"} and not _truthy_refs(task.get("result_refs")):
            findings.append(
                _finding(
                    "RUNTIME_LIFECYCLE_RESULT_REGISTRY_STALE",
                    "error",
                    "RESULT_RECEIVED exists but TASK_REGISTRY has no result_refs for this task.",
                    f"task_id={task_id}; task_status={task_status or 'NONE'}",
                    "Record the RESULT reference in TASK_REGISTRY or reconcile state from the lifecycle log.",
                )
            )
    if state == "AUDIT_PENDING" and task_status not in {"audit_pending", "audit_passed", "failed", "blocked", "completed"}:
        findings.append(
            _finding(
                "RUNTIME_LIFECYCLE_TASK_REGISTRY_STALE",
                "error",
                "Lifecycle log has reached audit routing but TASK_REGISTRY status is not audit-aware.",
                f"task_id={task_id}; lifecycle_state={state}; task_status={task_status or 'NONE'}",
                "Update TASK_REGISTRY to audit_pending or reconcile from lifecycle-derived state.",
            )
        )
    if state == "CHECKPOINT_ELIGIBLE" and task_status not in {"audit_passed", "checkpoint_done", "completed"}:
        findings.append(
            _finding(
                "RUNTIME_LIFECYCLE_CHECKPOINT_REGISTRY_STALE",
                "error",
                "Audit pass lifecycle progress conflicts with TASK_REGISTRY status.",
                f"task_id={task_id}; task_status={task_status or 'NONE'}",
                "Record audit-pass evidence before checkpoint planning.",
            )
        )
    if state == "CORRECTION_REQUIRED" and task_status not in {"failed", "blocked"}:
        findings.append(
            _finding(
                "RUNTIME_LIFECYCLE_CORRECTION_REGISTRY_STALE",
                "error",
                "Audit fail/correction lifecycle progress conflicts with TASK_REGISTRY status.",
                f"task_id={task_id}; task_status={task_status or 'NONE'}",
                "Route correction and update TASK_REGISTRY to failed or blocked.",
            )
        )

    accepted_events = [
        event
        for event in _relevant_lifecycle_events(_mapping({}), _lifecycle_events(sidecars), task_id)
        if _text(event.get("event_type") or event.get("event")) in {"ARTIFACT_ACCEPTED", "artifact_accepted"}
    ]
    accepted_entries = _accepted_artifact_entries(sidecars)
    if accepted_events and isinstance(_content(sidecars, "ACCEPTED_ARTIFACTS").get("artifacts"), list):
        for event in accepted_events:
            if _artifact_event_has_sidecar_entry(event, accepted_entries):
                continue
            findings.append(
                _finding(
                    "RUNTIME_LIFECYCLE_ARTIFACT_SIDECAR_STALE",
                    "error",
                    "ARTIFACT_ACCEPTED exists but ACCEPTED_ARTIFACTS has no matching accepted entry.",
                    f"task_id={task_id}; artifact_ref={_text(event.get('artifact_ref')) or 'NONE'}",
                    "Update ACCEPTED_ARTIFACTS from the artifact acceptance receipt.",
                )
            )
    return findings


def _infer_contract_state(
    contract: Mapping[str, Any] | None,
    sidecars: Mapping[str, Mapping[str, object]],
) -> tuple[str, dict[str, object], tuple[TransitionFinding, ...]]:
    project_state = _content(sidecars, "PROJECT_STATE")
    current_gate = _content(sidecars, "CURRENT_GATE")
    tasks = _tasks_by_id(sidecars)
    task_id = _active_task_id(project_state, current_gate)
    if not task_id:
        task_id = _single_active_task_id(tasks)
    lifecycle_findings: tuple[TransitionFinding, ...] = ()
    completed_signals: dict[str, object] = {
        "state_source": "sidecars",
        "task_id": task_id,
        "task_status": "",
        "current_phase": _text(project_state.get("current_phase")),
        "project_status": _text(project_state.get("project_status")),
    }
    if (
        _text(project_state.get("project_status")) == "completed"
        or _text(project_state.get("current_phase")) == "completed"
    ):
        return "PROJECT_COMPLETED", completed_signals, tuple(_lifecycle_log_findings(sidecars))

    if contract is not None:
        lifecycle_state, lifecycle_signals, lifecycle_findings = _lifecycle_state(contract, sidecars, task_id)
        if lifecycle_state:
            task_id = _text(lifecycle_signals.get("task_id")) or task_id
            task = tasks.get(task_id, {})
            lifecycle_signals.update(
                {
                    "task_status": _text(task.get("status")),
                    "current_phase": _text(project_state.get("current_phase")),
                    "project_status": _text(project_state.get("project_status")),
                }
            )
            findings = list(lifecycle_findings)
            findings.extend(_lifecycle_consistency_findings(lifecycle_state, sidecars, task, task_id))
            return lifecycle_state, lifecycle_signals, tuple(findings)

    task = tasks.get(task_id, {})
    task_status = _text(task.get("status"))
    current_phase = _text(project_state.get("current_phase"))
    project_status = _text(project_state.get("project_status"))
    audit_status = _text(project_state.get("audit_status"))
    checkpoint_eligibility = _text(project_state.get("checkpoint_eligibility"))
    checkpoint_eligibility_status = _text(project_state.get("checkpoint_eligibility_status"))
    project_checkpoint_status = _text(project_state.get("project_checkpoint_status"))
    checkpoint_preflight_status = _text(project_state.get("checkpoint_preflight_status"))
    checkpoint_receipt_ref = _truthy_text(project_state.get("checkpoint_receipt_ref"))
    current_gate_type = _text(current_gate.get("gate_type"))
    current_gate_required_role = _text(current_gate.get("required_next_role"))
    current_gate_status = _text(current_gate.get("status"))
    current_gate_checkpoint_status = _text(current_gate.get("project_checkpoint_status"))
    blockers = active_blockers_from_sidecars(sidecars)
    active_gaps = project_state.get("active_gaps")
    has_active_gaps = isinstance(active_gaps, list) and any(
        (isinstance(item, str) and not _is_none(item))
        or (isinstance(item, Mapping) and item)
        for item in active_gaps
    )
    has_audit_evidence = _has_audit_evidence(task, sidecars, task_id)

    signals: dict[str, object] = {
        "state_source": "sidecars",
        "task_id": task_id,
        "task_status": task_status,
        "current_phase": current_phase,
        "project_status": project_status,
        "audit_status": audit_status,
        "checkpoint_eligibility": checkpoint_eligibility,
        "checkpoint_eligibility_status": checkpoint_eligibility_status,
        "project_checkpoint_status": project_checkpoint_status,
        "checkpoint_preflight_status": checkpoint_preflight_status,
        "current_gate_type": current_gate_type,
        "current_gate_status": current_gate_status,
        "current_gate_required_next_role": current_gate_required_role,
    }

    if project_status == "archived":
        return "TERMINAL_STOP", signals, lifecycle_findings
    if task_status in {"failed", "blocked"} or current_phase == "correction" or audit_status == "failed":
        return "CORRECTION_REQUIRED", signals, lifecycle_findings
    if (
        current_phase in {"finalization", "final_acceptance"}
        and (
            project_checkpoint_status == "passed"
            or bool(checkpoint_receipt_ref)
            or current_gate_checkpoint_status == "passed"
        )
    ):
        return "FINAL_CHECKPOINT_COMPLETE", signals, lifecycle_findings
    if checkpoint_preflight_status == "passed" and task_status in {"audit_passed", "checkpoint_done", "completed"}:
        return "FINAL_AUDIT_PASS", signals, lifecycle_findings
    if task_status in {"audit_passed", "checkpoint_done", "completed"} or has_audit_evidence:
        return "CHECKPOINT_ELIGIBLE", signals, lifecycle_findings
    if audit_status == "passed" and (
        checkpoint_eligibility in {"local_only", "push_allowed"}
        or checkpoint_eligibility_status == "eligible"
        or current_gate.get("checkpoint_eligibility") in {"local_only", "push_allowed"}
        or current_gate.get("checkpoint_eligibility_status") == "eligible"
    ):
        return "CHECKPOINT_ELIGIBLE", signals, lifecycle_findings
    if task_status == "audit_pending":
        return "AUDIT_PENDING", signals, lifecycle_findings
    if current_gate_type == "audit" and current_gate_required_role == "auditor":
        return "AUDIT_PENDING", signals, lifecycle_findings
    if task_status == "running":
        if _truthy_refs(task.get("result_refs")):
            return "RESULT_PENDING_ARTIFACT_ACCEPTANCE", signals, lifecycle_findings
        return "AGENT_RUNNING", signals, lifecycle_findings
    if task_status in {"ready", "pending"}:
        return "TASK_READY", signals, lifecycle_findings
    if project_status == "blocked" or current_phase == "blocked" or blockers or has_active_gaps:
        return "OWNER_INPUT_REQUIRED", signals, lifecycle_findings
    if current_phase == "bootstrap" and not task_id:
        return "CORRECTION_REQUIRED", signals, lifecycle_findings
    if task_id and current_gate_status == "open":
        return "TASK_READY", signals, lifecycle_findings
    return "CORRECTION_REQUIRED", signals, lifecycle_findings


def infer_contract_state_from_sidecars(sidecars: Mapping[str, Mapping[str, object]]) -> str:
    state, _signals, _findings = _infer_contract_state(None, sidecars)
    return state


def recommendation_from_next_action_content(next_action: Mapping[str, object]) -> str:
    action_type = _text(next_action.get("action_type"))
    target_role = _text(next_action.get("target_role"))
    checkpoint_policy = _text(next_action.get("checkpoint_policy"))
    action_id = _text(next_action.get("action_id")).upper().replace("-", "_")
    instruction = _text(next_action.get("instruction_for_orchestrator")).upper().replace("-", "_")
    route_hint = f"{action_id} {instruction}"
    if "NO_NEXT_ACTION" in route_hint:
        return "NO_NEXT_ACTION"
    if "ACCEPT_RESULT" in route_hint:
        return "ACCEPT_RESULT"
    if "VALIDATE_ARTIFACT" in route_hint:
        return "VALIDATE_ARTIFACT"
    if "ACCEPT_ARTIFACT" in route_hint:
        return "ACCEPT_ARTIFACT"
    if "TERMINATE_AGENT" in route_hint:
        return "TERMINATE_AGENT"
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


def _canonical_input_summary(
    contract: Mapping[str, Any],
    sidecars: Mapping[str, Mapping[str, object]],
    signals: Mapping[str, object],
) -> dict[str, object]:
    task_id = _text(signals.get("task_id"))
    tasks = _tasks_by_id(sidecars)
    task = tasks.get(task_id, {})
    lifecycle_events = _lifecycle_events(sidecars)
    accepted_artifacts = _accepted_artifact_entries(sidecars)
    result_refs = _truthy_refs(task.get("result_refs"))
    audit_refs = _truthy_refs(task.get("audit_refs"))
    correction_links = _truthy_refs(task.get("correction_links"))
    artifact_receipt_refs: list[str] = []
    for event in lifecycle_events:
        for key in ("receipt_ref", "artifact_receipt_ref"):
            ref = _truthy_text(event.get(key))
            if ref:
                artifact_receipt_refs.append(ref)
        refs = event.get("artifact_receipt_refs")
        if isinstance(refs, list):
            artifact_receipt_refs.extend(item.strip() for item in refs if isinstance(item, str) and not _is_none(item))

    return {
        "task_registry": {
            "present": "TASK_REGISTRY" in sidecars,
            "task_count": len(tasks),
            "task_id": task_id or "NONE",
            "task_status": _text(task.get("status")) or "NONE",
            "result_refs": result_refs,
            "audit_refs": audit_refs,
        },
        "lifecycle_events": {
            "present": bool(lifecycle_events),
            "event_count": len(lifecycle_events),
            "latest_event": _text(signals.get("latest_lifecycle_event")) or "NONE",
        },
        "artifact_receipts": {
            "accepted_artifact_count": len(accepted_artifacts),
            "receipt_refs": sorted(dict.fromkeys(artifact_receipt_refs)),
        },
        "audit_results": {
            "task_audit_refs": audit_refs,
            "accepted_artifact_audit_refs": _accepted_artifact_audit_refs(sidecars, task_id),
            "current_gate_audit_evidence_refs": _current_gate_audit_refs(sidecars),
        },
        "current_gate": {
            "present": "CURRENT_GATE" in sidecars,
            "task_id": _truthy_text(_content(sidecars, "CURRENT_GATE").get("task_id")) or "NONE",
            "status": _truthy_text(_content(sidecars, "CURRENT_GATE").get("status")) or "NONE",
            "required_next_role": _truthy_text(_content(sidecars, "CURRENT_GATE").get("required_next_role")) or "NONE",
        },
        "correction_records": {
            "task_correction_links": correction_links,
            "project_phase": _truthy_text(_content(sidecars, "PROJECT_STATE").get("current_phase")) or "NONE",
            "active_blockers": active_blockers_from_sidecars(sidecars),
        },
        "runtime_contract": {
            "contract_version": _truthy_text(contract.get("contract_version")) or "NONE",
            "runtime_schema_version": _truthy_text(contract.get("runtime_schema_version")) or "NONE",
            "next_actions_by_state": sorted(_mapping(contract.get("next_actions_by_state"))),
        },
    }


def derived_next_action_cache_content(
    contract: Mapping[str, Any],
    sidecars: Mapping[str, Mapping[str, object]],
    decision: TransitionDecision | None = None,
) -> dict[str, object]:
    """Render the canonical NEXT_ACTION cache content from non-cache state inputs."""

    if decision is None:
        decision = explain_next_action_from_sidecars(contract, sidecars)
    existing = _content(sidecars, "NEXT_ACTION")
    action = decision.next_action
    recommended = _text(action.get("recommended_next_action")) or "NONE"
    action_type = _text(action.get("action_type")) or "update_state"
    target_role = _text(action.get("target_role")) or "orchestrator"
    signals = decision.inputs.get("sidecar_state_signals")
    signal_task_id = _text(signals.get("task_id")) if isinstance(signals, Mapping) else ""
    task_id = _text(action.get("task_id")) or signal_task_id
    task_packet = _text(action.get("task_packet")) or _canonical_task_packet(sidecars, task_id)
    checkpoint = recommended == "CHECKPOINT_PREFLIGHT"
    terminal = recommended == "NO_NEXT_ACTION" or action_type == "stop"
    stored_recommended = recommendation_from_next_action_content(existing)
    same_recommendation = _recommendations_match(contract, recommended, stored_recommended)
    existing_task_id = _truthy_text(existing.get("task_id"))
    same_route_identity = same_recommendation and existing_task_id in {"", task_id}
    derived_action_id = f"ACTION-{recommended.replace('_', '-')}-{task_id or 'GLOBAL'}"
    derived_instruction = (
        "NO_NEXT_ACTION: project is completed."
        if terminal and recommended == "NO_NEXT_ACTION"
        else f"Route lifecycle-derived next action {recommended}."
    )
    return {
        "action_id": existing.get("action_id", derived_action_id) if same_route_identity else derived_action_id,
        "action_type": action_type,
        "target_role": target_role,
        "task_id": "NONE" if terminal else task_id or "NONE",
        "task_packet": "NONE" if terminal else task_packet or "NONE",
        "dependency_status": "completed" if terminal else "ready",
        "blocked_by": [],
        "action_semantic": "stop_terminal" if terminal else "normal",
        "workspace_identity_required": bool(existing.get("workspace_identity_required")) if action_type == "create_agent" else False,
        "repository_lock_required": bool(existing.get("repository_lock_required")) if action_type == "create_agent" else False,
        "checkpoint_policy": _text(action.get("checkpoint_policy")) or ("local_only" if checkpoint else "no_checkpoint"),
        "checkpoint_preflight_required": checkpoint,
        "checkpoint_receipt_required": checkpoint,
        "checkpoint_receipt_ref": _truthy_text(existing.get("checkpoint_receipt_ref")) or "NONE",
        "requester_return_context": existing.get("requester_return_context", "NONE"),
        "blocking_or_resume_context": existing.get("blocking_or_resume_context", "NONE"),
        "required_universal_docs": existing.get("required_universal_docs", []),
        "required_project_docs": (
            existing.get("required_project_docs", [])
            if same_route_identity
            else action.get("required_docs", []) if isinstance(action.get("required_docs"), list) else []
        ),
        "expected_result": existing.get("expected_result", []),
        "instruction_for_orchestrator": existing.get("instruction_for_orchestrator", derived_instruction) if same_route_identity else derived_instruction,
    }


def next_action_cache_mismatches(stored: Mapping[str, object], expected: Mapping[str, object]) -> list[dict[str, object]]:
    mismatches: list[dict[str, object]] = []
    for field in DERIVED_NEXT_ACTION_CACHE_FIELDS:
        if field not in stored:
            continue
        if stored.get(field) == expected.get(field):
            continue
        mismatches.append(
            {
                "field": field,
                "expected": expected.get(field),
                "actual": stored.get(field),
            }
        )
    return mismatches


def explain_next_action_from_sidecars(
    contract: Mapping[str, Any],
    sidecars: Mapping[str, Mapping[str, object]],
) -> TransitionDecision:
    state, signals, inference_findings = _infer_contract_state(contract, sidecars)
    next_action_content = _content(sidecars, "NEXT_ACTION")
    task_id = _text(signals.get("task_id"))
    task_packet = _canonical_task_packet(sidecars, task_id)
    target_role = _canonical_target_role(sidecars, task_id)
    derived_action = derive_next_action(
        contract,
        state,
        target_role=target_role,
        task_id=task_id,
        task_packet=task_packet,
    )
    expected = _text(derived_action.get("recommended_next_action"))
    actual = recommendation_from_next_action_content(next_action_content)
    precheck_decision = TransitionDecision(
        inputs={
            "sidecar_state_signals": signals,
            "stored_next_action": {
                "action_type": next_action_content.get("action_type", ""),
                "target_role": _text(next_action_content.get("target_role")),
                "task_id": next_action_content.get("task_id", ""),
                "task_packet": _text(next_action_content.get("task_packet")),
                "checkpoint_policy": next_action_content.get("checkpoint_policy", ""),
            },
            "stored_recommended_next_action": actual,
        },
        transition_selected={
            "derivation": signals.get("state_source", "sidecars"),
            "state": state,
            "expected_recommended_next_action": expected,
        },
        findings=tuple(inference_findings),
        next_action=derived_action,
        reference_docs_used=(),
        allowed=not any(finding.severity == "error" for finding in inference_findings),
        current_state=state,
        event="",
        next_state=state,
    )
    expected_cache = derived_next_action_cache_content(contract, sidecars, precheck_decision)
    cache_mismatches = next_action_cache_mismatches(next_action_content, expected_cache)

    findings: list[TransitionFinding] = list(inference_findings)
    if not _recommendations_match(contract, expected, actual) or cache_mismatches:
        mismatch_evidence = (
            f"contract_state={state}; expected={expected or 'NONE'}; actual={actual or 'NONE'}; "
            f"cache_mismatches={json.dumps(cache_mismatches, sort_keys=True)}"
        )
        findings.append(
            _finding(
                "RUNTIME_NEXT_ACTION_STALE",
                "error",
                "Stored NEXT_ACTION cache differs from the transition engine derived next action.",
                mismatch_evidence,
                "Regenerate NEXT_ACTION from the runtime contract and current state sidecars.",
            )
        )
    if any(item.get("field") == "task_id" for item in cache_mismatches):
        findings.append(
            _finding(
                "STALE_NEXT_ACTION_TASK_ID",
                "error",
                "Stored NEXT_ACTION.task_id differs from the canonical active task.",
                json.dumps(
                    {
                        "expected_task_id": expected_cache.get("task_id"),
                        "actual_task_id": next_action_content.get("task_id", ""),
                        "contract_state": state,
                    },
                    sort_keys=True,
                ),
                "Regenerate NEXT_ACTION from canonical runtime state before routing.",
            )
        )
    if actual in {"CREATE_AGENT", "CREATE_AUDITOR"} and not role_registry.is_dispatchable_role(target_role, contract):
        findings.append(
            _finding(
                "RUNTIME_FORBIDDEN_DISPATCH_ROLE",
                "error",
                "Stored NEXT_ACTION targets a role that the runtime contract does not permit for dispatch.",
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
                "target_role": _text(next_action_content.get("target_role")),
                "task_id": next_action_content.get("task_id", ""),
                "task_packet": _text(next_action_content.get("task_packet")),
                "checkpoint_policy": next_action_content.get("checkpoint_policy", ""),
            },
            "stored_recommended_next_action": actual,
            "canonical_derivation_inputs": _canonical_input_summary(contract, sidecars, signals),
        },
        transition_selected={
            "derivation": signals.get("state_source", "sidecars"),
            "state": state,
            "expected_recommended_next_action": expected,
            "expected_cache_fields": {
                field: expected_cache.get(field)
                for field in DERIVED_NEXT_ACTION_CACHE_FIELDS
            },
            "cache_mismatches": cache_mismatches,
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
