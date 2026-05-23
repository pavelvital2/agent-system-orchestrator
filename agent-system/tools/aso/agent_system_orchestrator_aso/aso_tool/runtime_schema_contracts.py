"""Runtime state schema contract metadata and stdlib validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ACTIVE_RUNTIME_SCHEMA_VERSION = "3.1.1"
ACTIVE_PACKAGE_VERSION = "3.7.4"
ACTIVE_GOVERNANCE_RULESET_VERSION = "3.7.4"
ACTIVE_ARTIFACT_PACKAGE_SCHEMA_VERSION = "1.1.0"

STATE_ROOT = "project-runtime/state"
CONTRACT_RELATIVE_PATH = "agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json"

REQUIRED_ENVELOPE_FIELDS = (
    "schema_version",
    "sidecar_type",
    "runtime_schema_version",
    "state_revision",
    "updated_at",
    "updated_by",
    "content",
)
OPTIONAL_ENVELOPE_FIELDS = (
    "markdown_source",
    "source_hash",
    "previous_revision_hash",
    "migration_source_schema",
)

REQUIRED_SIDECARS = (
    "PROJECT_STATE",
    "TASK_REGISTRY",
    "NEXT_ACTION",
    "CURRENT_GATE",
    "WORKSPACE_IDENTITY",
    "SCHEMA_MANIFEST",
)
OPTIONAL_SIDECARS = (
    "REPOSITORY_LOCK",
    "ACCEPTED_ARTIFACTS",
    "CHECKPOINT_STATE",
)
ALL_SIDECARS = REQUIRED_SIDECARS + OPTIONAL_SIDECARS

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
ACTION_STATUSES = (
    "ready",
    "blocked",
    "completed",
    "not_applicable",
)
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

LEGACY_COMPATIBILITY = {
    "2.0.0": "compatible_migration_available",
    "3.0.0": "compatible_migration_available",
    "3.1.0": "compatible_migration_available",
    ACTIVE_RUNTIME_SCHEMA_VERSION: "current",
}


@dataclass(frozen=True)
class ContractValidationResult:
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


def compatibility_status(schema_version: object) -> str:
    """Return the governed compatibility status for a sidecar schema version."""

    if not isinstance(schema_version, str) or not schema_version.strip():
        return "malformed"
    return LEGACY_COMPATIBILITY.get(schema_version, "unsupported")


def contract_summary() -> dict[str, object]:
    """Return the active runtime schema contract summary for validator reports."""

    return {
        "runtime_schema_version": ACTIVE_RUNTIME_SCHEMA_VERSION,
        "package_version": ACTIVE_PACKAGE_VERSION,
        "governance_ruleset_version": ACTIVE_GOVERNANCE_RULESET_VERSION,
        "artifact_package_schema_version": ACTIVE_ARTIFACT_PACKAGE_SCHEMA_VERSION,
        "state_root": STATE_ROOT,
        "contract_path": CONTRACT_RELATIVE_PATH,
        "required_envelope_fields": list(REQUIRED_ENVELOPE_FIELDS),
        "optional_envelope_fields": list(OPTIONAL_ENVELOPE_FIELDS),
        "required_sidecars": list(REQUIRED_SIDECARS),
        "optional_sidecars": list(OPTIONAL_SIDECARS),
        "compatibility_statuses": list(COMPATIBILITY_STATUSES),
    }


def validate_contract_document(contract: dict[str, Any]) -> ContractValidationResult:
    """Validate the packaged contract document using only stdlib data checks."""

    errors: list[str] = []
    if contract.get("runtime_schema_version") != ACTIVE_RUNTIME_SCHEMA_VERSION:
        errors.append("runtime_schema_version must be 3.1.1")
    if contract.get("state_root") != STATE_ROOT:
        errors.append("state_root must be project-runtime/state")

    envelope = contract.get("sidecar_envelope")
    if not isinstance(envelope, dict):
        errors.append("sidecar_envelope must be an object")
    else:
        required_fields = envelope.get("required_fields")
        if required_fields != list(REQUIRED_ENVELOPE_FIELDS):
            errors.append("sidecar_envelope.required_fields do not match active contract")
        optional_fields = envelope.get("optional_fields")
        if optional_fields != list(OPTIONAL_ENVELOPE_FIELDS):
            errors.append("sidecar_envelope.optional_fields do not match active contract")

    sidecars = contract.get("sidecars")
    if not isinstance(sidecars, dict):
        errors.append("sidecars must be an object")
    else:
        missing = sorted(set(ALL_SIDECARS) - set(sidecars))
        extra = sorted(set(sidecars) - set(ALL_SIDECARS))
        if missing:
            errors.append(f"sidecars missing expected entries: {', '.join(missing)}")
        if extra:
            errors.append(f"sidecars has unknown entries: {', '.join(extra)}")
        for sidecar_type in REQUIRED_SIDECARS:
            sidecar = sidecars.get(sidecar_type)
            if isinstance(sidecar, dict) and sidecar.get("required") is not True:
                errors.append(f"{sidecar_type}.required must be true")
        for sidecar_type in OPTIONAL_SIDECARS:
            sidecar = sidecars.get(sidecar_type)
            if isinstance(sidecar, dict) and sidecar.get("required") is not False:
                errors.append(f"{sidecar_type}.required must be false")

    statuses = contract.get("allowed_statuses")
    expected_statuses = {
        "lifecycle": LIFECYCLE_STATUSES,
        "checkpoint": CHECKPOINT_STATUSES,
        "action": ACTION_STATUSES,
        "action_type": ACTION_TYPES,
        "action_semantic": ACTION_SEMANTICS,
        "compatibility": COMPATIBILITY_STATUSES,
    }
    if not isinstance(statuses, dict):
        errors.append("allowed_statuses must be an object")
    else:
        for name, expected in expected_statuses.items():
            if statuses.get(name) != list(expected):
                errors.append(f"allowed_statuses.{name} does not match active contract")

    compatibility = contract.get("migration_compatibility")
    if not isinstance(compatibility, dict):
        errors.append("migration_compatibility must be an object")
    else:
        supported = compatibility.get("supported_source_schema_versions")
        if supported != ["2.0.0", "3.0.0", "3.1.0"]:
            errors.append("migration_compatibility.supported_source_schema_versions must be ['2.0.0', '3.0.0', '3.1.0']")
        default_status = compatibility.get("default_unsupported_status")
        if default_status != "unsupported":
            errors.append("migration_compatibility.default_unsupported_status must be unsupported")

    return ContractValidationResult(tuple(errors))
