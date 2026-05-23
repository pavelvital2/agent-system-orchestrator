"""Read-only dry-run planner for the next orchestrator action."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import state_verify


EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_IO_ERROR = 3

RULES_RELATIVE_PATH = Path("agent-system/09_validators/rules/governance_rules.json")
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}
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


def _is_none(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in NONE_VALUES)


def _as_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _content(sidecars: dict[str, dict[str, object]], sidecar_type: str) -> dict[str, object]:
    payload = sidecars.get(sidecar_type, {})
    content = payload.get("content")
    return content if isinstance(content, dict) else {}


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / RULES_RELATIVE_PATH).is_file():
            return parent
    return Path(__file__).resolve().parents[6]


def _rules_path(workspace_root: Path) -> Path:
    workspace_rules = workspace_root / RULES_RELATIVE_PATH
    if workspace_rules.is_file():
        return workspace_rules
    return _repo_root() / RULES_RELATIVE_PATH


def _load_governance_rules(workspace_root: Path) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    path = _rules_path(workspace_root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, {
            "path": str(path),
            "registry_id": "",
            "rule_count": 0,
            "load_error": str(exc),
        }

    rules: dict[str, dict[str, object]] = {}
    raw_rules = payload.get("rules") if isinstance(payload, dict) else None
    if isinstance(raw_rules, list):
        for item in raw_rules:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                rules[item["id"]] = item
    return rules, {
        "path": str(path),
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
    sidecars: dict[str, dict[str, object]],
    task: dict[str, object],
    task_id: str,
) -> dict[str, object]:
    task_status = _as_text(task.get("status"))
    task_audit_refs = _truthy_string_list(task.get("audit_refs"))
    artifact_audit_refs = _accepted_artifact_audit_refs(sidecars, task_id)
    current_gate_refs = _current_gate_audit_evidence(sidecars)
    present = bool(task_audit_refs or artifact_audit_refs or current_gate_refs)
    return {
        "present": present,
        "task_status": task_status,
        "task_audit_refs": task_audit_refs,
        "accepted_artifact_audit_refs": artifact_audit_refs,
        "current_gate_audit_evidence_refs": current_gate_refs,
    }


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


def _is_checkpoint_attempt(next_action: dict[str, object]) -> bool:
    return next_action.get("checkpoint_policy") in CHECKPOINT_PREFLIGHT_POLICIES


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


def _recommended_for_action_type(action_type: str, target_role: str, blockers: list[str]) -> str:
    if action_type == "create_agent":
        return "CREATE_AUDITOR" if target_role == "auditor" else "CREATE_AGENT"
    if action_type == "route_result":
        return "ROUTE_RESULT"
    if action_type == "update_state":
        return "UPDATE_STATE"
    if action_type == "wait_for_owner":
        return "ASK_OWNER"
    if action_type == "correction":
        return "CREATE_AGENT"
    if action_type == "finalize":
        return "FINALIZE"
    if action_type == "stop":
        return "STOP"
    return "ASK_OWNER" if blockers else "NONE"


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
    audit_evidence = _audit_pass_evidence(sidecars, task, task_id)

    blocking_rules = _state_verify_blockers(rules, verify_report)
    recommended_next_action = "NONE"

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
        blocking_rules.append(
            _rule(
                rules,
                "GOV-ACTION-SEMANTICS",
                "Active/open bootstrap with mandatory inputs cannot route to terminal STOP before first dispatch.",
                "route=repair_bootstrap_state/create_or_reference_bootstrap_task_packet",
            )
        )
    elif _is_checkpoint_attempt(next_action):
        if audit_evidence["present"]:
            recommended_next_action = "CHECKPOINT_PREFLIGHT"
        else:
            recommended_next_action = "CREATE_AUDITOR"
            target_role = "auditor"
            blocking_rules.append(
                _rule(
                    rules,
                    "GOV-CHECKPOINT-AUDIT-GATE",
                    "Checkpoint preflight is blocked because audit-pass evidence is absent.",
                    f"task_id={task_id or 'NONE'}",
                )
            )
    elif verify_exit_code != 0:
        recommended_next_action = "NONE"
    elif action_type == "wait_for_owner":
        recommended_next_action = "ASK_OWNER"
        blocking_rules.append(
            _rule(
                rules,
                "GOV-ACTION-SEMANTICS",
                "NEXT_ACTION requires owner-facing routing before dependent work continues.",
                f"action_type={action_type}",
            )
        )
    elif action_type in {"create_agent", "route_result", "update_state", "correction", "finalize", "stop"}:
        recommended_next_action = _recommended_for_action_type(action_type, target_role, blockers)

    blocking_rules = _dedupe_rules(blocking_rules)
    status = "blocked" if blocking_rules else "ready"
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
        "target_role": target_role,
        "task_id": task_id,
        "task_packet": task_packet,
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
            },
            "task": {
                "task_id": task_id,
                "status": task.get("status", ""),
                "result_refs": task.get("result_refs", []),
                "audit_refs": task.get("audit_refs", []),
            },
            "audit_pass_evidence": audit_evidence,
        },
    }


def _print_text(report: dict[str, object]) -> None:
    print(f"ASO plan-next: {str(report['status']).upper()} (dry-run/read-only)")
    print(f"Root: {report['root']}")
    print(f"Strict: {report['strict']}")
    print(f"Recommended next action: {report['recommended_next_action']}")
    print(f"Target role: {report['target_role'] or 'NONE'}")
    print(f"Task packet: {report['task_packet'] or 'NONE'}")
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


def run(args: argparse.Namespace) -> int:
    """Run the dry-run planner."""

    root = Path(args.root).expanduser()
    verify_report, verify_exit_code = state_verify._report(root, bool(args.strict))
    sidecars = _load_sidecars(root)
    rules, rules_evidence = _load_governance_rules(root)
    report = _plan(root, bool(args.strict), verify_report, verify_exit_code, sidecars, rules, rules_evidence)
    _print_text(report)
    if args.json_out and not _write_json(str(args.json_out), report):
        return EXIT_IO_ERROR
    return EXIT_OK if report["status"] == "ready" else EXIT_BLOCKED
