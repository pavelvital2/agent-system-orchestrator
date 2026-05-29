"""Source-boundary severity and allowed-source contract helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


ALLOWED_SOURCES_TYPE = "ALLOWED_SOURCES"
SCHEMA_VERSION = "1.0.0"
SCHEMA_RELATIVE_PATH = "agent-system/09_validators/schemas/allowed_sources.schema.json"
TEMPLATE_RELATIVE_PATH = "agent-system/03_templates/allowed_sources.template.json"
ALLOWED_SOURCES_REF_TEMPLATE = "project-runtime/handoffs/<TASK_ID>.allowed_sources.json"
DISPATCH_RECEIPT_REF_TEMPLATE = "project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json"
NONE_REF = "NONE"

SEVERITIES = (
    "SB0_ALLOWED",
    "SB1_REPORTING_ONLY",
    "SB2_GOVERNANCE_WARNING",
    "SB3_BLOCKING",
    "SB4_INVALIDATING",
)
SEVERITY_RANK = {severity: index for index, severity in enumerate(SEVERITIES)}
NON_CORRECTION_SEVERITIES = frozenset(SEVERITIES[:3])
CORRECTION_REQUIRED_SEVERITIES = frozenset(SEVERITIES[3:])
INVALIDATING_SEVERITIES = frozenset({"SB4_INVALIDATING"})
DEFAULT_BLOCKING_SEVERITY = "SB3_BLOCKING"
DEFAULT_ALLOWED_SEVERITY = "SB0_ALLOWED"

SEVERITY_RE = re.compile(r"\bSB[0-4]_[A-Z_]+\b")
SOURCE_BOUNDARY_CHECK_RE = re.compile(
    r"(SOURCE_BOUNDARY|SOURCE_HYGIENE|PROJECT_INPUT_TRACKING|FORBIDDEN_SOURCE|FORBIDDEN_READ|ALLOWED_SOURCES)",
    flags=re.IGNORECASE,
)
NON_SOURCE_BOUNDARY_CHECK_RE = re.compile(
    r"(CHANGED_FILES|TASK_PACKET|REPOSITORY|RUNTIME_MUTATION|EVIDENCE_STATUS|SECRET|REASONING_LEVEL|ARTIFACT|LIFECYCLE|SCHEMA)",
    flags=re.IGNORECASE,
)
OWN_DELIVERY_RE = re.compile(
    r"(own[-_ ]?(handoff|prompt|dispatch|delivery)|assigned task packet|current task packet|dispatch receipt)",
    flags=re.IGNORECASE,
)
CRITICAL_SOURCE_RE = re.compile(
    r"(agent-system/09_validators/|agent-system/tools/aso/|secret|credential|private key|\\.env|unauthorized validator source)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class AllowedSourcesValidationResult:
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


def allowed_sources_ref(task_id: str) -> str:
    return ALLOWED_SOURCES_REF_TEMPLATE.replace("<TASK_ID>", _safe_ref_token(task_id or NONE_REF))


def source_boundary_contract() -> dict[str, object]:
    return {
        "schema_ref": SCHEMA_RELATIVE_PATH,
        "template_ref": TEMPLATE_RELATIVE_PATH,
        "allowed_sources_ref_template": ALLOWED_SOURCES_REF_TEMPLATE,
        "severity_tiers": severity_tiers(),
        "severity_order": list(SEVERITIES),
        "correction_required_for": sorted(CORRECTION_REQUIRED_SEVERITIES, key=SEVERITY_RANK.__getitem__),
        "fresh_agent_required_for": sorted(INVALIDATING_SEVERITIES, key=SEVERITY_RANK.__getitem__),
        "allowed_delivery_context_classes": [
            "own_handoff",
            "own_prompt",
            "own_dispatch_receipt",
            "assigned_task_packet",
            "validator_error_ref",
            "accepted_artifact",
            "explicit_project_source",
            "specific_required_doc",
        ],
        "reporting_only_classes": [
            "incidental_delivery_artifact",
        ],
        "blocking_classes": [
            "forbidden_governance_corpus",
            "unlisted_validator_source",
            "critical_unlisted_project_source",
        ],
    }


def severity_tiers() -> dict[str, dict[str, str]]:
    return {
        "SB0_ALLOWED": {
            "label": "allowed",
            "meaning": "Source is part of the assigned agent's explicit delivery context.",
            "recommended_action": "ALLOW",
            "correction_required": False,
        },
        "SB1_REPORTING_ONLY": {
            "label": "reporting_only",
            "meaning": "Harmless reporting or incidental delivery-context drift; record it, do not create correction.",
            "recommended_action": "REPORT_ONLY",
            "correction_required": False,
        },
        "SB2_GOVERNANCE_WARNING": {
            "label": "governance_warning",
            "meaning": "Non-critical unlisted read requiring governance note or future handoff cleanup.",
            "recommended_action": "WARN",
            "correction_required": False,
        },
        "SB3_BLOCKING": {
            "label": "blocking",
            "meaning": "Forbidden source could influence output; route bounded correction.",
            "recommended_action": "ROUTE_CORRECTION",
            "correction_required": True,
        },
        "SB4_INVALIDATING": {
            "label": "invalidating",
            "meaning": "Forbidden source invalidates independence; discard affected result and use a fresh agent.",
            "recommended_action": "INVALIDATE_AND_REDISPATCH_FRESH_AGENT",
            "correction_required": True,
        },
    }


def severity_interpretation() -> dict[str, object]:
    return {
        "order": list(SEVERITIES),
        "correction_task_created_only_for": sorted(CORRECTION_REQUIRED_SEVERITIES, key=SEVERITY_RANK.__getitem__),
        "no_correction_task_for": sorted(NON_CORRECTION_SEVERITIES, key=SEVERITY_RANK.__getitem__),
        "fresh_agent_required_for": sorted(INVALIDATING_SEVERITIES, key=SEVERITY_RANK.__getitem__),
        "default_for_unclassified_source_boundary_fail": DEFAULT_BLOCKING_SEVERITY,
    }


def build_allowed_sources(
    *,
    contract: Mapping[str, Any] | None,
    task_id: str,
    role: str,
    task_packet: str,
    required_docs: Iterable[Mapping[str, object]] = (),
    reference_docs: Iterable[Mapping[str, object]] = (),
    current_result: str = NONE_REF,
    current_artifact: str = NONE_REF,
    validator_error_refs: Iterable[str] = (),
    accepted_artifact_refs: Iterable[str] = (),
    allowed_project_refs: Iterable[str] = (),
    forbidden_refs: Iterable[str] = (),
) -> dict[str, object]:
    own_handoff_ref = f"project-runtime/handoffs/{_safe_ref_token(task_id or NONE_REF)}.json"
    own_prompt_ref = f"project-runtime/handoffs/{_safe_ref_token(task_id or NONE_REF)}.prompt.md"
    allowed_sources_path = allowed_sources_ref(task_id)
    required_doc_paths = [_normalize_ref(item.get("path")) for item in required_docs if isinstance(item, Mapping)]
    reference_doc_paths = [_normalize_ref(item.get("path")) for item in reference_docs if isinstance(item, Mapping)]
    validator_errors = _dedupe(_normalize_ref(ref) for ref in validator_error_refs)
    accepted_artifacts = _dedupe(
        [
            *(_normalize_ref(ref) for ref in accepted_artifact_refs),
            _normalize_ref(current_artifact),
        ]
    )
    project_refs = _dedupe(
        [
            task_packet,
            _normalize_ref(current_result),
            *_project_refs_from_doc_paths(required_doc_paths),
            *_project_refs_from_doc_paths(reference_doc_paths),
            *(_normalize_ref(ref) for ref in allowed_project_refs),
        ]
    )
    forbidden = _forbidden_refs(contract, forbidden_refs)

    allowed_entries = [
        _allowed_entry(own_handoff_ref, "own_handoff", "Own machine-readable handoff issued for this task."),
        _allowed_entry(own_prompt_ref, "own_prompt", "Own external runner prompt issued for this task."),
        _allowed_entry(
            DISPATCH_RECEIPT_REF_TEMPLATE,
            "own_dispatch_receipt",
            "Own dispatch receipt; concrete agent instance id is filled by dispatch receipt writer.",
            template=True,
        ),
        _allowed_entry(allowed_sources_path, "allowed_sources", "Allowed-source contract for this agent."),
        _allowed_entry(task_packet, "assigned_task_packet", "Assigned task packet for this bounded run."),
    ]
    for ref in required_doc_paths:
        allowed_entries.append(_allowed_entry(ref, "specific_required_doc", "Specific required handoff doc."))
    for ref in reference_doc_paths:
        allowed_entries.append(_allowed_entry(ref, "authorized_reference_doc", "Reference doc included with explicit authorization."))
    for ref in validator_errors:
        allowed_entries.append(_allowed_entry(ref, "validator_error_ref", "Specific validator error report provided as input."))
    for ref in accepted_artifacts:
        allowed_entries.append(_allowed_entry(ref, "accepted_artifact", "Accepted artifact or receipt provided as input."))
    for ref in project_refs:
        allowed_entries.append(_allowed_entry(ref, "explicit_project_source", "Explicit project source provided as input."))

    payload = {
        "allowed_sources_type": ALLOWED_SOURCES_TYPE,
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id or NONE_REF,
        "role": role or NONE_REF,
        "allowed_sources_ref": allowed_sources_path,
        "own_handoff_ref": own_handoff_ref,
        "own_prompt_ref": own_prompt_ref,
        "own_dispatch_receipt_ref_template": DISPATCH_RECEIPT_REF_TEMPLATE,
        "task_packet_ref": _normalize_ref(task_packet),
        "validator_error_refs": validator_errors,
        "accepted_artifact_refs": accepted_artifacts,
        "allowed_project_refs": project_refs,
        "allowed_refs": _dedupe_ref_entries(allowed_entries),
        "forbidden_refs": forbidden,
        "severity_tiers": severity_tiers(),
        "severity_interpretation": severity_interpretation(),
    }
    validation = validate_allowed_sources(payload)
    payload["validation"] = {"status": "passed" if validation.passed else "failed", "errors": list(validation.errors)}
    return payload


def validate_allowed_sources(payload: Mapping[str, object]) -> AllowedSourcesValidationResult:
    errors: list[str] = []
    for field in (
        "allowed_sources_type",
        "schema_version",
        "task_id",
        "role",
        "allowed_sources_ref",
        "own_handoff_ref",
        "own_prompt_ref",
        "own_dispatch_receipt_ref_template",
        "task_packet_ref",
        "allowed_refs",
        "forbidden_refs",
        "severity_tiers",
        "severity_interpretation",
    ):
        if field not in payload:
            errors.append(f"{field} is required")
    if payload.get("allowed_sources_type") != ALLOWED_SOURCES_TYPE:
        errors.append(f"allowed_sources_type must be {ALLOWED_SOURCES_TYPE}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    tiers = payload.get("severity_tiers")
    if not isinstance(tiers, Mapping):
        errors.append("severity_tiers must be an object")
    else:
        missing = [severity for severity in SEVERITIES if severity not in tiers]
        if missing:
            errors.append(f"severity_tiers missing {', '.join(missing)}")

    allowed_refs = payload.get("allowed_refs")
    if not isinstance(allowed_refs, list) or not allowed_refs:
        errors.append("allowed_refs must be a non-empty list")
        allowed_refs = []
    for index, entry in enumerate(allowed_refs):
        if not isinstance(entry, Mapping):
            errors.append(f"allowed_refs[{index}] must be an object")
            continue
        if not _normalize_ref(entry.get("ref")):
            errors.append(f"allowed_refs[{index}].ref is required")
        if entry.get("severity") != DEFAULT_ALLOWED_SEVERITY:
            errors.append(f"allowed_refs[{index}].severity must be {DEFAULT_ALLOWED_SEVERITY}")

    forbidden_refs = payload.get("forbidden_refs")
    if not isinstance(forbidden_refs, list):
        errors.append("forbidden_refs must be a list")
        forbidden_refs = []
    for index, entry in enumerate(forbidden_refs):
        if not isinstance(entry, Mapping):
            errors.append(f"forbidden_refs[{index}] must be an object")
            continue
        severity = _as_text(entry.get("severity"))
        if severity not in CORRECTION_REQUIRED_SEVERITIES:
            errors.append(f"forbidden_refs[{index}].severity must be SB3_BLOCKING or SB4_INVALIDATING")
        if not _normalize_ref(entry.get("ref")):
            errors.append(f"forbidden_refs[{index}].ref is required")

    return AllowedSourcesValidationResult(tuple(errors))


def classify_audit_result(
    *,
    failed_checks: Iterable[object] = (),
    findings: Iterable[object] = (),
    source_boundary_evidence: Iterable[object] = (),
) -> dict[str, object]:
    checks = [_as_text(item) for item in failed_checks if _as_text(item)]
    finding_items = [_as_text(item) for item in findings if _as_text(item)]
    evidence = [_as_text(item) for item in source_boundary_evidence if _as_text(item)]
    combined = "\n".join([*checks, *finding_items, *evidence])
    source_boundary_applies = bool(evidence) or any(_is_source_boundary_check(item) for item in [*checks, *finding_items])
    if not source_boundary_applies:
        return _classification("NONE", False, "NO_SOURCE_BOUNDARY_FINDING", [], applies=False)

    explicit = [match.group(0) for match in SEVERITY_RE.finditer(combined) if match.group(0) in SEVERITY_RANK]
    if explicit:
        severity = max(explicit, key=lambda item: SEVERITY_RANK[item])
        reason = "EXPLICIT_SOURCE_BOUNDARY_SEVERITY"
    elif CRITICAL_SOURCE_RE.search(combined):
        severity = DEFAULT_BLOCKING_SEVERITY
        reason = "CRITICAL_SOURCE_BOUNDARY_REF"
    elif OWN_DELIVERY_RE.search(combined):
        severity = "SB1_REPORTING_ONLY"
        reason = "OWN_DELIVERY_CONTEXT_SHOULD_NOT_ROUTE_CORRECTION"
    elif any("failed" in item.lower() or "fail" == item.lower() for item in evidence + checks):
        severity = DEFAULT_BLOCKING_SEVERITY
        reason = "UNCLASSIFIED_SOURCE_BOUNDARY_FAIL"
    elif any("passed" in item.lower() or "pass" == item.lower() for item in evidence + checks):
        severity = DEFAULT_ALLOWED_SEVERITY
        reason = "SOURCE_BOUNDARY_ALLOWED_OR_PASSED"
    elif source_boundary_applies:
        severity = DEFAULT_BLOCKING_SEVERITY
        reason = "UNCLASSIFIED_SOURCE_BOUNDARY_FINDING"
    else:
        severity = DEFAULT_ALLOWED_SEVERITY
        reason = "SOURCE_BOUNDARY_ALLOWED_OR_PASSED"
    return _classification(severity, True, reason, evidence or checks or finding_items, applies=True)


def classify_inspection_item(item: Mapping[str, object]) -> dict[str, object]:
    return classify_audit_result(
        failed_checks=_list_value(item.get("failed_checks")),
        findings=_list_value(item.get("findings")),
        source_boundary_evidence=_list_value(item.get("source_boundary_evidence")),
    )


def audit_failure_requires_correction(item: Mapping[str, object]) -> bool:
    classification = classify_inspection_item(item)
    if not classification.get("applies"):
        return True
    if classification.get("correction_required") is True:
        return True
    return bool(non_source_boundary_failed_checks(_list_value(item.get("failed_checks"))))


def nonblocking_source_boundary_failure(item: Mapping[str, object]) -> bool:
    classification = classify_inspection_item(item)
    return bool(classification.get("applies")) and not audit_failure_requires_correction(item)


def non_source_boundary_failed_checks(failed_checks: Iterable[object]) -> list[str]:
    result: list[str] = []
    for check in failed_checks:
        text = _as_text(check)
        if not text:
            continue
        if _is_source_boundary_check(text) and not NON_SOURCE_BOUNDARY_CHECK_RE.search(text):
            continue
        result.append(text)
    return result


def _classification(
    severity: str,
    source_boundary_related: bool,
    reason: str,
    evidence: Iterable[str],
    *,
    applies: bool,
) -> dict[str, object]:
    rank = SEVERITY_RANK.get(severity, -1)
    tiers = severity_tiers()
    tier = tiers.get(severity, {})
    correction_required = severity in CORRECTION_REQUIRED_SEVERITIES
    return {
        "applies": applies,
        "source_boundary_related": source_boundary_related,
        "severity": severity,
        "severity_rank": rank,
        "recommended_action": tier.get("recommended_action", "NONE"),
        "correction_required": correction_required,
        "fresh_agent_required": severity in INVALIDATING_SEVERITIES,
        "reason_code": reason,
        "evidence": list(evidence),
    }


def _forbidden_refs(contract: Mapping[str, Any] | None, explicit_forbidden_refs: Iterable[str]) -> list[dict[str, object]]:
    contract_map = contract if isinstance(contract, Mapping) else {}
    source_boundary = contract_map.get("source_boundary_contract")
    forbidden: list[str] = []
    if isinstance(source_boundary, Mapping):
        configured = source_boundary.get("default_forbidden_refs")
        if isinstance(configured, list):
            forbidden.extend(_as_text(item) for item in configured if _as_text(item))
    if not forbidden:
        handoff_context = contract_map.get("handoff_context_builder_contract")
        if isinstance(handoff_context, Mapping):
            configured = handoff_context.get("routine_handoff_excludes")
            if isinstance(configured, list):
                forbidden.extend(_as_text(item) for item in configured if _as_text(item))
    forbidden.extend(_as_text(item) for item in explicit_forbidden_refs if _as_text(item))
    entries: list[dict[str, object]] = []
    for ref in _dedupe(_normalize_ref(item) for item in forbidden):
        severity = "SB3_BLOCKING"
        if "secret" in ref.lower() or ".env" in ref.lower():
            severity = "SB4_INVALIDATING"
        entries.append(
            {
                "ref": ref,
                "source_class": "forbidden_governance_corpus",
                "severity": severity,
                "rationale": "Broad or forbidden source must not be read unless explicitly authorized as validator error evidence.",
            }
        )
    return entries


def _allowed_entry(ref: object, source_class: str, rationale: str, *, template: bool = False) -> dict[str, object]:
    entry: dict[str, object] = {
        "ref": _normalize_ref(ref),
        "source_class": source_class,
        "severity": DEFAULT_ALLOWED_SEVERITY,
        "rationale": rationale,
    }
    if template:
        entry["template"] = True
    return entry


def _dedupe_ref_entries(entries: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        ref = _normalize_ref(entry.get("ref"))
        source_class = _as_text(entry.get("source_class"))
        if not ref or ref.upper() == NONE_REF:
            continue
        key = (ref, source_class)
        if key in seen:
            continue
        seen.add(key)
        result.append({**dict(entry), "ref": ref})
    return result


def _project_refs_from_doc_paths(paths: Iterable[str]) -> list[str]:
    return [
        path
        for path in paths
        if path.startswith("project-input/")
        or path.startswith("project-runtime/")
        or path.startswith("project-archive/")
    ]


def _is_source_boundary_check(value: str) -> bool:
    return bool(SOURCE_BOUNDARY_CHECK_RE.search(value))


def _list_value(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _normalize_ref(value: object) -> str:
    text = _as_text(value).strip("`'\"")
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


def _safe_ref_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_:-]+", "-", value).strip("-") or NONE_REF


def _as_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _normalize_ref(value)
        if not text or text.upper() == NONE_REF or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
