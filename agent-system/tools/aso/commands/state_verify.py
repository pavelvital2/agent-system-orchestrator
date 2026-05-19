"""Read-only workspace state sidecar verifier."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3

SCHEMA_VERSION = "2.0.0"
ENVELOPE_FIELDS = (
    "schema_version",
    "sidecar_type",
    "markdown_source",
    "state_revision",
    "updated_at",
    "updated_by",
    "content",
)
ENVELOPE_FIELD_SET = set(ENVELOPE_FIELDS)
RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}


@dataclass(frozen=True)
class SidecarSpec:
    sidecar_type: str
    filename: str
    markdown_source: str
    required_fields: tuple[str, ...]
    list_item_fields: dict[str, tuple[str, ...]]


SIDECARS: tuple[SidecarSpec, ...] = (
    SidecarSpec(
        "PROJECT_STATE",
        "PROJECT_STATE.json",
        "project-runtime/PROJECT_STATE.md",
        (
            "project_slug",
            "workspace_type",
            "current_phase",
            "project_status",
            "active_doc_root",
            "package_version",
            "governance_ruleset_version",
            "runtime_schema_version",
            "workspace_identity_ref",
            "repository_lock_ref",
            "expected_git_remote",
            "actual_git_remote",
            "expected_branch",
            "actual_branch",
            "push_allowed",
            "identity_validation_status",
            "identity_validation_error",
            "repository_lock_status",
            "checkpoint_eligibility",
            "checkpoint_blocked_by",
            "active_blockers",
            "active_branches",
        ),
        {
            "active_branches": (
                "branch_id",
                "status",
                "current_task",
                "current_agent_role",
                "dependencies",
                "blocked_by",
            ),
        },
    ),
    SidecarSpec(
        "CURRENT_GATE",
        "CURRENT_GATE.json",
        "project-runtime/CURRENT_GATE.md",
        (
            "gate_id",
            "gate_type",
            "status",
            "owner_role",
            "task_id",
            "task_packet",
            "action_semantic",
            "workspace_identity_status",
            "repository_lock_status",
            "checkpoint_eligibility",
            "checkpoint_blocked_by",
            "evidence_refs",
        ),
        {},
    ),
    SidecarSpec(
        "NEXT_ACTION",
        "NEXT_ACTION.json",
        "project-runtime/NEXT_ACTION.md",
        (
            "action_id",
            "action_type",
            "target_role",
            "task_id",
            "task_packet",
            "dependency_status",
            "action_semantic",
            "workspace_identity_required",
            "repository_lock_required",
            "checkpoint_policy",
            "requester_return_context",
            "blocked_by",
            "summary",
        ),
        {},
    ),
    SidecarSpec(
        "TASK_REGISTRY",
        "TASK_REGISTRY.json",
        "project-runtime/TASK_REGISTRY.md",
        ("registry_revision", "tasks"),
        {
            "tasks": (
                "task_id",
                "task_packet",
                "role",
                "status",
                "audit_required",
                "checkpoint_required",
                "requester_return_metadata",
                "blocked_by",
                "result_refs",
                "audit_refs",
            ),
        },
    ),
    SidecarSpec(
        "ACCEPTED_ARTIFACTS",
        "ACCEPTED_ARTIFACTS.json",
        "project-runtime/ACCEPTED_ARTIFACTS.md",
        ("artifacts",),
        {
            "artifacts": (
                "artifact_id",
                "path",
                "task_id",
                "accepted_result_ref",
                "audit_ref",
                "status",
                "commit_hash",
                "notes",
            ),
        },
    ),
    SidecarSpec(
        "WORKSPACE_IDENTITY",
        "WORKSPACE_IDENTITY.json",
        "project-runtime/WORKSPACE_IDENTITY.md",
        (
            "workspace_id",
            "project_slug",
            "workspace_type",
            "expected_git_remote",
            "actual_git_remote",
            "expected_branch",
            "actual_branch",
            "identity_validation_status",
            "repository_lock_status",
            "push_allowed",
            "validated_at",
            "validation_errors",
        ),
        {},
    ),
)

STATUS_FIELDS = {
    ("PROJECT_STATE", "project_status"): {"active", "blocked", "paused", "completed", "archived", "initialized"},
    ("PROJECT_STATE", "identity_validation_status"): {"passed", "pending", "failed", "blocked", "not_required"},
    ("PROJECT_STATE", "repository_lock_status"): {"passed", "accepted", "pending", "failed", "blocked", "not_required"},
    ("PROJECT_STATE", "checkpoint_eligibility"): {"eligible", "not_required", "blocked", "pending", "ineligible"},
    ("PROJECT_STATE", "active_branches[].status"): {"active", "blocked", "complete", "completed", "paused", "pending"},
    ("CURRENT_GATE", "status"): {"active", "open", "blocked", "passed", "failed", "complete", "completed", "pending"},
    ("CURRENT_GATE", "action_semantic"): {"dispatch", "checkpoint", "audit", "return", "none"},
    ("CURRENT_GATE", "workspace_identity_status"): {"passed", "pending", "failed", "blocked", "not_required"},
    ("CURRENT_GATE", "repository_lock_status"): {"passed", "accepted", "pending", "failed", "blocked", "not_required"},
    ("CURRENT_GATE", "checkpoint_eligibility"): {"eligible", "not_required", "blocked", "pending", "ineligible"},
    ("NEXT_ACTION", "action_type"): {"create_agent", "run_audit", "checkpoint", "return_to_requester", "none", "manual"},
    ("NEXT_ACTION", "dependency_status"): {"ready", "blocked", "pending", "waiting", "not_required", "failed"},
    ("NEXT_ACTION", "action_semantic"): {"dispatch", "checkpoint", "audit", "return", "none"},
    ("NEXT_ACTION", "checkpoint_policy"): {"not_required", "required", "forbidden", "after_audit_pass", "audit_pass_required"},
    ("TASK_REGISTRY", "tasks[].status"): {
        "active",
        "ready",
        "pending",
        "in_progress",
        "audit_pending",
        "audit_passed",
        "completed",
        "blocked",
        "failed",
        "cancelled",
    },
    ("ACCEPTED_ARTIFACTS", "artifacts[].status"): {"accepted", "pending", "rejected", "superseded"},
    ("WORKSPACE_IDENTITY", "identity_validation_status"): {"passed", "pending", "failed", "blocked", "not_required"},
    ("WORKSPACE_IDENTITY", "repository_lock_status"): {"passed", "accepted", "pending", "failed", "blocked", "not_required"},
}


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


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _finding(
    rule_id: str,
    title: str,
    details: str,
    path: str,
    field: str,
    recommendation: str,
    *,
    severity: str = "error",
) -> Finding:
    return Finding(rule_id, severity, title, details, path, field, recommendation)


def _summary(findings: Iterable[Finding]) -> dict[str, int]:
    finding_list = list(findings)
    return {
        "errors": sum(1 for finding in finding_list if finding.severity == "error"),
        "warnings": sum(1 for finding in finding_list if finding.severity == "warning"),
        "info": sum(1 for finding in finding_list if finding.severity == "info"),
    }


def _status(summary: dict[str, int], strict: bool, *, io_error: bool = False) -> tuple[str, int]:
    if io_error:
        return "io_error", EXIT_IO_ERROR
    if summary["errors"] > 0 or (strict and summary["warnings"] > 0):
        return "failed", EXIT_FINDINGS
    if summary["warnings"] > 0:
        return "warning", EXIT_OK
    return "passed", EXIT_OK


def _is_none(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in NONE_VALUES)


def _value_to_text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, sort_keys=True)


def _parse_markdown_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return fields
    for line in lines:
        match = re.match(r"^([A-Z0-9_]+):\s*(.*?)\s*$", line)
        if match:
            fields[match.group(1)] = match.group(2)
    return fields


def _validate_content_type(spec: SidecarSpec, content: dict[str, object], relpath: str) -> list[Finding]:
    findings: list[Finding] = []
    for field in spec.required_fields:
        if field not in content:
            continue
        value = content[field]
        if field in spec.list_item_fields or field in {"checkpoint_blocked_by", "active_blockers", "evidence_refs", "blocked_by", "validation_errors"}:
            if not isinstance(value, list):
                findings.append(
                    _finding(
                        "SIDECAR_TYPE_INVALID",
                        "Sidecar field type is invalid",
                        f"{spec.sidecar_type}.content.{field} must be a list.",
                        relpath,
                        f"content.{field}",
                        "Use the documented JSON type for every governed field.",
                    )
                )
        elif field in {
            "push_allowed",
            "workspace_identity_required",
            "repository_lock_required",
            "audit_required",
            "checkpoint_required",
        }:
            if not isinstance(value, bool):
                findings.append(
                    _finding(
                        "SIDECAR_TYPE_INVALID",
                        "Sidecar field type is invalid",
                        f"{spec.sidecar_type}.content.{field} must be a boolean.",
                        relpath,
                        f"content.{field}",
                        "Use true or false for boolean governed fields.",
                    )
                )
        elif field in {"registry_revision"}:
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                findings.append(
                    _finding(
                        "SIDECAR_TYPE_INVALID",
                        "Sidecar field type is invalid",
                        f"{spec.sidecar_type}.content.{field} must be a positive integer.",
                        relpath,
                        f"content.{field}",
                        "Use a positive integer for revision fields.",
                    )
                )
        elif field in {"requester_return_context", "requester_return_metadata"}:
            if not isinstance(value, dict):
                findings.append(
                    _finding(
                        "SIDECAR_TYPE_INVALID",
                        "Sidecar field type is invalid",
                        f"{spec.sidecar_type}.content.{field} must be an object.",
                        relpath,
                        f"content.{field}",
                        "Use the documented JSON type for every governed field.",
                    )
                )
        elif not isinstance(value, str):
            findings.append(
                _finding(
                    "SIDECAR_TYPE_INVALID",
                    "Sidecar field type is invalid",
                    f"{spec.sidecar_type}.content.{field} must be a string.",
                    relpath,
                    f"content.{field}",
                    "Use the documented JSON type for every governed field.",
                )
            )
    return findings


def _validate_list_items(spec: SidecarSpec, content: dict[str, object], relpath: str) -> list[Finding]:
    findings: list[Finding] = []
    for field, item_fields in spec.list_item_fields.items():
        value = content.get(field)
        if not isinstance(value, list):
            continue
        for index, item in enumerate(value):
            item_path = f"content.{field}[{index}]"
            if not isinstance(item, dict):
                findings.append(
                    _finding(
                        "SIDECAR_TYPE_INVALID",
                        "Sidecar list entry type is invalid",
                        f"{spec.sidecar_type}.{item_path} must be an object.",
                        relpath,
                        item_path,
                        "Use objects for governed list entries.",
                    )
                )
                continue
            for required in item_fields:
                if required not in item:
                    findings.append(
                        _finding(
                            "SIDECAR_REQUIRED_FIELD_MISSING",
                            "Required sidecar field is missing",
                            f"{spec.sidecar_type}.{item_path}.{required} is missing.",
                            relpath,
                            f"{item_path}.{required}",
                            "Populate every required governed field from the sidecar contract.",
                        )
                    )
            unknown = sorted(set(item) - set(item_fields))
            for extra in unknown:
                findings.append(
                    _finding(
                        "SIDECAR_UNKNOWN_GOVERNED_FIELD",
                        "Sidecar has an unknown governed field",
                        f"{spec.sidecar_type}.{item_path}.{extra} is not part of the documented contract.",
                        relpath,
                        f"{item_path}.{extra}",
                        "Remove unknown governed fields or update the contract in a separate bounded task.",
                    )
                )
    return findings


def _validate_required_fields(spec: SidecarSpec, content: object, relpath: str) -> list[Finding]:
    if not isinstance(content, dict):
        return [
            _finding(
                "SIDECAR_TYPE_INVALID",
                "Sidecar content type is invalid",
                f"{spec.sidecar_type}.content must be an object.",
                relpath,
                "content",
                "Use an object for sidecar content.",
            )
        ]

    findings: list[Finding] = []
    for field in spec.required_fields:
        if field not in content:
            findings.append(
                _finding(
                    "SIDECAR_REQUIRED_FIELD_MISSING",
                    "Required sidecar field is missing",
                    f"{spec.sidecar_type}.content.{field} is missing.",
                    relpath,
                    f"content.{field}",
                    "Populate every required governed field from the sidecar contract.",
                )
            )
            continue
        value = content[field]
        if isinstance(value, str) and field not in {"identity_validation_error", "blocked_by"} and not value.strip():
            findings.append(
                _finding(
                    "SIDECAR_REQUIRED_FIELD_EMPTY",
                    "Required sidecar field is empty",
                    f"{spec.sidecar_type}.content.{field} must not be empty.",
                    relpath,
                    f"content.{field}",
                    "Use an explicit value or NONE only where the sidecar contract permits it.",
                )
            )

    unknown = sorted(set(content) - set(spec.required_fields))
    for extra in unknown:
        findings.append(
            _finding(
                "SIDECAR_UNKNOWN_GOVERNED_FIELD",
                "Sidecar has an unknown governed field",
                f"{spec.sidecar_type}.content.{extra} is not part of the documented contract.",
                relpath,
                f"content.{extra}",
                "Remove unknown governed fields or update the contract in a separate bounded task.",
            )
        )

    findings.extend(_validate_content_type(spec, content, relpath))
    findings.extend(_validate_list_items(spec, content, relpath))
    return findings


def _validate_status_values(spec: SidecarSpec, content: dict[str, object], relpath: str) -> list[Finding]:
    findings: list[Finding] = []
    for (sidecar_type, field), allowed in STATUS_FIELDS.items():
        if sidecar_type != spec.sidecar_type:
            continue
        if "[]." in field:
            list_name, item_field = field.split("[].", 1)
            entries = content.get(list_name)
            if not isinstance(entries, list):
                continue
            for index, item in enumerate(entries):
                if not isinstance(item, dict) or item_field not in item:
                    continue
                raw = item[item_field]
                if not isinstance(raw, str) or raw not in allowed:
                    findings.append(
                        _finding(
                            "SIDECAR_STATUS_INVALID",
                            "Sidecar status value is invalid",
                            f"{spec.sidecar_type}.content.{list_name}[{index}].{item_field}={raw!r} is not allowed.",
                            relpath,
                            f"content.{list_name}[{index}].{item_field}",
                            f"Use one of: {', '.join(sorted(allowed))}.",
                        )
                    )
            continue

        raw = content.get(field)
        if raw is None:
            continue
        if not isinstance(raw, str) or raw not in allowed:
            findings.append(
                _finding(
                    "SIDECAR_STATUS_INVALID",
                    "Sidecar status value is invalid",
                    f"{spec.sidecar_type}.content.{field}={raw!r} is not allowed.",
                    relpath,
                    f"content.{field}",
                    f"Use one of: {', '.join(sorted(allowed))}.",
                )
            )
    return findings


def _validate_markdown_parity(root: Path, spec: SidecarSpec, content: dict[str, object], relpath: str) -> list[Finding]:
    markdown_path = root / spec.markdown_source
    if not markdown_path.is_file():
        return [
            _finding(
                "SIDECAR_MARKDOWN_COMPATIBILITY_VIEW_MISSING",
                "Markdown compatibility view is missing",
                f"{spec.markdown_source} is required while Stage 2 keeps Markdown compatibility views.",
                spec.markdown_source,
                "",
                "Restore the matching project-runtime Markdown file.",
            )
        ]

    markdown_fields = _parse_markdown_fields(markdown_path)
    findings: list[Finding] = []
    for field, value in content.items():
        markdown_key = field.upper()
        if markdown_key not in markdown_fields or isinstance(value, (list, dict)):
            continue
        markdown_value = markdown_fields[markdown_key].strip()
        json_value = _value_to_text(value)
        if markdown_value != json_value:
            findings.append(
                _finding(
                    "SIDECAR_MARKDOWN_DRIFT",
                    "Sidecar differs from Markdown compatibility view",
                    (
                        f"{spec.sidecar_type}.{field}={json_value!r}; "
                        f"{spec.markdown_source} {markdown_key}={markdown_value!r}."
                    ),
                    relpath,
                    f"content.{field}",
                    "Regenerate or correct the sidecar and Markdown view through an orchestrator-owned migration.",
                )
            )
    return findings


def _validate_sidecar(root: Path, spec: SidecarSpec) -> tuple[dict[str, object] | None, list[Finding]]:
    path = root / "project-runtime" / "state" / spec.filename
    relpath = _rel(root, path)
    if not path.is_file():
        markdown_path = root / spec.markdown_source
        if markdown_path.is_file():
            return None, [
                _finding(
                    "SIDECAR_MISSING_MARKDOWN_FALLBACK_USED",
                    "Required sidecar is missing; Markdown fallback is present",
                    f"{relpath} is absent and {spec.markdown_source} is available as the Stage 2 fallback.",
                    relpath,
                    "",
                    "Create the sidecar through an orchestrator-owned migration before relying on sidecar verification.",
                    severity="warning",
                )
            ]
        return None, [
            _finding(
                "SIDECAR_REQUIRED_SIDECAR_MISSING",
                "Required state sidecar is missing",
                f"{relpath} is required for state sidecar verification.",
                relpath,
                "",
                "Restore the required state sidecar file.",
            )
        ]

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [
            _finding(
                "SIDECAR_JSON_PARSE_ERROR",
                "Sidecar is unreadable",
                f"{relpath}: {exc}",
                relpath,
                "",
                "Pass a readable workspace state sidecar.",
            )
        ]

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return None, [
            _finding(
                "SIDECAR_JSON_PARSE_ERROR",
                "Sidecar JSON is invalid",
                f"{relpath}: {exc.msg} at line {exc.lineno}, column {exc.colno}.",
                relpath,
                "",
                "Fix the JSON syntax before validation.",
            )
        ]

    if not isinstance(payload, dict):
        return None, [
            _finding(
                "SIDECAR_TOP_LEVEL_NOT_OBJECT",
                "Sidecar root must be a JSON object",
                f"{relpath} does not contain a JSON object at the top level.",
                relpath,
                "",
                "Use the documented sidecar object envelope.",
            )
        ]

    findings: list[Finding] = []
    for field in ENVELOPE_FIELDS:
        if field not in payload:
            findings.append(
                _finding(
                    "SIDECAR_REQUIRED_FIELD_MISSING",
                    "Required sidecar envelope field is missing",
                    f"{relpath}.{field} is missing.",
                    relpath,
                    field,
                    "Populate every required sidecar envelope field.",
                )
            )
    for extra in sorted(set(payload) - ENVELOPE_FIELD_SET):
        findings.append(
            _finding(
                "SIDECAR_UNKNOWN_GOVERNED_FIELD",
                "Sidecar has an unknown top-level field",
                f"{relpath}.{extra} is not part of the documented envelope.",
                relpath,
                extra,
                "Remove unknown top-level sidecar fields.",
            )
        )

    if payload.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                "SIDECAR_SCHEMA_VERSION_MISSING_OR_INVALID",
                "Sidecar schema version is invalid",
                f"{relpath}.schema_version must be {SCHEMA_VERSION!r}.",
                relpath,
                "schema_version",
                "Use the stable Stage 2 sidecar schema version.",
            )
        )
    if payload.get("sidecar_type") != spec.sidecar_type:
        findings.append(
            _finding(
                "SIDECAR_TYPE_MISMATCH",
                "Sidecar type does not match file",
                f"{relpath}.sidecar_type must be {spec.sidecar_type!r}.",
                relpath,
                "sidecar_type",
                "Keep sidecar_type aligned with the sidecar filename.",
            )
        )
    if payload.get("markdown_source") != spec.markdown_source:
        findings.append(
            _finding(
                "SIDECAR_MARKDOWN_SOURCE_MISMATCH",
                "Sidecar Markdown source does not match file",
                f"{relpath}.markdown_source must be {spec.markdown_source!r}.",
                relpath,
                "markdown_source",
                "Point markdown_source at the matching runtime Markdown compatibility view.",
            )
        )
    state_revision = payload.get("state_revision")
    if not isinstance(state_revision, int) or isinstance(state_revision, bool) or state_revision < 1:
        findings.append(
            _finding(
                "SIDECAR_STATE_REVISION_INVALID",
                "Sidecar state revision is invalid",
                f"{relpath}.state_revision must be a positive integer.",
                relpath,
                "state_revision",
                "Use a positive integer state revision.",
            )
        )
    updated_at = payload.get("updated_at")
    if not isinstance(updated_at, str) or not RFC3339_UTC_RE.match(updated_at):
        findings.append(
            _finding(
                "SIDECAR_TIMESTAMP_INVALID",
                "Sidecar updated_at timestamp is invalid",
                f"{relpath}.updated_at must be an RFC 3339 UTC timestamp ending in Z.",
                relpath,
                "updated_at",
                "Use a timestamp such as 2026-01-01T00:00:00Z.",
            )
        )
    updated_by = payload.get("updated_by")
    if not isinstance(updated_by, str) or not updated_by.strip():
        findings.append(
            _finding(
                "SIDECAR_REQUIRED_FIELD_EMPTY",
                "Sidecar updated_by is empty",
                f"{relpath}.updated_by must identify the actor that produced the sidecar.",
                relpath,
                "updated_by",
                "Record the producing actor.",
            )
        )
    elif updated_by != "orchestrator":
        findings.append(
            _finding(
                "SIDECAR_UPDATED_BY_NON_ORCHESTRATOR",
                "Sidecar updated_by is not orchestrator",
                f"{relpath}.updated_by={updated_by!r}.",
                relpath,
                "updated_by",
                "Use orchestrator-authored sidecars for governed workspace state.",
                severity="warning",
            )
        )

    content = payload.get("content")
    findings.extend(_validate_required_fields(spec, content, relpath))
    if isinstance(content, dict):
        findings.extend(_validate_status_values(spec, content, relpath))
        findings.extend(_validate_markdown_parity(root, spec, content, relpath))
    return payload, findings


def _content(sidecars: dict[str, dict[str, object]], sidecar_type: str) -> dict[str, object]:
    payload = sidecars.get(sidecar_type, {})
    content = payload.get("content")
    return content if isinstance(content, dict) else {}


def _task_registry(sidecars: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    content = _content(sidecars, "TASK_REGISTRY")
    tasks = content.get("tasks")
    registry: dict[str, dict[str, object]] = {}
    if isinstance(tasks, list):
        for item in tasks:
            if isinstance(item, dict) and isinstance(item.get("task_id"), str):
                registry[item["task_id"]] = item
    return registry


def _reference_findings(sidecars: dict[str, dict[str, object]]) -> list[Finding]:
    registry = _task_registry(sidecars)
    if not registry:
        return []

    refs: list[tuple[str, str, str]] = []
    project_state = _content(sidecars, "PROJECT_STATE")
    branches = project_state.get("active_branches")
    if isinstance(branches, list):
        for index, branch in enumerate(branches):
            if isinstance(branch, dict):
                refs.append(("PROJECT_STATE.json", f"content.active_branches[{index}].current_task", str(branch.get("current_task", ""))))

    current_gate = _content(sidecars, "CURRENT_GATE")
    refs.append(("CURRENT_GATE.json", "content.task_id", str(current_gate.get("task_id", ""))))
    next_action = _content(sidecars, "NEXT_ACTION")
    refs.append(("NEXT_ACTION.json", "content.task_id", str(next_action.get("task_id", ""))))
    accepted = _content(sidecars, "ACCEPTED_ARTIFACTS")
    artifacts = accepted.get("artifacts")
    if isinstance(artifacts, list):
        for index, artifact in enumerate(artifacts):
            if isinstance(artifact, dict):
                refs.append(("ACCEPTED_ARTIFACTS.json", f"content.artifacts[{index}].task_id", str(artifact.get("task_id", ""))))

    findings: list[Finding] = []
    for filename, field, task_id in refs:
        if _is_none(task_id) or task_id in registry:
            continue
        path = f"project-runtime/state/{filename}"
        findings.append(
            _finding(
                "SIDECAR_TASK_REFERENCE_UNKNOWN",
                "Sidecar references a task not in TASK_REGISTRY",
                f"{path}.{field}={task_id!r} is not present in TASK_REGISTRY.tasks.",
                path,
                field,
                "Add the task to TASK_REGISTRY or remove the stale active task reference.",
            )
        )
    return findings


def _truthy_refs(value: object) -> bool:
    if not isinstance(value, list):
        return False
    return any(isinstance(item, str) and item.strip() and item.strip() not in NONE_VALUES for item in value)


def _checkpoint_findings(sidecars: dict[str, dict[str, object]]) -> list[Finding]:
    next_action = _content(sidecars, "NEXT_ACTION")
    action_type = next_action.get("action_type")
    action_semantic = next_action.get("action_semantic")
    checkpoint_policy = next_action.get("checkpoint_policy")
    checkpoint_attempt = (
        action_type == "checkpoint"
        or action_semantic == "checkpoint"
        or checkpoint_policy in {"required", "after_audit_pass", "audit_pass_required"}
    )
    if not checkpoint_attempt:
        return []

    task_id = next_action.get("task_id")
    if not isinstance(task_id, str) or _is_none(task_id):
        return []
    task = _task_registry(sidecars).get(task_id)
    if not task:
        return []

    audit_required = task.get("audit_required")
    status = task.get("status")
    has_audit_ref = _truthy_refs(task.get("audit_refs"))
    if audit_required is False or status in {"audit_passed", "completed"} or has_audit_ref:
        return []

    return [
        _finding(
            "SIDECAR_CHECKPOINT_POLICY_INVALID",
            "NEXT_ACTION checkpoint attempt lacks audit-pass evidence",
            (
                "NEXT_ACTION requests a checkpoint for an audit-required task, "
                f"but TASK_REGISTRY task {task_id} has no audit-pass status or audit_refs evidence."
            ),
            "project-runtime/state/NEXT_ACTION.json",
            "content.checkpoint_policy",
            "Record audit-pass evidence before a checkpoint action, or mark checkpoint_policy not_required/forbidden.",
        )
    ]


def _report(root: Path, strict: bool) -> tuple[dict[str, object], int]:
    findings: list[Finding] = []
    loaded_sidecars: dict[str, dict[str, object]] = {}
    present: list[str] = []
    missing: list[str] = []

    if not root.exists() or not root.is_dir():
        finding = _finding(
            "SIDECAR_WORKSPACE_ROOT_UNREADABLE",
            "Workspace root is not readable",
            f"--root does not point to a readable directory: {root}",
            "",
            "root",
            "Pass --root pointing at an initialized workspace.",
        )
        summary = _summary([finding])
        status, exit_code = _status(summary, strict, io_error=True)
        return _build_report(root, strict, status, summary, [finding], {}, [], []), exit_code

    for spec in SIDECARS:
        payload, sidecar_findings = _validate_sidecar(root, spec)
        findings.extend(sidecar_findings)
        if payload is None:
            missing.append(spec.sidecar_type)
        else:
            present.append(spec.sidecar_type)
            loaded_sidecars[spec.sidecar_type] = payload

    findings.extend(_reference_findings(loaded_sidecars))
    findings.extend(_checkpoint_findings(loaded_sidecars))
    findings = sorted(findings, key=lambda item: (item.severity != "error", item.rule_id, item.path, item.field, item.details))
    summary = _summary(findings)
    status, exit_code = _status(summary, strict)
    return _build_report(root, strict, status, summary, findings, loaded_sidecars, present, missing), exit_code


def _build_report(
    root: Path,
    strict: bool,
    status: str,
    summary: dict[str, int],
    findings: list[Finding],
    sidecars: dict[str, dict[str, object]],
    present: list[str],
    missing: list[str],
) -> dict[str, object]:
    return {
        "tool": "aso",
        "command": "state verify",
        "mode": "workspace",
        "status": status,
        "root": str(root),
        "strict": strict,
        "summary": summary,
        "findings": [finding.to_json() for finding in findings],
        "state": {
            "sidecars_expected": [spec.sidecar_type for spec in SIDECARS],
            "sidecars_present": sorted(present),
            "sidecars_missing": sorted(missing),
            "task_registry_count": len(_task_registry(sidecars)),
        },
        "read_only": True,
    }


def _print_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    if not isinstance(summary, dict):
        raise TypeError("internal state verify report summary must be a dictionary")
    state = report["state"]
    if not isinstance(state, dict):
        raise TypeError("internal state verify report state must be a dictionary")

    print(f"ASO state verify: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    print(f"Mode: {report['mode']}")
    print(f"Strict: {report['strict']}")
    print(f"Sidecars present: {len(state['sidecars_present'])}/{len(state['sidecars_expected'])}")
    print(f"Task registry entries: {state['task_registry_count']}")
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Info: {summary['info']}")
    print(f"Findings: {len(report['findings'])}")
    for finding in report["findings"]:
        if not isinstance(finding, dict):
            continue
        print(f"- {finding['severity']} {finding['rule_id']}: {finding['title']}")


def _write_json(path_text: str, report: dict[str, object]) -> bool:
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso state verify: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso state verify: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def run(args: argparse.Namespace) -> int:
    """Run the state verify command."""

    root = Path(args.root).expanduser()
    report, exit_code = _report(root, args.strict)
    _print_text(report)
    if args.json_out and not _write_json(args.json_out, report):
        return EXIT_IO_ERROR
    return exit_code
