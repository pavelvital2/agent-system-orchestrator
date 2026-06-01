"""Internal state sidecar materialization after confirmed lifecycle writes."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from . import correction_routing
from . import enum_registry
from . import result_parser
from . import runtime_schema_contracts
from . import transition_engine
from .timestamps import utc_timestamp


STATE_ROOT = Path("project-runtime/state")
RECEIPT_ROOT = Path("project-runtime/receipts/state-reconciliation")
RUNTIME_ROOT = Path("project-runtime")
NONE = "NONE"
PLANNED_TIMESTAMP = "<reconcile_timestamp>"
GOVERNED_RECONCILE_SIDECARS = frozenset(
    {"PROJECT_STATE", "TASK_REGISTRY", "NEXT_ACTION", "CURRENT_GATE", "ACCEPTED_ARTIFACTS"}
)
KNOWN_STATE_SIDECARS = frozenset(runtime_schema_contracts.ALL_SIDECARS)
PRE_VERIFY_RECONCILABLE_RULES = {
    "RUNTIME_LIFECYCLE_TASK_REGISTRY_STALE": frozenset({"TASK_REGISTRY"}),
    "RUNTIME_LIFECYCLE_RESULT_REGISTRY_STALE": frozenset({"TASK_REGISTRY"}),
    "RUNTIME_LIFECYCLE_CHECKPOINT_REGISTRY_STALE": frozenset({"TASK_REGISTRY"}),
    "RUNTIME_LIFECYCLE_CORRECTION_REGISTRY_STALE": frozenset({"TASK_REGISTRY"}),
    "RUNTIME_LIFECYCLE_ARTIFACT_SIDECAR_STALE": frozenset({"ACCEPTED_ARTIFACTS"}),
    "RUNTIME_NEXT_ACTION_STALE": frozenset({"NEXT_ACTION"}),
    "STALE_NEXT_ACTION_TASK_ID": frozenset({"NEXT_ACTION"}),
}


@dataclass(frozen=True)
class MaterializationResult:
    status: str
    files_written: tuple[str, ...]
    error: str = ""
    receipt_ref: str = ""
    diff_count: int = 0
    state_verify_after_status: str = ""

    @property
    def ok(self) -> bool:
        return self.status in {"written", "no_changes", "no_state_sidecars"}

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "files_written": list(self.files_written),
            "diff_count": self.diff_count,
        }
        if self.receipt_ref:
            payload["receipt_ref"] = self.receipt_ref
        if self.state_verify_after_status:
            payload["state_verify_after_status"] = self.state_verify_after_status
        if self.error:
            payload["error"] = self.error
        return payload


@dataclass(frozen=True)
class ReconciliationPlan:
    status: str
    root: str
    sidecars: dict[str, dict[str, Any]]
    updated_sidecars: dict[str, dict[str, Any]]
    changed_sidecars: tuple[str, ...]
    diff: tuple[dict[str, Any], ...]
    files_planned: tuple[str, ...]
    findings: tuple[dict[str, str], ...]
    evidence: dict[str, Any]
    transition_engine: dict[str, Any]

    @property
    def blocked(self) -> bool:
        return self.status == "blocked"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _read_json_with_finding(path: Path, relpath: str) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, {
            "rule_id": "STATE_RECONCILE_JSON_INVALID",
            "severity": "error",
            "message": f"{relpath} is not valid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}.",
            "path": relpath,
            "recommendation": "Repair malformed runtime state before confirmed reconciliation.",
        }
    except OSError as exc:
        return None, {
            "rule_id": "STATE_RECONCILE_JSON_UNREADABLE",
            "severity": "error",
            "message": f"{relpath} could not be read: {exc}",
            "path": relpath,
            "recommendation": "Repair workspace permissions before confirmed reconciliation.",
        }
    if not isinstance(payload, dict):
        return None, {
            "rule_id": "STATE_RECONCILE_JSON_NOT_OBJECT",
            "severity": "error",
            "message": f"{relpath} must contain a JSON object.",
            "path": relpath,
            "recommendation": "Restore a governed sidecar JSON object before reconciliation.",
        }
    return payload, None


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _content(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    content = payload.get("content")
    return dict(content) if isinstance(content, Mapping) else {}


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _append_unique(values: object, value: str) -> list[str]:
    result = [item for item in values if isinstance(item, str)] if isinstance(values, list) else []
    if value and value not in result:
        result.append(value)
    return result


def _event_name(event: Mapping[str, Any]) -> str:
    raw = _text(event.get("event_type") or event.get("event") or event.get("type"))
    status = _text(event.get("status") or event.get("result_status") or event.get("audit_status")).lower()
    audit_result_event = (
        "AUDIT_RESULT_RECEIVED_PASS"
        if status == "pass"
        else "AUDIT_RESULT_RECEIVED_FAIL" if status == "fail" else "AUDIT_RESULT_RECEIVED"
    )
    aliases = {
        "agent_result_received": "RESULT_RECEIVED",
        "RESULT_RECEIVED": "RESULT_RECEIVED",
        "result_validated": "RESULT_VALIDATED",
        "RESULT_VALIDATED": "RESULT_VALIDATED",
        "result_accepted": "RESULT_ACCEPTED",
        "RESULT_ACCEPTED": "RESULT_ACCEPTED",
        "artifact_package_received": "ARTIFACT_PACKAGE_RECEIVED",
        "ARTIFACT_PACKAGE_RECEIVED": "ARTIFACT_PACKAGE_RECEIVED",
        "artifact_validated": "ARTIFACT_VALIDATED",
        "ARTIFACT_VALIDATED": "ARTIFACT_VALIDATED",
        "AUDIT_RESULT_RECEIVED": audit_result_event,
        "artifact_accepted": "ARTIFACT_ACCEPTED",
        "ARTIFACT_ACCEPTED": "ARTIFACT_ACCEPTED",
        "agent_instance_terminated": "AGENT_TERMINATED",
        "AGENT_TERMINATED": "AGENT_TERMINATED",
        "auditor_agent_terminated": "AGENT_TERMINATED",
        "AUDITOR_AGENT_TERMINATED": "AGENT_TERMINATED",
        "agent_task_dispatched": "CREATE_AGENT_DISPATCHED",
        "CREATE_AGENT_DISPATCHED": "CREATE_AGENT_DISPATCHED",
        "audit_route_ready": "AUDIT_ROUTE_READY",
        "AUDIT_ROUTE_READY": "AUDIT_ROUTE_READY",
    }
    return aliases.get(raw, raw)


def _event_task_id(event: Mapping[str, Any]) -> str:
    return _text(event.get("task_id") or event.get("TASK_ID") or event.get("task"))


def _event_role(event: Mapping[str, Any]) -> str:
    return _text(event.get("role") or event.get("agent_role") or event.get("ROLE")).lower()


def _event_result_ref(event: Mapping[str, Any]) -> str:
    return _text(event.get("result_ref") or event.get("source_result_ref"))


def _event_timestamp(event: Mapping[str, Any], fallback: str) -> str:
    return _text(event.get("timestamp_utc") or event.get("accepted_at") or event.get("received_at")) or fallback


def _matching_received_result_ref(events: list[dict[str, Any]], event: Mapping[str, Any]) -> str:
    task_id = _event_task_id(event)
    agent_id = _text(event.get("agent_instance_id"))
    role = _event_role(event)
    for candidate in reversed(events):
        if _event_name(candidate) not in {"RESULT_RECEIVED", "AUDIT_RESULT_RECEIVED_PASS", "AUDIT_RESULT_RECEIVED_FAIL", "AUDIT_RESULT_RECEIVED"}:
            continue
        if task_id and _event_task_id(candidate) != task_id:
            continue
        if agent_id and _text(candidate.get("agent_instance_id")) != agent_id:
            continue
        if role and _event_role(candidate) != role:
            continue
        result_ref = _event_result_ref(candidate)
        if result_ref:
            return result_ref
    return ""


def _sidecars(root: Path) -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = {}
    state_dir = root / STATE_ROOT
    if not state_dir.is_dir():
        return loaded
    for path in state_dir.glob("*.json"):
        payload = _read_json(path)
        if payload is not None:
            sidecar_type = _text(payload.get("sidecar_type")) or path.stem
            loaded[sidecar_type] = payload
    lifecycle_log = transition_engine.load_lifecycle_log(root)
    if lifecycle_log.get("events") or lifecycle_log.get("findings"):
        loaded["LIFECYCLE_LOG"] = lifecycle_log
    return loaded


def _sidecars_for_reconcile(root: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    loaded: dict[str, dict[str, Any]] = {}
    findings: list[dict[str, str]] = []
    state_dir = root / STATE_ROOT
    if state_dir.is_dir():
        for path in sorted(state_dir.glob("*.json")):
            relpath = path.relative_to(root).as_posix()
            payload, finding = _read_json_with_finding(path, relpath)
            if finding is not None:
                findings.append(finding)
                continue
            if payload is None:
                continue
            sidecar_type = _text(payload.get("sidecar_type")) or path.stem
            loaded[sidecar_type] = payload
            if sidecar_type in KNOWN_STATE_SIDECARS:
                finding = _markdown_source_write_boundary_finding(root, sidecar_type, payload)
                if finding is not None:
                    findings.append(finding)

    lifecycle_log = transition_engine.load_lifecycle_log(root)
    lifecycle_findings = [
        {
            "rule_id": str(finding.get("rule_id", "RUNTIME_LIFECYCLE_LOG_INVALID")),
            "severity": str(finding.get("severity", "error")),
            "message": str(finding.get("message", "")),
            "path": transition_engine.LIFECYCLE_LOG_RELATIVE_PATH.as_posix(),
            "recommendation": str(finding.get("recommendation", "Repair lifecycle log before reconciliation.")),
        }
        for finding in lifecycle_log.get("findings", [])
        if isinstance(finding, Mapping)
    ]
    findings.extend(lifecycle_findings)
    if lifecycle_log.get("events") or lifecycle_log.get("findings"):
        loaded["LIFECYCLE_LOG"] = lifecycle_log
    return loaded, findings


def _workspace_ref(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _path_resolves_under(root: Path, path: Path, allowed_root: Path) -> bool:
    try:
        root_resolved = root.resolve(strict=False)
        allowed_resolved = allowed_root.resolve(strict=False)
        allowed_resolved.relative_to(root_resolved)
        path.resolve(strict=False).relative_to(allowed_resolved)
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _markdown_source_write_boundary_finding(
    root: Path,
    sidecar_type: str,
    payload: Mapping[str, Any],
) -> dict[str, str] | None:
    if "markdown_source" not in payload:
        return None

    raw_source = payload.get("markdown_source")
    expected = f"{RUNTIME_ROOT.as_posix()}/{sidecar_type}.md"
    relpath = f"{STATE_ROOT.as_posix()}/{sidecar_type}.json"

    reason = ""
    if not isinstance(raw_source, str):
        reason = f"must be {expected!r}, not {type(raw_source).__name__}."
        source_text = str(raw_source)
    else:
        source_text = raw_source.strip()
        parts = PurePosixPath(source_text).parts
        if source_text != raw_source:
            reason = f"must be normalized with no leading or trailing whitespace and equal {expected!r}."
        elif PurePosixPath(source_text).is_absolute():
            reason = f"must be relative and equal {expected!r}."
        elif ".." in parts:
            reason = f"must not contain path traversal and must equal {expected!r}."
        elif source_text != expected:
            reason = f"must equal the declared governed runtime view {expected!r}."
        elif not _path_resolves_under(root, root / source_text, root / RUNTIME_ROOT):
            reason = f"must resolve under {RUNTIME_ROOT.as_posix()} without symlink escape."

    if not reason:
        return None

    return {
        "rule_id": "STATE_RECONCILE_MARKDOWN_SOURCE_FORBIDDEN",
        "severity": "error",
        "message": f"{relpath}.markdown_source={source_text!r} is outside the reconcile write allowlist: {reason}",
        "path": relpath,
        "recommendation": "Set markdown_source to the matching project-runtime/<SIDE_CAR>.md governed compatibility view before reconciling.",
    }


def _write_boundary_findings(
    root: Path,
    sidecars: Mapping[str, Mapping[str, Any]],
    changed_sidecars: Iterable[str],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for sidecar_type in sorted(changed_sidecars):
        if sidecar_type not in GOVERNED_RECONCILE_SIDECARS:
            findings.append(
                {
                    "rule_id": "STATE_RECONCILE_STATE_WRITE_FORBIDDEN",
                    "severity": "error",
                    "message": f"Reconciliation is not allowed to write sidecar {sidecar_type!r}.",
                    "path": f"{STATE_ROOT.as_posix()}/{sidecar_type}.json",
                    "recommendation": "Limit reconciliation writes to governed runtime state sidecars.",
                }
            )
            continue
        state_path = root / STATE_ROOT / f"{sidecar_type}.json"
        if not _path_resolves_under(root, state_path, root / STATE_ROOT):
            findings.append(
                {
                    "rule_id": "STATE_RECONCILE_STATE_WRITE_FORBIDDEN",
                    "severity": "error",
                    "message": f"State write target for {sidecar_type} escapes {STATE_ROOT.as_posix()}.",
                    "path": f"{STATE_ROOT.as_posix()}/{sidecar_type}.json",
                    "recommendation": "Repair runtime state paths before reconciliation.",
                }
            )
        payload = sidecars.get(sidecar_type, {})
        finding = _markdown_source_write_boundary_finding(root, sidecar_type, payload)
        if finding is not None:
            findings.append(finding)
    return findings


def _scan_json_receipts(root: Path, pattern: str) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for path in sorted(root.glob(pattern)):
        if not path.is_file():
            continue
        relpath = _workspace_ref(root, path)
        payload = _read_json(path)
        receipts.append(
            {
                "path": relpath,
                "readable": isinstance(payload, dict),
                "receipt_type": _text((payload or {}).get("receipt_type")),
                "task_id": _text((payload or {}).get("task_id")),
            }
        )
    return receipts


def _scan_results(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    profile_results: list[dict[str, Any]] = []
    audit_results: list[dict[str, Any]] = []
    results_root = root / "project-runtime" / "results"
    if not results_root.is_dir():
        return profile_results, audit_results
    for path in sorted(results_root.rglob("*.md")):
        if not path.is_file():
            continue
        relpath = _workspace_ref(root, path)
        try:
            parsed = result_parser.parse_result_file(path, strict=False)
        except (OSError, UnicodeError) as exc:
            row = {
                "path": relpath,
                "readable": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            audit_results.append(row) if "audit" in relpath.lower() else profile_results.append(row)
            continue
        row = {
            "path": relpath,
            "readable": True,
            "result_type": parsed.result_type,
            "task_id": parsed.task_id,
            "role": parsed.role,
            "status": parsed.status,
            "agent_instance_id": parsed.agent_instance_id,
        }
        if parsed.result_type == "audit_result":
            row["audit"] = parsed.audit.to_json()
            audit_results.append(row)
        else:
            profile_results.append(row)
    return profile_results, audit_results


def _correction_records(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    patterns = (
        "project-runtime/proposals/correction-*.json",
        "project-runtime/receipts/corrections/**/*.json",
        "project-runtime/corrections/**/*.json",
    )
    for pattern in patterns:
        records.extend(_scan_json_receipts(root, pattern))
    return sorted(records, key=lambda item: str(item.get("path", "")))


def _checkpoint_receipts(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    patterns = (
        "project-runtime/receipts/checkpoints/**/*.json",
        "project-runtime/checkpoints/**/*.json",
    )
    for pattern in patterns:
        records.extend(_scan_json_receipts(root, pattern))
    return sorted(records, key=lambda item: str(item.get("path", "")))


def _structured_evidence(root: Path, sidecars: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    profile_results, audit_results = _scan_results(root)
    lifecycle = sidecars.get("LIFECYCLE_LOG", {})
    lifecycle_events = lifecycle.get("events") if isinstance(lifecycle, Mapping) else []
    artifact_receipts = _scan_json_receipts(root, "project-runtime/receipts/artifacts/**/*.json")
    correction_records = _correction_records(root)
    checkpoint_receipts = _checkpoint_receipts(root)
    task_id = ""
    if any(key in sidecars for key in ("PROJECT_STATE", "CURRENT_GATE", "TASK_REGISTRY")):
        try:
            authority = transition_engine.routing_authority_report(
                transition_engine.load_runtime_contract(),
                sidecars,
                root=root,
            )
            inputs = authority.get("inputs")
            signals = inputs.get("sidecar_state_signals") if isinstance(inputs, Mapping) else {}
            task_id = _text(signals.get("task_id")) if isinstance(signals, Mapping) else ""
        except (OSError, transition_engine.RuntimeContractError):
            task_id = ""
    return {
        "state_sidecars": sorted(key for key in sidecars if key != "LIFECYCLE_LOG"),
        "lifecycle_log": {
            "path": transition_engine.LIFECYCLE_LOG_RELATIVE_PATH.as_posix(),
            "exists": bool(lifecycle.get("exists")) if isinstance(lifecycle, Mapping) else False,
            "event_count": len(lifecycle_events) if isinstance(lifecycle_events, list) else 0,
        },
        "results": {
            "profile_result_count": len(profile_results),
            "audit_result_count": len(audit_results),
            "profile_results": profile_results,
            "audit_results": audit_results,
        },
        "artifact_receipts": {
            "count": len(artifact_receipts),
            "receipts": artifact_receipts,
        },
        "correction_resolution_records": {
            "count": len(correction_records),
            "records": correction_records,
        },
        "checkpoint_receipts": {
            "count": len(checkpoint_receipts),
            "receipts": checkpoint_receipts,
        },
        "active_task_id": task_id or NONE,
    }


def _tasks_by_id(task_registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tasks = _content(task_registry).get("tasks")
    result: dict[str, dict[str, Any]] = {}
    if isinstance(tasks, list):
        for task in tasks:
            if isinstance(task, dict) and isinstance(task.get("task_id"), str):
                result[task["task_id"]] = task
    return result


def _events(sidecars: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    payload = sidecars.get("LIFECYCLE_LOG", {})
    raw = payload.get("events") if isinstance(payload, Mapping) else None
    return [dict(item) for item in raw if isinstance(item, Mapping)] if isinstance(raw, list) else []


def _artifact_type_from_manifest(root: Path, artifact_ref: str, role: str) -> str:
    if artifact_ref:
        manifest = _read_json(root / artifact_ref)
        value = _text((manifest or {}).get("artifact_type"))
        if value:
            return value
    return "AUDIT_RESULT" if role == "auditor" else "RESULT"


def _accepted_artifact_entry(root: Path, events: list[dict[str, Any]], event: Mapping[str, Any], timestamp: str) -> dict[str, Any]:
    role = _event_role(event)
    result_ref = _event_result_ref(event) or _matching_received_result_ref(events, event) or NONE
    artifact_ref = _text(event.get("artifact_ref")) or NONE
    artifact_id = _text(event.get("artifact_id")) or Path(artifact_ref).stem.upper() or "ARTIFACT"
    return {
        "artifact_id": artifact_id,
        "artifact_type": _artifact_type_from_manifest(root, artifact_ref if artifact_ref != NONE else "", role),
        "artifact_ref": artifact_ref,
        "status": "accepted",
        "source_task": _event_task_id(event) or NONE,
        "source_result_ref": result_ref,
        "audit_ref": result_ref if role == "auditor" else NONE,
        "supersedes": NONE,
        "superseded_by": NONE,
        "commit_hash": NONE,
        "branch": NONE,
        "push_status": "not_required",
        "checkpoint_ref": NONE,
        "accepted_at": _event_timestamp(event, timestamp),
        "updated_at": timestamp,
        "notes": "Materialized from lifecycle ARTIFACT_ACCEPTED event.",
    }


def _merge_accepted_artifacts(root: Path, payload: dict[str, Any], events: list[dict[str, Any]], timestamp: str) -> bool:
    content = _content(payload)
    artifacts = content.get("artifacts")
    if not isinstance(artifacts, list):
        return False

    changed = False
    for event in events:
        if _event_name(event) != "ARTIFACT_ACCEPTED":
            continue
        entry = _accepted_artifact_entry(root, events, event, timestamp)
        keys = {
            _text(entry.get("artifact_id")),
            _text(entry.get("artifact_ref")),
        }
        existing = None
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            if _text(artifact.get("artifact_id")) in keys or _text(artifact.get("artifact_ref")) in keys:
                existing = artifact
                break
        if existing is None:
            artifacts.append(entry)
            changed = True
        else:
            for key, value in entry.items():
                if existing.get(key) != value:
                    existing[key] = value
                    changed = True

    if changed:
        content["artifacts"] = artifacts
        payload["content"] = content
    return changed


def _materialize_task_registry(payload: dict[str, Any], events: list[dict[str, Any]], timestamp: str) -> bool:
    tasks = _tasks_by_id(payload)
    if not tasks:
        return False
    changed = False
    for event in events:
        task_id = _event_task_id(event)
        if not task_id or task_id not in tasks:
            continue
        task = tasks[task_id]
        event_name = _event_name(event)
        role = _event_role(event)
        result_ref = _event_result_ref(event)

        if event_name == "RESULT_RECEIVED":
            if result_ref:
                refs = _append_unique(task.get("result_refs"), result_ref)
                if refs != task.get("result_refs"):
                    task["result_refs"] = refs
                    changed = True
            if task.get("status") in {"pending", "ready"}:
                task["status"] = "running"
                changed = True
        elif event_name == "ARTIFACT_ACCEPTED":
            artifact_ref = _text(event.get("artifact_ref"))
            if artifact_ref:
                accepted_files = _append_unique(task.get("accepted_files"), artifact_ref)
                if accepted_files != task.get("accepted_files"):
                    task["accepted_files"] = accepted_files
                    changed = True
        elif event_name == "CREATE_AGENT_DISPATCHED" and role == "auditor":
            if task.get("status") != "audit_pending":
                task["status"] = "audit_pending"
                changed = True
        elif event_name == "AUDIT_RESULT_RECEIVED_PASS":
            if result_ref:
                refs = _append_unique(task.get("audit_refs"), result_ref)
                if refs != task.get("audit_refs"):
                    task["audit_refs"] = refs
                    changed = True
            if task.get("status") != "audit_passed":
                task["status"] = "audit_passed"
                changed = True
        elif event_name == "AUDIT_RESULT_RECEIVED_FAIL":
            if result_ref:
                refs = _append_unique(task.get("audit_refs"), result_ref)
                if refs != task.get("audit_refs"):
                    task["audit_refs"] = refs
                    changed = True
                links = _append_unique(task.get("correction_links"), result_ref)
                if links != task.get("correction_links"):
                    task["correction_links"] = links
                    changed = True
            if task.get("status") != "failed":
                task["status"] = "failed"
                changed = True
        if changed and isinstance(task.get("updated_at"), str):
            task["updated_at"] = timestamp

    if changed:
        content = _content(payload)
        if isinstance(content.get("registry_revision"), int):
            content["registry_revision"] = int(content["registry_revision"]) + 1
        payload["content"] = content
    return changed


def _next_action_content(
    existing: Mapping[str, Any],
    decision: transition_engine.TransitionDecision,
    task_packet: str,
) -> dict[str, Any]:
    sidecars = {
        "NEXT_ACTION": {
            "content": dict(existing),
        }
    }
    if task_packet:
        action = dict(decision.next_action)
        action["task_packet"] = task_packet
        decision = transition_engine.TransitionDecision(
            inputs=decision.inputs,
            transition_selected=decision.transition_selected,
            findings=decision.findings,
            next_action=action,
            reference_docs_used=decision.reference_docs_used,
            allowed=decision.allowed,
            current_state=decision.current_state,
            event=decision.event,
            next_state=decision.next_state,
        )
    return transition_engine.derived_next_action_cache_content(
        transition_engine.load_runtime_contract(),
        sidecars,
        decision,
    )


def _task_packet_for(sidecars: Mapping[str, Mapping[str, Any]], task_id: str) -> str:
    current_gate = _content(sidecars.get("CURRENT_GATE", {}))
    gate_task_id = _text(current_gate.get("task_id"))
    if (not task_id or not gate_task_id or gate_task_id == task_id) and _text(current_gate.get("task_packet")):
        return _text(current_gate.get("task_packet"))
    task_registry = dict(sidecars.get("TASK_REGISTRY", {}))
    task = _tasks_by_id(task_registry).get(task_id, {})
    return _text(task.get("task_packet"))


def _materialize_next_action(payload: dict[str, Any], sidecars: Mapping[str, Mapping[str, Any]]) -> bool:
    contract = transition_engine.load_runtime_contract()
    decision = transition_engine.explain_next_action_from_sidecars(contract, sidecars)
    if not decision.current_state:
        return False
    existing = _content(payload)
    signals = decision.inputs.get("sidecar_state_signals")
    task_id = _text(signals.get("task_id")) if isinstance(signals, Mapping) else ""
    task_packet = _task_packet_for(sidecars, task_id)
    updated = _next_action_content(existing, decision, task_packet)
    if existing == updated:
        return False
    payload["content"] = updated
    return True


def refresh_next_action_cache(root: Path) -> MaterializationResult:
    """Refresh only NEXT_ACTION.json as a rendered cache from canonical inputs."""

    sidecars = _sidecars(root)
    payload = sidecars.get("NEXT_ACTION")
    if not isinstance(payload, dict):
        return MaterializationResult("no_state_sidecars", ())
    timestamp = utc_timestamp()
    try:
        if not _materialize_next_action(payload, sidecars):
            return MaterializationResult("written", ())
        _touch(payload, timestamp)
        path = root / STATE_ROOT / "NEXT_ACTION.json"
        _write_json(path, payload)
    except (OSError, transition_engine.RuntimeContractError) as exc:
        return MaterializationResult("failed", (), str(exc))
    return MaterializationResult("written", (path.relative_to(root).as_posix(),))


def _materialize_project_state(payload: dict[str, Any], sidecars: Mapping[str, Mapping[str, Any]], timestamp: str) -> bool:
    contract = transition_engine.load_runtime_contract()
    decision = transition_engine.explain_next_action_from_sidecars(contract, sidecars)
    state = decision.current_state
    if not state:
        return False
    content = _content(payload)
    before = dict(content)
    if state == "AUDIT_PENDING":
        content["current_phase"] = "audit"
        content["audit_status"] = "pending"
        content["checkpoint_eligibility"] = "blocked"
        content["checkpoint_eligibility_status"] = "ineligible"
    elif state == "CHECKPOINT_ELIGIBLE":
        content["audit_status"] = "passed"
        content["checkpoint_eligibility"] = "local_only"
        content["checkpoint_eligibility_status"] = "eligible"
        content["current_phase"] = "audit"
    elif state == "CORRECTION_REQUIRED":
        content["current_phase"] = "correction"
        content["project_status"] = "blocked"
        content["audit_status"] = "failed"
        content["checkpoint_eligibility"] = "blocked"
        content["checkpoint_eligibility_status"] = "blocked"
    if before != content:
        payload["content"] = content
        return True
    return False


def _materialize_current_gate(payload: dict[str, Any], sidecars: Mapping[str, Mapping[str, Any]]) -> bool:
    contract = transition_engine.load_runtime_contract()
    decision = transition_engine.explain_next_action_from_sidecars(contract, sidecars)
    state = decision.current_state
    if not state:
        return False
    content = _content(payload)
    before = dict(content)
    signals = decision.inputs.get("sidecar_state_signals")
    task_id = _text(signals.get("task_id")) if isinstance(signals, Mapping) else _text(content.get("task_id"))
    task_packet = _task_packet_for(sidecars, task_id)
    content["task_id"] = task_id or content.get("task_id", NONE)
    content["task_packet"] = task_packet or content.get("task_packet", NONE)
    if state == "AUDIT_PENDING":
        content["gate_type"] = "audit"
        content["required_next_role"] = "auditor"
        content["status"] = "open"
        content["checkpoint_eligibility"] = "blocked"
        content["checkpoint_eligibility_status"] = "ineligible"
    elif state == "CHECKPOINT_ELIGIBLE":
        content["gate_type"] = "audit"
        content["required_next_role"] = "orchestrator"
        content["status"] = "passed"
        content["checkpoint_eligibility"] = "local_only"
        content["checkpoint_eligibility_status"] = "eligible"
    elif state == "CORRECTION_REQUIRED":
        content["gate_type"] = "correction"
        content["required_next_role"] = "orchestrator"
        content["status"] = "blocked"
        content["checkpoint_eligibility"] = "blocked"
        content["checkpoint_eligibility_status"] = "blocked"
    if before != content:
        payload["content"] = content
        return True
    return False


def _touch(payload: dict[str, Any], timestamp: str) -> None:
    old_revision = payload.get("state_revision")
    if isinstance(old_revision, int) and not isinstance(old_revision, bool):
        payload["state_revision"] = old_revision + 1
    payload["updated_at"] = timestamp
    payload["updated_by"] = "orchestrator"


def _markdown_value(value: object) -> str:
    if isinstance(value, bool):
        return enum_registry.canonical_bool_text(value)
    if isinstance(value, list):
        return "NONE" if not value else ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return "NONE" if not value else json.dumps(value, sort_keys=True)
    return str(value)


def _sync_markdown(root: Path, payload: Mapping[str, Any], *, write: bool = True) -> bool:
    sidecar_type = _text(payload.get("sidecar_type"))
    if sidecar_type:
        if _markdown_source_write_boundary_finding(root, sidecar_type, payload) is not None:
            return False
    elif "markdown_source" in payload:
        return False
    markdown_source = _text(payload.get("markdown_source"))
    if not markdown_source:
        return False
    path = root / markdown_source
    if not path.is_file():
        return False
    content = _content(payload)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    changed = False
    for key, value in content.items():
        if isinstance(value, (list, dict)):
            continue
        prefix = f"{key.upper()}:"
        replacement = f"{prefix} {_markdown_value(value)}"
        for index, line in enumerate(lines):
            if line.startswith(prefix):
                if line != replacement:
                    lines[index] = replacement
                    changed = True
                break
    if changed:
        if write:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _flatten_diff(
    before: object,
    after: object,
    prefix: str,
    rows: list[dict[str, Any]],
) -> None:
    if before == after:
        return
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        for key in sorted(set(before) | set(after)):
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            _flatten_diff(before.get(key), after.get(key), child_prefix, rows)
        return
    if isinstance(before, list) and isinstance(after, list):
        max_len = max(len(before), len(after))
        for index in range(max_len):
            child_prefix = f"{prefix}[{index}]"
            old = before[index] if index < len(before) else None
            new = after[index] if index < len(after) else None
            _flatten_diff(old, new, child_prefix, rows)
        return
    rows.append({"field": prefix, "before": before, "after": after})


def _content_diff(
    before_sidecars: Mapping[str, Mapping[str, Any]],
    after_sidecars: Mapping[str, Mapping[str, Any]],
    changed_sidecars: Iterable[str],
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for sidecar_type in sorted(changed_sidecars):
        before_content = _content(before_sidecars.get(sidecar_type, {}))
        after_content = _content(after_sidecars.get(sidecar_type, {}))
        sidecar_rows: list[dict[str, Any]] = []
        _flatten_diff(before_content, after_content, "content", sidecar_rows)
        for row in sidecar_rows:
            rows.append(
                {
                    "sidecar_type": sidecar_type,
                    "file": f"{STATE_ROOT.as_posix()}/{sidecar_type}.json",
                    **row,
                }
            )
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                str(item.get("sidecar_type", "")),
                str(item.get("field", "")),
                _canonical_json(item.get("before")),
                _canonical_json(item.get("after")),
            ),
        )
    )


def _planned_files(root: Path, changed: Mapping[str, Mapping[str, Any]]) -> tuple[str, ...]:
    files: list[str] = []
    for sidecar_type in sorted(changed):
        payload = changed[sidecar_type]
        files.append(f"{STATE_ROOT.as_posix()}/{sidecar_type}.json")
        if _sync_markdown(root, payload, write=False):
            markdown_source = _text(payload.get("markdown_source"))
            if markdown_source:
                files.append(markdown_source)
    return tuple(sorted(dict.fromkeys(files)))


def _transition_report(root: Path, sidecars: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    try:
        contract = transition_engine.load_runtime_contract()
        return transition_engine.routing_authority_report(contract, sidecars, root=root)
    except (OSError, transition_engine.RuntimeContractError) as exc:
        return {
            "allowed": False,
            "contract_authoritative": True,
            "canonical_recommended_next_action": "NONE",
            "findings": [
                {
                    "rule_id": "RUNTIME_CONTRACT_LOAD_FAILED",
                    "severity": "error",
                    "message": "Runtime contract could not be loaded.",
                    "evidence": str(exc),
                    "recommendation": "Restore ORCHESTRATOR_RUNTIME_CONTRACT.json before state reconciliation.",
                }
            ],
            "reference_docs_used": [transition_engine.CONTRACT_RELATIVE_PATH.as_posix()],
        }


def _apply_reconciliation_mutators(
    root: Path,
    sidecars: dict[str, dict[str, Any]],
    timestamp: str,
) -> dict[str, dict[str, Any]]:
    changed: dict[str, dict[str, Any]] = {}
    events = _events(sidecars)
    if events:
        if "TASK_REGISTRY" in sidecars and _materialize_task_registry(sidecars["TASK_REGISTRY"], events, timestamp):
            changed["TASK_REGISTRY"] = sidecars["TASK_REGISTRY"]
        if "ACCEPTED_ARTIFACTS" in sidecars and _merge_accepted_artifacts(root, sidecars["ACCEPTED_ARTIFACTS"], events, timestamp):
            changed["ACCEPTED_ARTIFACTS"] = sidecars["ACCEPTED_ARTIFACTS"]

    materialized_sidecars = dict(sidecars)
    materialized_sidecars.update(changed)
    if "PROJECT_STATE" in materialized_sidecars and _materialize_project_state(materialized_sidecars["PROJECT_STATE"], materialized_sidecars, timestamp):
        changed["PROJECT_STATE"] = materialized_sidecars["PROJECT_STATE"]
    materialized_sidecars.update(changed)
    if "CURRENT_GATE" in materialized_sidecars and _materialize_current_gate(materialized_sidecars["CURRENT_GATE"], materialized_sidecars):
        changed["CURRENT_GATE"] = materialized_sidecars["CURRENT_GATE"]
    materialized_sidecars.update(changed)
    if "NEXT_ACTION" in materialized_sidecars and _materialize_next_action(materialized_sidecars["NEXT_ACTION"], materialized_sidecars):
        changed["NEXT_ACTION"] = materialized_sidecars["NEXT_ACTION"]
    return changed


def build_reconciliation_plan(root: Path) -> ReconciliationPlan:
    sidecars, findings = _sidecars_for_reconcile(root)
    governed_keys = {"PROJECT_STATE", "TASK_REGISTRY", "NEXT_ACTION", "CURRENT_GATE", "ACCEPTED_ARTIFACTS"}
    has_governed_sidecars = any(key in sidecars for key in governed_keys)
    transition_report = _transition_report(root, sidecars) if has_governed_sidecars else {
        "allowed": False,
        "canonical_recommended_next_action": "NONE",
        "reason": "no governed state sidecars present",
    }
    evidence = _structured_evidence(root, sidecars)
    blocking_findings = [finding for finding in findings if finding.get("severity") == "error"]
    if blocking_findings:
        return ReconciliationPlan(
            status="blocked",
            root=str(root),
            sidecars=sidecars,
            updated_sidecars=sidecars,
            changed_sidecars=(),
            diff=(),
            files_planned=(),
            findings=tuple(findings),
            evidence=evidence,
            transition_engine=transition_report,
        )
    if not has_governed_sidecars:
        return ReconciliationPlan(
            status="no_state_sidecars",
            root=str(root),
            sidecars=sidecars,
            updated_sidecars=sidecars,
            changed_sidecars=(),
            diff=(),
            files_planned=(),
            findings=tuple(findings),
            evidence=evidence,
            transition_engine=transition_report,
        )

    working = copy.deepcopy(sidecars)
    try:
        changed = _apply_reconciliation_mutators(root, working, PLANNED_TIMESTAMP)
    except (OSError, transition_engine.RuntimeContractError) as exc:
        blocked = {
            "rule_id": "STATE_RECONCILE_DERIVATION_FAILED",
            "severity": "error",
            "message": f"State reconciliation derivation failed: {exc}",
            "path": STATE_ROOT.as_posix(),
            "recommendation": "Repair runtime contract and sidecar evidence before reconciliation.",
        }
        return ReconciliationPlan(
            status="blocked",
            root=str(root),
            sidecars=sidecars,
            updated_sidecars=working,
            changed_sidecars=(),
            diff=(),
            files_planned=(),
            findings=tuple([*findings, blocked]),
            evidence=evidence,
            transition_engine=transition_report,
        )

    changed_sidecars = tuple(sorted(changed))
    diff = _content_diff(sidecars, working, changed_sidecars)
    boundary_findings = _write_boundary_findings(root, working, changed_sidecars)
    if boundary_findings:
        return ReconciliationPlan(
            status="blocked",
            root=str(root),
            sidecars=sidecars,
            updated_sidecars=working,
            changed_sidecars=changed_sidecars,
            diff=diff,
            files_planned=(),
            findings=tuple([*findings, *boundary_findings]),
            evidence=evidence,
            transition_engine=_transition_report(root, working),
        )
    files_planned = _planned_files(root, changed)
    return ReconciliationPlan(
        status="changes_pending" if diff else "no_changes",
        root=str(root),
        sidecars=sidecars,
        updated_sidecars=working,
        changed_sidecars=changed_sidecars,
        diff=diff,
        files_planned=files_planned,
        findings=tuple(findings),
        evidence=evidence,
        transition_engine=_transition_report(root, working),
    )


def _summary_from_verify(report: Mapping[str, object]) -> dict[str, object]:
    return {
        "status": report.get("status", "unknown"),
        "summary": report.get("summary", {}),
        "finding_count": len(report.get("findings", [])) if isinstance(report.get("findings"), list) else 0,
    }


def _state_verify_report(root: Path) -> tuple[dict[str, object], int]:
    from .commands import state_verify

    return state_verify._report(root, True)


def _pre_verify_blocking_findings(
    report: Mapping[str, object],
    changed_sidecars: Iterable[str],
) -> list[dict[str, object]]:
    findings = report.get("findings")
    if not isinstance(findings, list):
        return [
            {
                "rule_id": "STATE_RECONCILE_PRE_VERIFY_UNKNOWN_FAILURE",
                "severity": "error",
                "message": "State verify failed before reconciliation without structured findings.",
                "path": STATE_ROOT.as_posix(),
                "recommendation": "Repair state verification failures before running confirmed reconciliation.",
            }
        ]

    changed = set(changed_sidecars)
    blocking: list[dict[str, object]] = []
    for finding in findings:
        if not isinstance(finding, Mapping):
            blocking.append(
                {
                    "rule_id": "STATE_RECONCILE_PRE_VERIFY_UNSTRUCTURED_FINDING",
                    "severity": "error",
                    "message": str(finding),
                    "path": STATE_ROOT.as_posix(),
                    "recommendation": "Repair state verification failures before running confirmed reconciliation.",
                }
            )
            continue
        rule_id = _text(finding.get("rule_id"))
        reconcilable_sidecars = PRE_VERIFY_RECONCILABLE_RULES.get(rule_id)
        if reconcilable_sidecars is not None and not changed.isdisjoint(reconcilable_sidecars):
            continue
        blocking.append(dict(finding))
    return blocking


def _receipt_ref(timestamp: str, diff: Iterable[Mapping[str, Any]]) -> str:
    stable = hashlib.sha256(_canonical_json(list(diff)).encode("utf-8")).hexdigest()[:12]
    safe_timestamp = timestamp.replace(":", "").replace("-", "")
    return (RECEIPT_ROOT / f"STATE_RECONCILE_{safe_timestamp}_{stable}.json").as_posix()


def _receipt_payload(
    root: Path,
    command: str,
    timestamp: str,
    plan: ReconciliationPlan,
    files_written: list[str],
    pre_verify: Mapping[str, object],
    post_verify: Mapping[str, object],
) -> dict[str, Any]:
    correction_route = correction_routing.from_transition_evidence(root, plan.transition_engine)
    return {
        "receipt_type": "STATE_RECONCILIATION_RECEIPT",
        "receipt_schema_version": "1.0.0",
        "command": command,
        "root": str(root),
        "created_at": timestamp,
        "created_by": "orchestrator",
        "mutation_type": "structured_state_reconciliation",
        "sidecars_changed": list(plan.changed_sidecars),
        "diff": list(plan.diff),
        "files_written": sorted(dict.fromkeys(files_written)),
        "state_verify_before": _summary_from_verify(pre_verify),
        "state_verify_after": _summary_from_verify(post_verify),
        "transition_engine": plan.transition_engine,
        "correction_routing": correction_route,
        "evidence_summary": {
            "state_sidecars": plan.evidence.get("state_sidecars", []),
            "lifecycle_log": plan.evidence.get("lifecycle_log", {}),
            "profile_result_count": plan.evidence.get("results", {}).get("profile_result_count", 0)
            if isinstance(plan.evidence.get("results"), Mapping)
            else 0,
            "audit_result_count": plan.evidence.get("results", {}).get("audit_result_count", 0)
            if isinstance(plan.evidence.get("results"), Mapping)
            else 0,
            "artifact_receipt_count": plan.evidence.get("artifact_receipts", {}).get("count", 0)
            if isinstance(plan.evidence.get("artifact_receipts"), Mapping)
            else 0,
            "correction_record_count": plan.evidence.get("correction_resolution_records", {}).get("count", 0)
            if isinstance(plan.evidence.get("correction_resolution_records"), Mapping)
            else 0,
            "checkpoint_receipt_count": plan.evidence.get("checkpoint_receipts", {}).get("count", 0)
            if isinstance(plan.evidence.get("checkpoint_receipts"), Mapping)
            else 0,
        },
    }


def _write_receipt(root: Path, receipt_ref: str, payload: Mapping[str, Any]) -> None:
    path = root / receipt_ref
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(path, payload)


def _replace_planned_timestamp(value: object, timestamp: str) -> object:
    if value == PLANNED_TIMESTAMP:
        return timestamp
    if isinstance(value, list):
        return [_replace_planned_timestamp(item, timestamp) for item in value]
    if isinstance(value, dict):
        return {key: _replace_planned_timestamp(item, timestamp) for key, item in value.items()}
    return value


def reconcile_state(
    root: Path,
    *,
    confirm_write: bool = False,
    command: str = "state reconcile",
) -> dict[str, Any]:
    if not root.exists() or not root.is_dir():
        return {
            "tool": "aso",
            "command": command,
            "root": str(root),
            "status": "blocked",
            "dry_run": not confirm_write,
            "read_only": True,
            "mutations_performed": False,
            "findings": [
                {
                    "rule_id": "STATE_RECONCILE_ROOT_UNREADABLE",
                    "severity": "error",
                    "message": f"--root does not point at a readable workspace directory: {root}",
                    "path": "",
                    "recommendation": "Pass --root pointing at an initialized ASO workspace.",
                }
            ],
            "diff": [],
            "diff_count": 0,
            "changed_sidecars": [],
            "planned_files": [],
            "files_written": [],
            "receipt_ref": "",
            "transition_engine": {},
            "evidence": {},
            "expected_values": {},
        }
    plan = build_reconciliation_plan(root)
    dry_run = not confirm_write
    base_report: dict[str, Any] = {
        "tool": "aso",
        "command": command,
        "root": str(root),
        "status": plan.status if dry_run else ("blocked" if plan.blocked else plan.status),
        "dry_run": dry_run,
        "read_only": dry_run,
        "mutations_performed": False,
        "findings": list(plan.findings),
        "diff": list(plan.diff),
        "diff_count": len(plan.diff),
        "changed_sidecars": list(plan.changed_sidecars),
        "planned_files": list(plan.files_planned),
        "files_written": [],
        "receipt_ref": "",
        "transition_engine": plan.transition_engine,
        "evidence": plan.evidence,
        "expected_values": {
            sidecar_type: _content(plan.updated_sidecars.get(sidecar_type, {}))
            for sidecar_type in ("TASK_REGISTRY", "CURRENT_GATE", "NEXT_ACTION", "PROJECT_STATE")
            if sidecar_type in plan.updated_sidecars
        },
    }
    if dry_run or plan.blocked or plan.status in {"no_state_sidecars", "no_changes"}:
        if plan.blocked:
            base_report["read_only"] = True
        if confirm_write and plan.status == "no_changes":
            base_report["status"] = "no_changes"
        return base_report

    pre_verify, _pre_exit = _state_verify_report(root)
    blocking_pre_verify = _pre_verify_blocking_findings(pre_verify, plan.changed_sidecars) if _pre_exit != 0 else []
    if blocking_pre_verify:
        base_report["status"] = "blocked"
        base_report["read_only"] = True
        base_report["state_verify_before"] = pre_verify
        base_report["state_verify_before_blocking_findings"] = blocking_pre_verify
        base_report["findings"] = [
            *list(plan.findings),
            {
                "rule_id": "STATE_RECONCILE_PRE_VERIFY_FAILED",
                "severity": "error",
                "message": "State verify failed before confirmed reconciliation with non-reconcilable findings; no writes were performed.",
                "path": STATE_ROOT.as_posix(),
                "recommendation": "Repair state_verify_before findings before running confirmed state reconciliation.",
            },
        ]
        return base_report
    timestamp = utc_timestamp()
    files_written: list[str] = []
    changed_payloads = {
        sidecar_type: _replace_planned_timestamp(copy.deepcopy(plan.updated_sidecars[sidecar_type]), timestamp)
        for sidecar_type in plan.changed_sidecars
    }
    try:
        for sidecar_type in sorted(changed_payloads):
            payload = changed_payloads[sidecar_type]
            _touch(payload, timestamp)
            path = root / STATE_ROOT / f"{sidecar_type}.json"
            _write_json(path, payload)
            files_written.append(path.relative_to(root).as_posix())
            if _sync_markdown(root, payload):
                markdown_source = _text(payload.get("markdown_source"))
                if markdown_source:
                    files_written.append(markdown_source)
    except OSError as exc:
        base_report["status"] = "failed"
        base_report["error"] = str(exc)
        base_report["files_written"] = sorted(dict.fromkeys(files_written))
        return base_report

    post_verify, post_exit = _state_verify_report(root)
    receipt_ref = _receipt_ref(timestamp, plan.diff)
    receipt = _receipt_payload(root, command, timestamp, plan, files_written, pre_verify, post_verify)
    try:
        _write_receipt(root, receipt_ref, receipt)
        files_written.append(receipt_ref)
    except OSError as exc:
        base_report["status"] = "failed"
        base_report["error"] = str(exc)
        base_report["files_written"] = sorted(dict.fromkeys(files_written))
        return base_report

    base_report["status"] = "written" if post_exit == 0 else "written_with_verify_findings"
    base_report["read_only"] = False
    base_report["mutations_performed"] = True
    base_report["files_written"] = sorted(dict.fromkeys(files_written))
    base_report["receipt_ref"] = receipt_ref
    base_report["receipt"] = receipt
    base_report["state_verify_before"] = pre_verify
    base_report["state_verify_after"] = post_verify
    if post_exit != 0:
        base_report["findings"] = [
            *list(plan.findings),
            {
                "rule_id": "STATE_RECONCILE_POST_VERIFY_FAILED",
                "severity": "error",
                "message": "State verify failed after confirmed reconciliation.",
                "path": STATE_ROOT.as_posix(),
                "recommendation": "Inspect state_verify_after findings before continuing runtime operations.",
            },
        ]
    return base_report


def materialize_after_confirmed_write(root: Path) -> MaterializationResult:
    """Update existing canonical sidecars from lifecycle evidence."""
    report = reconcile_state(root, confirm_write=True, command="state materialize")
    status = str(report.get("status", "failed"))
    if status == "changes_pending":
        status = "failed"
    if status == "written_with_verify_findings":
        return MaterializationResult(
            status,
            tuple(str(item) for item in report.get("files_written", []) if isinstance(item, str)),
            "state verify failed after reconciliation",
            receipt_ref=str(report.get("receipt_ref", "")),
            diff_count=int(report.get("diff_count", 0)),
            state_verify_after_status=str(
                report.get("state_verify_after", {}).get("status", "")
                if isinstance(report.get("state_verify_after"), Mapping)
                else ""
            ),
        )
    return MaterializationResult(
        status,
        tuple(str(item) for item in report.get("files_written", []) if isinstance(item, str)),
        str(report.get("error", "")),
        receipt_ref=str(report.get("receipt_ref", "")),
        diff_count=int(report.get("diff_count", 0)),
        state_verify_after_status=str(
            report.get("state_verify_after", {}).get("status", "")
            if isinstance(report.get("state_verify_after"), Mapping)
            else ""
        ),
    )
