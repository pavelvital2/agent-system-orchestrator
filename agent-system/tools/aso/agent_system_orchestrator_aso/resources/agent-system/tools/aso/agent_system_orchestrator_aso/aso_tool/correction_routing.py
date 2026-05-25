"""Structured correction routing evidence for failed audit results."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import result_parser


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
) -> dict[str, object]:
    source_result_list = _dedupe(source_result_refs)
    source_task_list = _dedupe(source_task_refs)
    resolved_task_id = source_task_id or (source_task_list[0] if source_task_list else "UNKNOWN")
    resolved_failed_checks = _dedupe(failed_checks) or ["AUDIT_RESULT_STATUS_FAIL"]
    resolved_target_role = target_correction_role or _target_role_from_source_result(root, source_result_list)
    proposal_path = correction_proposal_path(resolved_task_id)
    return {
        "route": "CORRECTION_REQUIRED",
        "route_source": "audit_result_fail",
        "source_audit_result": source_audit_result_ref or "NONE",
        "source_audit_result_ref": source_audit_result_ref or "NONE",
        "source_result_refs": source_result_list,
        "source_task_id": resolved_task_id,
        "source_task_refs": source_task_list,
        "failed_checks": resolved_failed_checks,
        "audit_findings": _dedupe(audit_findings),
        "target_correction_role": resolved_target_role,
        "routing_owner_role": "orchestrator",
        "correction_task_packet_path": "NONE",
        "correction_task_proposal_path": proposal_path,
        "correction_task_packet_or_proposal_path": proposal_path,
        "checkpoint_preflight_blocked": True,
    }


def from_parsed_audit_result(
    *,
    root: Path | None,
    result_path: Path | str,
    parsed: result_parser.ParsedResult,
) -> dict[str, object]:
    if parsed.result_type != "audit_result" or parsed.status != "fail":
        return {}
    audit = parsed.audit
    return build_audit_fail_route(
        root=root,
        source_audit_result_ref=workspace_result_ref(root, result_path),
        source_task_id=parsed.task_id,
        source_result_refs=audit.source_result_refs,
        source_task_refs=audit.source_task_refs,
        failed_checks=audit.failed_checks,
        audit_findings=audit.findings,
    )


def from_audit_inspection(
    root: Path,
    invalid_audit_results: object,
) -> dict[str, object]:
    if not isinstance(invalid_audit_results, list):
        return {}
    for item in invalid_audit_results:
        if not isinstance(item, Mapping):
            continue
        if _text(item.get("status")).lower() != "fail":
            continue
        return build_audit_fail_route(
            root=root,
            source_audit_result_ref=_text(item.get("ref")),
            source_task_id=_text(item.get("task_id")),
            source_result_refs=item.get("source_result_refs") if isinstance(item.get("source_result_refs"), list) else (),
            source_task_refs=item.get("source_task_refs") if isinstance(item.get("source_task_refs"), list) else (),
            failed_checks=item.get("failed_checks") if isinstance(item.get("failed_checks"), list) else (),
            audit_findings=item.get("findings") if isinstance(item.get("findings"), list) else (),
        )
    return {}


def from_transition_evidence(root: Path, transition_evidence: Mapping[str, object]) -> dict[str, object]:
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
