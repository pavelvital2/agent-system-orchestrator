"""Structured correction routing evidence for failed audit results."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import result_parser
from . import source_boundary


NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}
SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_.:-]+")


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _is_none(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in NONE_VALUES)


def _dedupe(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _text(value)
        if not text or text in NONE_VALUES or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _safe_id(value: str) -> str:
    clean = SAFE_ID_RE.sub("-", value.strip()).strip("-")
    return clean or "UNKNOWN"


def _workspace_ref_path(root: Path | None, ref: str) -> Path | None:
    if root is None or _is_none(ref):
        return None
    ref_path = Path(ref)
    candidate = ref_path if ref_path.is_absolute() else root / ref_path
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return None
    return candidate


def workspace_result_ref(root: Path | None, result_path: Path | str) -> str:
    path = Path(result_path)
    if root is None:
        return path.as_posix()
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _target_role_from_source_result(root: Path | None, source_result_refs: Iterable[str]) -> str:
    for ref in source_result_refs:
        path = _workspace_ref_path(root, ref)
        if path is None or not path.is_file():
            continue
        try:
            parsed = result_parser.parse_result_file(path)
        except (OSError, UnicodeError):
            continue
        role = parsed.role
        if role and role != "auditor":
            return role
    return "orchestrator"


def correction_proposal_path(source_task_id: str) -> str:
    return f"project-runtime/proposals/correction-{_safe_id(source_task_id)}.json"


def correction_task_packet_ref(source_task_id: str) -> str:
    return f"project-runtime/tasks/active/TASK_CORRECTION_{_safe_id(source_task_id)}.md"


def build_audit_fail_route(
    *,
    root: Path | None = None,
    source_audit_result_ref: str,
    source_task_id: str,
    source_result_refs: Iterable[str] = (),
    source_task_refs: Iterable[str] = (),
    failed_checks: Iterable[str] = (),
    audit_findings: Iterable[str] = (),
    target_correction_role: str = "",
    severity: str = "error",
    route_source: str = "audit_result_fail",
    diagnostic_rule_id: str = "",
    routing_issue: str = "",
    source_boundary_classification: Mapping[str, object] | None = None,
) -> dict[str, object]:
    source_result_list = _dedupe(source_result_refs)
    source_task_list = _dedupe(source_task_refs)
    requested_task_id = "" if _is_none(source_task_id) else source_task_id
    resolved_task_id = requested_task_id or (source_task_list[0] if source_task_list else "UNKNOWN")
    resolved_failed_checks = _dedupe(failed_checks) or ["AUDIT_RESULT_STATUS_FAIL"]
    resolved_target_role = target_correction_role or _target_role_from_source_result(root, source_result_list)
    proposal_path = correction_proposal_path(resolved_task_id)
    packet_ref = correction_task_packet_ref(resolved_task_id)
    context_refs = _dedupe(
        [
            source_audit_result_ref,
            *source_result_list,
            *source_task_list,
            "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json",
        ]
    )
    route = {
        "route": "CORRECTION_REQUIRED",
        "route_source": route_source or "audit_result_fail",
        "severity": severity or "error",
        "task_id": resolved_task_id,
        "source_audit_result": source_audit_result_ref or "NONE",
        "source_audit_result_ref": source_audit_result_ref or "NONE",
        "source_audit_result_status": "fail",
        "source_result_refs": source_result_list,
        "source_task_id": resolved_task_id,
        "source_task_refs": source_task_list,
        "failed_checks": resolved_failed_checks,
        "audit_findings": _dedupe(audit_findings),
        "target_role": resolved_target_role,
        "target_correction_role": resolved_target_role,
        "routing_owner_role": "orchestrator",
        "correction_task_packet_ref": packet_ref,
        "correction_task_packet_path": packet_ref,
        "correction_task_proposal_path": proposal_path,
        "correction_task_packet_or_proposal_path": packet_ref,
        "required_context_refs": context_refs,
        "required_context_references": context_refs,
        "diagnostic_rule_id": diagnostic_rule_id or "NONE",
        "routing_issue": routing_issue or "NONE",
        "checkpoint_preflight_blocked": True,
    }
    if source_boundary_classification:
        route["source_boundary_classification"] = dict(source_boundary_classification)
        route["source_boundary_severity"] = source_boundary_classification.get("severity", "NONE")
        route["fresh_agent_required"] = bool(source_boundary_classification.get("fresh_agent_required"))
    return route


def build_profile_fail_route(
    *,
    root: Path | None = None,
    source_result_ref: str,
    source_task_id: str,
    source_role: str = "",
    failed_checks: Iterable[str] = (),
    route_source: str = "profile_result_fail",
) -> dict[str, object]:
    requested_task_id = "" if _is_none(source_task_id) else source_task_id
    resolved_task_id = requested_task_id or "UNKNOWN"
    resolved_failed_checks = _dedupe(failed_checks) or ["PROFILE_RESULT_STATUS_FAIL"]
    resolved_target_role = source_role if not _is_none(source_role) else "orchestrator"
    proposal_path = correction_proposal_path(resolved_task_id)
    packet_ref = correction_task_packet_ref(resolved_task_id)
    context_refs = _dedupe(
        [
            source_result_ref,
            resolved_task_id,
            "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json",
        ]
    )
    return {
        "route": "CORRECTION_REQUIRED",
        "route_source": route_source,
        "severity": "error",
        "task_id": resolved_task_id,
        "source_result": source_result_ref or "NONE",
        "source_result_ref": source_result_ref or "NONE",
        "source_result_status": "fail",
        "source_audit_result": "NONE",
        "source_audit_result_ref": "NONE",
        "source_audit_result_status": "NONE",
        "source_result_refs": _dedupe([source_result_ref]),
        "source_task_id": resolved_task_id,
        "source_task_refs": _dedupe([resolved_task_id]),
        "failed_checks": resolved_failed_checks,
        "audit_findings": [],
        "target_role": resolved_target_role,
        "target_correction_role": resolved_target_role,
        "routing_owner_role": "orchestrator",
        "correction_task_packet_ref": packet_ref,
        "correction_task_packet_path": packet_ref,
        "correction_task_proposal_path": proposal_path,
        "correction_task_packet_or_proposal_path": packet_ref,
        "required_context_refs": context_refs,
        "required_context_references": context_refs,
        "diagnostic_rule_id": "NONE",
        "routing_issue": "NONE",
        "checkpoint_preflight_blocked": True,
    }


def from_parsed_profile_result(
    *,
    root: Path | None,
    result_path: Path | str,
    parsed: result_parser.ParsedResult,
) -> dict[str, object]:
    if parsed.result_type == "audit_result" or parsed.status not in {"fail", "blocked", "gap"}:
        return {}
    return build_profile_fail_route(
        root=root,
        source_result_ref=workspace_result_ref(root, result_path),
        source_task_id=parsed.task_id,
        source_role=parsed.role,
        failed_checks=["PROFILE_RESULT_STATUS_FAIL"],
    )


def from_parsed_audit_result(
    *,
    root: Path | None,
    result_path: Path | str,
    parsed: result_parser.ParsedResult,
) -> dict[str, object]:
    if parsed.result_type != "audit_result" or parsed.status != "fail":
        return {}
    audit = parsed.audit
    classification = source_boundary.classify_audit_result(
        failed_checks=audit.failed_checks,
        findings=audit.findings,
        source_boundary_evidence=audit.source_boundary_evidence,
    )
    if classification.get("applies") and not classification.get("correction_required"):
        if not source_boundary.non_source_boundary_failed_checks(audit.failed_checks):
            return {}
    return build_audit_fail_route(
        root=root,
        source_audit_result_ref=workspace_result_ref(root, result_path),
        source_task_id=parsed.task_id,
        source_result_refs=audit.source_result_refs,
        source_task_refs=audit.source_task_refs,
        failed_checks=audit.failed_checks,
        audit_findings=audit.findings,
        source_boundary_classification=classification if classification.get("applies") else None,
    )


def from_audit_inspection(
    root: Path,
    invalid_audit_results: object,
) -> dict[str, object]:
    if isinstance(invalid_audit_results, Mapping):
        unresolved = invalid_audit_results.get("unresolved_audit_failures")
        if isinstance(unresolved, list):
            invalid_audit_results = unresolved
    if not isinstance(invalid_audit_results, list):
        return {}
    for item in invalid_audit_results:
        if not isinstance(item, Mapping):
            continue
        if _text(item.get("status")).lower() != "fail":
            continue
        classification = source_boundary.classify_inspection_item(item)
        if classification.get("applies") and not source_boundary.audit_failure_requires_correction(item):
            continue
        routing_task_id = _text(item.get("routing_task_id"))
        if _is_none(routing_task_id):
            routing_task_id = ""
        source_task_id = ""
        for candidate in (routing_task_id, _text(item.get("source_task_id")), _text(item.get("task_id"))):
            if not _is_none(candidate):
                source_task_id = candidate
                break
        diagnostic_rule_id = _text(item.get("diagnostic_rule_id"))
        if _is_none(diagnostic_rule_id):
            diagnostic_rule_id = ""
        routing_issue = _text(item.get("routing_issue"))
        if _is_none(routing_issue):
            routing_issue = ""
        if not source_task_id and not diagnostic_rule_id:
            diagnostic_rule_id = "UNROUTABLE_UNRESOLVED_AUDIT_FAIL"
            routing_issue = "CORRECTION_REQUIRED_TARGET_UNRESOLVED"
        route_source = "unroutable_unresolved_audit_fail" if diagnostic_rule_id else "audit_result_fail"
        failed_checks = item.get("failed_checks") if isinstance(item.get("failed_checks"), list) else []
        if not failed_checks and isinstance(item.get("issues"), list):
            failed_checks = [
                _text(issue.get("rule_id"))
                for issue in item["issues"]
                if isinstance(issue, Mapping) and _text(issue.get("rule_id"))
            ]
        return build_audit_fail_route(
            root=root,
            source_audit_result_ref=_text(item.get("ref")),
            source_task_id=source_task_id,
            source_result_refs=item.get("source_result_refs") if isinstance(item.get("source_result_refs"), list) else (),
            source_task_refs=item.get("source_task_refs") if isinstance(item.get("source_task_refs"), list) else (),
            failed_checks=failed_checks,
            audit_findings=item.get("findings") if isinstance(item.get("findings"), list) else (),
            target_correction_role=(
                _text(item.get("target_correction_role"))
                or _text(item.get("target_role"))
                or _text(item.get("owner_role"))
            ),
            route_source=route_source,
            diagnostic_rule_id=diagnostic_rule_id,
            routing_issue=routing_issue,
            source_boundary_classification=classification if classification.get("applies") else None,
        )
    return {}


def from_transition_evidence(root: Path, transition_evidence: Mapping[str, object]) -> dict[str, object]:
    route = from_audit_inspection(root, transition_evidence.get("audit_failure_evidence"))
    if route:
        return route
    inputs = transition_evidence.get("inputs")
    if not isinstance(inputs, Mapping):
        return {}
    signals = inputs.get("sidecar_state_signals")
    if not isinstance(signals, Mapping):
        return {}
    events = signals.get("lifecycle_events")
    if not isinstance(events, list):
        return {}
    for item in reversed(events):
        if not isinstance(item, Mapping):
            continue
        event_name = _text(item.get("event"))
        status = _text(item.get("status")).lower()
        profile_failed = event_name in {"RESULT_RECEIVED", "AGENT_TERMINATED", "AUDIT_ROUTE_READY"} and status in {
            "fail",
            "blocked",
            "gap",
        }
        if profile_failed:
            result_ref = _text(item.get("result_ref"))
            path = _workspace_ref_path(root, result_ref)
            if path is not None and path.is_file():
                try:
                    parsed = result_parser.parse_result_file(path)
                except (OSError, UnicodeError):
                    parsed = None
                if parsed is not None:
                    route = from_parsed_profile_result(root=root, result_path=path, parsed=parsed)
                    if route:
                        return route
            return build_profile_fail_route(
                root=root,
                source_result_ref=result_ref,
                source_task_id=_text(item.get("task_id")),
                source_role=_text(item.get("role") or item.get("agent_role")),
            )
        failed = event_name == "AUDIT_RESULT_RECEIVED_FAIL" or (
            event_name == "AUDIT_RESULT_RECEIVED" and status == "fail"
        )
        if not failed:
            continue
        audit_ref = _text(item.get("result_ref"))
        path = _workspace_ref_path(root, audit_ref)
        if path is not None and path.is_file():
            try:
                parsed = result_parser.parse_result_file(path)
            except (OSError, UnicodeError):
                parsed = None
            if parsed is not None:
                route = from_parsed_audit_result(root=root, result_path=path, parsed=parsed)
                if route:
                    return route
        return build_audit_fail_route(
            root=root,
            source_audit_result_ref=audit_ref,
            source_task_id=_text(item.get("task_id")),
            failed_checks=["AUDIT_RESULT_STATUS_FAIL"],
        )
    return {}
