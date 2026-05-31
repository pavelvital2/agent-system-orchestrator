"""Read-only runtime consistency lint command."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .. import result_parser
from . import mode_guard, package_checks, repair_hints, state_verify


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3

REQUIRED_RUNTIME_FILES = (
    "PROJECT_STATE.md",
    "CURRENT_GATE.md",
    "NEXT_ACTION.md",
    "TASK_REGISTRY.md",
    "ACCEPTED_ARTIFACTS.md",
    "REPOSITORY_LOCK.md",
    "WORKSPACE_IDENTITY.md",
)

SINGLETON_RUNTIME_FILES = {
    "PROJECT_STATE.md",
    "CURRENT_GATE.md",
    "NEXT_ACTION.md",
    "REPOSITORY_LOCK.md",
    "WORKSPACE_IDENTITY.md",
}

FIELD_RE = re.compile(r"^([A-Z][A-Z0-9_]*):(?:[ \t]*(.*))?$")
ALLOWED_REASONING_LEVELS = {"low", "medium", "high", "xhigh"}
REASONING_LEVEL_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "xhigh": 3,
}
DEPRECATED_REASONING_LEVELS = {
    "default",
    "maximum",
    "role_default",
    "standard",
    "analytical",
    "critical",
    "mechanical",
}
ROLE_ALIASES = {
    "designer": "solution_architect",
}
GATE_REASONING_FLOORS = {
    "initial_tz_analysis": "xhigh",
    "architecture_design": "xhigh",
    "task_decomposition": "high",
    "implementation": "high",
    "audit": "xhigh",
    "checkpoint": "high",
    "runtime_lint": "medium",
    "docs_update": "medium",
    "simple_file_move": "low",
}
FLOOR_FIELD_NAMES = {
    "REASONING_LEVEL_REQUIRED_FLOOR",
    "REASONING_LEVEL_FLOOR",
    "GATE_REASONING_FLOOR",
    "GATE_REQUIRED_FLOOR",
}
TERMINAL_TASK_STATUSES = {"checkpoint_done", "completed", "superseded"}
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}
CHECKPOINT_POLICIES = {"local_only", "commit_and_push"}
AUDIT_RESULT_REF_FIELDS = (
    "SOURCE_RESULT_REF",
    "AUDITED_RESULT_REF",
    "RESULT_REF",
    "ACCEPTED_RESULT_REF",
)
VERSION_FIELD_NAMES = (
    "PACKAGE_VERSION",
    "GOVERNANCE_RULESET_VERSION",
    "RUNTIME_SCHEMA_VERSION",
)
ACTIVE_VERSION_FIELD_NAMES = (
    "CURRENT_PACKAGE_VERSION",
    "CURRENT_GOVERNANCE_RULESET_VERSION",
    "CURRENT_RUNTIME_SCHEMA_VERSION",
)


@dataclass(frozen=True)
class FieldOccurrence:
    key: str
    value: str
    line: int


@dataclass(frozen=True)
class RuntimeFile:
    name: str
    relpath: str
    path: Path
    exists: bool
    text: str
    fields: dict[str, str]
    occurrences: list[FieldOccurrence]
    error: str | None = None


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    title: str
    details: str
    files: list[str]
    recommendation: str

    def to_json(self, mode: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.details,
            "path": self.files[0] if self.files else "",
            "title": self.title,
            "details": self.details,
            "files": self.files,
            "recommendation": self.recommendation,
        }
        if mode is not None:
            payload["mode"] = mode
        return payload


@dataclass
class AgentEventRecord:
    events: set[str]
    task_ids: set[str]
    reuse_violations: set[str]
    result_events: list[dict[str, object]]
    termination_events: list[dict[str, object]]


def _runtime_path(root: Path, name: str) -> Path:
    return root / "project-runtime" / name


def _read_text(path: Path) -> tuple[str, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return "", str(exc)


def _read_runtime_file(root: Path, name: str) -> RuntimeFile:
    relpath = f"project-runtime/{name}"
    path = _runtime_path(root, name)
    if not path.exists():
        return RuntimeFile(name, relpath, path, False, "", {}, [])
    if not path.is_file():
        return RuntimeFile(name, relpath, path, False, "", {}, [], "path exists but is not a regular file")

    text, error = _read_text(path)
    if error:
        return RuntimeFile(name, relpath, path, True, "", {}, [], error)

    occurrences = _parse_occurrences(text)
    fields: dict[str, str] = {}
    for occurrence in occurrences:
        if occurrence.value:
            fields.setdefault(occurrence.key, occurrence.value)
    return RuntimeFile(name, relpath, path, True, text, fields, occurrences)


def _parse_occurrences(text: str) -> list[FieldOccurrence]:
    occurrences: list[FieldOccurrence] = []
    pending_key: str | None = None
    pending_line = 0

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        match = FIELD_RE.match(line)
        if match:
            if pending_key is not None:
                occurrences.append(FieldOccurrence(pending_key, "", pending_line))
            pending_key = match.group(1)
            pending_line = line_no
            value = (match.group(2) or "").strip()
            if value:
                occurrences.append(FieldOccurrence(pending_key, value, pending_line))
                pending_key = None
            continue

        if pending_key is None:
            continue
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        occurrences.append(FieldOccurrence(pending_key, line, pending_line))
        pending_key = None

    if pending_key is not None:
        occurrences.append(FieldOccurrence(pending_key, "", pending_line))

    return occurrences


def _entries(occurrences: Iterable[FieldOccurrence], start_key: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for occurrence in occurrences:
        if occurrence.key == start_key:
            if current:
                entries.append(current)
            current = {occurrence.key: occurrence.value}
            continue
        if current is not None:
            current.setdefault(occurrence.key, occurrence.value)

    if current:
        entries.append(current)
    return entries


def _is_none(value: str | None) -> bool:
    return value is None or value.strip() in NONE_VALUES


def _is_affirmative(value: str | None) -> bool:
    return (value or "").strip().lower() in {"yes", "true", "waived", "approved", "historical", "covered"}


def _has_explicit_reason(entry: dict[str, str], *field_names: str) -> bool:
    reason_fields = set(field_names) | {
        "WAIVER_REASON",
        "TRACEABILITY_WAIVER_REASON",
        "HISTORICAL_REASON",
        "COVERAGE_REASON",
        "ARCHIVE_REASON",
        "REMOVAL_REASON",
        "MISSING_REASON",
        "RETENTION_REASON",
        "REASON",
        "NOTES",
    }
    return any(not _is_none(entry.get(field_name)) for field_name in reason_fields)


def _entry_is_historical(entry: dict[str, str]) -> bool:
    historical_fields = (
        "HISTORICAL",
        "HISTORICAL_RECORD",
        "IS_HISTORICAL",
        "TRACEABILITY_HISTORICAL",
    )
    return any(_is_affirmative(entry.get(field_name)) for field_name in historical_fields)


def _entry_is_waived(entry: dict[str, str]) -> bool:
    waiver_fields = (
        "WAIVED",
        "WAIVER",
        "LINT_WAIVER",
        "TRACEABILITY_WAIVER",
        "TRACEABILITY_WAIVED",
    )
    return any(_is_affirmative(entry.get(field_name)) for field_name in waiver_fields) and _has_explicit_reason(entry)


def _entry_is_historical_or_waived(entry: dict[str, str]) -> bool:
    return _entry_is_historical(entry) or _entry_is_waived(entry)


def _entry_has_checkpoint_coverage(entry: dict[str, str]) -> bool:
    coverage_fields = (
        "AGGREGATE_CHECKPOINT_REF",
        "COVERED_BY_CHECKPOINT_REF",
        "CHECKPOINT_COVERAGE_REF",
        "CHECKPOINT_COVERED_BY",
        "COVERED_BY_CHECKPOINT",
    )
    if any(not _is_none(entry.get(field_name)) for field_name in coverage_fields):
        return True
    coverage_value = entry.get("CHECKPOINT_COVERAGE", entry.get("TRACEABILITY_COVERAGE", ""))
    return _is_affirmative(coverage_value) and _has_explicit_reason(entry)


def _extract_reasoning_level(text: str, fields: dict[str, str]) -> str:
    for key in ("REASONING_LEVEL", "REASONING_LEVEL_VALUE"):
        value = fields.get(key, "").strip()
        if value:
            return value.lower()

    section_match = re.search(
        r"^##\s+REASONING_LEVEL\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not section_match:
        return ""
    value_match = re.search(
        r"^VALUE:\s*([A-Za-z_]+)\s*$",
        section_match.group("body"),
        re.MULTILINE,
    )
    return value_match.group(1).lower() if value_match else ""


def _extract_reasoning_floor(fields: dict[str, str]) -> tuple[str, str]:
    for key in FLOOR_FIELD_NAMES:
        value = fields.get(key, "").strip().lower()
        if value:
            return key, value

    gate = fields.get(
        "GATE_REASONING_FLOOR_NAME",
        fields.get("GATE_REASONING_FLOOR_KEY", ""),
    ).strip().lower()
    if gate in GATE_REASONING_FLOORS:
        return "GATE_REASONING_FLOOR_NAME", GATE_REASONING_FLOORS[gate]

    task_kind = fields.get("TASK_KIND", "").strip().lower()
    if task_kind == "audit":
        return "TASK_KIND", GATE_REASONING_FLOORS["audit"]
    if task_kind in {"setup", "launch"}:
        return "TASK_KIND", GATE_REASONING_FLOORS["implementation"]

    target_role = fields.get("TARGET_ROLE", "").strip().lower()
    if target_role == "auditor":
        return "TARGET_ROLE", GATE_REASONING_FLOORS["audit"]
    if target_role in {"designer", "solution_architect"}:
        return "TARGET_ROLE", GATE_REASONING_FLOORS["architecture_design"]

    return "", ""


def _is_below_reasoning_floor(level: str, floor: str) -> bool:
    return (
        level in REASONING_LEVEL_ORDER
        and floor in REASONING_LEVEL_ORDER
        and REASONING_LEVEL_ORDER[level] < REASONING_LEVEL_ORDER[floor]
    )


def _norm(value: str) -> str:
    return value.strip()


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _field(file: RuntimeFile, key: str) -> str:
    return file.fields.get(key, "")


def _validate_root_and_required_files(root: Path) -> tuple[dict[str, RuntimeFile], list[Finding], bool]:
    findings: list[Finding] = []
    files: dict[str, RuntimeFile] = {}

    if not root.exists() or not root.is_dir():
        findings.append(
            Finding(
                "LINT_IO_001",
                "error",
                "Project root is unreadable",
                f"{root} is not an existing readable directory.",
                [str(root)],
                "Pass --root pointing at an initialized project workspace.",
            )
        )
        return files, findings, False

    runtime_dir = root / "project-runtime"
    if not runtime_dir.exists() or not runtime_dir.is_dir():
        findings.append(
            Finding(
                "LINT_IO_002",
                "error",
                "project-runtime directory is missing",
                "Required runtime directory project-runtime is not present.",
                ["project-runtime"],
                "Initialize or restore project-runtime before running aso lint.",
            )
        )
        return files, findings, False

    missing_runtime_files: list[RuntimeFile] = []
    for name in REQUIRED_RUNTIME_FILES:
        runtime_file = _read_runtime_file(root, name)
        files[name] = runtime_file
        if runtime_file.error:
            findings.append(
                Finding(
                    "LINT_IO_003",
                    "error",
                    "Required runtime file is unreadable",
                    f"{runtime_file.relpath}: {runtime_file.error}",
                    [runtime_file.relpath],
                    "Repair the runtime path or permissions and rerun aso lint.",
                )
            )
        elif not runtime_file.exists:
            missing_runtime_files.append(runtime_file)

    missing_names = [runtime_file.name for runtime_file in missing_runtime_files]
    if repair_hints.missing_runtime_views_with_valid_sidecars(root, missing_names):
        missing_relpaths = [runtime_file.relpath for runtime_file in missing_runtime_files]
        findings.append(
            Finding(
                "LINT_IO_004",
                "error",
                repair_hints.MISSING_RUNTIME_VIEWS_TITLE,
                f"{repair_hints.MISSING_RUNTIME_VIEWS_TITLE} Missing views: {', '.join(missing_relpaths)}.",
                missing_relpaths,
                repair_hints.MISSING_RUNTIME_VIEWS_RECOMMENDATION,
            )
        )
    else:
        for runtime_file in missing_runtime_files:
            findings.append(
                Finding(
                    "LINT_IO_004",
                    "error",
                    "Required runtime file is missing",
                    f"{runtime_file.relpath} is not present.",
                    [runtime_file.relpath],
                    "Run aso state render --root WORKSPACE --confirm-write to materialize derived Markdown views from project-runtime/state JSON sidecars.",
                )
            )

    return files, findings, not findings


def _check_duplicate_field_mismatch(files: dict[str, RuntimeFile]) -> list[Finding]:
    findings: list[Finding] = []
    for name in SINGLETON_RUNTIME_FILES:
        runtime_file = files[name]
        values_by_key: dict[str, set[str]] = {}
        for occurrence in runtime_file.occurrences:
            value = _norm(occurrence.value)
            if _is_none(value):
                continue
            values_by_key.setdefault(occurrence.key, set()).add(value)

        for key, values in sorted(values_by_key.items()):
            if len(values) <= 1:
                continue
            findings.append(
                Finding(
                    "LINT_STATE_001",
                    "error",
                    "Duplicate field has conflicting values",
                    f"{runtime_file.relpath} repeats {key} with values: {', '.join(sorted(values))}.",
                    [runtime_file.relpath],
                    "Keep exactly one current value for singleton runtime fields.",
                )
            )
    return findings


def _check_checkpoint_gate(files: dict[str, RuntimeFile]) -> list[Finding]:
    checkpoint_status = _field(files["PROJECT_STATE.md"], "PROJECT_CHECKPOINT_STATUS")
    gate_status = _field(files["CURRENT_GATE.md"], "STATUS")
    if checkpoint_status == "passed" and gate_status not in {"passed", "skipped", "closed", "completed", "inactive"}:
        return [
            Finding(
                "LINT_STATE_002",
                "error",
                "Checkpoint passed but gate is active",
                f"PROJECT_CHECKPOINT_STATUS={checkpoint_status}; CURRENT_GATE.STATUS={gate_status or 'MISSING'}.",
                ["project-runtime/PROJECT_STATE.md", "project-runtime/CURRENT_GATE.md"],
                "Close the active gate or repair stale checkpoint state.",
            )
        ]
    return []


def _check_stale_next_action(files: dict[str, RuntimeFile]) -> list[Finding]:
    findings: list[Finding] = []
    next_action = files["NEXT_ACTION.md"]
    current_gate = files["CURRENT_GATE.md"]
    registry = files["TASK_REGISTRY.md"]
    action_type = _field(next_action, "ACTION_TYPE")
    task_id = _field(next_action, "TASK_ID")
    gate_task_id = _field(current_gate, "TASK_ID")
    project_status = _field(files["PROJECT_STATE.md"], "PROJECT_STATUS")
    task_entries = {entry.get("TASK_ID", ""): entry for entry in _entries(registry.occurrences, "TASK_ID")}

    if not _is_none(task_id) and not _is_none(gate_task_id) and task_id != gate_task_id:
        findings.append(
            Finding(
                "LINT_STATE_003",
                "error",
                "NEXT_ACTION task differs from current gate task",
                f"NEXT_ACTION.TASK_ID={task_id}; CURRENT_GATE.TASK_ID={gate_task_id}.",
                ["project-runtime/NEXT_ACTION.md", "project-runtime/CURRENT_GATE.md"],
                "Update NEXT_ACTION and CURRENT_GATE to point at the same active task or record a governed handoff.",
            )
        )

    if action_type not in {"stop", "finalize"} and not _is_none(task_id):
        task_entry = task_entries.get(task_id)
        if task_entry is None:
            findings.append(
                Finding(
                    "LINT_RT_004",
                    "error",
                    "NEXT_ACTION points to an unregistered task",
                    f"NEXT_ACTION.TASK_ID={task_id} is not present in TASK_REGISTRY.",
                    ["project-runtime/NEXT_ACTION.md", "project-runtime/TASK_REGISTRY.md"],
                    "Register the task before dispatch or repair the stale NEXT_ACTION.",
                )
            )
        elif task_entry.get("STATUS") in TERMINAL_TASK_STATUSES:
            findings.append(
                Finding(
                    "LINT_RT_004",
                    "error",
                    "NEXT_ACTION dispatches a terminal task",
                    f"TASK_REGISTRY marks {task_id} as {task_entry.get('STATUS')}.",
                    ["project-runtime/NEXT_ACTION.md", "project-runtime/TASK_REGISTRY.md"],
                    "Replace NEXT_ACTION with the next governed task or terminal stop action.",
                )
            )

    if project_status == "completed" and action_type not in {"stop", "finalize"}:
        findings.append(
            Finding(
                "LINT_STATE_006",
                "error",
                "NEXT_ACTION is stale for completed project",
                f"PROJECT_STATUS=completed but NEXT_ACTION.ACTION_TYPE={action_type or 'MISSING'}.",
                ["project-runtime/PROJECT_STATE.md", "project-runtime/NEXT_ACTION.md"],
                "Use a terminal stop/finalization action after completed project state.",
            )
        )

    return findings


def _check_checkpoint_receipt(files: dict[str, RuntimeFile]) -> list[Finding]:
    next_action = files["NEXT_ACTION.md"]
    project_state = files["PROJECT_STATE.md"]
    required = _field(next_action, "CHECKPOINT_RECEIPT_REQUIRED")
    policy = _field(next_action, "CHECKPOINT_POLICY")
    checkpoint_status = _field(project_state, "PROJECT_CHECKPOINT_STATUS")
    next_receipt_ref = _field(next_action, "CHECKPOINT_RECEIPT_REF")
    project_receipt_ref = _field(project_state, "CHECKPOINT_RECEIPT_REF")
    receipt_ref = next_receipt_ref if not _is_none(next_receipt_ref) else project_receipt_ref

    receipt_needed = (
        required == "yes"
        or policy in CHECKPOINT_POLICIES
        or checkpoint_status == "passed"
    )
    if receipt_needed and _is_none(receipt_ref):
        return [
            Finding(
                "LINT_STATE_007",
                "error",
                "Checkpoint receipt is missing",
                (
                    f"CHECKPOINT_RECEIPT_REQUIRED={required or 'MISSING'}; "
                    f"CHECKPOINT_POLICY={policy or 'MISSING'}; "
                    f"PROJECT_CHECKPOINT_STATUS={checkpoint_status or 'MISSING'}."
                ),
                ["project-runtime/PROJECT_STATE.md", "project-runtime/NEXT_ACTION.md"],
                "Record CHECKPOINT_RECEIPT_REF before marking checkpoint receipt requirements satisfied.",
            )
        ]
    return []


def _check_post_checkpoint_next_action(files: dict[str, RuntimeFile]) -> list[Finding]:
    project_state = files["PROJECT_STATE.md"]
    next_action = files["NEXT_ACTION.md"]
    current_gate = files["CURRENT_GATE.md"]

    checkpoint_status = _field(project_state, "PROJECT_CHECKPOINT_STATUS")
    if checkpoint_status != "passed":
        return []

    policy = _field(next_action, "CHECKPOINT_POLICY")
    action_type = _field(next_action, "ACTION_TYPE")
    task_id = _field(next_action, "TASK_ID")
    gate_task_id = _field(current_gate, "TASK_ID")
    project_receipt_ref = _field(project_state, "CHECKPOINT_RECEIPT_REF")
    next_receipt_ref = _field(next_action, "CHECKPOINT_RECEIPT_REF")
    next_action_is_checkpoint = policy in CHECKPOINT_POLICIES or action_type == "checkpoint"

    same_task_checkpoint = (
        next_action_is_checkpoint
        and not _is_none(task_id)
        and not _is_none(gate_task_id)
        and task_id == gate_task_id
    )
    same_receipt_checkpoint = (
        next_action_is_checkpoint
        and not _is_none(project_receipt_ref)
        and not _is_none(next_receipt_ref)
        and project_receipt_ref == next_receipt_ref
    )

    if same_task_checkpoint or same_receipt_checkpoint:
        return [
            Finding(
                "LINT_STATE_009",
                "error",
                "Checkpoint passed but NEXT_ACTION still points to the same checkpoint",
                (
                    f"PROJECT_CHECKPOINT_STATUS={checkpoint_status}; "
                    f"NEXT_ACTION.ACTION_TYPE={action_type or 'MISSING'}; "
                    f"NEXT_ACTION.CHECKPOINT_POLICY={policy or 'MISSING'}; "
                    f"NEXT_ACTION.TASK_ID={task_id or 'MISSING'}; "
                    f"CURRENT_GATE.TASK_ID={gate_task_id or 'MISSING'}."
                ),
                [
                    "project-runtime/PROJECT_STATE.md",
                    "project-runtime/NEXT_ACTION.md",
                    "project-runtime/CURRENT_GATE.md",
                ],
                "Recalculate NEXT_ACTION after checkpoint pass so it routes to the next governed action, not the completed checkpoint.",
            )
        ]
    return []


def _check_push_allowed(files: dict[str, RuntimeFile]) -> list[Finding]:
    values = {
        "PROJECT_STATE": _field(files["PROJECT_STATE.md"], "PUSH_ALLOWED"),
        "REPOSITORY_LOCK": _field(files["REPOSITORY_LOCK.md"], "PUSH_ALLOWED"),
        "WORKSPACE_IDENTITY": _field(files["WORKSPACE_IDENTITY.md"], "PUSH_ALLOWED"),
    }
    known = {source: value for source, value in values.items() if not _is_none(value)}
    if len(set(known.values())) <= 1:
        return []
    return [
        Finding(
            "LINT_STATE_008",
            "error",
            "Conflicting PUSH_ALLOWED values",
            ", ".join(f"{source}={value or 'MISSING'}" for source, value in values.items()),
            [
                "project-runtime/PROJECT_STATE.md",
                "project-runtime/REPOSITORY_LOCK.md",
                "project-runtime/WORKSPACE_IDENTITY.md",
            ],
            "Reconcile PUSH_ALLOWED across project state, repository lock, and workspace identity.",
        )
    ]


def _package_versioning_path(root: Path) -> Path:
    workspace_path = root / "agent-system" / "PACKAGE_VERSIONING.md"
    if workspace_path.is_file():
        return workspace_path
    return Path(__file__).resolve().parents[3] / "PACKAGE_VERSIONING.md"


def _active_version_tuple(root: Path) -> tuple[dict[str, str], str]:
    path = _package_versioning_path(root)
    text, error = _read_text(path)
    if error:
        return {}, _rel(root, path)
    active_section = re.search(
        r"^## Active version constants\s*(?P<body>.*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    source = active_section.group("body") if active_section else text
    fields = {occurrence.key: occurrence.value for occurrence in _parse_occurrences(source)}
    return {field_name: fields.get(field_name, "") for field_name in ACTIVE_VERSION_FIELD_NAMES}, _rel(root, path)


def _check_package_version_tuple(root: Path, files: dict[str, RuntimeFile]) -> list[Finding]:
    project_state = files["PROJECT_STATE.md"]
    if _entry_is_historical_or_waived(project_state.fields):
        return []

    runtime_tuple = {field_name: _field(project_state, field_name) for field_name in VERSION_FIELD_NAMES}
    if all(_is_none(value) for value in runtime_tuple.values()):
        return []

    active_tuple, versioning_relpath = _active_version_tuple(root)
    if not active_tuple or any(_is_none(value) for value in active_tuple.values()):
        return []

    expected = {
        "PACKAGE_VERSION": active_tuple["CURRENT_PACKAGE_VERSION"],
        "GOVERNANCE_RULESET_VERSION": active_tuple["CURRENT_GOVERNANCE_RULESET_VERSION"],
        "RUNTIME_SCHEMA_VERSION": active_tuple["CURRENT_RUNTIME_SCHEMA_VERSION"],
    }
    mismatches = [
        f"{field_name}={runtime_tuple[field_name] or 'MISSING'} expected {expected[field_name]}"
        for field_name in VERSION_FIELD_NAMES
        if runtime_tuple[field_name] != expected[field_name]
    ]
    if not mismatches:
        return []

    return [
        Finding(
            "LINT_RT_006",
            "error",
            "Package version tuple mismatch",
            "; ".join(mismatches),
            ["project-runtime/PROJECT_STATE.md", versioning_relpath],
            "Update PROJECT_STATE package/governance/schema versions to the active tuple or mark the runtime explicitly historical.",
        )
    ]


def _check_task_statuses(files: dict[str, RuntimeFile]) -> list[Finding]:
    findings: list[Finding] = []
    for entry in _entries(files["TASK_REGISTRY.md"].occurrences, "TASK_ID"):
        task_id = entry.get("TASK_ID", "UNKNOWN")
        status = entry.get("STATUS", "")
        result_refs = entry.get("RESULT_REFS", "")
        audit_refs = entry.get("AUDIT_REFS", "")
        checkpoint_ref = entry.get("CHECKPOINT_REF", "")
        commit_hash = entry.get("COMMIT_HASH", "")
        branch = entry.get("BRANCH", "")
        accepted_files = entry.get("ACCEPTED_FILES", "")
        traceability_exempt = _entry_is_historical_or_waived(entry)

        if status in {"completed", "audit_passed", "checkpoint_done"} and _is_none(result_refs):
            findings.append(
                Finding(
                    "LINT_TASK_001",
                    "error",
                    "Task status lacks result traceability",
                    f"{task_id} has STATUS={status} but RESULT_REFS is empty.",
                    ["project-runtime/TASK_REGISTRY.md"],
                    "Record the accepted RESULT reference or move the task back to a non-terminal status.",
                )
            )
        traceability_completed = status in {"completed", "checkpoint_done"}

        if traceability_completed and _is_none(audit_refs) and not traceability_exempt:
            findings.append(
                Finding(
                    "LINT_RT_002",
                    "error",
                    "Completed task lacks audit traceability",
                    f"{task_id} has STATUS={status} but AUDIT_REFS is empty.",
                    ["project-runtime/TASK_REGISTRY.md"],
                    "Record AUDIT_REFS, mark the entry explicitly historical, or add a governed traceability waiver with reason.",
                )
            )
        if (
            traceability_completed
            and _is_none(checkpoint_ref)
            and not traceability_exempt
            and not _entry_has_checkpoint_coverage(entry)
        ):
            findings.append(
                Finding(
                    "LINT_RT_003",
                    "error",
                    "Completed task lacks checkpoint traceability",
                    f"{task_id} has STATUS={status} but CHECKPOINT_REF is empty.",
                    ["project-runtime/TASK_REGISTRY.md"],
                    "Record CHECKPOINT_REF, record aggregate checkpoint coverage, or add a governed traceability waiver with reason.",
                )
            )
        if status in {"audit_passed", "checkpoint_done"} and _is_none(audit_refs):
            findings.append(
                Finding(
                    "LINT_TASK_002",
                    "error",
                    "Task status lacks audit traceability",
                    f"{task_id} has STATUS={status} but AUDIT_REFS is empty.",
                    ["project-runtime/TASK_REGISTRY.md"],
                    "Record the audit RESULT reference before using an audit-passed status.",
                )
            )
        if status == "checkpoint_done" and (
            _is_none(checkpoint_ref)
            or _is_none(commit_hash)
            or _is_none(branch)
            or _is_none(accepted_files)
        ):
            findings.append(
                Finding(
                    "LINT_TASK_003",
                    "error",
                    "Checkpoint-done task is missing checkpoint fields",
                    f"{task_id} has STATUS=checkpoint_done without complete commit, branch, accepted files, and checkpoint refs.",
                    ["project-runtime/TASK_REGISTRY.md"],
                    "Fill checkpoint traceability fields or repair the stale task status.",
                )
            )
    return findings


def _check_accepted_artifacts(root: Path, files: dict[str, RuntimeFile]) -> list[Finding]:
    findings: list[Finding] = []
    for entry in _entries(files["ACCEPTED_ARTIFACTS.md"].occurrences, "ARTIFACT_ID"):
        if entry.get("STATUS") != "accepted":
            continue
        artifact_ref = entry.get("ARTIFACT_REF", "")
        if _is_none(artifact_ref):
            findings.append(
                Finding(
                    "LINT_ARTIFACT_001",
                    "error",
                    "Accepted artifact has no ARTIFACT_REF",
                    f"{entry.get('ARTIFACT_ID', 'UNKNOWN')} is accepted but ARTIFACT_REF is empty.",
                    ["project-runtime/ACCEPTED_ARTIFACTS.md"],
                    "Record the accepted artifact path or supersede the artifact entry.",
                )
            )
            continue
        artifact_path = Path(artifact_ref)
        if not artifact_path.is_absolute():
            artifact_path = root / artifact_path
        if not artifact_path.exists():
            if _accepted_artifact_missing_allowed(entry):
                continue
            findings.append(
                Finding(
                    "LINT_RT_005",
                    "error",
                    "Accepted artifact is missing from workspace",
                    f"{entry.get('ARTIFACT_ID', 'UNKNOWN')} points to missing path {artifact_ref}.",
                    ["project-runtime/ACCEPTED_ARTIFACTS.md", artifact_ref],
                    "Restore the accepted artifact, or record archived/removed state with an explicit reason.",
                )
            )
    return findings


def _accepted_artifact_missing_allowed(entry: dict[str, str]) -> bool:
    archived_or_removed_values = {"archived", "archive", "removed", "deleted", "relocated"}
    explicit_archive_or_removal_reason = not _is_none(entry.get("ARCHIVE_REASON")) or not _is_none(
        entry.get("REMOVAL_REASON")
    )
    state_fields = (
        "PATH_STATUS",
        "ARTIFACT_PATH_STATUS",
        "FILESYSTEM_STATUS",
        "RETENTION_STATUS",
        "STORAGE_STATUS",
    )
    has_archived_or_removed_state = any(
        entry.get(field_name, "").strip().lower() in archived_or_removed_values
        for field_name in state_fields
    )
    has_archive_ref = not _is_none(entry.get("ARCHIVE_REF")) or not _is_none(entry.get("RELOCATION_REF"))
    return explicit_archive_or_removal_reason or (
        (has_archived_or_removed_state or has_archive_ref) and _has_explicit_reason(entry)
    )


def _classified_markdown_files(root: Path) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    search_roots = [
        root / "project-input",
        root / "project-runtime" / "tasks",
        root / "project-runtime" / "results",
        root / "project-runtime" / "agent-results",
        root / "project-runtime" / "audits",
    ]
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for path in search_root.rglob("*.md"):
            rel = _rel(root, path)
            name = path.name
            role = ""
            if name.startswith("AUDIT_RESULT_") or "/audits/" in f"/{rel}" or "/results/audit/" in f"/{rel}":
                role = "audit"
            elif name.startswith("RESULT_") or "/results/" in f"/{rel}" or "/agent-results/" in f"/{rel}":
                role = "result"
            elif name.startswith("TASK_") or "/tasks/" in f"/{rel}":
                role = "task"
            if role:
                candidates.append((role, path))
    return candidates


def _check_basename_collisions(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    by_stem: dict[str, dict[str, list[str]]] = {}
    for role, path in _classified_markdown_files(root):
        by_stem.setdefault(path.stem, {}).setdefault(role, []).append(_rel(root, path))

        if role == "result" and not path.name.startswith("RESULT_"):
            findings.append(
                Finding(
                    "LINT_NAMING_002",
                    "warning",
                    "Result file lacks RESULT_ prefix",
                    f"{_rel(root, path)} does not follow RESULT_<TASK_ID>_ATTEMPT_<NNN>.md.",
                    [_rel(root, path)],
                    "Use RESULT_<TASK_ID>_ATTEMPT_<NNN>.md for new result files.",
                )
            )
        if role == "audit" and not path.name.startswith("AUDIT_RESULT_"):
            findings.append(
                Finding(
                    "LINT_NAMING_003",
                    "warning",
                    "Audit file lacks AUDIT_RESULT_ prefix",
                    f"{_rel(root, path)} does not follow AUDIT_RESULT_<TASK_ID>_ATTEMPT_<NNN>.md.",
                    [_rel(root, path)],
                    "Use AUDIT_RESULT_<TASK_ID>_ATTEMPT_<NNN>.md for new audit result files.",
                )
            )

    for stem, roles in sorted(by_stem.items()):
        if len(roles) <= 1:
            continue
        paths = [path for role_paths in roles.values() for path in role_paths]
        findings.append(
            Finding(
                "LINT_NAMING_001",
                "warning",
                "Task/result/audit basename collision",
                f"{stem}.md is used for multiple record types: {', '.join(sorted(roles))}.",
                sorted(paths),
                "Use distinct TASK_, RESULT_, and AUDIT_RESULT_ prefixes with attempt suffixes for result records.",
            )
        )
    return findings


def _split_refs(value: str) -> list[str]:
    if _is_none(value):
        return []
    refs: list[str] = []
    for chunk in re.split(r"[, \n]+", value):
        ref = chunk.strip().strip("`")
        if ref and ref not in NONE_VALUES:
            refs.append(ref)
    return refs


def _read_fields(path: Path) -> dict[str, str]:
    text, error = _read_text(path)
    if error:
        return {}
    return {occurrence.key: occurrence.value for occurrence in _parse_occurrences(text)}


def _field_or_label_refs(path: Path, fields: dict[str, str], field_names: Iterable[str]) -> list[str]:
    refs: list[str] = []
    for field_name in field_names:
        refs.extend(_split_refs(fields.get(field_name, "")))

    text, error = _read_text(path)
    if error:
        return refs
    for field_name in field_names:
        label_re = re.compile(rf"^\s*-?\s*{re.escape(field_name)}:\s*(.+?)\s*$")
        for line in text.splitlines():
            match = label_re.match(line)
            if match:
                refs.extend(_split_refs(match.group(1)))
    return refs


def _registry_entries_by_task_id(files: dict[str, RuntimeFile]) -> dict[str, dict[str, str]]:
    registry = files.get("TASK_REGISTRY.md")
    if not registry:
        return {}
    return {
        entry.get("TASK_ID", ""): entry
        for entry in _entries(registry.occurrences, "TASK_ID")
        if not _is_none(entry.get("TASK_ID"))
    }


def _task_ids(root: Path, files: dict[str, RuntimeFile]) -> set[str]:
    task_ids: set[str] = set()
    for path in _task_packet_files(root):
        fields = _read_fields(path)
        task_id = fields.get("TASK_ID", "")
        if not _is_none(task_id):
            task_ids.add(task_id)
        elif path.stem.startswith("TASK_"):
            task_ids.add(path.stem)

    registry = files.get("TASK_REGISTRY.md")
    if registry:
        for entry in _entries(registry.occurrences, "TASK_ID"):
            task_id = entry.get("TASK_ID", "")
            if not _is_none(task_id):
                task_ids.add(task_id)
    return task_ids


def _existing_result_refs(root: Path, files: dict[str, RuntimeFile]) -> set[str]:
    refs: set[str] = set()
    for path in _result_files(root):
        rel = _rel(root, path)
        if "/results/audit/" in f"/{rel}" or "/audits/" in f"/{rel}":
            continue
        refs.add(rel)
        refs.add(path.name)
        refs.add(path.stem)

    registry = files.get("TASK_REGISTRY.md")
    if registry:
        for entry in _entries(registry.occurrences, "TASK_ID"):
            for ref in _split_refs(entry.get("RESULT_REFS", "")):
                refs.add(ref)
                refs.add(Path(ref).name)
                refs.add(Path(ref).stem)
    return refs


def _audit_result_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for search_root in [root / "project-runtime" / "results" / "audit", root / "project-runtime" / "audits"]:
        if search_root.exists():
            paths.extend(sorted(path for path in search_root.rglob("*.md") if path.is_file()))
    return paths


def _check_result_and_audit_references(root: Path, files: dict[str, RuntimeFile]) -> list[Finding]:
    findings: list[Finding] = []
    known_task_ids = _task_ids(root, files)
    known_result_refs = _existing_result_refs(root, files)

    for path in _result_files(root):
        relpath = _rel(root, path)
        if "/results/audit/" in f"/{relpath}" or "/audits/" in f"/{relpath}":
            continue
        try:
            parsed = result_parser.parse_result_file(path, strict=False)
            task_id = parsed.task_id
        except (OSError, UnicodeError):
            fields = _read_fields(path)
            task_id = fields.get("TASK_ID", "")
        if _is_none(task_id):
            findings.append(
                Finding(
                    "LINT_NAMING_004",
                    "warning",
                    "RESULT lacks TASK_ID reference",
                    f"{relpath} does not declare the task it executed.",
                    [relpath],
                    "Add TASK_ID pointing to the task packet or registered task.",
                )
            )
        elif task_id not in known_task_ids:
            findings.append(
                Finding(
                    "LINT_NAMING_005",
                    "warning",
                    "RESULT references unknown task",
                    f"{relpath} declares TASK_ID={task_id}, but no task packet or TASK_REGISTRY entry was found.",
                    [relpath],
                    "Register the task or keep a compatible task packet reference for traceability.",
                )
            )

    for path in _audit_result_files(root):
        relpath = _rel(root, path)
        try:
            parsed = result_parser.parse_result_file(path, strict=False)
            task_id = parsed.task_id
            result_refs = list(parsed.audit.source_result_refs or parsed.references.source_result_refs)
        except (OSError, UnicodeError):
            fields = _read_fields(path)
            task_id = fields.get("TASK_ID", "")
            result_refs = _field_or_label_refs(path, fields, AUDIT_RESULT_REF_FIELDS)

        if _is_none(task_id):
            findings.append(
                Finding(
                    "LINT_NAMING_006",
                    "warning",
                    "AUDIT_RESULT lacks TASK_ID reference",
                    f"{relpath} does not declare the audited task.",
                    [relpath],
                    "Add TASK_ID pointing to the audited task packet or registered task.",
                )
            )
        elif task_id not in known_task_ids:
            findings.append(
                Finding(
                    "LINT_NAMING_007",
                    "warning",
                    "AUDIT_RESULT references unknown task",
                    f"{relpath} declares TASK_ID={task_id}, but no task packet or TASK_REGISTRY entry was found.",
                    [relpath],
                    "Register the audited task or keep a compatible task packet reference for traceability.",
                )
            )

        if not result_refs:
            findings.append(
                Finding(
                    "LINT_NAMING_008",
                    "warning",
                    "AUDIT_RESULT lacks worker RESULT reference",
                    f"{relpath} does not reference the worker RESULT it audited.",
                    [relpath],
                    "Add SOURCE_RESULT_REF, AUDITED_RESULT_REF, RESULT_REF, or ACCEPTED_RESULT_REF.",
                )
            )
            continue

        missing_refs = [
            ref
            for ref in result_refs
            if ref not in known_result_refs and Path(ref).name not in known_result_refs and Path(ref).stem not in known_result_refs
        ]
        if missing_refs:
            findings.append(
                Finding(
                    "LINT_NAMING_009",
                    "warning",
                    "AUDIT_RESULT references unknown worker RESULT",
                    f"{relpath} references missing RESULT record(s): {', '.join(missing_refs)}.",
                    [relpath, *missing_refs],
                    "Point the audit record at an existing worker RESULT path or registry reference.",
                )
            )
    return findings


def _check_result_registry_traceability(root: Path, files: dict[str, RuntimeFile]) -> list[Finding]:
    findings: list[Finding] = []
    registry_entries = _registry_entries_by_task_id(files)

    for path in _result_files(root):
        relpath = _rel(root, path)
        fields = _read_fields(path)
        if _entry_is_historical_or_waived(fields):
            continue
        task_id = fields.get("TASK_ID", "")
        if _is_none(task_id):
            findings.append(
                Finding(
                    "LINT_RT_001",
                    "error",
                    "RESULT cannot be matched to TASK_REGISTRY",
                    f"{relpath} has no TASK_ID, so no TASK_REGISTRY entry can be matched.",
                    [relpath, "project-runtime/TASK_REGISTRY.md"],
                    "Add TASK_ID and register the task before accepting the RESULT.",
                )
            )
            continue
        if task_id not in registry_entries:
            findings.append(
                Finding(
                    "LINT_RT_001",
                    "error",
                    "RESULT task is missing from TASK_REGISTRY",
                    f"{relpath} declares TASK_ID={task_id}, but TASK_REGISTRY has no matching entry.",
                    [relpath, "project-runtime/TASK_REGISTRY.md"],
                    "Add the task to TASK_REGISTRY or archive/waive the historical RESULT explicitly.",
                )
            )
    return findings


def _result_files(root: Path) -> list[Path]:
    result_roots = [root / "project-runtime" / "results", root / "project-runtime" / "agent-results"]
    paths: list[Path] = []
    for result_root in result_roots:
        if result_root.exists():
            paths.extend(sorted(result_root.rglob("*.md")))
    return paths


TERMINATION_EVENT_TYPES = {
    "AGENT_TERMINATED",
    "AUDITOR_AGENT_TERMINATED",
    "agent_instance_terminated",
    "auditor_agent_terminated",
}


RESULT_RECEIVED_EVENT_TYPES = {
    "RESULT_RECEIVED",
    "AUDIT_RESULT_RECEIVED",
    "agent_result_received",
}


def _empty_agent_event_record() -> AgentEventRecord:
    return AgentEventRecord(set(), set(), set(), [], [])


def _payload_event_types(payload: dict[str, object]) -> set[str]:
    event = str(payload.get("event", "")).strip()
    event_type = str(payload.get("event_type", "")).strip()
    return {value for value in (event, event_type) if value}


def _agent_events(root: Path) -> dict[str, AgentEventRecord]:
    events_path = root / "project-runtime" / "agents" / "instances.jsonl"
    events: dict[str, AgentEventRecord] = {}
    if not events_path.exists():
        return events

    text, error = _read_text(events_path)
    if error:
        return events
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        agent_id = str(payload.get("agent_instance_id", "")).strip()
        payload_types = _payload_event_types(payload)
        if agent_id and payload_types:
            record = events.setdefault(agent_id, _empty_agent_event_record())
            record.events.update(payload_types)
            task_id = str(payload.get("task_id", payload.get("TASK_ID", ""))).strip()
            if task_id:
                record.task_ids.add(task_id)
            reuse_allowed = str(payload.get("reuse_allowed", "")).strip().lower()
            if payload_types & RESULT_RECEIVED_EVENT_TYPES:
                record.result_events.append(payload)
            if (payload_types & RESULT_RECEIVED_EVENT_TYPES) and reuse_allowed != "false":
                raw_reuse_allowed = str(payload.get("reuse_allowed", "MISSING")).strip()
                record.reuse_violations.add(raw_reuse_allowed or "MISSING")
            if payload_types & TERMINATION_EVENT_TYPES:
                record.termination_events.append(payload)
    return events


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _expected_termination_event_type(role: str) -> str:
    return "AUDITOR_AGENT_TERMINATED" if role == "auditor" else "AGENT_TERMINATED"


def _expected_next_allowed_action(role: str, status: str = "") -> str:
    if role == "auditor":
        return "correction_required" if status in {"fail", "blocked", "gap"} else "checkpoint_preflight"
    return "audit_route"


def _matching_result_received_event(
    event_record: AgentEventRecord,
    *,
    task_id: str,
    result_ref: str,
) -> dict[str, object] | None:
    for event in event_record.result_events:
        if str(event.get("task_id", "")).strip() != task_id:
            continue
        if str(event.get("result_ref", "")).strip() != result_ref:
            continue
        return event
    return None


def _valid_termination_event(
    root: Path,
    event_record: AgentEventRecord,
    *,
    result_fields: dict[str, str],
    result_ref: str,
) -> tuple[bool, str]:
    task_id = result_fields.get("TASK_ID", "")
    role = result_fields.get("ROLE", "")
    expected_type = _expected_termination_event_type(role)
    if len(event_record.termination_events) > 1:
        return False, "multiple termination events for agent instance"
    matching_received_event = _matching_result_received_event(
        event_record,
        task_id=task_id,
        result_ref=result_ref,
    )
    received_timestamp = None
    if matching_received_event is not None:
        received_timestamp = _parse_timestamp(
            matching_received_event.get("timestamp_utc")
            or matching_received_event.get("received_at")
        )

    matches: list[dict[str, object]] = []
    issues: list[str] = []
    for event in event_record.termination_events:
        event_type = str(event.get("event_type", "")).strip()
        if event_type != expected_type:
            issues.append(f"event_type={event_type or 'MISSING'}")
            continue
        if str(event.get("task_id", "")).strip() != task_id:
            issues.append(f"task_id={str(event.get('task_id', 'MISSING')).strip() or 'MISSING'}")
            continue
        if str(event.get("result_ref", "")).strip() != result_ref:
            issues.append(f"result_ref={str(event.get('result_ref', 'MISSING')).strip() or 'MISSING'}")
            continue
        if not (root / result_ref).is_file():
            issues.append(f"result_ref_missing={result_ref}")
            continue
        event_role = str(event.get("agent_role") or event.get("role", "")).strip()
        if event_role != role:
            issues.append(f"agent_role={event_role or 'MISSING'}")
            continue
        if str(event.get("termination_reason", "")).strip() != "result_submitted":
            issues.append("termination_reason invalid")
            continue
        if str(event.get("created_by", "")).strip() != "orchestrator":
            issues.append("created_by invalid")
            continue
        expected_next_action = _expected_next_allowed_action(
            role,
            str(result_fields.get("STATUS", "")).strip().lower(),
        )
        if str(event.get("next_allowed_action", "")).strip() != expected_next_action:
            issues.append("next_allowed_action invalid")
            continue
        if str(event.get("reuse_allowed", "false")).strip().lower() not in {"false", ""}:
            issues.append("reuse_allowed invalid")
            continue
        terminated_timestamp = _parse_timestamp(
            event.get("terminated_at") or event.get("timestamp_utc")
        )
        if received_timestamp is not None and terminated_timestamp is not None:
            if terminated_timestamp < received_timestamp:
                issues.append("terminated_at before result receipt")
                continue
        matches.append(event)

    if len(matches) == 1:
        return True, ""
    if len(matches) > 1:
        return False, "multiple matching termination events"
    if issues:
        return False, "; ".join(sorted(set(issues)))
    return False, "missing AGENT_TERMINATED event"


def _check_agent_lifecycle(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    events = _agent_events(root)
    required_lifecycle_fields = (
        "TASK_ID",
        "AGENT_INSTANCE_ID",
        "SUMMARY",
        "CHANGED_FILES",
        "COMMANDS_RUN",
        "TESTS_RUN",
        "RISKS",
        "LIMITATIONS",
        "REUSE_ALLOWED",
        "AGENT_TERMINATION_REQUIRED",
    )
    for path in _result_files(root):
        text, error = _read_text(path)
        if error:
            continue
        fields = {occurrence.key: occurrence.value for occurrence in _parse_occurrences(text)}
        relpath = _rel(root, path)
        agent_id = fields.get("AGENT_INSTANCE_ID", "")
        task_id = fields.get("TASK_ID", "")
        reuse_allowed = fields.get("REUSE_ALLOWED", "")
        termination_required = fields.get("AGENT_TERMINATION_REQUIRED", "")
        missing_fields = [
            field for field in required_lifecycle_fields if _is_none(fields.get(field))
        ]

        if missing_fields:
            findings.append(
                Finding(
                    "LINT_AGENT_005",
                    "error",
                    "RESULT is missing lifecycle fields",
                    f"{relpath} omits required lifecycle fields: {', '.join(missing_fields)}.",
                    [relpath],
                    "Add the mandatory profile-agent lifecycle fields from AGENT_RESULT_TEMPLATE.md.",
                )
            )

        if reuse_allowed != "false":
            findings.append(
                Finding(
                    "LINT_AGENT_001",
                    "error",
                    "RESULT does not forbid agent reuse",
                    f"{relpath} has REUSE_ALLOWED={reuse_allowed or 'MISSING'}.",
                    [relpath],
                    "Set REUSE_ALLOWED: false in every profile-agent RESULT.",
                )
            )
        if termination_required != "true":
            findings.append(
                Finding(
                    "LINT_AGENT_002",
                    "error",
                    "RESULT does not require agent termination",
                    f"{relpath} has AGENT_TERMINATION_REQUIRED={termination_required or 'MISSING'}.",
                    [relpath],
                    "Set AGENT_TERMINATION_REQUIRED: true in every profile-agent RESULT.",
                )
            )
        if not _is_none(agent_id):
            event_record = events.get(agent_id, _empty_agent_event_record())
            termination_valid, termination_issue = _valid_termination_event(
                root,
                event_record,
                result_fields=fields,
                result_ref=relpath,
            )
            if not termination_valid:
                findings.append(
                    Finding(
                        "LINT_AGENT_003",
                        "error",
                        repair_hints.LINT_AGENT_003_TITLE,
                        (
                            f"LINT_AGENT_003: {repair_hints.LINT_AGENT_003_TITLE} "
                            f"{relpath} records AGENT_INSTANCE_ID={agent_id} "
                            f"but no matching AGENT_TERMINATED event exists: {termination_issue}."
                        ),
                        [relpath, "project-runtime/agents/instances.jsonl"],
                        repair_hints.LINT_AGENT_003_RECOMMENDATION,
                    )
                )
            if event_record.reuse_violations:
                findings.append(
                    Finding(
                        "LINT_AGENT_004",
                        "error",
                        "Agent result event allows reuse",
                        f"agent_result_received for {agent_id} has reuse_allowed={', '.join(sorted(event_record.reuse_violations))}.",
                        ["project-runtime/agents/instances.jsonl"],
                        "Record result receipt with reuse_allowed=false and terminate the agent instance.",
                    )
                )
            if len(event_record.task_ids) > 1:
                findings.append(
                    Finding(
                        "LINT_AGENT_006",
                        "error",
                        "Agent instance is associated with multiple task ids",
                        f"{agent_id} appears with task ids: {', '.join(sorted(event_record.task_ids))}.",
                        ["project-runtime/agents/instances.jsonl"],
                        "Use one fresh AGENT_INSTANCE_ID per task.",
                    )
                )
    return findings


def _task_packet_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for search_root in [root / "project-input", root / "project-runtime" / "tasks"]:
        if search_root.exists():
            paths.extend(sorted(path for path in search_root.rglob("TASK_*.md") if path.is_file()))
    return paths


def _check_reasoning_and_designer(root: Path, files: dict[str, RuntimeFile]) -> list[Finding]:
    findings: list[Finding] = []
    for path in _task_packet_files(root):
        text, error = _read_text(path)
        if error:
            continue
        occurrences = _parse_occurrences(text)
        fields = {occurrence.key: occurrence.value for occurrence in occurrences}
        relpath = _rel(root, path)
        level = _extract_reasoning_level(text, fields)
        if _is_none(level):
            findings.append(
                Finding(
                    "LINT_REASONING_001",
                    "error",
                    "Task packet is missing REASONING_LEVEL",
                    f"{relpath} has no REASONING_LEVEL field.",
                    [relpath],
                    "Add REASONING_LEVEL: low|medium|high|xhigh.",
                )
            )
        elif level in DEPRECATED_REASONING_LEVELS:
            findings.append(
                Finding(
                    "LINT_REASONING_002",
                    "warning",
                    "Task packet uses deprecated REASONING_LEVEL",
                    f"{relpath} uses REASONING_LEVEL={level}.",
                    [relpath],
                    "Migrate new task packets to low, medium, high, or xhigh.",
                )
            )
        elif level not in ALLOWED_REASONING_LEVELS:
            findings.append(
                Finding(
                    "LINT_REASONING_003",
                    "error",
                    "Task packet uses invalid REASONING_LEVEL",
                    f"{relpath} uses REASONING_LEVEL={level}.",
                    [relpath],
                    "Use one of low, medium, high, or xhigh.",
                )
            )
        else:
            floor_source, floor = _extract_reasoning_floor(fields)
            if floor and floor not in ALLOWED_REASONING_LEVELS:
                findings.append(
                    Finding(
                        "LINT_REASONING_004",
                        "error",
                        "Task packet uses invalid reasoning floor",
                        f"{relpath} has {floor_source}={floor}.",
                        [relpath],
                        "Use a gate floor of low, medium, high, or xhigh.",
                    )
                )
            elif _is_below_reasoning_floor(level, floor):
                findings.append(
                    Finding(
                        "LINT_REASONING_005",
                        "error",
                        "Task packet is below reasoning gate floor",
                        f"{relpath} uses REASONING_LEVEL={level} below {floor_source}={floor}.",
                        [relpath],
                        "Raise REASONING_LEVEL to satisfy the gate-required floor.",
                    )
                )

        for role_key in ("TARGET_ROLE", "OWNER_ROLE", "ROLE", "CURRENT_AGENT_ROLE"):
            role_value = fields.get(role_key, "")
            if role_value in ROLE_ALIASES:
                findings.append(
                    Finding(
                        "LINT_ROLE_001",
                        "warning",
                        "Deprecated designer role alias is used",
                        f"{relpath} has {role_key}: {role_value}; canonical role is {ROLE_ALIASES[role_value]}.",
                        [relpath],
                        "Use solution_architect for new design work; keep designer only for legacy compatibility.",
                    )
                )

    for runtime_file in files.values():
        for occurrence in runtime_file.occurrences:
            if occurrence.key in {"TARGET_ROLE", "OWNER_ROLE", "ROLE", "CURRENT_AGENT_ROLE"} and occurrence.value in ROLE_ALIASES:
                findings.append(
                    Finding(
                        "LINT_ROLE_002",
                        "warning",
                        "Deprecated designer role alias is used in runtime state",
                        f"{runtime_file.relpath} line {occurrence.line} has {occurrence.key}: {occurrence.value}; canonical role is {ROLE_ALIASES[occurrence.value]}.",
                        [runtime_file.relpath],
                        "Use solution_architect for new design work; preserve designer only for legacy records.",
                    )
                )
    return findings


def _check_skeleton_product_pass(root: Path, files: dict[str, RuntimeFile]) -> list[Finding]:
    findings: list[Finding] = []
    paths = _task_packet_files(root) + _result_files(root)
    runtime_extra = [runtime_file.path for runtime_file in files.values()]
    for path in paths + runtime_extra:
        if not path.exists() or not path.is_file():
            continue
        text, error = _read_text(path)
        if error:
            continue
        lowered = text.lower()
        if "skeleton" not in lowered:
            continue
        occurrences = _parse_occurrences(text)
        fields = {occurrence.key: occurrence.value.lower() for occurrence in occurrences}
        product_markers = {
            "PRODUCT_PASS",
            "PRODUCT_STATUS",
            "MVP_READY",
            "MVP_STATUS",
            "FINAL_ACCEPTANCE",
            "CAPABILITY_PASS",
        }
        skeleton_pass = fields.get("SKELETON_STATUS") == "passed" or fields.get("SKELETON_PASS") in {"true", "yes", "passed"}
        product_pass = any(fields.get(marker) in {"passed", "pass", "true", "yes", "ready", "mvp_ready"} for marker in product_markers)
        if skeleton_pass and product_pass:
            findings.append(
                Finding(
                    "LINT_PRODUCT_001",
                    "error",
                    "Skeleton pass is marked as product/MVP pass",
                    f"{_rel(root, path)} records skeleton pass together with product/MVP readiness.",
                    [_rel(root, path)],
                    "Separate skeleton/task pass from capability, product, MVP, and final acceptance gates.",
                )
            )
    return findings


def _check_bootstrap_state_semantics(root: Path) -> list[Finding]:
    state_root = root / "project-runtime" / "state"
    if not state_root.is_dir():
        return []
    verify_report, _exit_code = state_verify._report(root, strict=False)
    raw_findings = verify_report.get("findings", [])
    if not isinstance(raw_findings, list):
        return []

    findings: list[Finding] = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        rule_id = str(item.get("rule_id", ""))
        if not rule_id.startswith("BSR_"):
            continue
        findings.append(
            Finding(
                rule_id,
                str(item.get("severity", "error")),
                str(item.get("title", item.get("message", "Bootstrap state semantic finding"))),
                str(item.get("details", item.get("message", ""))),
                [str(item.get("path", ""))] if item.get("path") else [],
                str(item.get("recommendation", "Run aso state verify --root WORKSPACE --strict and repair bootstrap state.")),
            )
        )
    return findings


def _all_lint_findings(root: Path, files: dict[str, RuntimeFile]) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_check_duplicate_field_mismatch(files))
    findings.extend(_check_checkpoint_gate(files))
    findings.extend(_check_stale_next_action(files))
    findings.extend(_check_checkpoint_receipt(files))
    findings.extend(_check_post_checkpoint_next_action(files))
    findings.extend(_check_push_allowed(files))
    findings.extend(_check_package_version_tuple(root, files))
    findings.extend(_check_task_statuses(files))
    findings.extend(_check_accepted_artifacts(root, files))
    findings.extend(_check_basename_collisions(root))
    findings.extend(_check_result_and_audit_references(root, files))
    findings.extend(_check_result_registry_traceability(root, files))
    findings.extend(_check_agent_lifecycle(root))
    findings.extend(_check_reasoning_and_designer(root, files))
    findings.extend(_check_skeleton_product_pass(root, files))
    findings.extend(_check_bootstrap_state_semantics(root))
    return findings


def _summary(findings: list[Finding]) -> dict[str, int]:
    return {
        "errors": sum(1 for finding in findings if finding.severity == "error"),
        "warnings": sum(1 for finding in findings if finding.severity == "warning"),
        "info": sum(1 for finding in findings if finding.severity == "info"),
    }


def _package_finding(finding: package_checks.Finding) -> Finding:
    return Finding(
        finding.rule_id,
        finding.severity,
        finding.title,
        finding.details,
        finding.files,
        finding.recommendation,
    )


def _package_report(root: Path, strict: bool) -> tuple[dict[str, object], int]:
    guard_finding = mode_guard.package_mode_guard(root)
    if guard_finding is not None:
        findings = [
            Finding(
                guard_finding.rule_id,
                guard_finding.severity,
                guard_finding.title,
                guard_finding.details,
                guard_finding.files,
                guard_finding.recommendation,
            )
        ]
        return {
            "tool": "aso",
            "command": "lint",
            "mode": "package",
            "status": "failed",
            "root": str(root),
            "strict": strict,
            "findings": [finding.to_json(mode="package") for finding in findings],
            "summary": _summary(findings),
            "package": {
                "package_consistency": "FAIL",
                "generated_roots": {},
                "readmes": {},
                "git_tracked_generated_files": [],
            },
        }, EXIT_FINDINGS

    inspection = package_checks.inspect_package(root)
    findings = [_package_finding(finding) for finding in inspection.findings]
    summary = _summary(findings)

    if any(finding.rule_id == "PACKAGE_IO_001" for finding in findings):
        exit_code = EXIT_IO_ERROR
        status = "io_error"
    else:
        failed = summary["errors"] > 0 or (strict and bool(findings))
        exit_code = EXIT_FINDINGS if failed else EXIT_OK
        status = "failed" if failed else ("warning" if findings else "passed")

    return {
        "tool": "aso",
        "command": "lint",
        "mode": "package",
        "status": status,
        "root": str(root),
        "strict": strict,
        "findings": [finding.to_json(mode="package") for finding in findings],
        "summary": summary,
        "package": {
            "package_consistency": package_checks.consistency(inspection.findings),
            "generated_roots": inspection.generated_roots,
            "readmes": inspection.readmes,
            "git_tracked_generated_files": inspection.git_tracked_generated_files,
        },
    }, exit_code


def _report(root: Path, strict: bool) -> tuple[dict[str, object], int]:
    files, io_findings, can_lint = _validate_root_and_required_files(root)
    findings = list(io_findings)
    exit_code = EXIT_OK

    if not can_lint:
        exit_code = EXIT_IO_ERROR
        status = "io_error"
    else:
        findings.extend(_all_lint_findings(root, files))
        summary = _summary(findings)
        failed = summary["errors"] > 0 or (strict and bool(findings))
        exit_code = EXIT_FINDINGS if failed else EXIT_OK
        status = "failed" if failed else ("warning" if findings else "passed")

    return {
        "tool": "aso",
        "command": "lint",
        "mode": "workspace",
        "status": status,
        "root": str(root),
        "strict": strict,
        "findings": [finding.to_json(mode="workspace") for finding in findings],
        "summary": _summary(findings),
    }, exit_code


def _print_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    if not isinstance(summary, dict):
        raise TypeError("internal lint report summary must be a dictionary")

    print(f"ASO lint: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    if "mode" in report:
        print(f"Mode: {report['mode']}")
    print(f"Strict: {report['strict']}")
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Info: {summary['info']}")
    print(f"Findings: {len(report['findings'])}")
    for finding in report["findings"]:
        if not isinstance(finding, dict):
            continue
        print(f"- {finding['severity']} {finding['rule_id']}: {finding['title']}")
        recommendation = str(finding.get("recommendation", "")).strip()
        if recommendation:
            print(f"  Recommendation: {recommendation}")


def _write_json(path_text: str, report: dict[str, object]) -> bool:
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso lint: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso lint: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def run(args: argparse.Namespace) -> int:
    """Run the lint command."""
    if args.mode == "package":
        report, exit_code = _package_report(args.root, args.strict)
    else:
        report, exit_code = _report(args.root, args.strict)
    _print_text(report)
    if args.json_out and not _write_json(args.json_out, report):
        return EXIT_IO_ERROR
    return exit_code
