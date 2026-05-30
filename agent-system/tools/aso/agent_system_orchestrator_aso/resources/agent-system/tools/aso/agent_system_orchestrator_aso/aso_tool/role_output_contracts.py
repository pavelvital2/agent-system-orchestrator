"""Compact role-output contract summaries derived from the runtime contract."""

from __future__ import annotations

from typing import Any, Mapping

from . import result_parser


RESULT_TEMPLATE_REF = "agent-system/03_templates/AGENT_RESULT_TEMPLATE.md"
WORKER_RESULT_REF_TEMPLATE = "project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_001.md"
AUDIT_RESULT_REF_TEMPLATE = "project-runtime/results/audit/AUDIT_RESULT_<TASK_ID>_ATTEMPT_001.md"
ARTIFACT_PACKAGE_REF_TEMPLATE = "project-runtime/artifacts/candidates/<TASK_ID>/manifest.json"
NONE_REF = "NONE"

DEFAULT_SELF_VALIDATION = {
    "required_before_result": True,
    "evidence_fields": ["COMMANDS_RUN", "TESTS_RUN", "EVIDENCE", "SCOPE_VERIFICATION"],
    "required_evidence_labels": [
        "VALIDATION_STATUS",
        "VALIDATION_COMMAND",
        "RESULT_SCHEMA_STATUS",
        "ARTIFACT_MANIFEST_SCHEMA_STATUS",
        "VALIDATION_NOT_RUN_REASON",
    ],
    "not_run_requires_reason": True,
    "pass_status_rule": (
        "STATUS: pass is forbidden when any required RESULT, artifact manifest, "
        "main document, structured artifact, audit result, or correction result schema validation fails."
    ),
}

DEFAULT_FIRST_PASS_ACCEPTANCE_METRICS = {
    "stage1_final_report_required": True,
    "definition": "First-pass acceptance means attempt 1 reached accepted RESULT/audit routing without schema-only correction.",
    "fields": [
        "task_id",
        "role",
        "attempt_no",
        "result_schema_valid_on_first_parse",
        "required_output_schemas_valid_on_first_parse",
        "validation_evidence_present",
        "audit_passed_first_attempt",
        "schema_only_correction_count",
        "first_pass_accepted",
    ],
}

DEFAULT_SKELETONS: dict[str, dict[str, object]] = {
    "result_file": {
        "format": "markdown",
        "marker": "RESULT:",
        "path_template": WORKER_RESULT_REF_TEMPLATE,
        "required_fields": list(result_parser.REQUIRED_RESULT_FIELDS),
        "required_constants": {
            "REUSE_ALLOWED": "false",
            "AGENT_TERMINATION_REQUIRED": "true",
        },
        "validation_evidence_minimum": [
            "VALIDATION_STATUS: passed | not_run",
            "VALIDATION_COMMAND: <command and result> | VALIDATION_NOT_RUN_REASON: <reason>",
        ],
    },
    "audit_result_file": {
        "format": "markdown",
        "marker": "AUDIT_RESULT:",
        "path_template": AUDIT_RESULT_REF_TEMPLATE,
        "required_fields": list(result_parser.REQUIRED_RESULT_FIELDS),
        "required_constants": {
            "ROLE": "auditor",
            "REUSE_ALLOWED": "false",
            "AGENT_TERMINATION_REQUIRED": "true",
        },
        "validation_evidence_minimum": [
            "SOURCE_RESULT_REF: project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_<N>.md",
            "VALIDATION_STATUS: passed | not_run",
            "VALIDATION_COMMAND: <command and result> | VALIDATION_NOT_RUN_REASON: <reason>",
        ],
        "mandatory_audit_labels": [
            "CHANGED_FILES_SCOPE_STATUS",
            "TASK_PACKET_SCHEMA_STATUS",
            "REPOSITORY_IDENTITY_STATUS",
            "FORBIDDEN_PATH_STATUS",
            "RUNTIME_MUTATION_STATUS",
            "EVIDENCE_STATUS",
            "SECRET_EXPOSURE_STATUS",
            "REASONING_LEVEL_COMPLIANCE",
            "VALIDATED_TASK_PACKETS",
        ],
    },
    "correction_result": {
        "format": "markdown",
        "marker": "RESULT:",
        "path_template": WORKER_RESULT_REF_TEMPLATE,
        "required_fields": list(result_parser.REQUIRED_RESULT_FIELDS),
        "required_evidence_labels": [
            "CORRECTION_OF",
            "RESOLVES_AUDIT_REF",
            "VALIDATION_STATUS",
        ],
    },
    "artifact_manifest": {
        "format": "json",
        "path_template": ARTIFACT_PACKAGE_REF_TEMPLATE,
        "required_fields": [
            "artifact_package_schema_version",
            "artifact_type",
            "artifact_id",
            "task_id",
            "role",
            "attempt_no",
            "status",
            "main_document",
            "structured_artifacts",
            "evidence_refs",
            "created_at",
            "producer",
        ],
        "minimal_json": {
            "artifact_package_schema_version": "1.1.0",
            "artifact_type": "RESULT",
            "artifact_id": "RESULT_<TASK_ID>_ATTEMPT_001",
            "task_id": "<TASK_ID>",
            "role": "<ROLE>",
            "attempt_no": 1,
            "status": "pass",
            "main_document": "RESULT.md",
            "structured_artifacts": ["structured/result_package.json"],
            "evidence_refs": "NONE",
            "created_at": "<RFC3339_UTC>",
            "producer": {
                "agent_instance_id": "<AGENT_INSTANCE_ID>",
                "role": "<ROLE>",
            },
        },
    },
    "main_document": {
        "format": "markdown",
        "path_template": "RESULT.md",
        "required_sections": ["RESULT:"],
    },
    "structured_artifact": {
        "format": "json",
        "path_template": "structured/result_package.json",
        "required_fields": [
            "schema_version",
            "package_version",
            "governance_ruleset_version",
            "runtime_schema_version",
            "artifact_package_schema_version",
            "artifact_id",
            "artifact_type",
            "created_at",
            "created_by",
            "source_refs",
            "content",
            "validation",
        ],
    },
}


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _legacy_result_kind(target_role: str, required_doc_tokens: list[str]) -> str:
    if target_role == "auditor" or "audit_result_template" in required_doc_tokens:
        return "audit_result"
    if "test_result_template" in required_doc_tokens:
        return "test_result"
    return "worker_result"


