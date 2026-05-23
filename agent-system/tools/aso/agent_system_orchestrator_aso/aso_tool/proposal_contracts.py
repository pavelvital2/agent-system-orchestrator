"""P3 proposal artifact and apply receipt stdlib validation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from . import runtime_schema_contracts


PROPOSAL_SCHEMA_RELATIVE_PATH = "agent-system/09_validators/schemas/proposal_artifact.schema.json"
APPLY_RECEIPT_SCHEMA_RELATIVE_PATH = "agent-system/09_validators/schemas/apply_receipt.schema.json"
PROPOSAL_TEMPLATE_RELATIVE_PATH = "agent-system/03_templates/proposal_artifact.template.json"
APPLY_RECEIPT_TEMPLATE_RELATIVE_PATH = "agent-system/03_templates/apply_receipt.template.json"

CONTRACT_SCHEMA_VERSION = "1.0.0"
PACKAGE_VERSION = runtime_schema_contracts.ACTIVE_PACKAGE_VERSION
RUNTIME_SCHEMA_VERSION = runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION

PROPOSAL_TYPES = ("next_task", "transition", "checkpoint")
PROPOSAL_SAFETY_CLASSES = ("read_only_plan", "runtime_state_only", "checkpoint_proposal_only")
PROPOSAL_STATUSES = ("proposed", "blocked", "applied", "rejected", "superseded")
OPERATION_TYPES = ("sidecar_replace", "sidecar_patch", "receipt_write", "report_write")
RECEIPT_OUTCOMES = ("applied", "blocked", "failed")
APPLIED_OPERATION_STATUSES = ("applied", "skipped", "blocked", "failed")

REQUIRED_PROPOSAL_FIELDS = (
    "proposal_id",
    "proposal_type",
    "schema_version",
    "package_version",
    "runtime_schema_version",
    "created_at",
    "created_by",
    "target_root",
    "target_workspace_identity",
    "base_state_hashes",
    "required_validators",
    "operations",
    "safety_class",
    "status",
    "human_summary",
)
REQUIRED_RECEIPT_FIELDS = (
    "receipt_id",
    "proposal_id",
    "proposal_type",
    "schema_version",
    "package_version",
    "runtime_schema_version",
    "applied_at",
    "applied_by",
    "target_root",
    "validators_passed",
    "base_state_hashes",
    "result_state_hashes",
    "applied_operations",
    "outcome",
)

_PROPOSAL_ID_RE = re.compile(r"^PROPOSAL-[A-Za-z0-9_.:-]+$")
_RECEIPT_ID_RE = re.compile(r"^RECEIPT-[A-Za-z0-9_.:-]+$")
_HASH_RE = re.compile(r"^sha256:[a-f0-9]{64}$")


@dataclass(frozen=True)
class ContractValidationResult:
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


def proposal_contract_summary() -> dict[str, object]:
    """Return the active proposal/apply contract constants."""

    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "package_version": PACKAGE_VERSION,
        "runtime_schema_version": RUNTIME_SCHEMA_VERSION,
        "proposal_schema_path": PROPOSAL_SCHEMA_RELATIVE_PATH,
        "apply_receipt_schema_path": APPLY_RECEIPT_SCHEMA_RELATIVE_PATH,
        "proposal_template_path": PROPOSAL_TEMPLATE_RELATIVE_PATH,
        "apply_receipt_template_path": APPLY_RECEIPT_TEMPLATE_RELATIVE_PATH,
        "proposal_types": list(PROPOSAL_TYPES),
        "proposal_safety_classes": list(PROPOSAL_SAFETY_CLASSES),
        "receipt_outcomes": list(RECEIPT_OUTCOMES),
    }


def validate_proposal_artifact(payload: dict[str, Any]) -> ContractValidationResult:
    """Validate required P3 proposal contract fields without external dependencies."""

    errors: list[str] = []
    _validate_required_fields(payload, REQUIRED_PROPOSAL_FIELDS, errors)
    _validate_const(payload, "schema_version", CONTRACT_SCHEMA_VERSION, errors)
    _validate_const(payload, "package_version", PACKAGE_VERSION, errors)
    _validate_const(payload, "runtime_schema_version", RUNTIME_SCHEMA_VERSION, errors)
    _validate_pattern(payload, "proposal_id", _PROPOSAL_ID_RE, errors)
    _validate_enum(payload, "proposal_type", PROPOSAL_TYPES, errors)
    _validate_enum(payload, "safety_class", PROPOSAL_SAFETY_CLASSES, errors)
    _validate_enum(payload, "status", PROPOSAL_STATUSES, errors)

    for field in ("created_at", "created_by", "target_root", "human_summary"):
        _validate_non_empty_string(payload, field, errors)

    _validate_object(payload, "target_workspace_identity", errors)
    _validate_hash_map(payload, "base_state_hashes", errors)
    _validate_string_list(payload, "required_validators", errors)
    _validate_operations(payload.get("operations"), "operations", errors, applied=False)

    if payload.get("proposal_type") == "checkpoint" and payload.get("safety_class") != "checkpoint_proposal_only":
        errors.append("checkpoint proposal_type requires safety_class checkpoint_proposal_only")

    return ContractValidationResult(tuple(errors))


def validate_apply_receipt(payload: dict[str, Any]) -> ContractValidationResult:
    """Validate required P3 apply receipt contract fields without external dependencies."""

    errors: list[str] = []
    _validate_required_fields(payload, REQUIRED_RECEIPT_FIELDS, errors)
    _validate_const(payload, "schema_version", CONTRACT_SCHEMA_VERSION, errors)
    _validate_const(payload, "package_version", PACKAGE_VERSION, errors)
    _validate_const(payload, "runtime_schema_version", RUNTIME_SCHEMA_VERSION, errors)
    _validate_pattern(payload, "receipt_id", _RECEIPT_ID_RE, errors)
    _validate_pattern(payload, "proposal_id", _PROPOSAL_ID_RE, errors)
    _validate_enum(payload, "proposal_type", PROPOSAL_TYPES, errors)
    _validate_enum(payload, "outcome", RECEIPT_OUTCOMES, errors)

    for field in ("applied_at", "applied_by", "target_root"):
        _validate_non_empty_string(payload, field, errors)

    _validate_string_list(payload, "validators_passed", errors)
    _validate_hash_map(payload, "base_state_hashes", errors)
    _validate_hash_map(payload, "result_state_hashes", errors)
    _validate_operations(payload.get("applied_operations"), "applied_operations", errors, applied=True)

    return ContractValidationResult(tuple(errors))


def _validate_required_fields(payload: dict[str, Any], required: tuple[str, ...], errors: list[str]) -> None:
    missing = [field for field in required if field not in payload]
    for field in missing:
        errors.append(f"{field} is required")


def _validate_const(payload: dict[str, Any], field: str, expected: str, errors: list[str]) -> None:
    if field in payload and payload.get(field) != expected:
        errors.append(f"{field} must be {expected}")


def _validate_enum(payload: dict[str, Any], field: str, allowed: tuple[str, ...], errors: list[str]) -> None:
    if field in payload and payload.get(field) not in allowed:
        errors.append(f"{field} must be one of {list(allowed)}, got {payload.get(field)!r}")


def _validate_pattern(payload: dict[str, Any], field: str, pattern: re.Pattern[str], errors: list[str]) -> None:
    value = payload.get(field)
    if field in payload and (not isinstance(value, str) or not pattern.fullmatch(value)):
        errors.append(f"{field} has invalid format")


def _validate_non_empty_string(payload: dict[str, Any], field: str, errors: list[str]) -> None:
    value = payload.get(field)
    if field in payload and (not isinstance(value, str) or not value.strip()):
        errors.append(f"{field} must be a non-empty string")


def _validate_object(payload: dict[str, Any], field: str, errors: list[str]) -> None:
    if field in payload and not isinstance(payload.get(field), dict):
        errors.append(f"{field} must be an object")


def _validate_string_list(payload: dict[str, Any], field: str, errors: list[str]) -> None:
    value = payload.get(field)
    if field not in payload:
        return
    if not isinstance(value, list):
        errors.append(f"{field} must be an array")
        return
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{field}[{index}] must be a non-empty string")


def _validate_hash_map(payload: dict[str, Any], field: str, errors: list[str]) -> None:
    value = payload.get(field)
    if field not in payload:
        return
    if not isinstance(value, dict):
        errors.append(f"{field} must be an object")
        return
    for key, digest in value.items():
        if not isinstance(key, str) or not key.strip():
            errors.append(f"{field} keys must be non-empty strings")
        if not isinstance(digest, str) or not _HASH_RE.fullmatch(digest):
            errors.append(f"{field}.{key} must be a sha256 digest")


def _validate_operations(value: object, field: str, errors: list[str], *, applied: bool) -> None:
    if not isinstance(value, list):
        errors.append(f"{field} must be an array")
        return

    required = ("operation_id", "operation_type", "target", "status") if applied else (
        "operation_id",
        "operation_type",
        "target",
        "description",
    )
    for index, operation in enumerate(value):
        location = f"{field}[{index}]"
        if not isinstance(operation, dict):
            errors.append(f"{location} must be an object")
            continue
        for required_field in required:
            if required_field not in operation:
                errors.append(f"{location}.{required_field} is required")
        _validate_non_empty_string(operation, "operation_id", errors)
        _validate_non_empty_string(operation, "target", errors)
        _validate_enum(operation, "operation_type", OPERATION_TYPES, errors)
        if applied:
            _validate_enum(operation, "status", APPLIED_OPERATION_STATUSES, errors)
        else:
            _validate_non_empty_string(operation, "description", errors)
