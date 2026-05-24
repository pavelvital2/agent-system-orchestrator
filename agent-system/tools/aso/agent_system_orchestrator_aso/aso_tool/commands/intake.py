"""Raw TZ intake bootstrap command."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_USAGE = 2
EXIT_WRITE_ERROR = 4

TASK_ID = "TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001"
TASK_PACKET = Path("project-runtime/bootstrap") / f"{TASK_ID}.md"
TARGET_ROLE = "requirements_analyst"
UPDATED_AT = "2026-05-21T00:00:00Z"


def _json_bytes(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _write_json(path_text: str | None, payload: dict[str, Any]) -> bool:
    if not path_text:
        return True
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso intake bootstrap: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(_json_bytes(payload), encoding="utf-8")
    except OSError as exc:
        print(f"aso intake bootstrap: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def _receipt(
    *,
    root: Path,
    status: str,
    tz_path: str,
    mutations_performed: bool,
    message: str = "",
) -> dict[str, Any]:
    payload = {
        "status": status,
        "task_id": TASK_ID,
        "task_packet": TASK_PACKET.as_posix(),
        "target_role": TARGET_ROLE,
        "tz_path": tz_path,
        "next_action": "CREATE_AGENT",
        "mutations_performed": mutations_performed,
        "root": str(root),
    }
    if message:
        payload["message"] = message
    return payload


def _blocked(root: Path, tz_path: str, message: str, args: argparse.Namespace, exit_code: int = EXIT_BLOCKED) -> int:
    receipt = _receipt(root=root, status="blocked", tz_path=tz_path, mutations_performed=False, message=message)
    print(f"aso intake bootstrap: {message}", file=sys.stderr)
    if args.json_out and not _write_json(args.json_out, receipt):
        return EXIT_WRITE_ERROR
    print(_json_bytes(receipt), end="")
    return exit_code


def _workspace_relative_path(root: Path, value: str) -> tuple[Path | None, str]:
    raw = Path(value).expanduser()
    candidate = raw if raw.is_absolute() else root / raw
    resolved_root = root.resolve(strict=False)
    resolved_candidate = candidate.resolve(strict=False)
    try:
        relpath = resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return None, "--tz must point to a workspace-local file"
    if relpath == Path(".") or ".." in relpath.parts:
        return None, "--tz must point to a workspace-local file"
    if not candidate.is_file():
        return None, f"--tz file is missing or unreadable: {value}"
    try:
        text = candidate.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"--tz file is not readable: {exc}"
    if not text.strip():
        return None, f"--tz file is empty: {value}"
    return relpath, ""


def _load_sidecar(root: Path, filename: str) -> tuple[dict[str, Any] | None, str]:
    path = root / "project-runtime" / "state" / filename
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, f"state sidecar is missing or unreadable: {path}: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"state sidecar is invalid JSON: {path}: {exc}"
    if not isinstance(payload, dict) or not isinstance(payload.get("content"), dict):
        return None, f"state sidecar has invalid envelope/content: {path}"
    return payload, ""


def _write_sidecar(root: Path, filename: str, payload: dict[str, Any]) -> None:
    path = root / "project-runtime" / "state" / filename
    path.write_text(_json_bytes(payload), encoding="utf-8")


def _task_entry() -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "task_title": "Bootstrap raw TZ intake for requirements analysis",
        "task_type": TARGET_ROLE,
        "task_kind": "bootstrap",
        "owner_role": TARGET_ROLE,
        "status": "ready",
        "task_packet": TASK_PACKET.as_posix(),
        "dependencies": [],
        "requested_by_role": "NONE",
        "requested_by_task": "NONE",
        "return_to_requester_after_audit_pass": False,
        "return_to_role_after_audit_pass": "none",
        "return_task_after_audit_pass": "NONE",
        "research_question_id": "NONE",
        "result_refs": [],
        "audit_refs": [],
        "correction_links": [],
        "commit_hash": "NONE",
        "branch": "NONE",
        "push_status": "not_required",
        "accepted_files": [],
        "checkpoint_ref": "NONE",
        "created_at": UPDATED_AT,
        "updated_at": UPDATED_AT,
    }


def _next_action(tz_path: str) -> dict[str, Any]:
    return {
        "action_id": "ACTION-BOOTSTRAP-REQUIREMENTS-001",
        "action_type": "create_agent",
        "target_role": TARGET_ROLE,
        "task_id": TASK_ID,
        "task_packet": TASK_PACKET.as_posix(),
        "dependency_status": "ready",
        "blocked_by": [],
        "action_semantic": "normal",
        "workspace_identity_required": False,
        "repository_lock_required": False,
        "checkpoint_policy": "no_checkpoint",
        "checkpoint_preflight_required": False,
        "checkpoint_receipt_required": False,
        "checkpoint_receipt_ref": "NONE",
        "requester_return_context": "NONE",
        "blocking_or_resume_context": "NONE",
        "required_universal_docs": [],
        "required_project_docs": [tz_path],
        "expected_result": ["requirements analysis result package"],
        "instruction_for_orchestrator": "Create one requirements_analyst profile agent for the bounded raw-TZ bootstrap task packet. Do not interpret product requirements in the orchestrator.",
    }


def _current_gate() -> dict[str, Any]:
    return {
        "gate_id": "GATE-BOOTSTRAP-REQUIREMENTS-001",
        "gate_name": "Raw TZ intake bootstrap dispatch",
        "gate_type": "bootstrap",
        "status": "open",
        "owner_role": "orchestrator",
        "task_id": TASK_ID,
        "task_packet": TASK_PACKET.as_posix(),
        "action_semantic": "normal",
        "workspace_identity_status": "not_checked",
        "repository_lock_status": "draft",
        "baseline_tracking_status": "not_checked",
        "checkpoint_eligibility": "local_only",
        "checkpoint_eligibility_status": "not_checked",
        "project_checkpoint_status": "not_required",
        "entry_criteria": ["workspace-local TZ file exists and is readable"],
        "exit_criteria": ["requirements_analyst returns a governed result package"],
        "required_next_role": TARGET_ROLE,
        "gate_evidence": [],
        "blocking_status": "NONE",
        "notes": ["Created by aso intake bootstrap without product interpretation."],
    }


def _task_packet_text(tz_path: str) -> str:
    return f"""# TASK PACKET

