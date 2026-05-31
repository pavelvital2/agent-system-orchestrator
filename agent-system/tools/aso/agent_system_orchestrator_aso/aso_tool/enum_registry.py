"""Canonical ASO enum and active version registry."""

from __future__ import annotations

from dataclasses import dataclass


ACTIVE_PACKAGE_VERSION = "3.8.0"
ACTIVE_GOVERNANCE_RULESET_VERSION = "3.8.0"
ACTIVE_RUNTIME_SCHEMA_VERSION = "3.2.0"
ACTIVE_ARTIFACT_PACKAGE_SCHEMA_VERSION = "1.1.0"

CANONICAL_BOOLEAN_TEXT = ("true", "false")
LEGACY_TRUE_TEXT = ("yes",)
LEGACY_FALSE_TEXT = ("no",)
TRUE_TEXT = ("true", *LEGACY_TRUE_TEXT)
FALSE_TEXT = ("false", *LEGACY_FALSE_TEXT)

TASK_KINDS = (
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
)
FAILURE_TYPES = (
    "governance",
    "workflow",
    "filesystem",
    "runtime_state",
    "audit",
    "testing",
    "gap",
    "blocked",
    "none",
)
RESULT_ACCEPTANCE_MODES = ("result_only", "artifact_package")

DISPATCHABLE_ROLE_IDS = (
    "requirements_analyst",
    "solution_architect",
    "developer",
    "tester",
    "auditor",
    "technical_writer",
)
LEGACY_LIFECYCLE_SYSTEM_ROLE_IDS = (
    "designer",
    "devops_setup_engineer",
    "release_manager",
)
PROFILE_RESULT_ROLE_IDS = tuple(
    dict.fromkeys((*DISPATCHABLE_ROLE_IDS, *LEGACY_LIFECYCLE_SYSTEM_ROLE_IDS))
)
CONTROL_OR_PSEUDO_ROLE_IDS = (
    "orchestrator",
    "project_owner",
    "owner",
    "control",
    "none",
)
CONTROL_OR_TARGET_ROLE_IDS = tuple(
    dict.fromkeys(
        (
            "orchestrator",
            *PROFILE_RESULT_ROLE_IDS,
            "project_owner",
            "none",
        )
    )
)
FORBIDDEN_DISPATCH_ROLE_IDS = (
    "orchestrator",
    "owner",
    "control",
    "release_manager",
)

LIFECYCLE_STATUSES = (
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
)
TASK_STATUSES = (
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
)
TASK_RESOLUTION_STATUSES = ("not_required", "unresolved", "resolved", "superseded")
AUDIT_STATUSES = ("not_applicable", "pending", "passed", "failed", "blocked", "gap")
CHECKPOINT_STATUSES = (
    "not_required",
    "not_run",
    "pending",
    "eligible",
    "ineligible",
    "passed",
    "failed",
    "blocked",
)
PROJECT_CHECKPOINT_STATUSES = ("not_required", "pending", "passed", "failed", "blocked")
CHECKPOINT_PREFLIGHT_STATUSES = ("not_run", "passed", "failed", "blocked")
CHECKPOINT_ELIGIBILITY_STATUSES = ("not_checked", "eligible", "ineligible", "blocked")
CHECKPOINT_ELIGIBILITIES = ("blocked", "local_only", "push_allowed", "not_applicable")

ACTION_STATUSES = ("ready", "blocked", "completed", "not_applicable")
ACTION_TYPES = (
    "create_agent",
    "route_result",
    "update_state",
    "wait_for_owner",
    "correction",
    "finalize",
    "stop",
)
ACTION_SEMANTICS = (
    "normal",
    "wait_for_owner",
    "pause",
    "stop_terminal",
    "completed_state_transition",
)
COMPATIBILITY_STATUSES = (
    "current",
    "compatible_migration_available",
    "compatible_legacy_read_only",
    "unsupported",
    "malformed",
)


@dataclass(frozen=True)
class BooleanNormalization:
    value: bool | None
    canonical_text: str
    was_legacy: bool

    @property
    def valid(self) -> bool:
        return self.value is not None


def normalize_boolean_text(value: object, *, allow_legacy: bool = True) -> BooleanNormalization:
    """Normalize canonical true/false text, optionally accepting legacy aliases."""

    lowered = value.strip().lower() if isinstance(value, str) else ""
    if lowered == "true":
        return BooleanNormalization(True, "true", False)
    if lowered == "false":
        return BooleanNormalization(False, "false", False)
    if allow_legacy and lowered in LEGACY_TRUE_TEXT:
        return BooleanNormalization(True, "true", True)
    if allow_legacy and lowered in LEGACY_FALSE_TEXT:
        return BooleanNormalization(False, "false", True)
    return BooleanNormalization(None, "", False)


def canonical_bool_text(value: bool) -> str:
    return "true" if value else "false"
