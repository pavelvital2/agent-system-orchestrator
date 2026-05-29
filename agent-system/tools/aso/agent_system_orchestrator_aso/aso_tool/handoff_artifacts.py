"""Machine-readable profile-agent handoff artifact helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from . import dispatch_receipts
from . import source_boundary
from . import transition_engine


HANDOFF_TYPE = "ORCHESTRATOR_HANDOFF"
SCHEMA_VERSION = "1.0.0"
SCHEMA_RELATIVE_PATH = "agent-system/09_validators/schemas/orchestrator_handoff.schema.json"
TEMPLATE_RELATIVE_PATH = "agent-system/03_templates/orchestrator_handoff.template.json"
HANDOFF_REF_TEMPLATE = "project-runtime/handoffs/<TASK_ID>.json"
PROMPT_REF_TEMPLATE = "project-runtime/handoffs/<TASK_ID>.prompt.md"
WORKER_RESULT_REF_TEMPLATE = "project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_001.md"
AUDIT_RESULT_REF_TEMPLATE = "project-runtime/results/audit/AUDIT_RESULT_<TASK_ID>_ATTEMPT_001.md"
ARTIFACT_PACKAGE_REF_TEMPLATE = "project-runtime/artifacts/candidates/<TASK_ID>/manifest.json"
DEFAULT_LIFECYCLE_POLICY = "one_agent_one_task_delete_after_result"
NONE_REF = "NONE"
CURRENT_TASK_TOKENS = {"current_task_packet", "current_test_packet", "current_audit_packet"}
TOKEN_DOC_MAP = {
    "agent_result_template": "agent-system/03_templates/AGENT_RESULT_TEMPLATE.md",
    "test_result_template": "agent-system/03_templates/AGENT_RESULT_TEMPLATE.md",
    "audit_result_template": "agent-system/03_templates/AGENT_RESULT_TEMPLATE.md",
    "artifact_contract_summary": "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json",
    "audit_rules_summary": "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json",
}
TASK_ID_RE = re.compile(r"^[A-Za-z0-9_:-]+$")


@dataclass(frozen=True)
class HandoffValidationResult:
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


def handoff_ref(task_id: str) -> str:
    return HANDOFF_REF_TEMPLATE.replace("<TASK_ID>", task_id or NONE_REF)


def prompt_ref(task_id: str) -> str:
    return PROMPT_REF_TEMPLATE.replace("<TASK_ID>", task_id or NONE_REF)


def expected_result_path(task_id: str, role: str) -> str:
    template = AUDIT_RESULT_REF_TEMPLATE if role == "auditor" else WORKER_RESULT_REF_TEMPLATE
    return template.replace("<TASK_ID>", task_id or NONE_REF)


def expected_artifact_package_path(task_id: str) -> str:
    return ARTIFACT_PACKAGE_REF_TEMPLATE.replace("<TASK_ID>", task_id or NONE_REF)


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _normalize_path(value: object) -> str:
    text = _text(value).strip("`'\"")
    if not text or text.upper() == NONE_REF:
        return NONE_REF
    text = text.split("#", 1)[0].strip().replace("\\", "/")
    has_trailing_slash = text.endswith("/")
    parts = [part for part in text.split("/") if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        return text
    normalized = "/".join(parts)
    if has_trailing_slash:
        normalized = f"{normalized}/"
    return normalized


def _doc_ref(path: str, why_needed: str, *, source: str = "routine") -> dict[str, object] | None:
    normalized = _normalize_path(path)
    if normalized == NONE_REF:
        return None
    return {
        "path": normalized,
        "sections": ["Bounded task-relevant sections"],
        "why_needed": why_needed,
        "source": source,
    }


def _dedupe_doc_refs(refs: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    result: list[dict[str, object]] = []
    for ref in refs:
        path = str(ref.get("path", ""))
        if not path or path in seen:
            continue
        seen.add(path)
        result.append(ref)
    return result


def _role_required_doc_refs(
    contract: Mapping[str, Any],
    target_role: str,
    task_packet: str,
) -> tuple[list[dict[str, object]], list[str]]:
    docs_by_role = _mapping(contract.get("required_docs_by_role"))
    tokens = _string_list(docs_by_role.get(target_role))
    refs: list[dict[str, object]] = []
    for token in tokens:
        if token in CURRENT_TASK_TOKENS:
            ref = _doc_ref(task_packet, f"Current {token} required by target role {target_role}.")
        else:
            path = TOKEN_DOC_MAP.get(token, token if "/" in token else "")
            ref = _doc_ref(path, f"Target role {target_role} requires {token}.")
        if ref is not None:
            refs.append(ref)
    return _dedupe_doc_refs(refs), tokens


def _runtime_contract_ref(contract: Mapping[str, Any]) -> dict[str, object] | None:
    handoff_context = _mapping(contract.get("handoff_context_builder_contract"))
    ref = _doc_ref(
        transition_engine.CONTRACT_RELATIVE_PATH.as_posix(),
        "Compact operational transition and routine handoff contract.",
    )
    if ref is not None:
        ref["sections"] = _string_list(handoff_context.get("runtime_contract_required_sections"))
    return ref


def _target_role_doc_ref(contract: Mapping[str, Any], target_role: str) -> dict[str, object] | None:
    handoff_context = _mapping(contract.get("handoff_context_builder_contract"))
    role_doc_map = _mapping(handoff_context.get("target_role_doc_map"))
    ref = _doc_ref(_text(role_doc_map.get(target_role)), f"Specific role instructions for target role {target_role}.")
    if ref is not None:
        ref["sections"] = ["Role rules for this target role"]
    return ref


def _required_doc_refs(
    contract: Mapping[str, Any],
    target_role: str,
    task_packet: str,
) -> tuple[list[dict[str, object]], list[str]]:
    refs: list[dict[str, object]] = []
    runtime_ref = _runtime_contract_ref(contract)
    if runtime_ref is not None:
        refs.append(runtime_ref)
    task_ref = _doc_ref(task_packet, "Current task packet for this bounded handoff.")
    if task_ref is not None:
        refs.append(task_ref)
    role_ref = _target_role_doc_ref(contract, target_role)
    if role_ref is not None:
        refs.append(role_ref)
    role_required_refs, role_required_tokens = _role_required_doc_refs(contract, target_role, task_packet)
    refs.extend(role_required_refs)
    return _dedupe_doc_refs(refs), role_required_tokens


def _handoff_context_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(contract.get("handoff_context_builder_contract"))


def _forbidden_docs(contract: Mapping[str, Any]) -> list[str]:
    return _string_list(_handoff_context_contract(contract).get("routine_handoff_excludes"))


def _forbidden_doc_tokens(contract: Mapping[str, Any]) -> list[str]:
    routine_policy = _mapping(contract.get("routine_context_policy"))
    return _string_list(routine_policy.get("orchestrator_must_not_read_routinely"))


def _packet_field(packet_fields: Mapping[str, str], key: str, default: str) -> str:
    value = _text(packet_fields.get(key))
    return default if not value or value.upper() == NONE_REF else value


def _is_broad_reference(path: str, forbidden_docs: list[str]) -> bool:
    clean_path = path.rstrip("/")
    for forbidden in forbidden_docs:
        clean_forbidden = forbidden.rstrip("/")
        if forbidden.endswith("/"):
            if clean_path == clean_forbidden:
                return True
            if clean_path in {f"{clean_forbidden}/*", f"{clean_forbidden}/**"}:
                return True
            continue
        if clean_path == clean_forbidden:
            return True
    return False


def build_handoff_artifact(
    *,
    contract: Mapping[str, Any],
    task_id: str,
    role: str,
    resolved_reasoning_level: str,
    task_packet: str,
    packet_fields: Mapping[str, str] | None = None,
    context_mode: str = "routine",
    current_event: str = NONE_REF,
    current_result: str = NONE_REF,
    current_artifact: str = NONE_REF,
    reference_docs: list[str] | None = None,
    reference_reason: str = "",
    validator_required: bool = False,
) -> dict[str, object]:
    """Build the deterministic handoff JSON payload for one external profile-agent run."""

    packet_fields = packet_fields or {}
    required_docs, required_doc_tokens = _required_doc_refs(contract, role, task_packet)
    forbidden_docs = _forbidden_docs(contract)
    handoff_context = _handoff_context_contract(contract)
    context_mode = context_mode or _text(handoff_context.get("normal_context_mode")) or "routine"
    refs = [_normalize_path(path) for path in (reference_docs or [])]
    reference_doc_refs: list[dict[str, object]] = []
    for path in refs:
        ref = _doc_ref(
            path,
            reference_reason or ("Required by validator." if validator_required else "Explicit reference."),
            source="validator_required" if validator_required else context_mode,
        )
        if ref is not None:
            ref["authorization"] = "validator_required" if validator_required else "explicit_reference_reason"
            reference_doc_refs.append(ref)

    result_path = _packet_field(packet_fields, "RESULT_PATH", expected_result_path(task_id, role))
    artifact_package_path = _packet_field(
        packet_fields,
        "EXPECTED_ARTIFACT_PACKAGE",
        expected_artifact_package_path(task_id),
    )
    lifecycle_policy = _packet_field(packet_fields, "AGENT_LIFECYCLE_POLICY", DEFAULT_LIFECYCLE_POLICY)
    handoff_path = handoff_ref(task_id)
    prompt_path = prompt_ref(task_id)
    allowed_sources = source_boundary.build_allowed_sources(
        contract=contract,
        task_id=task_id,
        role=role,
        task_packet=task_packet,
        required_docs=required_docs,
        reference_docs=reference_doc_refs,
        current_result=current_result,
        current_artifact=current_artifact,
    )

    return {
        "handoff_type": HANDOFF_TYPE,
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id or NONE_REF,
        "role": role or NONE_REF,
        "resolved_reasoning_level": resolved_reasoning_level or NONE_REF,
        "context_mode": context_mode,
        "handoff_ref": handoff_path,
        "prompt_ref": prompt_path,
        "allowed_sources_ref": allowed_sources["allowed_sources_ref"],
        "allowed_sources": allowed_sources,
        "required_docs": required_docs,
        "required_doc_tokens": required_doc_tokens,
        "forbidden_docs": forbidden_docs,
        "forbidden_doc_tokens": _forbidden_doc_tokens(contract),
        "reference_docs": _dedupe_doc_refs(reference_doc_refs),
        "reference_doc_inclusion_rule": _text(handoff_context.get("reference_doc_inclusion_rule")),
        "routine_context_includes": _string_list(handoff_context.get("routine_handoff_includes")),
        "governance_corpus_included": bool(reference_doc_refs and context_mode != "routine"),
        "current_state_refs": [
            "project-runtime/state/*.json",
            "project-runtime/agents/instances.jsonl",
        ],
        "current_event_result_artifact_refs": {
            "event": _normalize_path(current_event),
            "result_or_audit_result": _normalize_path(current_result),
            "artifact_manifest_or_receipt": _normalize_path(current_artifact),
        },
        "expected_result_path": result_path,
        "expected_artifact_package_path": artifact_package_path,
        "lifecycle_policy": lifecycle_policy,
        "expected_receipt_ref_template": dispatch_receipts.RECEIPT_REF_TEMPLATE,
        "external_runner_contract": {
            "runner": dispatch_receipts.RUNNER_EXTERNAL_CODEX_CLI,
            "runner_semantics": dispatch_receipts.RUNNER_SEMANTICS,
            "external_runner_command_template": dispatch_receipts.EXTERNAL_RUNNER_COMMAND_TEMPLATE,
            "receipt_writer_command_template": dispatch_receipts.WRITER_COMMAND_TEMPLATE,
            "live_dispatch_performed_by_aso": False,
        },
        "result_contract_ref": "agent-system/03_templates/AGENT_RESULT_TEMPLATE.md",
        "allowed_sources_schema_ref": source_boundary.SCHEMA_RELATIVE_PATH,
        "artifact_package_manifest": "manifest.json",
        "lifecycle_policy_enforcement": {
            "reuse_allowed": False,
            "agent_termination_required": True,
        },
    }


def validate_handoff_artifact(payload: Mapping[str, Any]) -> HandoffValidationResult:
    """Validate the parts of the handoff contract enforced without jsonschema."""

    errors: list[str] = []
    required = (
        "handoff_type",
        "schema_version",
        "task_id",
        "role",
        "resolved_reasoning_level",
        "context_mode",
        "handoff_ref",
        "prompt_ref",
        "required_docs",
        "forbidden_docs",
        "reference_docs",
        "allowed_sources_ref",
        "allowed_sources",
        "expected_result_path",
        "expected_artifact_package_path",
        "lifecycle_policy",
        "external_runner_contract",
        "lifecycle_policy_enforcement",
    )
    for field in required:
        if field not in payload:
            errors.append(f"{field} is required")

    if payload.get("handoff_type") != HANDOFF_TYPE:
        errors.append(f"handoff_type must be {HANDOFF_TYPE}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    task_id = _text(payload.get("task_id"))
    if not task_id or task_id == NONE_REF or not TASK_ID_RE.match(task_id):
        errors.append("task_id must be a concrete task id using letters, numbers, underscore, dash, or colon")
    if _text(payload.get("role")) not in dispatch_receipts.PROFILE_ROLES:
        errors.append("role must be a runtime-contract dispatchable profile role")
    if _text(payload.get("resolved_reasoning_level")) not in dispatch_receipts.LEVEL_RANK:
        errors.append("resolved_reasoning_level must be one of low, medium, high, xhigh")

    context_mode = _text(payload.get("context_mode"))
    if context_mode not in {"routine", "debug", "explain", "violation_recovery"}:
        errors.append("context_mode must be routine, debug, explain, or violation_recovery")

    handoff = _text(payload.get("handoff_ref"))
    prompt = _text(payload.get("prompt_ref"))
    if task_id and handoff != handoff_ref(task_id):
        errors.append(f"handoff_ref must be {handoff_ref(task_id)}")
    if task_id and prompt != prompt_ref(task_id):
        errors.append(f"prompt_ref must be {prompt_ref(task_id)}")
    expected_allowed_sources_ref = source_boundary.allowed_sources_ref(task_id)
    if task_id and _text(payload.get("allowed_sources_ref")) != expected_allowed_sources_ref:
        errors.append(f"allowed_sources_ref must be {expected_allowed_sources_ref}")
    allowed_sources_payload = _mapping(payload.get("allowed_sources"))
    allowed_sources_validation = source_boundary.validate_allowed_sources(allowed_sources_payload)
    if not allowed_sources_validation.passed:
        errors.extend(f"allowed_sources.{error}" for error in allowed_sources_validation.errors)

    required_docs = payload.get("required_docs")
    if not isinstance(required_docs, list) or not required_docs:
        errors.append("required_docs must be a non-empty list")
        required_docs = []
    forbidden_docs = _string_list(payload.get("forbidden_docs"))
    reference_docs = payload.get("reference_docs")
    if not isinstance(reference_docs, list):
        errors.append("reference_docs must be a list")
        reference_docs = []

    all_doc_refs: list[object] = [*required_docs, *reference_docs] if isinstance(required_docs, list) else list(reference_docs)
    for index, doc in enumerate(all_doc_refs):
        if not isinstance(doc, Mapping):
            errors.append(f"doc reference {index} must be an object")
            continue
        path = _normalize_path(doc.get("path"))
        if path == NONE_REF:
            errors.append(f"doc reference {index} must include a concrete path")
        if context_mode == "routine" and _is_broad_reference(path, forbidden_docs):
            errors.append(f"routine handoff must not include broad governance corpus path: {path}")

    if context_mode == "routine":
        if reference_docs:
            errors.append("routine handoff must not include reference_docs")
        if payload.get("governance_corpus_included") is not False:
            errors.append("routine handoff must set governance_corpus_included to false")
    elif reference_docs:
        for index, doc in enumerate(reference_docs):
            if not isinstance(doc, Mapping) or not _text(doc.get("authorization")):
                errors.append(f"reference_docs[{index}] must record authorization outside routine mode")

    result_path = _text(payload.get("expected_result_path"))
    if not result_path.startswith("project-runtime/results/"):
        errors.append("expected_result_path must be under project-runtime/results/")
    artifact_path = _text(payload.get("expected_artifact_package_path"))
    if not (
        artifact_path.startswith("project-runtime/artifacts/candidates/")
        and artifact_path.endswith("/manifest.json")
    ):
        errors.append("expected_artifact_package_path must be a candidate manifest.json path")
    if not _text(payload.get("lifecycle_policy")):
        errors.append("lifecycle_policy must be non-empty")

    runner_contract = _mapping(payload.get("external_runner_contract"))
    if runner_contract.get("runner") != dispatch_receipts.RUNNER_EXTERNAL_CODEX_CLI:
        errors.append("external_runner_contract.runner must be external_codex_cli")
    if runner_contract.get("external_runner_command_template") != dispatch_receipts.EXTERNAL_RUNNER_COMMAND_TEMPLATE:
        errors.append("external_runner_contract.external_runner_command_template must match the dispatch contract")
    if runner_contract.get("receipt_writer_command_template") != dispatch_receipts.WRITER_COMMAND_TEMPLATE:
        errors.append("external_runner_contract.receipt_writer_command_template must match the dispatch contract")
    if runner_contract.get("live_dispatch_performed_by_aso") is not False:
        errors.append("external_runner_contract.live_dispatch_performed_by_aso must be false")

    lifecycle = _mapping(payload.get("lifecycle_policy_enforcement"))
    if lifecycle.get("reuse_allowed") is not False:
        errors.append("lifecycle_policy_enforcement.reuse_allowed must be false")
    if lifecycle.get("agent_termination_required") is not True:
        errors.append("lifecycle_policy_enforcement.agent_termination_required must be true")

    return HandoffValidationResult(tuple(errors))


def handoff_plan(
    *,
    contract: Mapping[str, Any],
    task_id: str,
    role: str,
    resolved_reasoning_level: str,
    task_packet: str,
    packet_fields: Mapping[str, str] | None = None,
    dispatchable: bool,
) -> dict[str, object]:
    """Return the planner-facing handoff proposal section."""

    payload = build_handoff_artifact(
        contract=contract,
        task_id=task_id,
        role=role,
        resolved_reasoning_level=resolved_reasoning_level,
        task_packet=task_packet,
        packet_fields=packet_fields,
    )
    validation = validate_handoff_artifact(payload) if dispatchable else HandoffValidationResult(())
    return {
        "required": dispatchable,
        "machine_readable": True,
        "schema_ref": SCHEMA_RELATIVE_PATH,
        "template_ref": TEMPLATE_RELATIVE_PATH,
        "handoff_ref_template": HANDOFF_REF_TEMPLATE,
        "prompt_ref_template": PROMPT_REF_TEMPLATE,
        "handoff_ref": payload["handoff_ref"],
        "prompt_ref": payload["prompt_ref"],
        "allowed_sources_ref": payload["allowed_sources_ref"],
        "expected_result_path": payload["expected_result_path"],
        "expected_artifact_package_path": payload["expected_artifact_package_path"],
        "lifecycle_policy": payload["lifecycle_policy"],
        "payload": payload if dispatchable else {},
        "validation": {
            "status": ("passed" if validation.passed else "failed") if dispatchable else "not_required",
            "errors": list(validation.errors),
        },
        "live_dispatch_performed_by_aso": False,
    }