```text
TASK_ID: {TASK_ID}
TASK_STATUS: ready
TASK_KIND: bootstrap
TASK_TYPE: {TARGET_ROLE}
TARGET_ROLE: {TARGET_ROLE}
```

## Purpose

Create the first bounded requirements analysis from the raw TZ document.

## Scope In

- Read `{tz_path}` as the authoritative raw TZ input.
- Identify requirements, ambiguities, conflicts, and owner questions for downstream governed work.
- Produce a requirements analysis result package using ASO result conventions.

## Scope Out

- Do not implement product logic.
- Do not generate product source files.
- Do not dispatch additional agents.
- Do not bypass audit, correction, or checkpoint gates.

## Expected Outputs

- Requirements analysis result package with traceability to `{tz_path}`.
- Explicit conflict, ambiguity, and owner-question notes when present.

## Allowed File Changes

- project-runtime/results/**
- project-docs/requirements/**

## Acceptance Criteria

- The raw TZ file remains the source of truth.
- Product implementation is deferred to downstream governed tasks.
- The result is ready for audit routing.
"""


def _same_task(existing: dict[str, Any], tz_path: str) -> bool:
    expected = _task_entry()
    for key, value in expected.items():
        if existing.get(key) != value:
            return False
    return True


def _apply_payloads(root: Path, tz_path: str) -> tuple[str, list[tuple[str, dict[str, Any]]], str]:
    project_state, error = _load_sidecar(root, "PROJECT_STATE.json")
    if error:
        return "blocked", [], error
    task_registry, error = _load_sidecar(root, "TASK_REGISTRY.json")
    if error:
        return "blocked", [], error
    next_action, error = _load_sidecar(root, "NEXT_ACTION.json")
    if error:
        return "blocked", [], error
    current_gate, error = _load_sidecar(root, "CURRENT_GATE.json")
    if error:
        return "blocked", [], error

    registry_content = task_registry["content"]
    tasks = registry_content.get("tasks")
    if not isinstance(tasks, list):
        return "blocked", [], "TASK_REGISTRY.content.tasks must be a list"

    matching = [task for task in tasks if isinstance(task, dict) and task.get("task_id") == TASK_ID]
    expected_task = _task_entry()
    expected_next = _next_action(tz_path)
    expected_gate = _current_gate()
    packet_path = root / TASK_PACKET
    packet_exists = packet_path.is_file()

    if matching:
        if len(matching) > 1:
            return "blocked", [], f"duplicate task id already exists: {TASK_ID}"
        if not _same_task(matching[0], tz_path):
            return "blocked", [], f"task id already exists with incompatible content: {TASK_ID}"
        already = (
            next_action["content"] == expected_next
            and current_gate["content"] == expected_gate
            and project_state["content"].get("tz_path") == tz_path
            and packet_exists
            and packet_path.read_text(encoding="utf-8") == _task_packet_text(tz_path)
        )
        if already:
            return "already_exists", [], "bootstrap task already exists"
        return "blocked", [], f"task id already exists but bootstrap state is incomplete: {TASK_ID}"

    tasks.append(expected_task)
    registry_content["registry_revision"] = int(registry_content.get("registry_revision", 1)) + 1
    project_state["content"]["tz_path"] = tz_path
    next_action["content"] = expected_next
    current_gate["content"] = expected_gate
    return "created", [
        ("PROJECT_STATE.json", project_state),
        ("TASK_REGISTRY.json", task_registry),
        ("NEXT_ACTION.json", next_action),
        ("CURRENT_GATE.json", current_gate),
    ], ""


def run_bootstrap(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    if not root.exists() or not root.is_dir():
        return _blocked(root, "", "--root must be an existing workspace directory", args, EXIT_USAGE)
    root = root.resolve(strict=False)
    if args.target_role != TARGET_ROLE:
        return _blocked(root, "", f"--target-role must be {TARGET_ROLE}", args, EXIT_USAGE)

    tz_relpath, error = _workspace_relative_path(root, args.tz)
    if tz_relpath is None:
        return _blocked(root, args.tz, error, args, EXIT_USAGE)
    tz_path = tz_relpath.as_posix()

    status, payloads, message = _apply_payloads(root, tz_path)
    if status == "blocked":
        return _blocked(root, tz_path, message, args)

    if not args.confirm_write:
        receipt = _receipt(
            root=root,
            status="blocked",
            tz_path=tz_path,
            mutations_performed=False,
            message="writes require --confirm-write",
        )
        if args.json_out and not _write_json(args.json_out, receipt):
            return EXIT_WRITE_ERROR
        print(_json_bytes(receipt), end="")
        return EXIT_BLOCKED

    if status == "created":
        try:
            packet_path = root / TASK_PACKET
            packet_path.parent.mkdir(parents=True, exist_ok=True)
            packet_path.write_text(_task_packet_text(tz_path), encoding="utf-8")
            for filename, payload in payloads:
                _write_sidecar(root, filename, payload)
        except OSError as exc:
            return _blocked(root, tz_path, f"failed to write bootstrap state: {exc}", args, EXIT_WRITE_ERROR)

    receipt = _receipt(
        root=root,
        status=status,
        tz_path=tz_path,
        mutations_performed=(status == "created"),
        message=message,
    )
    if args.json_out and not _write_json(args.json_out, receipt):
        return EXIT_WRITE_ERROR
    print(_json_bytes(receipt), end="")
    return EXIT_OK
