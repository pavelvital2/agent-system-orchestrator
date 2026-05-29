"""Read-only workspace state sidecar verifier."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .. import runtime_schema_contracts
from .. import result_parser
from .. import transition_engine
from . import repair_hints


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3

LEGACY_SCHEMA_VERSION = "2.0.0"
CURRENT_SCHEMA_VERSION = runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION
LEGACY_ENVELOPE_FIELDS = (
    "schema_version",
    "sidecar_type",
    "markdown_source",
    "state_revision",
    "updated_at",
    "updated_by",
    "content",
)
CURRENT_ENVELOPE_FIELDS = runtime_schema_contracts.REQUIRED_ENVELOPE_FIELDS
CURRENT_OPTIONAL_ENVELOPE_FIELDS = runtime_schema_contracts.OPTIONAL_ENVELOPE_FIELDS
LEGACY_ENVELOPE_FIELD_SET = set(LEGACY_ENVELOPE_FIELDS)
CURRENT_ENVELOPE_FIELD_SET = set(CURRENT_ENVELOPE_FIELDS) | set(CURRENT_OPTIONAL_ENVELOPE_FIELDS)
RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
RESULT_PACKAGE_REF_RE = re.compile(r"^project-runtime/artifacts/accepted/RESULT_PACKAGE_[A-Za-z0-9_:-]+\.json$")
AUDIT_RESULT_PACKAGE_REF_RE = re.compile(r"^project-runtime/artifacts/accepted/AUDIT_RESULT_PACKAGE_[A-Za-z0-9_:-]+\.json$")
WORKER_RESULT_REF_RE = re.compile(r"^project-runtime/results/worker/RESULT_[A-Za-z0-9_:-]+_ATTEMPT_[0-9]+\.md$")
AUDIT_RESULT_REF_RE = re.compile(r"^project-runtime/results/audit/AUDIT_RESULT_[A-Za-z0-9_:-]+_ATTEMPT_[0-9]+\.md$")
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}
IANA_TIMEZONE_RE = re.compile(r"^[A-Za-z_]+/[A-Za-z0-9_.+-]+(?:/[A-Za-z0-9_.+-]+)?$")
IANA_SINGLETON_TIMEZONES = {
    "CET",
    "CST6CDT",
    "EET",
    "EST",
    "EST5EDT",
    "Factory",
    "GMT",
    "HST",
    "MET",
    "MST",
    "MST7MDT",
    "UTC",
    "WET",
}
PROFILE_ROLES = {
    "requirements_analyst",
    "solution_architect",
    "designer",
    "developer",
    "auditor",
    "tester",
    "technical_writer",
    "devops_setup_engineer",
    "release_manager",
}
CONTROL_OR_TARGET_ROLES = PROFILE_ROLES | {"orchestrator", "project_owner", "none"}
OWNER_ROLES = PROFILE_ROLES | {"orchestrator", "project_owner"}
ACTION_SEMANTICS = {"normal", "wait_for_owner", "pause", "stop_terminal", "completed_state_transition"}
BLOCKER_TYPES = {"owner_decision", "pause", "audit_fail", "gap", "runtime", "dependency", "governance", "other"}


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
            "project_name",
            "project_slug",
            "project_root",
            "tz_path",
            "active_doc_root",
            "package_version",
            "governance_ruleset_version",
            "runtime_schema_version",
            "workspace_type",
            "workspace_identity_ref",
            "repository_lock_ref",
            "project_root_expected",
            "git_toplevel_actual",
            "expected_remote",
            "actual_remote",
            "expected_git_remote",
            "actual_git_remote",
            "expected_branch",
            "actual_branch",
            "push_allowed",
            "identity_validation_status",
            "identity_validation_error",
            "identity_validation_evidence",
            "repository_lock_status",
            "baseline_tracking_status",
            "project_input_tracking_policy",
            "checkpoint_eligibility",
            "audit_status",
            "checkpoint_eligibility_status",
            "checkpoint_preflight_status",
            "checkpoint_preflight_ref",
            "checkpoint_receipt_ref",
            "commit_status",
            "last_commit_hash",
            "last_commit_branch",
            "push_status",
            "last_push_remote",
            "last_push_branch",
            "last_push_target_status",
            "project_checkpoint_status",
            "checkpoint_blocked_by",
            "last_checkpoint_failure_reason",
            "current_phase",
            "project_status",
            "action_semantic",
            "semantic_reason",
            "active_branches",
            "completed_milestones",
            "active_risks",
            "active_blockers",
            "active_gaps",
            "last_accepted_result",
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
            "active_blockers": (
                "blocker_id",
                "blocker_type",
                "status",
                "blocks",
                "blocked_by",
                "resolution_path",
            ),
        },
    ),
    SidecarSpec(
        "CURRENT_GATE",
        "CURRENT_GATE.json",
        "project-runtime/CURRENT_GATE.md",
        (
            "gate_id",
            "gate_name",
            "gate_type",
            "status",
            "owner_role",
            "task_id",
            "task_packet",
            "action_semantic",
            "workspace_identity_status",
            "repository_lock_status",
            "baseline_tracking_status",
            "checkpoint_eligibility",
            "checkpoint_eligibility_status",
            "project_checkpoint_status",
            "entry_criteria",
            "exit_criteria",
            "required_next_role",
            "gate_evidence",
            "blocking_status",
            "notes",
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
            "blocked_by",
            "action_semantic",
            "workspace_identity_required",
            "repository_lock_required",
            "checkpoint_policy",
            "checkpoint_preflight_required",
            "checkpoint_receipt_required",
            "checkpoint_receipt_ref",
            "requester_return_context",
            "blocking_or_resume_context",
            "required_universal_docs",
            "required_project_docs",
            "expected_result",
            "instruction_for_orchestrator",
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
                "task_title",
                "task_type",
                "task_kind",
                "owner_role",
                "status",
                "task_packet",
                "dependencies",
                "requested_by_role",
                "requested_by_task",
                "return_to_requester_after_audit_pass",
                "return_to_role_after_audit_pass",
                "return_task_after_audit_pass",
                "research_question_id",
                "result_refs",
                "audit_refs",
                "correction_links",
                "commit_hash",
                "branch",
                "push_status",
                "accepted_files",
                "checkpoint_ref",
                "created_at",
                "updated_at",
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
                "artifact_type",
                "artifact_ref",
                "status",
                "source_task",
                "source_result_ref",
                "audit_ref",
                "supersedes",
                "superseded_by",
                "commit_hash",
                "branch",
                "push_status",
                "checkpoint_ref",
                "accepted_at",
                "updated_at",
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

CURRENT_P2_EXTRA_SIDECARS: tuple[SidecarSpec, ...] = (
    SidecarSpec(
        "SCHEMA_MANIFEST",
        "SCHEMA_MANIFEST.json",
        "project-runtime/SCHEMA_MANIFEST.md",
        (
            "state_root",
            "runtime_schema_version",
            "package_version",
            "created_by_profile",
            "sidecars",
        ),
        {},
    ),
)
SIDECAR_BY_TYPE = {spec.sidecar_type: spec for spec in (*SIDECARS, *CURRENT_P2_EXTRA_SIDECARS)}

ENUM_FIELDS = {
    ("PROJECT_STATE", "workspace_type"): {"package_repo", "project_workspace", "implementation_repo", "test_fixture"},
    ("PROJECT_STATE", "identity_validation_status"): {"not_checked", "passed", "failed", "blocked"},
    ("PROJECT_STATE", "identity_validation_error"): {
        "NONE",
        "repository_identity_mismatch",
        "repository_branch_mismatch",
        "workspace_identity_leakage",
        "unapproved_ssh_host_alias",
        "missing_identity_manifest",
        "repository_lock_missing",
        "push_without_repository_lock",
    },
    ("PROJECT_STATE", "repository_lock_status"): {"absent", "draft", "accepted", "revoked", "blocked"},
    ("PROJECT_STATE", "baseline_tracking_status"): {"not_checked", "passed", "blocked", "owner_action_required"},
    ("PROJECT_STATE", "project_input_tracking_policy"): {"tracked", "owner-private/untracked", "not_set"},
    ("PROJECT_STATE", "checkpoint_eligibility"): {"blocked", "local_only", "push_allowed", "not_applicable"},
    ("PROJECT_STATE", "audit_status"): {"not_applicable", "pending", "passed", "failed", "blocked", "gap"},
    ("PROJECT_STATE", "checkpoint_eligibility_status"): {"not_checked", "eligible", "ineligible", "blocked"},
    ("PROJECT_STATE", "checkpoint_preflight_status"): {"not_run", "passed", "failed", "blocked"},
    ("PROJECT_STATE", "commit_status"): {"not_required", "not_attempted", "committed", "failed", "blocked"},
    ("PROJECT_STATE", "push_status"): {"not_required", "not_attempted", "pushed", "failed", "blocked"},
    ("PROJECT_STATE", "last_push_target_status"): {"not_checked", "matched", "mismatched", "blocked", "not_required"},
    ("PROJECT_STATE", "project_checkpoint_status"): {"not_required", "pending", "passed", "failed", "blocked"},
    ("PROJECT_STATE", "current_phase"): {
        "bootstrap",
        "requirements",
        "design",
        "design_audit",
        "implementation",
        "implementation_audit",
        "audit",
        "testing",
        "setup",
        "run",
        "launch",
        "documentation",
        "handover",
        "correction",
        "blocked",
        "finalization",
        "final_acceptance",
        "completed",
    },
    ("PROJECT_STATE", "project_status"): {"active", "blocked", "completed", "archived"},
    ("PROJECT_STATE", "action_semantic"): ACTION_SEMANTICS,
    ("PROJECT_STATE", "active_branches[].status"): {"active", "blocked", "completed", "archived"},
    ("PROJECT_STATE", "active_branches[].current_agent_role"): PROFILE_ROLES,
    ("PROJECT_STATE", "active_blockers[].blocker_type"): BLOCKER_TYPES,
    ("PROJECT_STATE", "active_blockers[].status"): {"active", "resolving"},
    ("PROJECT_STATE", "last_accepted_result.role"): PROFILE_ROLES,
    ("CURRENT_GATE", "gate_type"): {
        "bootstrap",
        "requirements",
        "design",
        "audit",
        "implementation",
        "testing",
        "setup",
        "run",
        "launch",
        "documentation",
        "handover",
        "correction",
        "finalization",
        "final_acceptance",
        "terminal",
    },
    ("CURRENT_GATE", "status"): {"open", "passed", "failed", "blocked", "skipped"},
    ("CURRENT_GATE", "owner_role"): OWNER_ROLES,
    ("CURRENT_GATE", "action_semantic"): ACTION_SEMANTICS,
    ("CURRENT_GATE", "workspace_identity_status"): {"not_checked", "passed", "failed", "blocked"},
    ("CURRENT_GATE", "repository_lock_status"): {"absent", "draft", "accepted", "revoked", "blocked", "not_required"},
    ("CURRENT_GATE", "baseline_tracking_status"): {"not_checked", "passed", "blocked", "owner_action_required"},
    ("CURRENT_GATE", "checkpoint_eligibility"): {"blocked", "local_only", "push_allowed", "not_applicable"},
    ("CURRENT_GATE", "checkpoint_eligibility_status"): {"not_checked", "eligible", "ineligible", "blocked"},
    ("CURRENT_GATE", "project_checkpoint_status"): {"not_required", "pending", "passed", "failed", "blocked"},
    ("CURRENT_GATE", "required_next_role"): CONTROL_OR_TARGET_ROLES,
    ("CURRENT_GATE", "blocking_status.blocker_type"): BLOCKER_TYPES,
    ("NEXT_ACTION", "action_type"): {"create_agent", "route_result", "update_state", "wait_for_owner", "correction", "finalize", "stop"},
    ("NEXT_ACTION", "target_role"): CONTROL_OR_TARGET_ROLES,
    ("NEXT_ACTION", "dependency_status"): {"ready", "blocked", "completed", "not_applicable"},
    ("NEXT_ACTION", "action_semantic"): ACTION_SEMANTICS,
    ("NEXT_ACTION", "checkpoint_policy"): {"forbidden", "local_only", "commit_and_push", "no_checkpoint"},
    ("NEXT_ACTION", "requester_return_context.requested_by_role"): PROFILE_ROLES | {"NONE"},
    ("NEXT_ACTION", "requester_return_context.return_to_role_after_audit_pass"): PROFILE_ROLES | {"none"},
    ("NEXT_ACTION", "blocking_or_resume_context.blocker_type"): BLOCKER_TYPES,
    ("TASK_REGISTRY", "tasks[].task_type"): PROFILE_ROLES,
    ("TASK_REGISTRY", "tasks[].task_kind"): {
        "bootstrap",
        "normal",
        "research_dependency",
        "design_continuation",
        "task_continuation",
        "correction",
        "audit",
        "testing",
        "setup",
        "launch",
        "handover",
    },
    ("TASK_REGISTRY", "tasks[].owner_role"): CONTROL_OR_TARGET_ROLES,
    ("TASK_REGISTRY", "tasks[].status"): {
        "pending",
        "ready",
        "running",
        "audit_pending",
        "audit_passed",
        "checkpoint_done",
        "blocked",
        "failed",
        "superseded",
        "completed",
    },
    ("TASK_REGISTRY", "tasks[].requested_by_role"): PROFILE_ROLES | {"NONE"},
    ("TASK_REGISTRY", "tasks[].return_to_role_after_audit_pass"): PROFILE_ROLES | {"none"},
    ("TASK_REGISTRY", "tasks[].push_status"): {"not_required", "not_attempted", "pushed", "failed"},
    ("ACCEPTED_ARTIFACTS", "artifacts[].status"): {"draft", "accepted", "failed", "superseded"},
    ("ACCEPTED_ARTIFACTS", "artifacts[].push_status"): {"not_required", "not_attempted", "pushed", "failed"},
    ("WORKSPACE_IDENTITY", "workspace_type"): {"package_repo", "project_workspace", "implementation_repo", "test_fixture"},
    ("WORKSPACE_IDENTITY", "identity_validation_status"): {"passed", "pending", "failed", "blocked", "not_required"},
    ("WORKSPACE_IDENTITY", "repository_lock_status"): {"passed", "accepted", "pending", "failed", "blocked", "not_required"},
}

BOOLEAN_FIELDS = {
    ("PROJECT_STATE", "push_allowed"),
    ("NEXT_ACTION", "workspace_identity_required"),
    ("NEXT_ACTION", "repository_lock_required"),
    ("NEXT_ACTION", "checkpoint_preflight_required"),
    ("NEXT_ACTION", "checkpoint_receipt_required"),
    ("WORKSPACE_IDENTITY", "push_allowed"),
}

INTEGER_FIELDS = {("TASK_REGISTRY", "registry_revision")}

LIST_OR_NONE_FIELDS = {
    ("PROJECT_STATE", "checkpoint_blocked_by"),
    ("PROJECT_STATE", "active_branches"),
    ("PROJECT_STATE", "completed_milestones"),
    ("PROJECT_STATE", "active_risks"),
    ("PROJECT_STATE", "active_blockers"),
    ("PROJECT_STATE", "active_gaps"),
    ("CURRENT_GATE", "entry_criteria"),
    ("CURRENT_GATE", "exit_criteria"),
    ("CURRENT_GATE", "gate_evidence"),
    ("CURRENT_GATE", "notes"),
    ("NEXT_ACTION", "blocked_by"),
    ("NEXT_ACTION", "required_universal_docs"),
    ("NEXT_ACTION", "required_project_docs"),
    ("NEXT_ACTION", "expected_result"),
    ("TASK_REGISTRY", "tasks"),
    ("ACCEPTED_ARTIFACTS", "artifacts"),
    ("WORKSPACE_IDENTITY", "validation_errors"),
    ("SCHEMA_MANIFEST", "sidecars"),
}

OBJECT_OR_NONE_FIELDS = {
    ("PROJECT_STATE", "last_accepted_result"),
    ("CURRENT_GATE", "blocking_status"),
    ("NEXT_ACTION", "requester_return_context"),
    ("NEXT_ACTION", "blocking_or_resume_context"),
}

NESTED_OBJECT_FIELDS = {
    ("PROJECT_STATE", "last_accepted_result"): ("role", "task", "date", "status", "result_ref"),
    ("CURRENT_GATE", "blocking_status"): ("blocker_id", "blocker_type", "blocks", "blocked_by", "resolution_path"),
    ("NEXT_ACTION", "requester_return_context"): (
        "requested_by_role",
        "requested_by_task",
        "return_to_requester_after_audit_pass",
        "return_to_role_after_audit_pass",
        "return_task_after_audit_pass",
        "research_question_id",
        "accepted_research_result_ref",
        "accepted_research_audit_ref",
    ),
    ("NEXT_ACTION", "blocking_or_resume_context"): (
        "blocker_id",
        "blocker_type",
        "blocks",
        "resolution_path",
        "owner_question",
        "resume_condition",
    ),
}

NESTED_BOOLEAN_FIELDS = {
    ("NEXT_ACTION", "requester_return_context.return_to_requester_after_audit_pass"),
}

LIST_ITEM_LIST_OR_NONE_FIELDS = {
    ("PROJECT_STATE", "active_branches[].dependencies"),
    ("TASK_REGISTRY", "tasks[].dependencies"),
    ("TASK_REGISTRY", "tasks[].result_refs"),
    ("TASK_REGISTRY", "tasks[].audit_refs"),
    ("TASK_REGISTRY", "tasks[].correction_links"),
    ("TASK_REGISTRY", "tasks[].accepted_files"),
}

LIST_ITEM_BOOLEAN_FIELDS = {
    ("TASK_REGISTRY", "tasks[].return_to_requester_after_audit_pass"),
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


def _is_inside_workspace(root: Path, path: Path) -> bool:
    return path.resolve(strict=False).is_relative_to(root.resolve(strict=False))


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


def _markdown_scalar(value: str) -> object:
    normalized = value.strip()
    lowered = normalized.lower()
    if lowered in {"yes", "true"}:
        return True
    if lowered in {"no", "false"}:
        return False
    return normalized


def _json_scalar(value: object) -> object:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return value


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


def _type_finding(spec: SidecarSpec, relpath: str, field: str, expected: str) -> Finding:
    return _finding(
        "SIDECAR_TYPE_INVALID",
        "Sidecar field type is invalid",
        f"{spec.sidecar_type}.{field} must be {expected}.",
        relpath,
        field,
        "Use the documented JSON type for every governed field.",
    )


def _boolean_finding(spec: SidecarSpec, relpath: str, field: str) -> Finding:
    return _finding(
        "SIDECAR_BOOLEAN_VALUE_INVALID",
        "Sidecar boolean value is invalid",
        f"{spec.sidecar_type}.{field} must be a JSON boolean, not a Markdown string spelling.",
        relpath,
        field,
        "Use true or false for boolean governed fields.",
    )


def _enum_finding(spec: SidecarSpec, relpath: str, field: str, raw: object, allowed: set[str]) -> Finding:
    return _finding(
        "SIDECAR_ENUM_VALUE_INVALID",
        "Sidecar enum value is invalid",
        f"{spec.sidecar_type}.{field}={raw!r} is not allowed.",
        relpath,
        field,
        f"Use one of: {', '.join(sorted(allowed))}.",
    )


def _is_list_or_none(value: object) -> bool:
    return isinstance(value, list) or value == "NONE"


def _is_object_or_none(value: object) -> bool:
    return isinstance(value, dict) or value == "NONE"


def _validate_content_type(spec: SidecarSpec, content: dict[str, object], relpath: str) -> list[Finding]:
    findings: list[Finding] = []
    for field in spec.required_fields:
        if field not in content:
            continue
        value = content[field]
        field_key = (spec.sidecar_type, field)
        if field_key in LIST_OR_NONE_FIELDS:
            if not _is_list_or_none(value):
                findings.append(_type_finding(spec, relpath, f"content.{field}", "a list or 'NONE'"))
        elif field_key in OBJECT_OR_NONE_FIELDS:
            if not _is_object_or_none(value):
                findings.append(_type_finding(spec, relpath, f"content.{field}", "an object or 'NONE'"))
        elif field_key in BOOLEAN_FIELDS:
            if not isinstance(value, bool):
                findings.append(_boolean_finding(spec, relpath, f"content.{field}"))
        elif field_key in INTEGER_FIELDS:
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                findings.append(_type_finding(spec, relpath, f"content.{field}", "a positive integer"))
        elif not isinstance(value, str):
            findings.append(_type_finding(spec, relpath, f"content.{field}", "a string"))
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
            for item_field in item_fields:
                if item_field not in item:
                    continue
                item_value = item[item_field]
                item_field_key = (spec.sidecar_type, f"{field}[].{item_field}")
                display_field = f"{item_path}.{item_field}"
                if item_field_key in LIST_ITEM_LIST_OR_NONE_FIELDS:
                    if not _is_list_or_none(item_value):
                        findings.append(_type_finding(spec, relpath, display_field, "a list or 'NONE'"))
                elif item_field_key in LIST_ITEM_BOOLEAN_FIELDS:
                    if not isinstance(item_value, bool):
                        findings.append(_boolean_finding(spec, relpath, display_field))
                elif not isinstance(item_value, str):
                    findings.append(_type_finding(spec, relpath, display_field, "a string"))
    return findings


def _validate_nested_objects(spec: SidecarSpec, content: dict[str, object], relpath: str) -> list[Finding]:
    findings: list[Finding] = []
    for (sidecar_type, field), required_fields in NESTED_OBJECT_FIELDS.items():
        if sidecar_type != spec.sidecar_type or field not in content:
            continue
        value = content[field]
        if value == "NONE":
            continue
        if not isinstance(value, dict):
            continue
        item_path = f"content.{field}"
        for required in required_fields:
            if required not in value:
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
        for extra in sorted(set(value) - set(required_fields)):
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
        for nested_field in required_fields:
            if nested_field not in value:
                continue
            nested_value = value[nested_field]
            nested_key = (spec.sidecar_type, f"{field}.{nested_field}")
            display_field = f"{item_path}.{nested_field}"
            if nested_key in NESTED_BOOLEAN_FIELDS:
                if not isinstance(nested_value, bool):
                    findings.append(_boolean_finding(spec, relpath, display_field))
            elif not isinstance(nested_value, str):
                findings.append(_type_finding(spec, relpath, display_field, "a string"))
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
    findings.extend(_validate_nested_objects(spec, content, relpath))
    return findings


def _validate_enum_values(spec: SidecarSpec, content: dict[str, object], relpath: str) -> list[Finding]:
    findings: list[Finding] = []
    for (sidecar_type, field), allowed in ENUM_FIELDS.items():
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
                    findings.append(_enum_finding(spec, relpath, f"content.{list_name}[{index}].{item_field}", raw, allowed))
            continue
        if "." in field:
            object_name, item_field = field.split(".", 1)
            entry = content.get(object_name)
            if entry == "NONE" or not isinstance(entry, dict) or item_field not in entry:
                continue
            raw = entry[item_field]
            if not isinstance(raw, str) or raw not in allowed:
                findings.append(_enum_finding(spec, relpath, f"content.{object_name}.{item_field}", raw, allowed))
            continue

        raw = content.get(field)
        if raw is None:
            continue
        if not isinstance(raw, str) or raw not in allowed:
            findings.append(_enum_finding(spec, relpath, f"content.{field}", raw, allowed))
    return findings


def _validate_markdown_parity(root: Path, spec: SidecarSpec, content: dict[str, object], relpath: str) -> list[Finding]:
    markdown_path = root / spec.markdown_source
    if not markdown_path.is_file():
        return [
            _finding(
                "SIDECAR_MARKDOWN_COMPATIBILITY_VIEW_MISSING",
                repair_hints.MISSING_RUNTIME_VIEWS_TITLE,
                f"{repair_hints.MISSING_RUNTIME_VIEWS_TITLE} Missing view: {spec.markdown_source}.",
                spec.markdown_source,
                "",
                repair_hints.MISSING_RUNTIME_VIEWS_RECOMMENDATION,
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
        if _markdown_scalar(markdown_value) != _json_scalar(value):
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


def _validate_sidecar(
    root: Path,
    spec: SidecarSpec,
    *,
    allow_markdown_fallback: bool = True,
) -> tuple[dict[str, object] | None, list[Finding]]:
    path = root / "project-runtime" / "state" / spec.filename
    relpath = _rel(root, path)
    if not path.is_file():
        markdown_path = root / spec.markdown_source
        if allow_markdown_fallback and markdown_path.is_file():
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
    raw_schema_version = payload.get("schema_version")
    is_current_schema = raw_schema_version == CURRENT_SCHEMA_VERSION
    envelope_fields = CURRENT_ENVELOPE_FIELDS if is_current_schema else LEGACY_ENVELOPE_FIELDS
    envelope_field_set = CURRENT_ENVELOPE_FIELD_SET if is_current_schema else LEGACY_ENVELOPE_FIELD_SET

    for field in envelope_fields:
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
    for extra in sorted(set(payload) - envelope_field_set):
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

    if raw_schema_version not in {LEGACY_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION}:
        findings.append(
            _finding(
                "SIDECAR_SCHEMA_VERSION_MISSING_OR_INVALID",
                "Sidecar schema version is invalid",
                f"{relpath}.schema_version must be {LEGACY_SCHEMA_VERSION!r} or {CURRENT_SCHEMA_VERSION!r}.",
                relpath,
                "schema_version",
                "Use a supported runtime sidecar schema version.",
            )
        )
    if is_current_schema and payload.get("runtime_schema_version") != CURRENT_SCHEMA_VERSION:
        findings.append(
            _finding(
                "SIDECAR_RUNTIME_SCHEMA_VERSION_INVALID",
                "Sidecar runtime schema version is invalid",
                f"{relpath}.runtime_schema_version must be {CURRENT_SCHEMA_VERSION!r}.",
                relpath,
                "runtime_schema_version",
                "Keep schema_version and runtime_schema_version aligned for current runtime state.",
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
    if "markdown_source" in payload and payload.get("markdown_source") != spec.markdown_source:
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
        findings.extend(_validate_enum_values(spec, content, relpath))
        if not is_current_schema:
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
                refs.append(("ACCEPTED_ARTIFACTS.json", f"content.artifacts[{index}].source_task", str(artifact.get("source_task", ""))))

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


def _artifact_package_findings(sidecars: dict[str, dict[str, object]]) -> list[Finding]:
    accepted = _content(sidecars, "ACCEPTED_ARTIFACTS")
    artifacts = accepted.get("artifacts")
    if not isinstance(artifacts, list):
        return []

    findings: list[Finding] = []
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            continue
        artifact_type = artifact.get("artifact_type")
        if artifact_type not in {"RESULT_PACKAGE", "AUDIT_RESULT_PACKAGE"}:
            continue
        path = "project-runtime/state/ACCEPTED_ARTIFACTS.json"
        prefix = f"content.artifacts[{index}]"
        status = artifact.get("status")
        artifact_ref = artifact.get("artifact_ref")
        source_result_ref = artifact.get("source_result_ref")
        audit_ref = artifact.get("audit_ref")
        if status != "accepted":
            findings.append(
                _finding(
                    "SIDECAR_ARTIFACT_PACKAGE_STATUS_INVALID",
                    "Artifact package entry is not accepted",
                    f"ACCEPTED_ARTIFACTS.{prefix}.status={status!r} must be 'accepted' for {artifact_type}.",
                    path,
                    f"{prefix}.status",
                    "Only accepted RESULT/AUDIT_RESULT package entries may participate in audit routing or checkpoint evidence.",
                )
            )
        if artifact_type == "RESULT_PACKAGE":
            if not isinstance(artifact_ref, str) or not RESULT_PACKAGE_REF_RE.fullmatch(artifact_ref):
                findings.append(
                    _finding(
                        "SIDECAR_RESULT_PACKAGE_REF_INVALID",
                        "RESULT package artifact_ref is invalid",
                        f"ACCEPTED_ARTIFACTS.{prefix}.artifact_ref={artifact_ref!r} must reference an accepted RESULT package JSON artifact.",
                        path,
                        f"{prefix}.artifact_ref",
                        "Use project-runtime/artifacts/accepted/RESULT_PACKAGE_<TASK_ID>_ATTEMPT_<N>.json.",
                    )
                )
            if not isinstance(source_result_ref, str) or not WORKER_RESULT_REF_RE.fullmatch(source_result_ref):
                findings.append(
                    _finding(
                        "SIDECAR_RESULT_PACKAGE_SOURCE_REF_INVALID",
                        "RESULT package source_result_ref is invalid",
                        f"ACCEPTED_ARTIFACTS.{prefix}.source_result_ref={source_result_ref!r} must reference the worker RESULT.",
                        path,
                        f"{prefix}.source_result_ref",
                        "Use project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_<N>.md.",
                    )
                )
            if audit_ref != "NONE":
                findings.append(
                    _finding(
                        "SIDECAR_RESULT_PACKAGE_AUDIT_REF_INVALID",
                        "RESULT package audit_ref must not preclaim audit evidence",
                        f"ACCEPTED_ARTIFACTS.{prefix}.audit_ref={audit_ref!r} must be 'NONE' before audit.",
                        path,
                        f"{prefix}.audit_ref",
                        "Leave audit_ref as NONE until an AUDIT_RESULT package is accepted.",
                    )
                )
        if artifact_type == "AUDIT_RESULT_PACKAGE":
            if not isinstance(artifact_ref, str) or not AUDIT_RESULT_PACKAGE_REF_RE.fullmatch(artifact_ref):
                findings.append(
                    _finding(
                        "SIDECAR_AUDIT_RESULT_PACKAGE_REF_INVALID",
                        "AUDIT_RESULT package artifact_ref is invalid",
                        f"ACCEPTED_ARTIFACTS.{prefix}.artifact_ref={artifact_ref!r} must reference an accepted AUDIT_RESULT package JSON artifact.",
                        path,
                        f"{prefix}.artifact_ref",
                        "Use project-runtime/artifacts/accepted/AUDIT_RESULT_PACKAGE_<TASK_ID>_ATTEMPT_<N>.json.",
                    )
                )
            if not isinstance(source_result_ref, str) or not WORKER_RESULT_REF_RE.fullmatch(source_result_ref):
                findings.append(
                    _finding(
                        "SIDECAR_AUDIT_RESULT_PACKAGE_SOURCE_REF_INVALID",
                        "AUDIT_RESULT package source_result_ref is invalid",
                        f"ACCEPTED_ARTIFACTS.{prefix}.source_result_ref={source_result_ref!r} must reference the audited worker RESULT.",
                        path,
                        f"{prefix}.source_result_ref",
                        "Use project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_<N>.md.",
                    )
                )
            if not isinstance(audit_ref, str) or not AUDIT_RESULT_REF_RE.fullmatch(audit_ref):
                findings.append(
                    _finding(
                        "SIDECAR_AUDIT_RESULT_PACKAGE_AUDIT_REF_INVALID",
                        "AUDIT_RESULT package audit_ref is invalid",
                        f"ACCEPTED_ARTIFACTS.{prefix}.audit_ref={audit_ref!r} must reference the AUDIT_RESULT.",
                        path,
                        f"{prefix}.audit_ref",
                        "Use project-runtime/results/audit/AUDIT_RESULT_<TASK_ID>_ATTEMPT_<N>.md.",
                    )
                )
    return findings


def _truthy_refs(value: object) -> bool:
    return bool(_truthy_ref_values(value))


def _truthy_ref_values(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip() and item.strip() not in NONE_VALUES]


def _checkpoint_findings(root: Path, sidecars: dict[str, dict[str, object]]) -> list[Finding]:
    next_action = _content(sidecars, "NEXT_ACTION")
    checkpoint_policy = next_action.get("checkpoint_policy")
    checkpoint_attempt = checkpoint_policy in {"local_only", "commit_and_push"} or next_action.get("checkpoint_receipt_required") is True
    if not checkpoint_attempt:
        return []

    task_id = next_action.get("task_id")
    if not isinstance(task_id, str) or _is_none(task_id):
        return []
    task = _task_registry(sidecars).get(task_id)
    if not task:
        return []

    status = task.get("status")
    audit_refs = _truthy_ref_values(task.get("audit_refs"))
    audit_inspection = result_parser.inspect_audit_references(root, audit_refs, task_id=task_id, strict=True)
    invalid_refs = audit_inspection["invalid_refs"]
    unparsed_refs = audit_inspection["unparsed_refs"]
    passed_refs = audit_inspection["passed_refs"]
    if invalid_refs or unparsed_refs:
        return [
            _finding(
                "SIDECAR_CHECKPOINT_AUDIT_RESULT_INVALID",
                "Checkpoint audit evidence is not a passing AUDIT_RESULT",
                json.dumps(
                    {
                        "invalid_refs": invalid_refs,
                        "unparsed_refs": unparsed_refs,
                    },
                    sort_keys=True,
                ),
                "project-runtime/state/TASK_REGISTRY.json",
                "content.tasks[].audit_refs",
                "Record an auditor AUDIT_RESULT with STATUS: pass for the task before a checkpoint action.",
            )
        ]
    if passed_refs:
        return []

    return [
        _finding(
            "SIDECAR_CHECKPOINT_POLICY_INVALID",
            "NEXT_ACTION checkpoint attempt lacks audit-pass evidence",
            (
                "NEXT_ACTION requests a checkpoint-capable policy, "
                f"but TASK_REGISTRY task {task_id} has no parsed passing AUDIT_RESULT evidence. "
                f"status={status or 'NONE'}; audit_refs={audit_refs}"
            ),
            "project-runtime/state/NEXT_ACTION.json",
            "content.checkpoint_policy",
            "Record audit-pass evidence before a checkpoint action, or use checkpoint_policy forbidden/no_checkpoint.",
        )
    ]


def _nonempty_terminal_blockers(value: object) -> list[str]:
    if isinstance(value, list):
        blockers: list[str] = []
        for item in value:
            if isinstance(item, str) and not _is_none(item):
                blockers.append(item.strip())
            elif isinstance(item, dict):
                blocker_id = item.get("blocker_id")
                status = item.get("status")
                if isinstance(blocker_id, str) and not _is_none(blocker_id):
                    blockers.append(f"{blocker_id}:{status or 'unknown'}")
                elif item:
                    blockers.append(json.dumps(item, sort_keys=True))
        return blockers
    if isinstance(value, str) and not _is_none(value):
        return [value.strip()]
    if isinstance(value, dict) and value:
        return [json.dumps(value, sort_keys=True)]
    return []


def _terminal_completion_findings(sidecars: dict[str, dict[str, object]]) -> list[Finding]:
    project_state = _content(sidecars, "PROJECT_STATE")
    current_gate = _content(sidecars, "CURRENT_GATE")
    next_action = _content(sidecars, "NEXT_ACTION")
    terminal_claimed = (
        project_state.get("project_status") == "completed"
        or project_state.get("current_phase") == "completed"
    )
    if not terminal_claimed:
        return []

    findings: list[Finding] = []
    tasks = _content(sidecars, "TASK_REGISTRY").get("tasks")
    unresolved: list[str] = []
    if isinstance(tasks, list):
        for task in tasks:
            if not isinstance(task, dict):
                continue
            status = task.get("status")
            if status in {"failed", "blocked", "audit_pending"}:
                unresolved.append(f"{task.get('task_id', 'UNKNOWN')}:{status}")
    if unresolved:
        findings.append(
            _finding(
                "PROJECT_COMPLETED_UNRESOLVED_TASKS",
                "PROJECT_COMPLETED has unresolved task states",
                f"PROJECT_COMPLETED is invalid with unresolved failed/blocked/audit_pending tasks: {', '.join(unresolved)}.",
                "project-runtime/state/TASK_REGISTRY.json",
                "content.tasks[].status",
                "Resolve, supersede, or correct failed/blocked/audit_pending tasks before lifecycle finalize can complete the project.",
            )
        )

    stale_blockers = sorted(
        set(
            _nonempty_terminal_blockers(project_state.get("active_blockers"))
            + _nonempty_terminal_blockers(project_state.get("active_gaps"))
            + _nonempty_terminal_blockers(project_state.get("checkpoint_blocked_by"))
            + _nonempty_terminal_blockers(next_action.get("blocked_by"))
            + _nonempty_terminal_blockers(current_gate.get("blocking_status"))
        )
    )
    if stale_blockers:
        findings.append(
            _finding(
                "PROJECT_COMPLETED_STALE_BLOCKERS",
                "PROJECT_COMPLETED has stale blockers",
                f"PROJECT_COMPLETED is invalid with active/stale blockers: {', '.join(stale_blockers)}.",
                "project-runtime/state/PROJECT_STATE.json",
                "content.active_blockers",
                "Clear checkpoint blockers, active blockers, and active GAPs before marking the project completed.",
            )
        )

    audit_status = project_state.get("audit_status")
    if audit_status not in {"passed", "not_applicable"}:
        findings.append(
            _finding(
                "PROJECT_COMPLETED_AUDIT_STATUS_INVALID",
                "PROJECT_COMPLETED audit status is not terminal-pass",
                f"PROJECT_STATE.content.audit_status={audit_status!r} is not valid for PROJECT_COMPLETED.",
                "project-runtime/state/PROJECT_STATE.json",
                "content.audit_status",
                "Record mandatory audit pass evidence before project completion.",
            )
        )

    checkpoint_status = project_state.get("project_checkpoint_status")
    if checkpoint_status in {"pending", "failed", "blocked"}:
        findings.append(
            _finding(
                "PROJECT_COMPLETED_CHECKPOINT_STATUS_INVALID",
                "PROJECT_COMPLETED checkpoint status is unresolved",
                f"PROJECT_STATE.content.project_checkpoint_status={checkpoint_status!r} is not valid for PROJECT_COMPLETED.",
                "project-runtime/state/PROJECT_STATE.json",
                "content.project_checkpoint_status",
                "Complete or explicitly mark checkpoint not_required before project completion.",
            )
        )

    route_valid = (
        current_gate.get("gate_type") == "terminal"
        and current_gate.get("status") == "passed"
        and next_action.get("action_type") == "stop"
        and next_action.get("target_role") == "none"
        and next_action.get("action_semantic") == "stop_terminal"
    )
    if not route_valid:
        findings.append(
            _finding(
                "PROJECT_COMPLETED_ROUTE_INVALID",
                "PROJECT_COMPLETED terminal route is incomplete",
                (
                    "PROJECT_COMPLETED requires CURRENT_GATE terminal/passed and "
                    "NEXT_ACTION stop/none/stop_terminal."
                ),
                "project-runtime/state/NEXT_ACTION.json",
                "content.action_type",
                "Run aso lifecycle finalize --root WORKSPACE --confirm-write to create the terminal route.",
            )
        )
    return findings


def _bootstrap_semantic_findings(root: Path, sidecars: dict[str, dict[str, object]]) -> list[Finding]:
    project_state = _content(sidecars, "PROJECT_STATE")
    current_gate = _content(sidecars, "CURRENT_GATE")
    next_action = _content(sidecars, "NEXT_ACTION")
    findings: list[Finding] = []

    if (
        project_state.get("current_phase") == "bootstrap"
        and project_state.get("project_status") == "active"
        and current_gate.get("status") == "open"
        and (
            next_action.get("action_semantic") == "stop_terminal"
            or next_action.get("action_type") == "stop"
        )
    ):
        findings.append(
            _finding(
                "BSR_BOOTSTRAP_STOP_TERMINAL_INVALID",
                "Active bootstrap state cannot use terminal stop",
                (
                    "PROJECT_STATE is bootstrap/active and CURRENT_GATE is open, "
                    "but NEXT_ACTION is terminal stop. Reconcile bootstrap state "
                    "or route a bootstrap correction/preparation action."
                ),
                "project-runtime/state/NEXT_ACTION.json",
                "content.action_semantic",
                (
                    "Use a bootstrap preparation/correction action, or close the gate and mark the project "
                    "terminal with evidence."
                ),
            )
        )

    tz_path = project_state.get("tz_path")
    tz_path_text = tz_path.strip() if isinstance(tz_path, str) else ""
    tz_path_valid = False
    if not tz_path_text or tz_path_text in NONE_VALUES:
        findings.append(
            _finding(
                "BSR_TZ_PATH_MISSING",
                "PROJECT_STATE tz_path is missing",
                "PROJECT_STATE.content.tz_path must reference a project TZ file path, not a timezone value.",
                "project-runtime/state/PROJECT_STATE.json",
                "content.tz_path",
                "Set tz_path to project-input/TZ.md or another existing workspace-local TZ file.",
            )
        )
    elif IANA_TIMEZONE_RE.fullmatch(tz_path_text) or tz_path_text in IANA_SINGLETON_TIMEZONES:
        findings.append(
            _finding(
                "BSR_TZ_PATH_TIMEZONE_VALUE",
                "PROJECT_STATE tz_path contains a timezone value",
                f"PROJECT_STATE.content.tz_path={tz_path_text!r} looks like an IANA timezone, not a file path.",
                "project-runtime/state/PROJECT_STATE.json",
                "content.tz_path",
                "Set tz_path to project-input/TZ.md; keep timezone values inside the TZ document.",
            )
        )
    elif Path(tz_path_text).is_absolute():
        findings.append(
            _finding(
                "BSR_TZ_PATH_ABSOLUTE",
                "PROJECT_STATE tz_path is absolute",
                f"PROJECT_STATE.content.tz_path={tz_path_text!r} must be workspace-relative.",
                "project-runtime/state/PROJECT_STATE.json",
                "content.tz_path",
                "Use a workspace-relative TZ document path such as project-input/TZ.md.",
            )
        )
    elif not _is_inside_workspace(root, root / tz_path_text):
        findings.append(
            _finding(
                "BSR_TZ_PATH_OUTSIDE_WORKSPACE",
                "PROJECT_STATE tz_path escapes workspace root",
                f"PROJECT_STATE.content.tz_path={tz_path_text!r} must stay inside the workspace.",
                "project-runtime/state/PROJECT_STATE.json",
                "content.tz_path",
                "Use a workspace-relative TZ document path such as project-input/TZ.md.",
            )
        )
    elif not (root / tz_path_text).is_file():
        findings.append(
            _finding(
                "BSR_TZ_PATH_TARGET_MISSING",
                "PROJECT_STATE tz_path target is missing",
                f"PROJECT_STATE.content.tz_path={tz_path_text!r} does not point to an existing file.",
                "project-runtime/state/PROJECT_STATE.json",
                "content.tz_path",
                "Create the TZ document or update tz_path to an existing workspace-local TZ file.",
            )
        )
    else:
        tz_path_valid = True

    canonical_tz = root / "project-input" / "TZ.md"
    if canonical_tz.is_file() and tz_path_valid and tz_path_text != "project-input/TZ.md":
        findings.append(
            _finding(
                "BSR_TZ_PATH_CANONICAL_MISMATCH",
                "PROJECT_STATE tz_path does not reference project-input/TZ.md",
                "project-input/TZ.md exists, so PROJECT_STATE.content.tz_path must reference project-input/TZ.md.",
                "project-runtime/state/PROJECT_STATE.json",
                "content.tz_path",
                "Set PROJECT_STATE.content.tz_path to project-input/TZ.md and rerun aso state render --root WORKSPACE --confirm-write so PROJECT_STATE.md shows the same TZ_PATH.",
            )
        )
    return findings


def _is_current_p2_state(sidecars: dict[str, dict[str, object]], root: Path) -> bool:
    if (root / runtime_schema_contracts.STATE_ROOT / "SCHEMA_MANIFEST.json").is_file():
        return True
    for payload in sidecars.values():
        if payload.get("schema_version") == CURRENT_SCHEMA_VERSION:
            return True
        content = payload.get("content")
        if isinstance(content, dict) and content.get("runtime_schema_version") == CURRENT_SCHEMA_VERSION:
            return True
    return False


def _optional_sidecar_status(root: Path) -> tuple[list[str], list[str]]:
    present: list[str] = []
    missing: list[str] = []
    for sidecar_type in runtime_schema_contracts.OPTIONAL_SIDECARS:
        filename = f"{sidecar_type}.json"
        if (root / runtime_schema_contracts.STATE_ROOT / filename).is_file():
            present.append(sidecar_type)
        else:
            missing.append(sidecar_type)
    return sorted(present), sorted(missing)


def _optional_readiness_findings(missing_optional: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for sidecar_type in missing_optional:
        findings.append(
            _finding(
                "SIDECAR_OPTIONAL_SIDECAR_MISSING",
                "Optional state sidecar is missing",
                f"{runtime_schema_contracts.STATE_ROOT}/{sidecar_type}.json is optional under Runtime Schema {CURRENT_SCHEMA_VERSION}.",
                f"{runtime_schema_contracts.STATE_ROOT}/{sidecar_type}.json",
                "",
                "Create the optional sidecar when that readiness signal is needed.",
                severity="info",
            )
        )
    return findings


def _transition_engine_findings(sidecars: dict[str, dict[str, object]]) -> list[Finding]:
    try:
        contract = transition_engine.load_runtime_contract()
    except (OSError, transition_engine.RuntimeContractError) as exc:
        return [
            _finding(
                "RUNTIME_CONTRACT_LOAD_FAILED",
                "Runtime contract could not be loaded",
                str(exc),
                transition_engine.CONTRACT_RELATIVE_PATH.as_posix(),
                "",
                "Restore ORCHESTRATOR_RUNTIME_CONTRACT.json and its schema before verifying current runtime state.",
            )
        ]

    decision = transition_engine.explain_next_action_from_sidecars(contract, sidecars)
    findings: list[Finding] = []
    for engine_finding in decision.findings:
        path = "project-runtime/state/NEXT_ACTION.json"
        field = "content"
        if engine_finding.rule_id.startswith("RUNTIME_LIFECYCLE"):
            path = transition_engine.LIFECYCLE_LOG_RELATIVE_PATH.as_posix()
            field = "event_log"
        findings.append(
            _finding(
                engine_finding.rule_id,
                "Transition engine rejected NEXT_ACTION",
                engine_finding.message,
                path,
                field,
                engine_finding.recommendation,
                severity=engine_finding.severity,
            )
        )
    return findings


def _reconciliation_report(root: Path, sidecars: dict[str, dict[str, object]], enabled: bool) -> dict[str, object]:
    try:
        contract = transition_engine.load_runtime_contract()
        payload = transition_engine.routing_authority_report(contract, sidecars, root=root)
    except (OSError, transition_engine.RuntimeContractError) as exc:
        return {
            "enabled": enabled,
            "status": "failed",
            "error": str(exc),
            "reference_docs_used": [transition_engine.CONTRACT_RELATIVE_PATH.as_posix()],
        }
    payload["enabled"] = enabled
    if not enabled:
        payload["reason"] = "transition authority reported in dry-run mode; reconciliation findings require current runtime schema or lifecycle log evidence"
    payload["status"] = "passed" if payload.get("allowed") else "failed"
    payload["read_only"] = True
    payload["mutations_performed"] = False
    return payload


def _report(root: Path, strict: bool) -> tuple[dict[str, object], int]:
    findings: list[Finding] = []
    loaded_sidecars: dict[str, dict[str, object]] = {}
    present: list[str] = []
    missing: list[str] = []
    optional_present: list[str] = []
    optional_missing: list[str] = []

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
        return _build_report(
            root,
            strict,
            status,
            summary,
            [finding],
            {},
            [],
            [],
            False,
            [],
            [],
            {"enabled": False, "reason": "workspace root is unreadable"},
        ), exit_code

    for spec in SIDECARS:
        payload, sidecar_findings = _validate_sidecar(root, spec)
        findings.extend(sidecar_findings)
        if payload is None:
            missing.append(spec.sidecar_type)
        else:
            present.append(spec.sidecar_type)
            loaded_sidecars[spec.sidecar_type] = payload

    lifecycle_log = transition_engine.load_lifecycle_log(root)
    lifecycle_has_evidence = bool(lifecycle_log.get("events")) or bool(lifecycle_log.get("findings"))
    if lifecycle_has_evidence:
        loaded_sidecars["LIFECYCLE_LOG"] = lifecycle_log

    current_p2_state = _is_current_p2_state(loaded_sidecars, root)
    if current_p2_state:
        current_required = set(runtime_schema_contracts.REQUIRED_SIDECARS)
        findings = [
            finding
            for finding in findings
            if not (
                finding.rule_id
                in {"SIDECAR_MISSING_MARKDOWN_FALLBACK_USED", "SIDECAR_REQUIRED_SIDECAR_MISSING"}
                and finding.path.removeprefix(f"{runtime_schema_contracts.STATE_ROOT}/").removesuffix(".json")
                in current_required
            )
        ]
        for sidecar_type in runtime_schema_contracts.REQUIRED_SIDECARS:
            if sidecar_type in loaded_sidecars:
                continue
            spec = SIDECAR_BY_TYPE.get(sidecar_type)
            if spec is None:
                findings.append(
                    _finding(
                        "SIDECAR_CONTRACT_SPEC_MISSING",
                        "Verifier is missing a required sidecar spec",
                        f"Runtime schema contract requires {sidecar_type}, but state verify has no validator spec.",
                        runtime_schema_contracts.STATE_ROOT,
                        sidecar_type,
                        "Update state verify sidecar specs from the active runtime schema contract.",
                    )
                )
                missing.append(sidecar_type)
                continue
            payload, sidecar_findings = _validate_sidecar(root, spec, allow_markdown_fallback=False)
            findings.extend(sidecar_findings)
            if payload is None:
                if sidecar_type not in missing:
                    missing.append(sidecar_type)
            else:
                if sidecar_type not in present:
                    present.append(sidecar_type)
                loaded_sidecars[sidecar_type] = payload

        optional_present, optional_missing = _optional_sidecar_status(root)
        findings.extend(_optional_readiness_findings(optional_missing))

    findings.extend(_reference_findings(loaded_sidecars))
    findings.extend(_artifact_package_findings(loaded_sidecars))
    findings.extend(_checkpoint_findings(root, loaded_sidecars))
    findings.extend(_bootstrap_semantic_findings(root, loaded_sidecars))
    findings.extend(_terminal_completion_findings(loaded_sidecars))
    reconciliation_enabled = current_p2_state or lifecycle_has_evidence
    if reconciliation_enabled:
        findings.extend(_transition_engine_findings(loaded_sidecars))
    findings = sorted(findings, key=lambda item: (item.severity != "error", item.rule_id, item.path, item.field, item.details))
    summary = _summary(findings)
    status, exit_code = _status(summary, strict)
    return _build_report(
        root,
        strict,
        status,
        summary,
        findings,
        loaded_sidecars,
        present,
        missing,
        current_p2_state,
        optional_present,
        optional_missing,
        _reconciliation_report(root, loaded_sidecars, reconciliation_enabled),
    ), exit_code


def _build_report(
    root: Path,
    strict: bool,
    status: str,
    summary: dict[str, int],
    findings: list[Finding],
    sidecars: dict[str, dict[str, object]],
    present: list[str],
    missing: list[str],
    current_p2_state: bool,
    optional_present: list[str],
    optional_missing: list[str],
    reconciliation: dict[str, object],
) -> dict[str, object]:
    required_expected = (
        list(runtime_schema_contracts.REQUIRED_SIDECARS)
        if current_p2_state
        else [spec.sidecar_type for spec in SIDECARS]
    )
    expected = (
        sorted(set(required_expected) | set(runtime_schema_contracts.OPTIONAL_SIDECARS))
        if current_p2_state
        else sorted(required_expected)
    )
    all_present = sorted(set(present) | set(optional_present))
    all_missing = sorted(set(missing) | set(optional_missing)) if current_p2_state else sorted(missing)
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
            "runtime_schema_current_p2": current_p2_state,
            "sidecars_expected": expected,
            "sidecars_present": all_present,
            "sidecars_missing": all_missing,
            "required_sidecars_expected": sorted(required_expected),
            "required_sidecars_present": sorted(sidecar for sidecar in present if sidecar in set(required_expected)),
            "required_sidecars_missing": sorted(sidecar for sidecar in missing if sidecar in set(required_expected)),
            "optional_sidecars_expected": sorted(runtime_schema_contracts.OPTIONAL_SIDECARS) if current_p2_state else [],
            "optional_sidecars_present": optional_present,
            "optional_sidecars_missing": optional_missing,
            "task_registry_count": len(_task_registry(sidecars)),
        },
        "runtime_schema_contract": runtime_schema_contracts.contract_summary(),
        "reconciliation": reconciliation,
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