def _default_role_contract(target_role: str, required_doc_tokens: list[str]) -> dict[str, object]:
    result_kind = _legacy_result_kind(target_role, required_doc_tokens)
    expected_path = AUDIT_RESULT_REF_TEMPLATE if result_kind == "audit_result" else WORKER_RESULT_REF_TEMPLATE
    required = ["audit_result_file"] if result_kind == "audit_result" else ["result_file"]
    conditional = ["artifact_manifest", "main_document", "structured_artifact"]
    if result_kind != "audit_result":
        conditional.append("correction_result")
    return {
        "result_kind": result_kind,
        "expected_result_path_template": expected_path,
        "required_outputs": required,
        "conditional_outputs": conditional,
        "required_skeletons": required,
        "conditional_skeletons": conditional,
        "output_paths": {
            "result": expected_path,
            "candidate_artifact_manifest": ARTIFACT_PACKAGE_REF_TEMPLATE,
        },
    }


def _role_contract(
    role_output_contracts: Mapping[str, Any],
    target_role: str,
    required_doc_tokens: list[str],
) -> dict[str, object]:
    roles = _mapping(role_output_contracts.get("roles"))
    configured = _mapping(roles.get(target_role))
    fallback = _default_role_contract(target_role, required_doc_tokens)
    return {**fallback, **configured}


def _selected_skeletons(
    role_output_contracts: Mapping[str, Any],
    role_contract: Mapping[str, object],
) -> dict[str, object]:
    catalog = _mapping(role_output_contracts.get("minimal_skeletons"))
    required = _string_list(role_contract.get("required_skeletons"))
    conditional = _string_list(role_contract.get("conditional_skeletons"))
    skeletons: dict[str, object] = {}
    for name in _dedupe(required + conditional):
        skeleton = _mapping(catalog.get(name)) or DEFAULT_SKELETONS.get(name, {})
        if skeleton:
            skeletons[name] = skeleton
    return skeletons


def result_contract_summary(
    contract: Mapping[str, Any],
    target_role: str,
    required_doc_tokens: list[str],
) -> dict[str, object]:
    """Build the compact role-specific RESULT contract for routine handoffs."""

    role_output_contracts = _mapping(contract.get("role_output_contracts"))
    role_contract = _role_contract(role_output_contracts, target_role, required_doc_tokens)
    result_kind = _text(role_contract.get("result_kind")) or _legacy_result_kind(target_role, required_doc_tokens)
    expected_path = _text(role_contract.get("expected_result_path_template"))
    if not expected_path:
        expected_path = AUDIT_RESULT_REF_TEMPLATE if result_kind == "audit_result" else WORKER_RESULT_REF_TEMPLATE

    common_fields = _string_list(role_output_contracts.get("common_result_required_fields"))
    if not common_fields:
        common_fields = list(result_parser.REQUIRED_RESULT_FIELDS)
    common_constants = _mapping(role_output_contracts.get("common_result_required_constants")) or {
        "REUSE_ALLOWED": "false",
        "AGENT_TERMINATION_REQUIRED": "true",
    }
    self_validation = _mapping(role_output_contracts.get("self_validation")) or dict(DEFAULT_SELF_VALIDATION)
    first_pass_metrics = (
        _mapping(role_output_contracts.get("first_pass_acceptance_metrics"))
        or dict(DEFAULT_FIRST_PASS_ACCEPTANCE_METRICS)
    )

    return {
        "contract_version": _text(role_output_contracts.get("contract_version")) or "fallback",
        "role": target_role or NONE_REF,
        "result_kind": result_kind,
        "template_ref": RESULT_TEMPLATE_REF,
        "summary": (
            "Formal RESULT fields, role-specific skeletons, output paths, and "
            "self-validation evidence are derived from role_output_contracts."
        ),
        "expected_result_path_template": expected_path,
        "required_result_fields": common_fields,
        "required_result_constants": common_constants,
        "result_acceptance": {
            "mode_field": "RESULT_ACCEPTANCE_MODE",
            "artifact_required_field": "ARTIFACT_PACKAGE_REQUIRED",
            "valid_modes": sorted(result_parser.RESULT_ACCEPTANCE_MODES),
        },
        "required_outputs": _string_list(role_contract.get("required_outputs")),
        "conditional_outputs": _string_list(role_contract.get("conditional_outputs")),
        "output_paths": _mapping(role_contract.get("output_paths")),
        "minimal_skeletons": _selected_skeletons(role_output_contracts, role_contract),
        "self_validation": self_validation,
        "pass_status_rule": _text(self_validation.get("pass_status_rule")),
        "first_pass_acceptance_metrics": first_pass_metrics,
    }
