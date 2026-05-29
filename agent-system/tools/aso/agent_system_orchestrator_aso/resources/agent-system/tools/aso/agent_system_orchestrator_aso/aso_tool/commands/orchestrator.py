"""Read-only orchestrator conveyor summaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import output_policy
from . import plan_next
from . import state_verify
from .. import source_boundary
from .. import transition_engine


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3
NONE_REF = "NONE"
REFERENCE_CONTEXT_MODES = {"debug", "explain", "violation_recovery"}
CURRENT_TASK_TOKENS = {"current_task_packet", "current_test_packet", "current_audit_packet"}
TOKEN_DOC_MAP = {
    "agent_result_template": "agent-system/03_templates/AGENT_RESULT_TEMPLATE.md",
    "test_result_template": "agent-system/03_templates/AGENT_RESULT_TEMPLATE.md",
    "audit_result_template": "agent-system/03_templates/AGENT_RESULT_TEMPLATE.md",
    "artifact_contract_summary": "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json",
    "audit_rules_summary": "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json",
}


def _json_bytes(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _sidecar_content(root: Path, name: str) -> dict[str, Any] | None:
    payload = _read_json(root / "project-runtime" / "state" / f"{name}.json")
    content = payload.get("content") if isinstance(payload, dict) else None
    return content if isinstance(content, dict) else payload


def _as_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_context_path(value: object) -> str:
    text = _as_text(value).strip("`'\"")
    if not text or text.upper() == NONE_REF:
        return NONE_REF
    text = text.split("#", 1)[0].strip().replace("\\", "/")
    has_trailing_slash = text.endswith("/")
    parts = [part for part in text.split("/") if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        return text
    normalized = "/".join(parts)
    if has_trailing_slash:
        normalized = f"{normalized}/"
    return normalized


def _load_runtime_contract_for_root(root: Path) -> dict[str, Any]:
    root_contract = root / transition_engine.CONTRACT_RELATIVE_PATH
    if root_contract.is_file():
        return transition_engine.load_runtime_contract(root_contract)
    return transition_engine.load_runtime_contract()


def _handoff_context_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return _mapping(contract.get("handoff_context_builder_contract"))


def _broad_routine_paths(contract: dict[str, Any]) -> list[str]:
    handoff_contract = _handoff_context_contract(contract)
    return _string_list(handoff_contract.get("routine_handoff_excludes"))


def _is_broad_routine_reference(path: str, contract: dict[str, Any]) -> bool:
    clean_path = path.rstrip("/")
    for broad_path in _broad_routine_paths(contract):
        clean_broad = broad_path.rstrip("/")
        if broad_path.endswith("/"):
            if clean_path == clean_broad:
                return True
            if clean_path in {f"{clean_broad}/*", f"{clean_broad}/**"}:
                return True
            continue
        if clean_path == clean_broad:
            return True
    return False


def _context_finding(
    rule_id: str,
    title: str,
    details: str,
    field: str,
    path: str,
    recommendation: str,
) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "severity": "error",
        "title": title,
        "details": details,
        "field": field,
        "path": path,
        "recommendation": recommendation,
    }


def _state_refs(root: Path) -> list[dict[str, object]]:
    state_dir = root / "project-runtime" / "state"
    paths = sorted(state_dir.glob("*.json")) if state_dir.is_dir() else []
    if not paths:
        paths = [
            state_dir / "PROJECT_STATE.json",
            state_dir / "CURRENT_GATE.json",
            state_dir / "NEXT_ACTION.json",
        ]
    refs = [
        {
            "path": _rel(root, path),
            "kind": "state_sidecar",
            "exists": path.is_file(),
        }
        for path in paths
    ]
    instances_path = root / "project-runtime" / "agents" / "instances.jsonl"
    refs.append(
        {
            "path": _rel(root, instances_path),
            "kind": "agent_instances_log",
            "exists": instances_path.is_file(),
        }
    )
    return refs


def _doc_ref(path: str, why_needed: str, *, source: str = "routine") -> dict[str, object] | None:
    normalized = _normalize_context_path(path)
    if normalized == NONE_REF:
        return None
    return {
        "path": normalized,
        "sections": ["Bounded task-relevant sections"],
        "why_needed": why_needed,
        "source": source,
    }


def _dedupe_doc_refs(refs: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    result: list[dict[str, object]] = []
    for ref in refs:
        path = str(ref.get("path", ""))
        if not path or path in seen:
            continue
        seen.add(path)
        result.append(ref)
    return result


def _role_required_doc_refs(
    contract: dict[str, Any],
    target_role: str,
    task_packet: str,
) -> tuple[list[dict[str, object]], list[str]]:
    docs_by_role = _mapping(contract.get("required_docs_by_role"))
    tokens = _string_list(docs_by_role.get(target_role))
    refs: list[dict[str, object]] = []
    for token in tokens:
        if token in CURRENT_TASK_TOKENS:
            ref = _doc_ref(task_packet, f"Current {token} required by target role {target_role}.")
        else:
            path = TOKEN_DOC_MAP.get(token, token if "/" in token else "")
            ref = _doc_ref(path, f"Target role {target_role} requires {token}.")
        if ref is not None:
            refs.append(ref)
    return _dedupe_doc_refs(refs), tokens


def _current_next_action(root: Path) -> dict[str, Any]:
    return _sidecar_content(root, "NEXT_ACTION") or {}


def _context_report(root: Path, args: argparse.Namespace) -> tuple[dict[str, object], int]:
    contract = _load_runtime_contract_for_root(root)
    handoff_contract = _handoff_context_contract(contract)
    next_action = _current_next_action(root)
    context_mode = args.context_mode
    allowed_modes = set(_string_list(handoff_contract.get("allowed_context_modes")))
    target_role = _as_text(args.target_role) or _as_text(next_action.get("target_role") or next_action.get("TARGET_ROLE"))
    task_id = _as_text(next_action.get("task_id") or next_action.get("TASK_ID"))
    task_packet = _normalize_context_path(
        _as_text(args.task_packet) or _as_text(next_action.get("task_packet") or next_action.get("TASK_PACKET"))
    )
    current_event = _as_text(args.current_event)
    current_result = _normalize_context_path(
        _as_text(args.current_result) or _as_text(next_action.get("requester_return_context"))
    )
    current_artifact = _normalize_context_path(_as_text(args.current_artifact))
    reference_reason = _as_text(args.reference_reason)
    reference_docs = [_normalize_context_path(path) for path in args.reference_doc]

    findings: list[dict[str, str]] = []
    if context_mode not in allowed_modes:
        findings.append(
            _context_finding(
                "OCM-000",
                "Context mode is not allowed by the runtime contract",
                f"context_mode={context_mode} is not listed in handoff_context_builder_contract.allowed_context_modes.",
                "context_mode",
                context_mode,
                "Use a context mode declared in ORCHESTRATOR_RUNTIME_CONTRACT.json.",
            )
        )

    allowed_roles = set(_string_list(contract.get("allowed_roles")))
    if target_role and target_role not in allowed_roles and target_role not in {"orchestrator", "project_owner", "none", "NONE"}:
        findings.append(
            _context_finding(
                "OCM-002",
                "Target role is not a runtime role",
                f"target_role={target_role} is not allowed for a routine profile handoff.",
                "target_role",
                target_role,
                "Use a role from ORCHESTRATOR_RUNTIME_CONTRACT.allowed_roles.",
            )
        )

    if context_mode == "routine" and reference_docs:
        findings.append(
            _context_finding(
                "OCM-001",
                "Routine context includes reference docs",
                "Routine orchestrator context must not include broad or reference governance docs.",
                "reference_doc",
                ", ".join(reference_docs),
                "Use only routine handoff inputs, or rerun in debug/explain/recovery mode with a reason.",
            )
        )
    if context_mode in REFERENCE_CONTEXT_MODES and reference_docs and not (reference_reason or args.validator_required):
        findings.append(
            _context_finding(
                "OCM-003",
                "Reference docs lack explicit authorization",
                "Debug, explain, or recovery reference docs require --reference-reason or --validator-required.",
                "reference_doc",
                ", ".join(reference_docs),
                "Record why each reference doc is included.",
            )
        )

    for index, path in enumerate(reference_docs):
        if _is_broad_routine_reference(path, contract) and context_mode == "routine":
            findings.append(
                _context_finding(
                    "OCM-004",
                    "Routine context includes broad corpus material",
                    f"reference_doc[{index}] points at broad routine-forbidden context: {path}",
                    f"reference_doc[{index}]",
                    path,
                    "Replace it with a current task packet, state sidecar, artifact/result ref, or specific role doc.",
                )
            )

    role_doc_map = _mapping(handoff_contract.get("target_role_doc_map"))
    required_docs: list[dict[str, object]] = []
    runtime_contract_ref = _doc_ref(
        transition_engine.CONTRACT_RELATIVE_PATH.as_posix(),
        "Compact operational transition and routine context contract.",
    )
    if runtime_contract_ref is not None:
        runtime_contract_ref["sections"] = _string_list(handoff_contract.get("runtime_contract_required_sections"))
        required_docs.append(runtime_contract_ref)
    task_ref = _doc_ref(task_packet, "Current task packet for this bounded handoff.")
    if task_ref is not None:
        required_docs.append(task_ref)
    role_doc_path = _as_text(role_doc_map.get(target_role))
    role_doc_ref = _doc_ref(role_doc_path, f"Specific role instructions for target role {target_role}.")
    if role_doc_ref is not None:
        role_doc_ref["sections"] = ["Role rules for this target role"]
        required_docs.append(role_doc_ref)
    role_required_refs, role_required_tokens = _role_required_doc_refs(contract, target_role, task_packet)
    required_docs.extend(role_required_refs)
    required_docs = _dedupe_doc_refs(required_docs)

    reference_doc_refs: list[dict[str, object]] = []
    for path in reference_docs:
        ref = _doc_ref(
            path,
            reference_reason
            or ("Required by validator." if args.validator_required else "Explicit debug/explain reference."),
            source="validator_required" if args.validator_required else context_mode,
        )
        if ref is not None:
            ref["authorization"] = "validator_required" if args.validator_required else "explicit_reference_reason"
            reference_doc_refs.append(ref)
    allowed_sources = source_boundary.build_allowed_sources(
        contract=contract,
        task_id=task_id,
        role=target_role,
        task_packet=task_packet,
        required_docs=required_docs,
        reference_docs=reference_doc_refs,
        current_result=current_result,
        current_artifact=current_artifact,
    )

    summary = {
        "errors": len(findings),
        "warnings": 0,
        "required_docs_count": len(required_docs),
        "reference_docs_count": len(reference_doc_refs),
    }
    status = "fail" if findings else "pass"
    report: dict[str, object] = {
        "tool": "aso",
        "command": "orchestrator context",
        "root": str(root),
        "status": status,
        "read_only": True,
        "mutations_performed": False,
        "context_mode": context_mode,
        "target_role": target_role or NONE_REF,
        "task_id": task_id or NONE_REF,
        "task_packet": task_packet,
        "summary": summary,
        "findings": findings,
        "runtime_contract": {
            "path": transition_engine.CONTRACT_RELATIVE_PATH.as_posix(),
            "required_sections": _string_list(handoff_contract.get("runtime_contract_required_sections")),
        },
        "current_state": {
            "state_refs": _state_refs(root),
            "next_action": next_action,
        },
        "current_event_result_artifact_refs": {
            "event": current_event or NONE_REF,
            "result_or_audit_result": current_result,
            "artifact_manifest_or_receipt": current_artifact,
        },
        "allowed_sources": allowed_sources,
        "handoff_context": {
            "required_docs": required_docs,
            "reference_docs": reference_doc_refs,
            "target_role_required_doc_tokens": role_required_tokens,
            "routine_includes": _string_list(handoff_contract.get("routine_handoff_includes")),
            "routine_excludes": _broad_routine_paths(contract),
            "reference_doc_inclusion_rule": _as_text(handoff_contract.get("reference_doc_inclusion_rule")),
        },
    }
    return report, EXIT_FINDINGS if findings else EXIT_OK


def _plan_next_report(root: Path) -> dict[str, object]:
    verify_report, verify_exit_code = state_verify._report(root, strict=False)
    sidecars = plan_next._load_sidecars(root)
    rules, rules_evidence = plan_next._load_governance_rules(root)
    return plan_next._plan(
        root,
        False,
        verify_report,
        verify_exit_code,
        sidecars,
        rules,
        rules_evidence,
    )


def _dispatchability_from_plan(report: dict[str, object]) -> dict[str, object]:
    dispatchability = report.get("dispatchability")
    return dispatchability if isinstance(dispatchability, dict) else {}


def _reason_codes(dispatchability: dict[str, object]) -> list[str]:
    reasons = dispatchability.get("reasons")
    if not isinstance(reasons, list):
        return []
    codes: list[str] = []
    for reason in reasons:
        if isinstance(reason, dict) and isinstance(reason.get("reason_code"), str):
            codes.append(reason["reason_code"])
    return codes


def _next_route_summary(plan_report: dict[str, object]) -> dict[str, object]:
    dispatchability = _dispatchability_from_plan(plan_report)
    return {
        "source_command": "plan-next",
        "plan_next_status": plan_report.get("status"),
        "recommended_next_action": plan_report.get("recommended_next_action"),
        "dispatchable": bool(dispatchability.get("dispatchable")),
        "verdict": dispatchability.get("verdict"),
        "reason_codes": _reason_codes(dispatchability),
        "reasons": dispatchability.get("reasons", []),
        "blocking_rules": plan_report.get("blocking_rules", []),
        "live_dispatch_performed": bool(dispatchability.get("live_dispatch_performed")),
    }


def _write_json_out(root: Path, path_text: str, payload: dict[str, object]) -> tuple[bool, str]:
    path = output_policy.resolve_output_path(path_text)
    error = output_policy.validate_generated_output_path(
        root,
        path,
        allowed_workspace_subdirs=("project-runtime/reports",),
    )
    if error is not None:
        return False, f"{error.rule_id}: {error.message}: {error.evidence}"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_json_bytes(payload), encoding="utf-8")
    except OSError as exc:
        return False, str(exc)
    return True, ""


def _status_report(root: Path) -> dict[str, object]:
    project_state = _sidecar_content(root, "PROJECT_STATE") or {}
    current_gate = _sidecar_content(root, "CURRENT_GATE") or {}
    next_action = _sidecar_content(root, "NEXT_ACTION") or {}
    plan_report = _plan_next_report(root)
    dispatchability = _dispatchability_from_plan(plan_report)
    next_route = _next_route_summary(plan_report)
    return {
        "tool": "aso",
        "command": "orchestrator status",
        "root": str(root),
        "status": "pass",
        "read_only": True,
        "mutations_performed": False,
        "recommended_next_action": plan_report.get("recommended_next_action"),
        "dispatchable": bool(dispatchability.get("dispatchable")),
        "dispatchability": dispatchability,
        "handoff_artifact": plan_report.get("handoff_artifact", {}),
        "next_route": next_route,
        "summary": {
            "current_phase": project_state.get("current_phase") or project_state.get("CURRENT_PHASE"),
            "project_status": project_state.get("project_status") or project_state.get("PROJECT_STATUS"),
            "gate_type": current_gate.get("gate_type") or current_gate.get("GATE_TYPE"),
            "gate_status": current_gate.get("status")
            or current_gate.get("gate_status")
            or current_gate.get("GATE_STATUS"),
            "next_action_type": next_action.get("action_type") or next_action.get("ACTION_TYPE"),
            "next_role": next_action.get("target_role")
            or next_action.get("TARGET_ROLE")
            or next_action.get("next_role")
            or next_action.get("NEXT_ROLE"),
            "task_packet": next_action.get("task_packet") or next_action.get("TASK_PACKET"),
            "next_recommended_action": plan_report.get("recommended_next_action"),
            "next_dispatchable": bool(dispatchability.get("dispatchable")),
            "next_dispatchability_verdict": dispatchability.get("verdict"),
            "next_dispatchability_reason_codes": next_route["reason_codes"],
        },
        "context_budget": {
            "normal_flow_docs": [
                "agent-system/00_start/ORCHESTRATOR_START.md",
                "agent-system/02_runtime/ORCHESTRATOR_CONVEYOR_PROTOCOL.md",
            ],
            "preferred_inputs": [
                "project-runtime/state/*.json",
                "project-runtime/receipts/**/*.json",
                "project-runtime/reports/**/*.json",
            ],
        },
    }


def _next_report(root: Path) -> dict[str, object]:
    next_action = _sidecar_content(root, "NEXT_ACTION") or {}
    plan_report = _plan_next_report(root)
    dispatchability = _dispatchability_from_plan(plan_report)
    return {
        "tool": "aso",
        "command": "orchestrator next",
        "root": str(root),
        "status": "pass",
        "read_only": True,
        "mutations_performed": False,
        "recommended_next_action": plan_report.get("recommended_next_action"),
        "dispatchable": bool(dispatchability.get("dispatchable")),
        "dispatchability": dispatchability,
        "handoff_artifact": plan_report.get("handoff_artifact", {}),
        "next_route": _next_route_summary(plan_report),
        "next_action": next_action,
        "summary": {
            "action_type": next_action.get("action_type") or next_action.get("ACTION_TYPE"),
            "target_role": next_action.get("target_role") or next_action.get("TARGET_ROLE"),
            "task_id": next_action.get("task_id") or next_action.get("TASK_ID"),
            "task_packet": next_action.get("task_packet") or next_action.get("TASK_PACKET"),
            "recommended_next_action": plan_report.get("recommended_next_action"),
            "dispatchable": bool(dispatchability.get("dispatchable")),
            "dispatchability_verdict": dispatchability.get("verdict"),
            "dispatchability_reason_codes": _reason_codes(dispatchability),
        },
    }


def _run(args: argparse.Namespace, report: dict[str, object]) -> int:
    if args.json_out:
        ok, error = _write_json_out(Path(args.root).expanduser(), str(args.json_out), report)
        if not ok:
            print(f"aso {report['command']}: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
    if not args.json_out or args.format == "json":
        print(_json_bytes(report), end="")
    elif not args.json_out:
        print(f"ASO {report['command']}: {str(report['status']).upper()}")
    return EXIT_OK


def run_status(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    return _run(args, _status_report(root))


def run_next(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    return _run(args, _next_report(root))


def run_context(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    report, exit_code = _context_report(root, args)
    if args.json_out:
        ok, error = _write_json_out(root, str(args.json_out), report)
        if not ok:
            print(f"aso {report['command']}: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
    if not args.json_out or args.format == "json":
        print(_json_bytes(report), end="")
    elif exit_code != EXIT_OK:
        print(f"ASO {report['command']}: {str(report['status']).upper()}", file=sys.stderr)
    return exit_code
