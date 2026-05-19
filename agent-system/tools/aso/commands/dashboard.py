"""Safe static workspace dashboard renderer."""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

from commands import checkpoint_preflight, dag, package_sync, plan_next, state_verify


EXIT_OK = 0
EXIT_IO_ERROR = 3
NOT_AVAILABLE = "not_available"


def _content(sidecars: dict[str, dict[str, object]], sidecar_type: str) -> dict[str, object]:
    payload = sidecars.get(sidecar_type, {})
    content = payload.get("content")
    return content if isinstance(content, dict) else {}


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, sort_keys=True)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = _as_text(item)
        if text and text not in {"NONE", "none", "null", "UNKNOWN"}:
            result.append(text)
    return result


def _is_meaningful(value: object) -> bool:
    text = _as_text(value)
    return bool(text) and text not in {"NONE", "none", "null", "UNKNOWN", NOT_AVAILABLE}


def _count_items(value: object) -> int:
    return len(value) if isinstance(value, list) else 0


def _blocking_status_messages(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    parts = []
    for key in ("blocker_id", "blocker_type", "blocks", "blocked_by", "resolution_path"):
        text = _as_text(value.get(key))
        if text and text not in {"NONE", "none", "null", "UNKNOWN"}:
            parts.append(f"{key}={text}")
    return ["; ".join(parts)] if parts else []


def _tasks(sidecars: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    raw_tasks = _content(sidecars, "TASK_REGISTRY").get("tasks")
    if not isinstance(raw_tasks, list):
        return []
    return [task for task in raw_tasks if isinstance(task, dict)]


def _task_counts(tasks: list[dict[str, object]]) -> dict[str, object]:
    by_status = Counter(_as_text(task.get("status")) or "unknown" for task in tasks)
    return {
        "total": len(tasks),
        "by_status": dict(sorted(by_status.items())),
        "with_result_refs": sum(1 for task in tasks if _string_list(task.get("result_refs"))),
        "with_audit_refs": sum(1 for task in tasks if _string_list(task.get("audit_refs"))),
        "audit_pending": by_status.get("audit_pending", 0),
        "checkpoint_done": by_status.get("checkpoint_done", 0),
    }


def _open_blockers(
    project_state: dict[str, object],
    current_gate: dict[str, object],
    next_action: dict[str, object],
    tasks: list[dict[str, object]],
    plan_report: dict[str, object],
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []

    for source, values in (
        ("project_state.active_blockers", _string_list(project_state.get("active_blockers"))),
        ("project_state.checkpoint_blocked_by", _string_list(project_state.get("checkpoint_blocked_by"))),
        ("current_gate.blocking_status", _blocking_status_messages(current_gate.get("blocking_status"))),
        ("next_action.blocked_by", _string_list(next_action.get("blocked_by"))),
    ):
        for value in values:
            blockers.append({"source": source, "message": value})

    for task in tasks:
        task_id = _as_text(task.get("task_id")) or "UNKNOWN_TASK"
        for value in _string_list(task.get("blocked_by")):
            blockers.append({"source": f"task.{task_id}.blocked_by", "message": value})

    plan_blockers = plan_report.get("blocking_rules")
    if isinstance(plan_blockers, list):
        for blocker in plan_blockers:
            if isinstance(blocker, dict):
                rule_id = _as_text(blocker.get("rule_id")) or "rule"
                message = _as_text(blocker.get("message")) or _as_text(blocker.get("evidence"))
                if message:
                    blockers.append({"source": f"plan_next.{rule_id}", "message": message})

    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for blocker in blockers:
        key = (blocker["source"], blocker["message"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(blocker)
    return deduped


def _accepted_artifact_audit_refs(sidecars: dict[str, dict[str, object]]) -> list[str]:
    artifacts = _content(sidecars, "ACCEPTED_ARTIFACTS").get("artifacts")
    if not isinstance(artifacts, list):
        return []
    refs: list[str] = []
    for artifact in artifacts:
        if isinstance(artifact, dict):
            refs.extend(_string_list([artifact.get("audit_ref")]))
    return refs


def _audit_signals(
    sidecars: dict[str, dict[str, object]],
    current_gate: dict[str, object],
    tasks: list[dict[str, object]],
    plan_report: dict[str, object],
) -> dict[str, object]:
    task_audit_refs = []
    pending = 0
    for task in tasks:
        refs = _string_list(task.get("audit_refs"))
        task_audit_refs.extend(refs)
        if _as_text(task.get("status")) == "audit_pending" and not refs:
            pending += 1

    evidence = plan_report.get("evidence")
    audit_pass_evidence = {}
    if isinstance(evidence, dict) and isinstance(evidence.get("audit_pass_evidence"), dict):
        audit_pass_evidence = evidence["audit_pass_evidence"]

    return {
        "audit_pending": pending,
        "task_audit_refs": task_audit_refs,
        "accepted_artifact_audit_refs": _accepted_artifact_audit_refs(sidecars),
        "current_gate_gate_evidence": _string_list(current_gate.get("gate_evidence")),
        "plan_audit_pass_evidence_present": audit_pass_evidence.get("present", False),
    }


def _checkpoint_signals(
    project_state: dict[str, object],
    current_gate: dict[str, object],
    next_action: dict[str, object],
    tasks: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "project_checkpoint_eligibility": _as_text(project_state.get("checkpoint_eligibility")) or "unknown",
        "current_gate_checkpoint_eligibility": _as_text(current_gate.get("checkpoint_eligibility")) or "unknown",
        "next_action_checkpoint_policy": _as_text(next_action.get("checkpoint_policy")) or "unknown",
        "checkpoint_done_tasks": sum(1 for task in tasks if _as_text(task.get("status")) == "checkpoint_done"),
        "checkpoint_blocked_by": sorted(
            set(
                _string_list(project_state.get("checkpoint_blocked_by"))
                + _blocking_status_messages(current_gate.get("blocking_status"))
            )
        ),
    }


def _find_context_budget(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        budget = value.get("context_budget")
        if isinstance(budget, dict):
            return budget
        for item in value.values():
            found = _find_context_budget(item)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_context_budget(item)
            if found is not None:
                return found
    return None


def _context_budget(sidecars: dict[str, dict[str, object]]) -> dict[str, object]:
    for sidecar_type in ("NEXT_ACTION", "TASK_REGISTRY", "PROJECT_STATE", "CURRENT_GATE"):
        budget = _find_context_budget(_content(sidecars, sidecar_type))
        if budget is not None:
            return {
                "available": True,
                "source": sidecar_type,
                "max_docs": budget.get("max_docs", ""),
                "max_sections_per_doc": budget.get("max_sections_per_doc", ""),
                "max_chars_total": budget.get("max_chars_total", ""),
            }
    return {
        "available": False,
        "source": NOT_AVAILABLE,
        "max_docs": NOT_AVAILABLE,
        "max_sections_per_doc": NOT_AVAILABLE,
        "max_chars_total": NOT_AVAILABLE,
    }


def _package_sync_status(root: Path) -> dict[str, object]:
    source_root = root / package_sync.SOURCE_TOOL_RELPATH
    bundled_root = root / package_sync.BUNDLED_TOOL_RELPATH
    if not source_root.is_dir() or not bundled_root.is_dir():
        return {
            "available": False,
            "status": NOT_AVAILABLE,
            "source_files": NOT_AVAILABLE,
            "bundled_files": NOT_AVAILABLE,
            "mismatches": NOT_AVAILABLE,
            "errors": NOT_AVAILABLE,
            "warnings": NOT_AVAILABLE,
        }
    try:
        report, exit_code = package_sync.build_report(root, True)
    except Exception as exc:  # pragma: no cover - defensive dashboard isolation
        return {
            "available": True,
            "status": "error",
            "exit_code": EXIT_IO_ERROR,
            "source_files": NOT_AVAILABLE,
            "bundled_files": NOT_AVAILABLE,
            "mismatches": NOT_AVAILABLE,
            "errors": 1,
            "warnings": 0,
            "details": str(exc),
        }
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "available": True,
        "status": report.get("status", "unknown"),
        "exit_code": exit_code,
        "source_files": summary.get("source_files", 0),
        "bundled_files": summary.get("bundled_files", 0),
        "mismatches": summary.get("mismatches", 0),
        "errors": summary.get("errors", 0),
        "warnings": summary.get("warnings", 0),
    }


def _dag_summary(root: Path, sidecars: dict[str, dict[str, object]]) -> dict[str, object]:
    if "TASK_REGISTRY" not in sidecars:
        return {
            "available": False,
            "status": NOT_AVAILABLE,
            "task_count": NOT_AVAILABLE,
            "edge_count": NOT_AVAILABLE,
            "finding_count": NOT_AVAILABLE,
            "task_ids": [],
        }
    try:
        report, exit_code = dag.verify_report(root)
    except Exception as exc:  # pragma: no cover - defensive dashboard isolation
        return {
            "available": True,
            "status": "error",
            "exit_code": EXIT_IO_ERROR,
            "task_count": NOT_AVAILABLE,
            "edge_count": NOT_AVAILABLE,
            "finding_count": NOT_AVAILABLE,
            "task_ids": [],
            "details": str(exc),
        }
    graph = report.get("graph") if isinstance(report.get("graph"), dict) else {}
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    task_ids = graph.get("task_ids") if isinstance(graph.get("task_ids"), list) else []
    return {
        "available": True,
        "status": report.get("status", "unknown"),
        "exit_code": exit_code,
        "task_count": graph.get("task_count", 0),
        "edge_count": graph.get("edge_count", 0),
        "finding_count": len(findings),
        "task_ids": task_ids,
    }


def _result_routing_summary(tasks: list[dict[str, object]], next_action: dict[str, object]) -> dict[str, object]:
    routes: list[str] = []
    requester_return_count = 0
    correction_link_count = 0

    for task in tasks:
        task_id = _as_text(task.get("task_id")) or "UNKNOWN_TASK"
        return_enabled = task.get("return_to_requester_after_audit_pass") is True
        return_role = task.get("return_to_role_after_audit_pass")
        return_task = task.get("return_task_after_audit_pass")
        requested_by_role = task.get("requested_by_role")
        requested_by_task = task.get("requested_by_task")
        correction_links = _string_list(task.get("correction_links"))
        correction_link_count += len(correction_links)

        if return_enabled or _is_meaningful(return_role) or _is_meaningful(return_task):
            requester_return_count += 1
            routes.append(
                f"{task_id}: return_to_requester={return_enabled}; "
                f"role={_as_text(return_role) or NOT_AVAILABLE}; "
                f"task={_as_text(return_task) or NOT_AVAILABLE}"
            )
        elif _is_meaningful(requested_by_role) or _is_meaningful(requested_by_task):
            routes.append(
                f"{task_id}: requested_by_role={_as_text(requested_by_role) or NOT_AVAILABLE}; "
                f"requested_by_task={_as_text(requested_by_task) or NOT_AVAILABLE}"
            )

    next_contexts = [
        _as_text(next_action.get("requester_return_context")),
        _as_text(next_action.get("blocking_or_resume_context")),
    ]
    next_context_available = any(_is_meaningful(value) for value in next_contexts)
    if next_context_available:
        routes.append(
            "NEXT_ACTION: "
            f"requester_return_context={next_contexts[0] or NOT_AVAILABLE}; "
            f"blocking_or_resume_context={next_contexts[1] or NOT_AVAILABLE}"
        )

    if not routes and correction_link_count == 0:
        return {
            "available": False,
            "status": NOT_AVAILABLE,
            "requester_return_tasks": NOT_AVAILABLE,
            "correction_links": NOT_AVAILABLE,
            "routes": [],
        }
    return {
        "available": True,
        "status": "present",
        "requester_return_tasks": requester_return_count,
        "correction_links": correction_link_count,
        "routes": routes,
    }


def _incident_health(project_state: dict[str, object], blockers: list[dict[str, str]]) -> dict[str, object]:
    if not project_state:
        return {
            "available": False,
            "status": NOT_AVAILABLE,
            "incident_markers": NOT_AVAILABLE,
            "signals": [],
        }

    signal_values: list[tuple[str, str]] = []
    for key in ("current_phase", "project_status", "semantic_reason", "last_checkpoint_failure_reason"):
        text = _as_text(project_state.get(key))
        if text:
            signal_values.append((f"project_state.{key}", text))
    for key in ("active_risks", "active_blockers", "active_gaps", "checkpoint_blocked_by"):
        for value in _string_list(project_state.get(key)):
            signal_values.append((f"project_state.{key}", value))
    for blocker in blockers:
        signal_values.append((blocker.get("source", "open_blocker"), blocker.get("message", "")))

    markers = []
    signals = []
    for source, value in signal_values:
        lower_value = value.lower()
        matched = sorted(marker for marker in plan_next.INCIDENT_MARKERS if marker.lower() in lower_value)
        if matched:
            markers.extend(matched)
            signals.append(f"{source}: {value}")

    unique_markers = sorted(set(markers))
    return {
        "available": True,
        "status": "active_signal_detected" if unique_markers else "no_active_signal",
        "incident_markers": len(unique_markers),
        "signals": signals,
    }


def _checkpoint_preflight_readiness(root: Path, sidecars: dict[str, dict[str, object]]) -> dict[str, object]:
    if not {"PROJECT_STATE", "CURRENT_GATE", "NEXT_ACTION", "TASK_REGISTRY"}.issubset(sidecars):
        return {
            "available": False,
            "status": NOT_AVAILABLE,
            "eligible": NOT_AVAILABLE,
            "blocking_rules": NOT_AVAILABLE,
            "warnings": NOT_AVAILABLE,
            "audit_evidence": NOT_AVAILABLE,
            "state_status": NOT_AVAILABLE,
        }
    try:
        report, exit_code = checkpoint_preflight._workspace_report(root, False)
    except Exception as exc:  # pragma: no cover - defensive dashboard isolation
        return {
            "available": True,
            "status": "error",
            "exit_code": EXIT_IO_ERROR,
            "eligible": False,
            "blocking_rules": 1,
            "warnings": 0,
            "audit_evidence": False,
            "state_status": "error",
            "details": str(exc),
        }
    evidence = report.get("evidence") if isinstance(report.get("evidence"), dict) else {}
    project_evidence = evidence.get("project_state") if isinstance(evidence.get("project_state"), dict) else {}
    audit_evidence = evidence.get("audit_pass_evidence") if isinstance(evidence.get("audit_pass_evidence"), dict) else {}
    return {
        "available": True,
        "status": report.get("status", "unknown"),
        "exit_code": exit_code,
        "eligible": report.get("eligible", False),
        "blocking_rules": _count_items(report.get("blocking_rules")),
        "warnings": _count_items(report.get("warnings")),
        "audit_evidence": audit_evidence.get("present", False),
        "state_status": project_evidence.get("checkpoint_preflight_status", NOT_AVAILABLE),
    }


def build_report(root: Path) -> dict[str, object]:
    verify_report, verify_exit_code = state_verify._report(root, False)
    sidecars = plan_next._load_sidecars(root)
    rules, rules_evidence = plan_next._load_governance_rules(root)
    planner = plan_next._plan(root, False, verify_report, verify_exit_code, sidecars, rules, rules_evidence)

    project_state = _content(sidecars, "PROJECT_STATE")
    current_gate = _content(sidecars, "CURRENT_GATE")
    next_action = _content(sidecars, "NEXT_ACTION")
    task_items = _tasks(sidecars)
    blockers = _open_blockers(project_state, current_gate, next_action, task_items, planner)

    return {
        "tool": "aso",
        "command": "dashboard",
        "mode": "workspace",
        "status": "blocked" if blockers else "ready",
        "root": str(root),
        "read_only": True,
        "mutations_performed": False,
        "output_policy": "stdout by default; file output only under /tmp or <workspace>/project-runtime/dashboard",
        "workspace": {
            "project_slug": project_state.get("project_slug", ""),
            "workspace_type": project_state.get("workspace_type", ""),
            "current_phase": project_state.get("current_phase", ""),
            "project_status": project_state.get("project_status", ""),
            "identity_validation_status": project_state.get("identity_validation_status", ""),
            "repository_lock_status": project_state.get("repository_lock_status", ""),
            "push_allowed": project_state.get("push_allowed", ""),
            "actual_branch": project_state.get("actual_branch", ""),
        },
        "current_gate": {
            "gate_id": current_gate.get("gate_id", ""),
            "gate_type": current_gate.get("gate_type", ""),
            "status": current_gate.get("status", ""),
            "owner_role": current_gate.get("owner_role", ""),
            "task_id": current_gate.get("task_id", ""),
            "action_semantic": current_gate.get("action_semantic", ""),
            "gate_evidence": current_gate.get("gate_evidence", []),
            "blocking_status": current_gate.get("blocking_status", "NONE"),
        },
        "next_action": {
            "recommended_next_action": planner.get("recommended_next_action", ""),
            "action_type": next_action.get("action_type", ""),
            "target_role": next_action.get("target_role", ""),
            "task_id": next_action.get("task_id", ""),
            "task_packet": next_action.get("task_packet", ""),
            "dependency_status": next_action.get("dependency_status", ""),
            "summary": next_action.get("summary", ""),
        },
        "task_counts": _task_counts(task_items),
        "open_blockers": blockers,
        "package_sync": _package_sync_status(root),
        "dag_summary": _dag_summary(root, sidecars),
        "audit_signals": _audit_signals(sidecars, current_gate, task_items, planner),
        "checkpoint_signals": _checkpoint_signals(project_state, current_gate, next_action, task_items),
        "context_budget": _context_budget(sidecars),
        "result_routing": _result_routing_summary(task_items, next_action),
        "incident_health": _incident_health(project_state, blockers),
        "checkpoint_preflight": _checkpoint_preflight_readiness(root, sidecars),
        "state_verify": {
            "status": verify_report.get("status", ""),
            "summary": verify_report.get("summary", {}),
            "sidecars_present": verify_report.get("state", {}).get("sidecars_present", [])
            if isinstance(verify_report.get("state"), dict)
            else [],
            "sidecars_missing": verify_report.get("state", {}).get("sidecars_missing", [])
            if isinstance(verify_report.get("state"), dict)
            else [],
        },
        "plan_next": {
            "status": planner.get("status", ""),
            "blocking_rule_count": len(planner.get("blocking_rules", []))
            if isinstance(planner.get("blocking_rules"), list)
            else 0,
            "governance_rules": rules_evidence,
        },
    }


def _h(value: object) -> str:
    return html.escape(_as_text(value), quote=True)


def _pairs(items: Iterable[tuple[str, object]]) -> str:
    rows = []
    for label, value in items:
        rows.append(f"<tr><th scope=\"row\">{_h(label)}</th><td>{_h(value)}</td></tr>")
    return "\n".join(rows)


def _list_items(values: Iterable[object]) -> str:
    rendered = [f"<li>{_h(value)}</li>" for value in values]
    return "\n".join(rendered) if rendered else "<li>None</li>"


def _optional_list_items(values: Iterable[object]) -> str:
    rendered = [f"<li>{_h(value)}</li>" for value in values]
    return "\n".join(rendered) if rendered else f"<li>{NOT_AVAILABLE}</li>"


def _render_blockers(blockers: object) -> str:
    if not isinstance(blockers, list) or not blockers:
        return "<li>None</li>"
    items = []
    for blocker in blockers:
        if isinstance(blocker, dict):
            items.append(f"<li><strong>{_h(blocker.get('source', 'unknown'))}</strong>: {_h(blocker.get('message', ''))}</li>")
    return "\n".join(items) if items else "<li>None</li>"


def render_html(report: dict[str, object]) -> str:
    workspace = report["workspace"] if isinstance(report.get("workspace"), dict) else {}
    current_gate = report["current_gate"] if isinstance(report.get("current_gate"), dict) else {}
    next_action = report["next_action"] if isinstance(report.get("next_action"), dict) else {}
    task_counts = report["task_counts"] if isinstance(report.get("task_counts"), dict) else {}
    package_sync_report = report["package_sync"] if isinstance(report.get("package_sync"), dict) else {}
    dag_report = report["dag_summary"] if isinstance(report.get("dag_summary"), dict) else {}
    audit = report["audit_signals"] if isinstance(report.get("audit_signals"), dict) else {}
    checkpoint = report["checkpoint_signals"] if isinstance(report.get("checkpoint_signals"), dict) else {}
    context_budget = report["context_budget"] if isinstance(report.get("context_budget"), dict) else {}
    result_routing = report["result_routing"] if isinstance(report.get("result_routing"), dict) else {}
    incident_health = report["incident_health"] if isinstance(report.get("incident_health"), dict) else {}
    checkpoint_preflight = report["checkpoint_preflight"] if isinstance(report.get("checkpoint_preflight"), dict) else {}
    state_verify_report = report["state_verify"] if isinstance(report.get("state_verify"), dict) else {}
    plan_report = report["plan_next"] if isinstance(report.get("plan_next"), dict) else {}
    by_status = task_counts.get("by_status") if isinstance(task_counts.get("by_status"), dict) else {}

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ASO Static Dashboard</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #f5f7fa; color: #172033; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 48px; }}
    header {{ margin-bottom: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; line-height: 1.2; letter-spacing: 0; }}
    h2 {{ margin: 0 0 12px; font-size: 18px; letter-spacing: 0; }}
    p {{ margin: 0; color: #4b5870; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
    section {{ background: #ffffff; border: 1px solid #dce3ee; border-radius: 8px; padding: 16px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 7px 0; border-bottom: 1px solid #edf1f6; text-align: left; vertical-align: top; }}
    th {{ width: 44%; color: #566278; font-weight: 600; }}
    td {{ color: #172033; word-break: break-word; }}
    ul {{ margin: 0; padding-left: 20px; }}
    li {{ margin: 6px 0; word-break: break-word; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 20px 0; }}
    .metric {{ background: #ffffff; border: 1px solid #dce3ee; border-radius: 8px; padding: 14px; }}
    .metric span {{ display: block; color: #566278; font-size: 12px; text-transform: uppercase; }}
    .metric strong {{ display: block; margin-top: 4px; font-size: 22px; }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>ASO Static Dashboard</h1>
    <p>Root: {_h(report.get("root", ""))}</p>
  </header>

  <div class="summary">
    <div class="metric"><span>Dashboard Status</span><strong>{_h(report.get("status", ""))}</strong></div>
    <div class="metric"><span>Current Gate</span><strong>{_h(current_gate.get("status", ""))}</strong></div>
    <div class="metric"><span>Next Action</span><strong>{_h(next_action.get("recommended_next_action", ""))}</strong></div>
    <div class="metric"><span>Open Blockers</span><strong>{_h(len(report.get("open_blockers", [])) if isinstance(report.get("open_blockers"), list) else 0)}</strong></div>
    <div class="metric"><span>Package Sync</span><strong>{_h(package_sync_report.get("status", NOT_AVAILABLE))}</strong></div>
    <div class="metric"><span>Checkpoint Preflight</span><strong>{_h(checkpoint_preflight.get("status", NOT_AVAILABLE))}</strong></div>
  </div>

  <div class="grid">
    <section>
      <h2>Workspace</h2>
      <table>{_pairs((
        ("Project", workspace.get("project_slug", "")),
        ("Type", workspace.get("workspace_type", "")),
        ("Phase", workspace.get("current_phase", "")),
        ("Status", workspace.get("project_status", "")),
        ("Branch", workspace.get("actual_branch", "")),
        ("Identity", workspace.get("identity_validation_status", "")),
        ("Repository lock", workspace.get("repository_lock_status", "")),
        ("Push allowed", workspace.get("push_allowed", "")),
      ))}</table>
    </section>

    <section>
      <h2>Current Gate</h2>
      <table>{_pairs((
        ("Gate ID", current_gate.get("gate_id", "")),
        ("Type", current_gate.get("gate_type", "")),
        ("Status", current_gate.get("status", "")),
        ("Owner", current_gate.get("owner_role", "")),
        ("Task", current_gate.get("task_id", "")),
        ("Semantic", current_gate.get("action_semantic", "")),
        ("Gate evidence", len(current_gate.get("gate_evidence", [])) if isinstance(current_gate.get("gate_evidence"), list) else 0),
        ("Blocking status", current_gate.get("blocking_status", "")),
      ))}</table>
    </section>

    <section>
      <h2>Next Action</h2>
      <table>{_pairs((
        ("Recommended", next_action.get("recommended_next_action", "")),
        ("Action type", next_action.get("action_type", "")),
        ("Target role", next_action.get("target_role", "")),
        ("Task", next_action.get("task_id", "")),
        ("Dependency", next_action.get("dependency_status", "")),
        ("Task packet", next_action.get("task_packet", "")),
        ("Summary", next_action.get("summary", "")),
      ))}</table>
    </section>

    <section>
      <h2>Tasks</h2>
      <table>{_pairs((
        ("Total", task_counts.get("total", 0)),
        ("Audit pending", task_counts.get("audit_pending", 0)),
        ("Checkpoint done", task_counts.get("checkpoint_done", 0)),
        ("With results", task_counts.get("with_result_refs", 0)),
        ("With audits", task_counts.get("with_audit_refs", 0)),
      ))}</table>
      <ul>{_list_items(f"{status}: {count}" for status, count in sorted(by_status.items()))}</ul>
    </section>

    <section>
      <h2>Open Blockers</h2>
      <ul>{_render_blockers(report.get("open_blockers"))}</ul>
    </section>

    <section>
      <h2>Package Sync Status</h2>
      <table>{_pairs((
        ("Status", package_sync_report.get("status", NOT_AVAILABLE)),
        ("Source files", package_sync_report.get("source_files", NOT_AVAILABLE)),
        ("Bundled files", package_sync_report.get("bundled_files", NOT_AVAILABLE)),
        ("Mismatches", package_sync_report.get("mismatches", NOT_AVAILABLE)),
        ("Errors", package_sync_report.get("errors", NOT_AVAILABLE)),
        ("Warnings", package_sync_report.get("warnings", NOT_AVAILABLE)),
      ))}</table>
    </section>

    <section>
      <h2>DAG Summary</h2>
      <table>{_pairs((
        ("Status", dag_report.get("status", NOT_AVAILABLE)),
        ("Tasks", dag_report.get("task_count", NOT_AVAILABLE)),
        ("Edges", dag_report.get("edge_count", NOT_AVAILABLE)),
        ("Findings", dag_report.get("finding_count", NOT_AVAILABLE)),
      ))}</table>
      <ul>{_optional_list_items(dag_report.get("task_ids", []) if isinstance(dag_report.get("task_ids"), list) else [])}</ul>
    </section>

    <section>
      <h2>Audit Signals</h2>
      <table>{_pairs((
        ("Audit pending", audit.get("audit_pending", 0)),
        ("Plan audit evidence", audit.get("plan_audit_pass_evidence_present", False)),
        ("Task audit refs", len(audit.get("task_audit_refs", [])) if isinstance(audit.get("task_audit_refs"), list) else 0),
        ("Artifact audit refs", len(audit.get("accepted_artifact_audit_refs", [])) if isinstance(audit.get("accepted_artifact_audit_refs"), list) else 0),
        ("Gate evidence refs", len(audit.get("current_gate_gate_evidence", [])) if isinstance(audit.get("current_gate_gate_evidence"), list) else 0),
      ))}</table>
    </section>

    <section>
      <h2>Checkpoint Signals</h2>
      <table>{_pairs((
        ("Project eligibility", checkpoint.get("project_checkpoint_eligibility", "")),
        ("Gate eligibility", checkpoint.get("current_gate_checkpoint_eligibility", "")),
        ("Next policy", checkpoint.get("next_action_checkpoint_policy", "")),
        ("Checkpoint done tasks", checkpoint.get("checkpoint_done_tasks", 0)),
      ))}</table>
      <ul>{_list_items(checkpoint.get("checkpoint_blocked_by", []) if isinstance(checkpoint.get("checkpoint_blocked_by"), list) else [])}</ul>
    </section>

    <section>
      <h2>Context Budget</h2>
      <table>{_pairs((
        ("Status", "available" if context_budget.get("available") is True else NOT_AVAILABLE),
        ("Source", context_budget.get("source", NOT_AVAILABLE)),
        ("Max docs", context_budget.get("max_docs", NOT_AVAILABLE)),
        ("Max sections/doc", context_budget.get("max_sections_per_doc", NOT_AVAILABLE)),
        ("Max chars total", context_budget.get("max_chars_total", NOT_AVAILABLE)),
      ))}</table>
    </section>

    <section>
      <h2>Result Routing Summary</h2>
      <table>{_pairs((
        ("Status", result_routing.get("status", NOT_AVAILABLE)),
        ("Requester return tasks", result_routing.get("requester_return_tasks", NOT_AVAILABLE)),
        ("Correction links", result_routing.get("correction_links", NOT_AVAILABLE)),
      ))}</table>
      <ul>{_optional_list_items(result_routing.get("routes", []) if isinstance(result_routing.get("routes"), list) else [])}</ul>
    </section>

    <section>
      <h2>Incident Health</h2>
      <table>{_pairs((
        ("Status", incident_health.get("status", NOT_AVAILABLE)),
        ("Incident markers", incident_health.get("incident_markers", NOT_AVAILABLE)),
      ))}</table>
      <ul>{_optional_list_items(incident_health.get("signals", []) if isinstance(incident_health.get("signals"), list) else [])}</ul>
    </section>

    <section>
      <h2>Checkpoint-Preflight Readiness</h2>
      <table>{_pairs((
        ("Status", checkpoint_preflight.get("status", NOT_AVAILABLE)),
        ("Eligible", checkpoint_preflight.get("eligible", NOT_AVAILABLE)),
        ("Blocking rules", checkpoint_preflight.get("blocking_rules", NOT_AVAILABLE)),
        ("Warnings", checkpoint_preflight.get("warnings", NOT_AVAILABLE)),
        ("Audit evidence", checkpoint_preflight.get("audit_evidence", NOT_AVAILABLE)),
        ("State status", checkpoint_preflight.get("state_status", NOT_AVAILABLE)),
      ))}</table>
    </section>

    <section>
      <h2>Verifier Signals</h2>
      <table>{_pairs((
        ("State verify", state_verify_report.get("status", "")),
        ("Plan next", plan_report.get("status", "")),
        ("Plan blockers", plan_report.get("blocking_rule_count", 0)),
      ))}</table>
    </section>
  </div>
</main>
</body>
</html>
"""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _resolve_output_path(root: Path, path_text: str) -> tuple[Path | None, str]:
    path = Path(path_text).expanduser()
    resolved = path.resolve(strict=False)
    tmp_root = Path("/tmp").resolve(strict=True)
    workspace_dashboard = (root / "project-runtime" / "dashboard").resolve(strict=False)

    if _is_relative_to(resolved, tmp_root) and resolved != tmp_root:
        return resolved, ""
    if _is_relative_to(resolved, workspace_dashboard) and resolved != workspace_dashboard:
        return resolved, ""
    return None, (
        "dashboard output path is forbidden; use /tmp/... or "
        "<workspace>/project-runtime/dashboard/..."
    )


def _write_allowed(root: Path, path_text: str, content: str, *, label: str) -> bool:
    path, error = _resolve_output_path(root, path_text)
    if path is None:
        print(f"aso dashboard: {label} {error}: {path_text}", file=sys.stderr)
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        print(f"aso dashboard: failed to write {label}: {exc}", file=sys.stderr)
        return False
    return True


def run(args: argparse.Namespace) -> int:
    """Run the static dashboard renderer."""

    root = Path(args.root).expanduser()
    report = build_report(root)
    rendered = render_html(report)

    if args.json_out:
        payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if not _write_allowed(root, str(args.json_out), payload, label="json-out"):
            return EXIT_IO_ERROR

    if args.out:
        if not _write_allowed(root, str(args.out), rendered, label="html-out"):
            return EXIT_IO_ERROR
        print(f"ASO dashboard written: {Path(args.out).expanduser()}")
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")
    return EXIT_OK
