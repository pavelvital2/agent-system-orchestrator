"""Read-only task dependency graph verification and rendering."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from commands import state_verify


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3

NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}
DEPENDENCY_SATISFIED_STATUSES = {"audit_passed", "checkpoint_done", "completed"}
DEPENDENCY_ACTIVE_STATUSES = {"ready", "running", "audit_pending", "audit_passed", "checkpoint_done", "completed"}
FORBIDDEN_OUTPUT_ROOTS = ("project-runtime", "project-input", "project-archive", ".tmp", "tmp")
SAFE_LABEL_RE = re.compile(r"[^A-Za-z0-9 _./:#-]+")


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    title: str
    details: str
    path: str
    field: str
    recommendation: str

    def to_json(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "message": self.details,
            "details": self.details,
            "path": self.path,
            "field": self.field,
            "recommendation": self.recommendation,
        }


def _finding(
    rule_id: str,
    title: str,
    details: str,
    field: str,
    recommendation: str,
    *,
    severity: str = "error",
) -> Finding:
    return Finding(
        rule_id,
        severity,
        title,
        details,
        "project-runtime/state/TASK_REGISTRY.json",
        field,
        recommendation,
    )


def _is_none(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in NONE_VALUES)


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


def _truthy_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    refs: list[str] = []
    for item in value:
        if isinstance(item, str) and not _is_none(item):
            refs.append(item.strip())
    return refs


def _task_registry_spec() -> state_verify.SidecarSpec:
    for spec in state_verify.SIDECARS:
        if spec.sidecar_type == "TASK_REGISTRY":
            return spec
    raise RuntimeError("TASK_REGISTRY sidecar spec is unavailable")


def _load_task_registry(root: Path) -> tuple[dict[str, object] | None, list[Finding]]:
    spec = _task_registry_spec()
    payload, sidecar_findings = state_verify._validate_sidecar(root, spec)
    findings = [
        Finding(
            item.rule_id,
            item.severity,
            item.title,
            item.details,
            item.path,
            item.field,
            item.recommendation,
        )
        for item in sidecar_findings
    ]
    return payload, findings


def _tasks(payload: dict[str, object] | None) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        return []
    content = payload.get("content")
    if not isinstance(content, dict):
        return []
    tasks = content.get("tasks")
    if not isinstance(tasks, list):
        return []
    return [task for task in tasks if isinstance(task, dict)]


def _task_ids(tasks: list[dict[str, object]]) -> list[str]:
    return [_as_text(task.get("task_id")) for task in tasks if _as_text(task.get("task_id"))]


def _duplicate_findings(tasks: list[dict[str, object]]) -> list[Finding]:
    seen: dict[str, int] = {}
    findings: list[Finding] = []
    for index, task_id in enumerate(_task_ids(tasks)):
        if task_id in seen:
            findings.append(
                _finding(
                    "DAG_TASK_ID_DUPLICATE",
                    "Task id appears more than once",
                    f"tasks[{index}].task_id={task_id!r} duplicates tasks[{seen[task_id]}].task_id.",
                    f"content.tasks[{index}].task_id",
                    "Use one unique task_id per task registry entry.",
                )
            )
        else:
            seen[task_id] = index
    return findings


def _missing_dependency_findings(tasks: list[dict[str, object]]) -> list[Finding]:
    known = set(_task_ids(tasks))
    findings: list[Finding] = []
    for index, task in enumerate(tasks):
        task_id = _as_text(task.get("task_id")) or f"tasks[{index}]"
        for dep in _truthy_string_list(task.get("dependencies")):
            if dep in known:
                continue
            findings.append(
                _finding(
                    "DAG_DEPENDENCY_MISSING",
                    "Task dependency is missing",
                    f"{task_id} depends on {dep!r}, but that task_id is absent from TASK_REGISTRY.tasks.",
                    f"content.tasks[{index}].dependencies",
                    "Add the dependency task to TASK_REGISTRY or remove the stale dependency reference.",
                )
            )
    return findings


def _cycle_findings(tasks: list[dict[str, object]]) -> list[Finding]:
    known = set(_task_ids(tasks))
    graph = {
        _as_text(task.get("task_id")): [dep for dep in _truthy_string_list(task.get("dependencies")) if dep in known]
        for task in tasks
        if _as_text(task.get("task_id"))
    }
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []
    cycles: list[list[str]] = []
    seen_cycles: set[tuple[str, ...]] = set()

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            start = stack.index(task_id)
            cycle = stack[start:] + [task_id]
            canonical = tuple(cycle)
            if canonical not in seen_cycles:
                seen_cycles.add(canonical)
                cycles.append(cycle)
            return
        visiting.add(task_id)
        stack.append(task_id)
        for dep in sorted(graph.get(task_id, [])):
            visit(dep)
        stack.pop()
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in sorted(graph):
        visit(task_id)

    return [
        _finding(
            "DAG_DEPENDENCY_CYCLE",
            "Task dependency graph contains a cycle",
            " -> ".join(cycle),
            "content.tasks[].dependencies",
            "Break the cycle by removing or reclassifying one dependency edge.",
        )
        for cycle in cycles
    ]


def _status_dependency_findings(tasks: list[dict[str, object]]) -> list[Finding]:
    by_id = {_as_text(task.get("task_id")): task for task in tasks if _as_text(task.get("task_id"))}
    findings: list[Finding] = []
    for index, task in enumerate(tasks):
        task_id = _as_text(task.get("task_id")) or f"tasks[{index}]"
        status = _as_text(task.get("status"))
        if status not in DEPENDENCY_ACTIVE_STATUSES:
            continue
        for dep in _truthy_string_list(task.get("dependencies")):
            dep_task = by_id.get(dep)
            if dep_task is None:
                continue
            dep_status = _as_text(dep_task.get("status"))
            if dep_status in DEPENDENCY_SATISFIED_STATUSES:
                continue
            rule_id = "DAG_READY_TASK_BLOCKED_BY_DEPENDENCY" if status == "ready" else "DAG_STATUS_DEPENDENCY_INVALID"
            findings.append(
                _finding(
                    rule_id,
                    "Task status is inconsistent with dependency status",
                    (
                        f"{task_id} is {status!r}, but dependency {dep} is {dep_status!r}; "
                        "there is no satisfied dependency evidence."
                    ),
                    f"content.tasks[{index}].status",
                    "Keep the task pending/blocked until dependency tasks have audit_passed, checkpoint_done, or completed status.",
                )
            )
    return findings


def _requester_return_findings(tasks: list[dict[str, object]]) -> list[Finding]:
    known = set(_task_ids(tasks))
    findings: list[Finding] = []
    for index, task in enumerate(tasks):
        task_id = _as_text(task.get("task_id")) or f"tasks[{index}]"
        requested_by_role = _as_text(task.get("requested_by_role"))
        requested_by_task = _as_text(task.get("requested_by_task"))
        return_enabled = task.get("return_to_requester_after_audit_pass") is True
        return_role = _as_text(task.get("return_to_role_after_audit_pass"))
        return_task = _as_text(task.get("return_task_after_audit_pass"))

        if not _is_none(requested_by_task) and requested_by_task not in known:
            findings.append(
                _finding(
                    "DAG_REQUESTER_TASK_MISSING",
                    "Requester task metadata references a missing task",
                    f"{task_id}.requested_by_task={requested_by_task!r} is absent from TASK_REGISTRY.tasks.",
                    f"content.tasks[{index}].requested_by_task",
                    "Point requested_by_task at an existing task_id or use NONE.",
                )
            )
        if requested_by_task == task_id:
            findings.append(
                _finding(
                    "DAG_REQUESTER_METADATA_INVALID",
                    "Requester metadata points to the same task",
                    f"{task_id}.requested_by_task must not point to itself.",
                    f"content.tasks[{index}].requested_by_task",
                    "Use the upstream requester task or NONE.",
                )
            )

        if return_enabled:
            missing = []
            if _is_none(requested_by_role):
                missing.append("requested_by_role")
            if _is_none(requested_by_task):
                missing.append("requested_by_task")
            if return_role in {"", "none", "NONE"}:
                missing.append("return_to_role_after_audit_pass")
            if _is_none(return_task):
                missing.append("return_task_after_audit_pass")
            if missing:
                findings.append(
                    _finding(
                        "DAG_REQUESTER_RETURN_METADATA_INCOMPLETE",
                        "Requester return metadata is incomplete",
                        f"{task_id} enables requester return but lacks: {', '.join(missing)}.",
                        f"content.tasks[{index}].return_to_requester_after_audit_pass",
                        "Populate requester and return metadata or disable requester return.",
                    )
                )
            if not _is_none(return_task) and return_task not in known:
                findings.append(
                    _finding(
                        "DAG_RETURN_TASK_MISSING",
                        "Return task metadata references a missing task",
                        f"{task_id}.return_task_after_audit_pass={return_task!r} is absent from TASK_REGISTRY.tasks.",
                        f"content.tasks[{index}].return_task_after_audit_pass",
                        "Point return_task_after_audit_pass at an existing task_id or use NONE when return is disabled.",
                    )
                )
        elif return_role not in {"", "none"} or not _is_none(return_task):
            findings.append(
                _finding(
                    "DAG_REQUESTER_RETURN_METADATA_INCONSISTENT",
                    "Requester return metadata is set while requester return is disabled",
                    f"{task_id} has return metadata but return_to_requester_after_audit_pass=false.",
                    f"content.tasks[{index}].return_to_requester_after_audit_pass",
                    "Set return metadata to none/NONE or enable requester return.",
                )
            )
    return findings


def verify_report(root: Path) -> tuple[dict[str, object], int]:
    payload, findings = _load_task_registry(root)
    tasks = _tasks(payload)
    findings.extend(_duplicate_findings(tasks))
    findings.extend(_missing_dependency_findings(tasks))
    findings.extend(_cycle_findings(tasks))
    findings.extend(_status_dependency_findings(tasks))
    findings.extend(_requester_return_findings(tasks))
    findings = sorted(findings, key=lambda item: (item.severity != "error", item.rule_id, item.field, item.details))
    summary = {
        "errors": sum(1 for finding in findings if finding.severity == "error"),
        "warnings": sum(1 for finding in findings if finding.severity == "warning"),
        "info": sum(1 for finding in findings if finding.severity == "info"),
    }
    status = "failed" if summary["errors"] else "passed"
    report = {
        "tool": "aso",
        "command": "dag verify",
        "mode": "workspace",
        "status": status,
        "root": str(root),
        "summary": summary,
        "findings": [finding.to_json() for finding in findings],
        "graph": {
            "task_count": len(tasks),
            "edge_count": sum(len(_truthy_string_list(task.get("dependencies"))) for task in tasks),
            "task_ids": sorted(_task_ids(tasks)),
        },
        "read_only": True,
        "mutations_performed": False,
    }
    return report, EXIT_FINDINGS if summary["errors"] else EXIT_OK


def _print_verify_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    graph = report["graph"]
    if not isinstance(summary, dict) or not isinstance(graph, dict):
        raise TypeError("internal dag verify report is malformed")
    print(f"ASO dag verify: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    print("Mode: workspace")
    print(f"Tasks: {graph['task_count']}")
    print(f"Edges: {graph['edge_count']}")
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Info: {summary['info']}")
    print(f"Findings: {len(report['findings'])}")
    for finding in report["findings"]:
        if isinstance(finding, dict):
            print(f"- {finding['severity']} {finding['rule_id']}: {finding['title']}")


def _safe_label(value: object) -> str:
    text = _as_text(value)
    text = text.replace("\r", " ").replace("\n", " ")
    text = SAFE_LABEL_RE.sub("?", text)
    text = " ".join(text.split())
    return text[:160]


def _node_ids(tasks: list[dict[str, object]]) -> dict[str, str]:
    return {task_id: f"n{index}" for index, task_id in enumerate(sorted(_task_ids(tasks)))}


def _render_mermaid(tasks: list[dict[str, object]]) -> str:
    node_ids = _node_ids(tasks)
    by_id = {_as_text(task.get("task_id")): task for task in tasks if _as_text(task.get("task_id"))}
    lines = ["flowchart TD"]
    for task_id in sorted(node_ids):
        task = by_id[task_id]
        label = "\\n".join(
            part
            for part in (
                _safe_label(task_id),
                _safe_label(task.get("task_title")),
                _safe_label(task.get("status")),
            )
            if part
        )
        lines.append(f'  {node_ids[task_id]}["{label}"]')
    for task_id in sorted(node_ids):
        task = by_id[task_id]
        for dep in sorted(_truthy_string_list(task.get("dependencies"))):
            if dep in node_ids:
                lines.append(f"  {node_ids[dep]} --> {node_ids[task_id]}")
    return "\n".join(lines) + "\n"


def _dot_label(value: str) -> str:
    return json.dumps(value)


def _render_dot(tasks: list[dict[str, object]]) -> str:
    node_ids = _node_ids(tasks)
    by_id = {_as_text(task.get("task_id")): task for task in tasks if _as_text(task.get("task_id"))}
    lines = ["digraph TASK_DAG {", "  rankdir=LR;"]
    for task_id in sorted(node_ids):
        task = by_id[task_id]
        label = "\n".join(
            part
            for part in (
                _safe_label(task_id),
                _safe_label(task.get("task_title")),
                _safe_label(task.get("status")),
            )
            if part
        )
        lines.append(f"  {node_ids[task_id]} [label={_dot_label(label)}];")
    for task_id in sorted(node_ids):
        task = by_id[task_id]
        for dep in sorted(_truthy_string_list(task.get("dependencies"))):
            if dep in node_ids:
                lines.append(f"  {node_ids[dep]} -> {node_ids[task_id]};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _render(root: Path, output_format: str) -> tuple[str, dict[str, object], int]:
    report, exit_code = verify_report(root)
    if exit_code != EXIT_OK:
        return "", report, exit_code
    payload, _findings = _load_task_registry(root)
    tasks = _tasks(payload)
    if output_format == "mermaid":
        return _render_mermaid(tasks), report, EXIT_OK
    return _render_dot(tasks), report, EXIT_OK


def _is_forbidden_output(root: Path, path: Path) -> bool:
    resolved = path.expanduser().resolve(strict=False)
    workspace = root.expanduser().resolve(strict=False)
    for name in FORBIDDEN_OUTPUT_ROOTS:
        candidate = workspace / name
        try:
            resolved.relative_to(candidate)
            return True
        except ValueError:
            continue
    return False


def _write_output(root: Path, path_text: str, rendered: str) -> bool:
    path = Path(path_text).expanduser()
    if _is_forbidden_output(root, path):
        print(f"aso dag render: forbidden output path: {path}", file=sys.stderr)
        return False
    if not path.parent.exists():
        print(f"aso dag render: output parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        print(f"aso dag render: failed to write output: {exc}", file=sys.stderr)
        return False
    return True


def run_verify(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    report, exit_code = verify_report(root)
    _print_verify_text(report)
    return exit_code


def run_render(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    rendered, report, exit_code = _render(root, args.format)
    if exit_code != EXIT_OK:
        _print_verify_text(report)
        return exit_code
    if args.out:
        if not _write_output(root, args.out, rendered):
            return EXIT_IO_ERROR
        print(f"ASO dag render written: {args.out}")
        return EXIT_OK
    print(rendered, end="")
    return EXIT_OK
