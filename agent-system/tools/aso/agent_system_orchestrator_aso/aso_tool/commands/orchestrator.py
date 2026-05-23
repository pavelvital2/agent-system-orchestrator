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


EXIT_OK = 0
EXIT_IO_ERROR = 3


def _json_bytes(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


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
