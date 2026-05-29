"""Internal state sidecar materialization after confirmed lifecycle writes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from . import transition_engine
from .timestamps import utc_timestamp


STATE_ROOT = Path("project-runtime/state")
NONE = "NONE"


@dataclass(frozen=True)
class MaterializationResult:
    status: str
    files_written: tuple[str, ...]
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status in {"written", "no_state_sidecars"}

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "files_written": list(self.files_written),
        }
        if self.error:
            payload["error"] = self.error
        return payload


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


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
        "AUDIT_RESULT_RECEIVED": audit_result_event,
        "artifact_accepted": "ARTIFACT_ACCEPTED",
        "ARTIFACT_ACCEPTED": "ARTIFACT_ACCEPTED",
        "agent_instance_terminated": "AGENT_TERMINATED",
        "AGENT_TERMINATED": "AGENT_TERMINATED",
        "auditor_agent_terminated": "AGENT_TERMINATED",
        "AUDITOR_AGENT_TERMINATED": "AGENT_TERMINATED",
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
        elif event_name == "AUDIT_ROUTE_READY" and role != "auditor":
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
        return "yes" if value else "no"
    if isinstance(value, list):
        return "NONE" if not value else ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return "NONE" if not value else json.dumps(value, sort_keys=True)
    return str(value)


def _sync_markdown(root: Path, payload: Mapping[str, Any]) -> bool:
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
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


def materialize_after_confirmed_write(root: Path) -> MaterializationResult:
    """Update existing canonical sidecars from lifecycle evidence."""

    sidecars = _sidecars(root)
    if not any(key in sidecars for key in ("PROJECT_STATE", "TASK_REGISTRY", "NEXT_ACTION", "CURRENT_GATE", "ACCEPTED_ARTIFACTS")):
        return MaterializationResult("no_state_sidecars", ())
    events = _events(sidecars)
    if not events:
        return MaterializationResult("no_lifecycle_events", ())

    timestamp = utc_timestamp()
    changed: dict[str, dict[str, Any]] = {}
    try:
        if "TASK_REGISTRY" in sidecars and _materialize_task_registry(sidecars["TASK_REGISTRY"], events, timestamp):
            changed["TASK_REGISTRY"] = sidecars["TASK_REGISTRY"]
        if "ACCEPTED_ARTIFACTS" in sidecars and _merge_accepted_artifacts(root, sidecars["ACCEPTED_ARTIFACTS"], events, timestamp):
            changed["ACCEPTED_ARTIFACTS"] = sidecars["ACCEPTED_ARTIFACTS"]

        # Recompute route-facing sidecars after registry/artifact evidence is present.
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
    except (OSError, transition_engine.RuntimeContractError) as exc:
        return MaterializationResult("failed", (), str(exc))

    files_written: list[str] = []
    try:
        for sidecar_type, payload in changed.items():
            _touch(payload, timestamp)
            path = root / STATE_ROOT / f"{sidecar_type}.json"
            _write_json(path, payload)
            files_written.append(path.relative_to(root).as_posix())
            if _sync_markdown(root, payload):
                markdown_source = _text(payload.get("markdown_source"))
                if markdown_source:
                    files_written.append(markdown_source)
    except OSError as exc:
        return MaterializationResult("failed", tuple(files_written), str(exc))

    return MaterializationResult("written", tuple(sorted(dict.fromkeys(files_written))))
