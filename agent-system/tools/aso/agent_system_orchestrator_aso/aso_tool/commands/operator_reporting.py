"""Stage 1 compact operator monitoring and final receipt reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

from .. import result_parser
from .. import transition_engine
from ..timestamps import utc_timestamp
from . import output_policy
from . import plan_next
from . import state_verify


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}
EVENT_LOG_REL = Path("project-runtime/events/operator_events.jsonl")
FINAL_RUN_RECEIPT_JSON_REL = Path("project-runtime/reports/FINAL_RUN_RECEIPT.json")
FINAL_RUN_RECEIPT_MD_REL = Path("project-runtime/reports/FINAL_RUN_RECEIPT.md")
OPERATOR_REPORT_JSON_REL = Path("project-runtime/reports/OPERATOR_REPORT.json")
OPERATOR_REPORT_MD_REL = Path("project-runtime/reports/OPERATOR_REPORT.md")
COMPACT_STDOUT_MAX_BYTES = 12_000
FINAL_RECEIPT_REQUIRED_MARKDOWN_FIELDS = (
    "product_tests",
    "commits",
    "agents",
    "tasks",
    "artifacts",
    "manual_nudges",
    "known_limitations",
)
FINAL_RECEIPT_ADDITIONAL_MARKDOWN_FIELDS = (
    "results",
    "audits",
    "mutation_receipts",
    "monitor_summary",
    "report_paths",
)


def _json_bytes(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _content(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    content = payload.get("content")
    return dict(content) if isinstance(content, Mapping) else dict(payload)


def _load_state_sidecars(root: Path) -> dict[str, dict[str, Any]]:
    state_root = root / "project-runtime" / "state"
    sidecars: dict[str, dict[str, Any]] = {}
    for path in sorted(state_root.glob("*.json")) if state_root.is_dir() else []:
        payload = _read_json(path)
        if payload is None:
            continue
        sidecar_type = str(payload.get("sidecar_type") or path.stem).strip() or path.stem
        sidecars[sidecar_type] = payload
    return sidecars


def _sidecar_content(sidecars: Mapping[str, Mapping[str, Any]], name: str) -> dict[str, Any]:
    return _content(sidecars.get(name))


def _text(value: object, default: str = "NONE") -> str:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else default
    if value is None:
        return default
    return str(value)


def _is_none(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in NONE_VALUES)


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _string_list(value: object) -> list[str]:
    result: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and not _is_none(item):
                result.append(item.strip())
            elif isinstance(item, Mapping) and item:
                result.append(json.dumps(dict(item), sort_keys=True))
    elif isinstance(value, str) and not _is_none(value):
        result.append(value.strip())
    return result


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve_ref_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return root / path


def _path_ref(root: Path, path: Path) -> dict[str, object]:
    ref = _rel(root, path)
    if not path.is_file():
        return {"path": ref, "exists": False}
    data = path.read_bytes()
    return {
        "path": ref,
        "exists": True,
        "sha256": _sha256_bytes(data),
        "size_bytes": len(data),
    }


def _refs(root: Path, values: Iterable[str]) -> list[dict[str, object]]:
    return [_path_ref(root, _resolve_ref_path(root, value)) for value in values if value]


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_bytes(payload), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_allowed_report(root: Path, path_text: str, text: str) -> tuple[bool, str, dict[str, object]]:
    path = output_policy.resolve_output_path(path_text, base=root)
    error = output_policy.validate_generated_output_path(
        root,
        path,
        allowed_workspace_subdirs=("project-runtime/reports",),
    )
    if error is not None:
        return False, f"{error.rule_id}: {error.message}: {error.evidence}", {}
    try:
        _write_text(path, text)
    except OSError as exc:
        return False, str(exc), {}
    return True, "", _path_ref(root, path)


def _state_verify_summary(root: Path) -> tuple[dict[str, object], int]:
    try:
        return state_verify._report(root, False)
    except Exception as exc:  # pragma: no cover - defensive report surface
        return {
            "status": "failed",
            "summary": {},
            "findings": [
                {
                    "rule_id": "OPERATOR_STATE_VERIFY_FAILED",
                    "severity": "error",
                    "message": str(exc),
                    "path": "project-runtime/state",
                    "recommendation": "Run aso state verify for the full failure.",
                }
            ],
        }, EXIT_FINDINGS


def _plan_next_summary(root: Path) -> dict[str, object]:
    verify_report, verify_exit_code = _state_verify_summary(root)
    sidecars = plan_next._load_sidecars(root)
    rules, rules_evidence = plan_next._load_governance_rules(root)
    return plan_next._plan(root, False, verify_report, verify_exit_code, sidecars, rules, rules_evidence)


def _transition_summary(root: Path, sidecars: Mapping[str, Mapping[str, Any]]) -> dict[str, object]:
    try:
        contract = transition_engine.load_runtime_contract()
        return transition_engine.routing_authority_report(contract, sidecars, root=root)
    except (OSError, transition_engine.RuntimeContractError) as exc:
        return {
            "allowed": False,
            "contract_authoritative": True,
            "canonical_recommended_next_action": "NONE",
            "current_state": "UNKNOWN",
            "findings": [
                {
                    "rule_id": "OPERATOR_RUNTIME_CONTRACT_LOAD_FAILED",
                    "severity": "error",
                    "message": "Runtime contract could not be loaded.",
                    "evidence": str(exc),
                    "recommendation": "Restore ORCHESTRATOR_RUNTIME_CONTRACT.json before operator reporting.",
                }
            ],
        }


def _task_entries(sidecars: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    tasks = _sidecar_content(sidecars, "TASK_REGISTRY").get("tasks")
    return [dict(item) for item in tasks if isinstance(item, Mapping)] if isinstance(tasks, list) else []


def _current_task(sidecars: Mapping[str, Mapping[str, Any]]) -> dict[str, object]:
    next_action = _sidecar_content(sidecars, "NEXT_ACTION")
    task_id = _text(next_action.get("task_id"), "")
    for task in _task_entries(sidecars):
        if _text(task.get("task_id"), "") == task_id:
            return {
                "task_id": task_id or "NONE",
                "status": _text(task.get("status")),
                "task_packet": _text(task.get("task_packet")),
                "role": _text(task.get("owner_role") or task.get("task_type")),
                "result_refs": _string_list(task.get("result_refs")),
                "audit_refs": _string_list(task.get("audit_refs")),
            }
    return {
        "task_id": task_id or "NONE",
        "status": "NONE",
        "task_packet": _text(next_action.get("task_packet")),
        "role": _text(next_action.get("target_role")),
        "result_refs": [],
        "audit_refs": [],
    }


def _active_blockers(sidecars: Mapping[str, Mapping[str, Any]]) -> list[str]:
    blockers = transition_engine.active_blockers_from_sidecars(sidecars)
    next_action = _sidecar_content(sidecars, "NEXT_ACTION")
    current_gate = _sidecar_content(sidecars, "CURRENT_GATE")
    blockers.extend(_string_list(next_action.get("blocked_by")))
    blockers.extend(_string_list(next_action.get("blocking_or_resume_context")))
    blockers.extend(_string_list(current_gate.get("blocking_status")))
    return sorted(dict.fromkeys(item for item in blockers if not _is_none(item)))


def _waiting_for(
    *,
    blockers: list[str],
    next_action: Mapping[str, Any],
    recommended_next_action: str,
    dispatchable: bool,
) -> str:
    if blockers:
        return "blocker_resolution"
    action_type = _text(next_action.get("action_type"), "")
    target_role = _text(next_action.get("target_role"), "")
    if recommended_next_action in {"NO_NEXT_ACTION", "STOP"} or action_type == "stop":
        return "none"
    if action_type == "wait_for_owner" or recommended_next_action == "ASK_OWNER":
        return "project_owner"
    if recommended_next_action == "CHECKPOINT_PREFLIGHT":
        return "checkpoint_preflight"
    if recommended_next_action == "FINALIZE" or action_type == "finalize":
        return "finalization"
    if dispatchable and target_role:
        return target_role
    if target_role and target_role not in {"none", "NONE"}:
        return target_role
    return action_type or "UNKNOWN"


def _final_receipt_refs(root: Path) -> dict[str, object]:
    return {
        "json": _path_ref(root, root / FINAL_RUN_RECEIPT_JSON_REL),
        "markdown": _path_ref(root, root / FINAL_RUN_RECEIPT_MD_REL),
        "lifecycle_finalization": _path_ref(root, root / "project-runtime/receipts/lifecycle/PROJECT_FINALIZATION_RECEIPT.json"),
    }


def build_monitor_summary(root: Path) -> dict[str, object]:
    sidecars = _load_state_sidecars(root)
    project_state = _sidecar_content(sidecars, "PROJECT_STATE")
    current_gate = _sidecar_content(sidecars, "CURRENT_GATE")
    next_action = _sidecar_content(sidecars, "NEXT_ACTION")
    state_report, state_exit = _state_verify_summary(root)
    plan_report = _plan_next_summary(root)
    dispatchability = plan_report.get("dispatchability")
    dispatchable = bool(dispatchability.get("dispatchable")) if isinstance(dispatchability, Mapping) else False
    transition = _transition_summary(root, sidecars)
    recommended = _text(plan_report.get("recommended_next_action") or transition.get("canonical_recommended_next_action"))
    blockers = _active_blockers(sidecars)
    terminal_state = (
        "PROJECT_COMPLETED"
        if project_state.get("project_status") == "completed" and next_action.get("action_type") == "stop"
        else _text(transition.get("current_state"), "UNKNOWN")
    )
    status = "pass" if state_exit == 0 else "fail"
    return {
        "tool": "aso",
        "command": "monitor-summary",
        "status": status,
        "read_only": True,
        "mutations_performed": False,
        "root": str(root),
        "current_phase": _text(project_state.get("current_phase"), "UNKNOWN"),
        "project_status": _text(project_state.get("project_status"), "UNKNOWN"),
        "active_blocker": blockers[0] if blockers else "NONE",
        "active_blockers": blockers,
        "waiting_for": _waiting_for(
            blockers=blockers,
            next_action=next_action,
            recommended_next_action=recommended,
            dispatchable=dispatchable,
        ),
        "audit_status": _text(project_state.get("audit_status"), "UNKNOWN"),
        "terminal_state": terminal_state,
        "recommended_next_action": recommended,
        "dispatchable": dispatchable,
        "current_task": _current_task(sidecars),
        "current_gate": {
            "gate_type": _text(current_gate.get("gate_type"), "UNKNOWN"),
            "status": _text(current_gate.get("status") or current_gate.get("gate_status"), "UNKNOWN"),
            "required_next_role": _text(current_gate.get("required_next_role"), "UNKNOWN"),
        },
        "next_action": {
            "action_type": _text(next_action.get("action_type"), "UNKNOWN"),
            "target_role": _text(next_action.get("target_role"), "UNKNOWN"),
            "task_id": _text(next_action.get("task_id"), "NONE"),
            "task_packet": _text(next_action.get("task_packet"), "NONE"),
        },
        "audit": {
            "status": _text(project_state.get("audit_status"), "UNKNOWN"),
            "task_audit_refs": _current_task(sidecars)["audit_refs"],
        },
        "final_receipt": _final_receipt_refs(root),
        "state_verify": {
            "status": state_report.get("status", "unknown"),
            "summary": state_report.get("summary", {}),
            "finding_count": len(state_report.get("findings", [])) if isinstance(state_report.get("findings"), list) else 0,
        },
        "transition_engine": {
            "current_state": transition.get("current_state", "UNKNOWN"),
            "canonical_recommended_next_action": transition.get("canonical_recommended_next_action", "NONE"),
            "contract_authoritative": bool(transition.get("contract_authoritative")),
        },
    }


def _compact_monitor(summary: Mapping[str, object]) -> dict[str, object]:
    return {
        "tool": "aso",
        "command": summary.get("command", "monitor-summary"),
        "status": summary.get("status", "unknown"),
        "root": summary.get("root", ""),
        "current_phase": summary.get("current_phase", "UNKNOWN"),
        "project_status": summary.get("project_status", "UNKNOWN"),
        "active_blocker": summary.get("active_blocker", "NONE"),
        "active_blocker_count": len(summary.get("active_blockers", [])) if isinstance(summary.get("active_blockers"), list) else 0,
        "waiting_for": summary.get("waiting_for", "UNKNOWN"),
        "audit_status": summary.get("audit_status", "UNKNOWN"),
        "terminal_state": summary.get("terminal_state", "UNKNOWN"),
        "recommended_next_action": summary.get("recommended_next_action", "NONE"),
        "dispatchable": bool(summary.get("dispatchable")),
        "current_task": summary.get("current_task", {}),
        "final_receipt": summary.get("final_receipt", {}),
    }


def _print_monitor_text(summary: Mapping[str, object]) -> None:
    print(f"ASO monitor summary: {str(summary.get('status', 'unknown')).upper()}")
    print(f"Current phase: {summary.get('current_phase', 'UNKNOWN')}")
    print(f"Project status: {summary.get('project_status', 'UNKNOWN')}")
    print(f"Active blocker: {summary.get('active_blocker', 'NONE')}")
    print(f"Waiting for: {summary.get('waiting_for', 'UNKNOWN')}")
    print(f"Audit status: {summary.get('audit_status', 'UNKNOWN')}")
    print(f"Terminal state: {summary.get('terminal_state', 'UNKNOWN')}")
    print(f"Recommended next action: {summary.get('recommended_next_action', 'NONE')}")


def _load_events(root: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for relpath in (Path("project-runtime/agents/instances.jsonl"), EVENT_LOG_REL):
        path = root / relpath
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                payload.setdefault("_source_log", relpath.as_posix())
                events.append(payload)
    return events


def _agent_summary(events: list[dict[str, Any]]) -> list[dict[str, object]]:
    agents: dict[str, dict[str, object]] = {}
    for event in events:
        agent_id = _text(event.get("agent_instance_id"), "")
        if not agent_id:
            continue
        record = agents.setdefault(
            agent_id,
            {
                "agent_instance_id": agent_id,
                "role": _text(event.get("role") or event.get("agent_role"), "UNKNOWN"),
                "task_id": _text(event.get("task_id"), "NONE"),
                "latest_event_type": "NONE",
                "result_ref": "NONE",
                "status": "UNKNOWN",
            },
        )
        record["latest_event_type"] = _text(event.get("event_type") or event.get("event"), "UNKNOWN")
        if not _is_none(event.get("result_ref")):
            record["result_ref"] = _text(event.get("result_ref"))
        if not _is_none(event.get("status") or event.get("result_status")):
            record["status"] = _text(event.get("status") or event.get("result_status"), "UNKNOWN")
    return sorted(agents.values(), key=lambda item: str(item.get("agent_instance_id", "")))


def _scan_results(root: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str], list[str]]:
    results: list[dict[str, object]] = []
    audits: list[dict[str, object]] = []
    product_tests: list[str] = []
    known_limitations: list[str] = []
    results_root = root / "project-runtime" / "results"
    for path in sorted(results_root.glob("**/*.md")) if results_root.is_dir() else []:
        try:
            parsed = result_parser.parse_result_file(path)
        except OSError:
            continue
        entry = {
            "path": _rel(root, path),
            "result_type": parsed.result_type,
            "task_id": parsed.task_id or "NONE",
            "agent_instance_id": parsed.agent_instance_id or "NONE",
            "role": parsed.role or "UNKNOWN",
            "status": parsed.status or "UNKNOWN",
            "tests_run": parsed.as_list("TESTS_RUN"),
            "commands_run": parsed.as_list("COMMANDS_RUN"),
            "limitations": parsed.as_list("LIMITATIONS"),
        }
        if parsed.result_type == "audit_result":
            entry["audit"] = parsed.audit.to_json()
            audits.append(entry)
        else:
            results.append(entry)
        for item in parsed.as_list("TESTS_RUN"):
            if item.upper() != "NONE":
                product_tests.append(f"{_rel(root, path)}: {item}")
        for item in parsed.as_list("LIMITATIONS"):
            if item.upper() != "NONE":
                known_limitations.append(f"{_rel(root, path)}: {item}")
    return results, audits, sorted(dict.fromkeys(product_tests)), sorted(dict.fromkeys(known_limitations))


def _artifact_summary(root: Path, sidecars: Mapping[str, Mapping[str, Any]]) -> list[dict[str, object]]:
    artifacts: list[dict[str, object]] = []
    accepted = _sidecar_content(sidecars, "ACCEPTED_ARTIFACTS").get("artifacts")
    if isinstance(accepted, list):
        for item in accepted:
            if isinstance(item, Mapping):
                artifact = dict(item)
                ref = _text(artifact.get("artifact_ref"), "")
                if ref:
                    artifact["artifact_ref_details"] = _path_ref(root, root / ref)
                artifacts.append(artifact)
    for manifest in sorted((root / "project-runtime" / "artifacts" / "accepted").glob("**/manifest.json")):
        artifacts.append({"manifest": _path_ref(root, manifest)})
    return artifacts


def _dispatch_receipts(root: Path) -> list[dict[str, object]]:
    receipts: list[dict[str, object]] = []
    dispatch_root = root / "project-runtime" / "agents" / "dispatches"
    for path in sorted(dispatch_root.glob("*.json")) if dispatch_root.is_dir() else []:
        payload = _read_json(path) or {}
        receipts.append(
            {
                "path": _rel(root, path),
                "sha256": _path_ref(root, path).get("sha256"),
                "agent_instance_id": _text(payload.get("agent_instance_id"), "UNKNOWN"),
                "task_id": _text(payload.get("task_id"), "NONE"),
                "role": _text(payload.get("role") or payload.get("target_role"), "UNKNOWN"),
            }
        )
    return receipts


def _manual_nudges(events: list[dict[str, Any]]) -> list[object]:
    nudges: list[object] = []
    for event in events:
        for key in ("manual_nudge_markers", "manual_nudges", "manual_nudge"):
            value = event.get(key)
            if isinstance(value, list):
                nudges.extend(item for item in value if not _is_none(item))
            elif not _is_none(value):
                nudges.append(value)
    return nudges


def _mutation_receipts(events: list[dict[str, Any]]) -> list[object]:
    receipts: list[object] = []
    for event in events:
        for key in ("mutation_receipts", "mutation_receipt", "receipt_ref", "artifact_receipt_refs"):
            value = event.get(key)
            if isinstance(value, list):
                receipts.extend(item for item in value if not _is_none(item))
            elif not _is_none(value):
                receipts.append(value)
    return receipts


def _commits(root: Path, sidecars: Mapping[str, Mapping[str, Any]]) -> list[dict[str, object]]:
    commits: list[dict[str, object]] = []
    project_state = _sidecar_content(sidecars, "PROJECT_STATE")
    last_commit = _text(project_state.get("last_commit_hash"), "")
    if last_commit and not _is_none(last_commit):
        commits.append(
            {
                "source": "PROJECT_STATE",
                "commit": last_commit,
                "branch": _text(project_state.get("last_commit_branch")),
                "push_status": _text(project_state.get("push_status")),
            }
        )
    for task in _task_entries(sidecars):
        commit_hash = _text(task.get("commit_hash"), "")
        if commit_hash and not _is_none(commit_hash):
            commits.append(
                {
                    "source": "TASK_REGISTRY",
                    "task_id": _text(task.get("task_id")),
                    "commit": commit_hash,
                    "branch": _text(task.get("branch")),
                    "push_status": _text(task.get("push_status")),
                }
            )
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=False,
            text=True,
            capture_output=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        result = None
    if result is not None and result.returncode == 0:
        commits.append({"source": "git", "commit": result.stdout.strip(), "branch": "HEAD"})
    return commits


def build_operator_report(root: Path) -> dict[str, object]:
    sidecars = _load_state_sidecars(root)
    events = _load_events(root)
    monitor = build_monitor_summary(root)
    state_report, state_exit = _state_verify_summary(root)
    results, audits, product_tests, known_limitations = _scan_results(root)
    blockers = monitor.get("active_blockers") if isinstance(monitor.get("active_blockers"), list) else []
    return {
        "tool": "aso",
        "command": "report operator",
        "report_schema_version": "1.0.0",
        "generated_at": utc_timestamp(),
        "root": str(root),
        "status": "pass" if state_exit == 0 else "fail",
        "read_only": True,
        "mutations_performed": False,
        "monitor_summary": monitor,
        "state_verify": {
            "status": state_report.get("status", "unknown"),
            "summary": state_report.get("summary", {}),
            "finding_count": len(state_report.get("findings", [])) if isinstance(state_report.get("findings"), list) else 0,
            "findings": state_report.get("findings", []),
        },
        "agents": _agent_summary(events),
        "handoffs": _dispatch_receipts(root),
        "results": results,
        "audits": audits,
        "tasks": _task_entries(sidecars),
        "artifacts": _artifact_summary(root, sidecars),
        "blockers": blockers,
        "manual_nudges": _manual_nudges(events),
        "mutation_receipts": _mutation_receipts(events),
        "product_tests": product_tests,
        "known_limitations": known_limitations,
        "stdout_policy": {
            "default": "compact",
            "full_report_requires": ["--diff-mode full"],
            "compact_stdout_max_bytes": COMPACT_STDOUT_MAX_BYTES,
        },
    }


def _operator_compact(report: Mapping[str, object], refs: list[dict[str, object]]) -> dict[str, object]:
    monitor = report.get("monitor_summary") if isinstance(report.get("monitor_summary"), Mapping) else {}
    compact = _compact_monitor(monitor)
    compact.update(
        {
            "command": "report operator",
            "report_refs": refs,
            "agents_count": len(report.get("agents", [])) if isinstance(report.get("agents"), list) else 0,
            "tasks_count": len(report.get("tasks", [])) if isinstance(report.get("tasks"), list) else 0,
            "results_count": len(report.get("results", [])) if isinstance(report.get("results"), list) else 0,
            "audits_count": len(report.get("audits", [])) if isinstance(report.get("audits"), list) else 0,
            "blockers_count": len(report.get("blockers", [])) if isinstance(report.get("blockers"), list) else 0,
            "manual_nudges_count": len(report.get("manual_nudges", [])) if isinstance(report.get("manual_nudges"), list) else 0,
            "full_report_sha256": _sha256_text(_json_bytes(report)),
        }
    )
    return compact


def _render_operator_markdown(report: Mapping[str, object], *, title: str = "ASO Operator Report") -> str:
    monitor = report.get("monitor_summary") if isinstance(report.get("monitor_summary"), Mapping) else {}
    lines = [
        f"# {title}",
        "",
        f"- generated_at: {report.get('generated_at', 'UNKNOWN')}",
        f"- final_status: {report.get('final_status', report.get('status', 'UNKNOWN'))}",
        f"- current_phase: {monitor.get('current_phase', 'UNKNOWN')}",
        f"- active_blocker: {monitor.get('active_blocker', 'NONE')}",
        f"- waiting_for: {monitor.get('waiting_for', 'UNKNOWN')}",
        f"- audit_status: {monitor.get('audit_status', 'UNKNOWN')}",
        f"- terminal_state: {monitor.get('terminal_state', 'UNKNOWN')}",
        "",
        "## Counts",
        "",
        f"- agents: {len(report.get('agents', [])) if isinstance(report.get('agents'), list) else 0}",
        f"- tasks: {len(report.get('tasks', [])) if isinstance(report.get('tasks'), list) else 0}",
        f"- results: {len(report.get('results', [])) if isinstance(report.get('results'), list) else 0}",
        f"- audits: {len(report.get('audits', [])) if isinstance(report.get('audits'), list) else 0}",
        f"- blockers: {len(report.get('blockers', [])) if isinstance(report.get('blockers'), list) else 0}",
        "",
    ]
    refs = report.get("report_refs")
    if isinstance(refs, list) and refs:
        lines.extend(["## Report Refs", ""])
        for ref in refs:
            if isinstance(ref, Mapping):
                lines.append(f"- {ref.get('path', 'UNKNOWN')} sha256={ref.get('sha256', 'UNKNOWN')}")
        lines.append("")
    return "\n".join(lines)


def _json_markdown_fragment(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def _render_final_receipt_markdown(receipt: Mapping[str, object]) -> str:
    lines = [
        "# ASO Final Run Receipt",
        "",
        "## Summary",
        "",
        f"- receipt_type: {receipt.get('receipt_type', 'UNKNOWN')}",
        f"- receipt_schema_version: {receipt.get('receipt_schema_version', 'UNKNOWN')}",
        f"- command: {receipt.get('command', 'UNKNOWN')}",
        f"- generated_at: {receipt.get('generated_at', 'UNKNOWN')}",
        f"- root: {receipt.get('root', 'UNKNOWN')}",
        f"- final_status: {receipt.get('final_status', 'UNKNOWN')}",
        f"- audit_status: {receipt.get('audit_status', 'UNKNOWN')}",
        f"- terminal_state: {receipt.get('terminal_state', 'UNKNOWN')}",
        "",
    ]
    for field in FINAL_RECEIPT_REQUIRED_MARKDOWN_FIELDS + FINAL_RECEIPT_ADDITIONAL_MARKDOWN_FIELDS:
        lines.extend(
            [
                f"## {field}",
                "",
                "```json",
                _json_markdown_fragment(receipt.get(field, [])),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def _event_record_from_args(root: Path, args: argparse.Namespace, summary: Mapping[str, object]) -> dict[str, object]:
    command = _text(getattr(args, "event_command", ""), "aso report operator")
    event_exit_code = int(getattr(args, "event_exit_code", 0))
    manual_nudges = [item for item in getattr(args, "manual_nudge", []) if item]
    return {
        "event": "operator_event_recorded",
        "event_type": "OPERATOR_EVENT_RECORDED",
        "recorded_at": utc_timestamp(),
        "created_by": "orchestrator",
        "command": command,
        "exit_code": event_exit_code,
        "stdout_refs": _refs(root, getattr(args, "stdout_ref", [])),
        "stderr_refs": _refs(root, getattr(args, "stderr_ref", [])),
        "files_changed": _refs(root, getattr(args, "file_changed", [])),
        "agents": list(getattr(args, "agent", [])),
        "handoffs": _refs(root, getattr(args, "handoff", [])),
        "results": _refs(root, getattr(args, "result", [])),
        "audits": _refs(root, getattr(args, "audit", [])),
        "blockers": list(getattr(args, "blocker", [])),
        "manual_nudge_markers": manual_nudges,
        "manual_nudges": manual_nudges,
        "mutation_receipts": _refs(root, getattr(args, "mutation_receipt", [])),
        "monitor_summary": _compact_monitor(summary),
    }


def _append_event(root: Path, record: Mapping[str, object]) -> tuple[bool, str, dict[str, object]]:
    path = root / EVENT_LOG_REL
    line = json.dumps(record, sort_keys=True)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError as exc:
        return False, str(exc), {}
    return True, "", {
        "event_log": _path_ref(root, path),
        "event_record_sha256": _sha256_text(line),
    }


def _print_operator_text(compact: Mapping[str, object]) -> None:
    print(f"ASO operator report: {str(compact.get('status', 'unknown')).upper()}")
    print(f"Current phase: {compact.get('current_phase', 'UNKNOWN')}")
    print(f"Active blocker: {compact.get('active_blocker', 'NONE')}")
    print(f"Waiting for: {compact.get('waiting_for', 'UNKNOWN')}")
    print(f"Audit status: {compact.get('audit_status', 'UNKNOWN')}")
    print(f"Terminal state: {compact.get('terminal_state', 'UNKNOWN')}")
    print(f"Report hash: {compact.get('full_report_sha256', 'UNKNOWN')}")
    refs = compact.get("report_refs")
    if isinstance(refs, list):
        for ref in refs:
            if isinstance(ref, Mapping):
                print(f"Report ref: {ref.get('path', 'UNKNOWN')} sha256={ref.get('sha256', 'UNKNOWN')}")


def _guard_compact_stdout(text: str) -> str:
    data = text.encode("utf-8")
    if len(data) <= COMPACT_STDOUT_MAX_BYTES:
        return text
    guard = {
        "tool": "aso",
        "command": "stdout-guard",
        "status": "compact_truncated",
        "original_size_bytes": len(data),
        "compact_stdout_max_bytes": COMPACT_STDOUT_MAX_BYTES,
        "message": "Compact output exceeded the stdout guard; rerun with --json-out or --diff-mode full.",
    }
    return _json_bytes(guard)


def run_monitor_summary(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    summary = build_monitor_summary(root)
    if args.json_out:
        ok, error, _ref = _write_allowed_report(root, str(args.json_out), _json_bytes(summary))
        if not ok:
            print(f"aso monitor-summary: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
    if args.json:
        print(_json_bytes(summary), end="")
    elif not args.json_out:
        _print_monitor_text(summary)
    return EXIT_OK if summary.get("status") == "pass" else EXIT_FINDINGS


def run_report_operator(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    report = build_operator_report(root)
    refs: list[dict[str, object]] = []
    exit_code = EXIT_OK if report.get("status") == "pass" else EXIT_FINDINGS

    json_text = _json_bytes(report)
    if args.json_out:
        ok, error, ref = _write_allowed_report(root, str(args.json_out), json_text)
        if not ok:
            print(f"aso report operator: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
        refs.append(ref)
    if args.out:
        markdown = _render_operator_markdown(report)
        ok, error, ref = _write_allowed_report(root, str(args.out), markdown)
        if not ok:
            print(f"aso report operator: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
        refs.append(ref)

    event_append: dict[str, object] = {}
    if args.record_event:
        if not args.confirm_write:
            print("aso report operator: --record-event writes require --confirm-write.", file=sys.stderr)
            return EXIT_FINDINGS
        record = _event_record_from_args(root, args, report["monitor_summary"])  # type: ignore[index]
        ok, error, event_append = _append_event(root, record)
        if not ok:
            print(f"aso report operator: failed to append event: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
        refs.append(event_append["event_log"])  # type: ignore[index]
        report["mutations_performed"] = True
        report["event_record"] = record
        report["event_record_ref"] = event_append

    compact = _operator_compact(report, refs)
    if event_append:
        compact["event_record_ref"] = event_append

    if args.json:
        if args.diff_mode == "full":
            print(_json_bytes(report), end="")
        else:
            print(_guard_compact_stdout(_json_bytes(compact)), end="")
    elif not args.json_out and not args.out:
        if args.diff_mode == "full":
            print(json_text, end="")
        else:
            text = "\n".join(
                [
                    f"ASO operator report: {str(compact.get('status', 'unknown')).upper()}",
                    f"Current phase: {compact.get('current_phase', 'UNKNOWN')}",
                    f"Active blocker: {compact.get('active_blocker', 'NONE')}",
                    f"Waiting for: {compact.get('waiting_for', 'UNKNOWN')}",
                    f"Audit status: {compact.get('audit_status', 'UNKNOWN')}",
                    f"Terminal state: {compact.get('terminal_state', 'UNKNOWN')}",
                    f"Report hash: {compact.get('full_report_sha256', 'UNKNOWN')}",
                    "",
                ]
            )
            print(_guard_compact_stdout(text), end="")
    return exit_code


def build_final_run_receipt(root: Path) -> dict[str, object]:
    sidecars = _load_state_sidecars(root)
    monitor = build_monitor_summary(root)
    events = _load_events(root)
    results, audits, product_tests, known_limitations = _scan_results(root)
    project_status = _text(monitor.get("project_status"), "UNKNOWN")
    terminal_state = _text(monitor.get("terminal_state"), "UNKNOWN")
    final_status = "completed" if terminal_state == "PROJECT_COMPLETED" or project_status == "completed" else project_status
    return {
        "receipt_type": "FINAL_RUN_RECEIPT",
        "receipt_schema_version": "1.0.0",
        "command": "report final-run",
        "generated_at": utc_timestamp(),
        "root": str(root),
        "final_status": final_status,
        "audit_status": monitor.get("audit_status", "UNKNOWN"),
        "product_tests": product_tests,
        "commits": _commits(root, sidecars),
        "agents": _agent_summary(events),
        "tasks": _task_entries(sidecars),
        "artifacts": _artifact_summary(root, sidecars),
        "manual_nudges": _manual_nudges(events),
        "known_limitations": known_limitations,
        "terminal_state": terminal_state,
        "monitor_summary": monitor,
        "results": results,
        "audits": audits,
        "mutation_receipts": _mutation_receipts(events),
        "report_paths": {
            "json": FINAL_RUN_RECEIPT_JSON_REL.as_posix(),
            "markdown": FINAL_RUN_RECEIPT_MD_REL.as_posix(),
        },
    }


def _final_compact(receipt: Mapping[str, object], refs: list[dict[str, object]]) -> dict[str, object]:
    return {
        "tool": "aso",
        "command": "report final-run",
        "status": "pass",
        "final_status": receipt.get("final_status", "UNKNOWN"),
        "audit_status": receipt.get("audit_status", "UNKNOWN"),
        "terminal_state": receipt.get("terminal_state", "UNKNOWN"),
        "product_tests_count": len(receipt.get("product_tests", [])) if isinstance(receipt.get("product_tests"), list) else 0,
        "commits_count": len(receipt.get("commits", [])) if isinstance(receipt.get("commits"), list) else 0,
        "agents_count": len(receipt.get("agents", [])) if isinstance(receipt.get("agents"), list) else 0,
        "tasks_count": len(receipt.get("tasks", [])) if isinstance(receipt.get("tasks"), list) else 0,
        "artifacts_count": len(receipt.get("artifacts", [])) if isinstance(receipt.get("artifacts"), list) else 0,
        "manual_nudges_count": len(receipt.get("manual_nudges", [])) if isinstance(receipt.get("manual_nudges"), list) else 0,
        "known_limitations_count": len(receipt.get("known_limitations", [])) if isinstance(receipt.get("known_limitations"), list) else 0,
        "receipt_refs": refs,
        "full_receipt_sha256": _sha256_text(_json_bytes(receipt)),
    }


def _print_final_text(compact: Mapping[str, object], *, dry_run: bool) -> None:
    prefix = "ASO final-run receipt plan" if dry_run else "ASO final-run receipt"
    print(f"{prefix}: {str(compact.get('status', 'unknown')).upper()}")
    print(f"Final status: {compact.get('final_status', 'UNKNOWN')}")
    print(f"Audit status: {compact.get('audit_status', 'UNKNOWN')}")
    print(f"Terminal state: {compact.get('terminal_state', 'UNKNOWN')}")
    print(f"Receipt hash: {compact.get('full_receipt_sha256', 'UNKNOWN')}")
    refs = compact.get("receipt_refs")
    if isinstance(refs, list):
        for ref in refs:
            if isinstance(ref, Mapping):
                print(f"Receipt ref: {ref.get('path', 'UNKNOWN')} sha256={ref.get('sha256', 'UNKNOWN')}")


def run_report_final_run(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    receipt = build_final_run_receipt(root)
    refs: list[dict[str, object]] = []
    if args.confirm_write:
        try:
            _write_json(root / FINAL_RUN_RECEIPT_JSON_REL, receipt)
            markdown = _render_final_receipt_markdown(receipt)
            _write_text(root / FINAL_RUN_RECEIPT_MD_REL, markdown)
            refs = [
                _path_ref(root, root / FINAL_RUN_RECEIPT_JSON_REL),
                _path_ref(root, root / FINAL_RUN_RECEIPT_MD_REL),
            ]
        except OSError as exc:
            print(f"aso report final-run: failed to write receipt: {exc}", file=sys.stderr)
            return EXIT_IO_ERROR
    else:
        refs = [
            {"path": FINAL_RUN_RECEIPT_JSON_REL.as_posix(), "exists": False, "planned": True},
            {"path": FINAL_RUN_RECEIPT_MD_REL.as_posix(), "exists": False, "planned": True},
        ]
    compact = _final_compact(receipt, refs)
    dry_run = not args.confirm_write
    if args.json:
        if args.diff_mode == "full":
            print(_json_bytes(receipt), end="")
        else:
            print(_guard_compact_stdout(_json_bytes(compact)), end="")
    else:
        if args.diff_mode == "full":
            print(_json_bytes(receipt), end="")
        else:
            _print_final_text(compact, dry_run=dry_run)
    return EXIT_OK
