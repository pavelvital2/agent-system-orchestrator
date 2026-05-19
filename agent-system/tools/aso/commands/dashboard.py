"""Safe static workspace dashboard renderer."""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

from commands import plan_next, state_verify


EXIT_OK = 0
EXIT_IO_ERROR = 3


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
        "audit_required": sum(1 for task in tasks if task.get("audit_required") is True),
        "checkpoint_required": sum(1 for task in tasks if task.get("checkpoint_required") is True),
        "with_result_refs": sum(1 for task in tasks if _string_list(task.get("result_refs"))),
        "with_audit_refs": sum(1 for task in tasks if _string_list(task.get("audit_refs"))),
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
        ("current_gate.checkpoint_blocked_by", _string_list(current_gate.get("checkpoint_blocked_by"))),
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
        if task.get("audit_required") is True and not refs:
            pending += 1

    evidence = plan_report.get("evidence")
    audit_pass_evidence = {}
    if isinstance(evidence, dict) and isinstance(evidence.get("audit_pass_evidence"), dict):
        audit_pass_evidence = evidence["audit_pass_evidence"]

    return {
        "audit_required": sum(1 for task in tasks if task.get("audit_required") is True),
        "audit_pending": pending,
        "task_audit_refs": task_audit_refs,
        "accepted_artifact_audit_refs": _accepted_artifact_audit_refs(sidecars),
        "current_gate_evidence_refs": _string_list(current_gate.get("evidence_refs")),
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
        "checkpoint_required_tasks": sum(1 for task in tasks if task.get("checkpoint_required") is True),
        "checkpoint_blocked_by": sorted(
            set(
                _string_list(project_state.get("checkpoint_blocked_by"))
                + _string_list(current_gate.get("checkpoint_blocked_by"))
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
        "source": "not_available",
        "max_docs": "",
        "max_sections_per_doc": "",
        "max_chars_total": "",
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
        "audit_signals": _audit_signals(sidecars, current_gate, task_items, planner),
        "checkpoint_signals": _checkpoint_signals(project_state, current_gate, next_action, task_items),
        "context_budget": _context_budget(sidecars),
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
    audit = report["audit_signals"] if isinstance(report.get("audit_signals"), dict) else {}
    checkpoint = report["checkpoint_signals"] if isinstance(report.get("checkpoint_signals"), dict) else {}
    context_budget = report["context_budget"] if isinstance(report.get("context_budget"), dict) else {}
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
        ("Audit required", task_counts.get("audit_required", 0)),
        ("Checkpoint required", task_counts.get("checkpoint_required", 0)),
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
      <h2>Audit Signals</h2>
      <table>{_pairs((
        ("Audit required", audit.get("audit_required", 0)),
        ("Audit pending", audit.get("audit_pending", 0)),
        ("Plan audit evidence", audit.get("plan_audit_pass_evidence_present", False)),
        ("Task audit refs", len(audit.get("task_audit_refs", [])) if isinstance(audit.get("task_audit_refs"), list) else 0),
        ("Artifact audit refs", len(audit.get("accepted_artifact_audit_refs", [])) if isinstance(audit.get("accepted_artifact_audit_refs"), list) else 0),
        ("Gate evidence refs", len(audit.get("current_gate_evidence_refs", [])) if isinstance(audit.get("current_gate_evidence_refs"), list) else 0),
      ))}</table>
    </section>

    <section>
      <h2>Checkpoint Signals</h2>
      <table>{_pairs((
        ("Project eligibility", checkpoint.get("project_checkpoint_eligibility", "")),
        ("Gate eligibility", checkpoint.get("current_gate_checkpoint_eligibility", "")),
        ("Next policy", checkpoint.get("next_action_checkpoint_policy", "")),
        ("Required tasks", checkpoint.get("checkpoint_required_tasks", 0)),
      ))}</table>
      <ul>{_list_items(checkpoint.get("checkpoint_blocked_by", []) if isinstance(checkpoint.get("checkpoint_blocked_by"), list) else [])}</ul>
    </section>

    <section>
      <h2>Context Budget</h2>
      <table>{_pairs((
        ("Available", context_budget.get("available", False)),
        ("Source", context_budget.get("source", "")),
        ("Max docs", context_budget.get("max_docs", "")),
        ("Max sections/doc", context_budget.get("max_sections_per_doc", "")),
        ("Max chars total", context_budget.get("max_chars_total", "")),
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
