"""Guarded Runtime Schema 3.1.1 workspace state initializer."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, NamedTuple

from .. import runtime_schema_contracts
from ..timestamps import DETERMINISTIC_TIMESTAMP, utc_timestamp


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_UNSAFE = 3
EXIT_WRITE_ERROR = 4

UPDATED_AT = DETERMINISTIC_TIMESTAMP
UPDATED_BY = "orchestrator"
NONE = "NONE"

SIDECAR_FILENAMES = (
    "PROJECT_STATE.json",
    "TASK_REGISTRY.json",
    "NEXT_ACTION.json",
    "CURRENT_GATE.json",
    "WORKSPACE_IDENTITY.json",
    "REPOSITORY_LOCK.json",
    "ACCEPTED_ARTIFACTS.json",
    "CHECKPOINT_STATE.json",
    "SCHEMA_MANIFEST.json",
)

CANONICAL_TZ_PATH = Path("project-input") / "TZ.md"
RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
TIMESTAMP_SENTINEL = "<runtime-timestamp>"
PLACEHOLDER_STATUS_KEY = "STATUS"
PLACEHOLDER_STATUS_VALUE = "placeholder"
PLACEHOLDER_MUST_REPLACE_KEY = "MUST_REPLACE_BEFORE_LIFECYCLE"

MARKDOWN_SOURCES = {
    "PROJECT_STATE": "project-runtime/PROJECT_STATE.md",
    "TASK_REGISTRY": "project-runtime/TASK_REGISTRY.md",
    "NEXT_ACTION": "project-runtime/NEXT_ACTION.md",
    "CURRENT_GATE": "project-runtime/CURRENT_GATE.md",
    "WORKSPACE_IDENTITY": "project-runtime/WORKSPACE_IDENTITY.md",
    "REPOSITORY_LOCK": "project-runtime/REPOSITORY_LOCK.md",
    "ACCEPTED_ARTIFACTS": "project-runtime/ACCEPTED_ARTIFACTS.md",
    "CHECKPOINT_STATE": "project-runtime/CHECKPOINT_STATE.md",
    "SCHEMA_MANIFEST": "project-runtime/SCHEMA_MANIFEST.md",
}


class TzSelection(NamedTuple):
    tz_path: Path
    source_path: Path | None
    explicit_tz_path: Path | None
    copy_to_canonical: bool
    detail: str


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "workspace"


def _workspace_id(project_slug: str) -> str:
    return "WORKSPACE-" + re.sub(r"[^A-Z0-9]+", "-", project_slug.upper()).strip("-")


def _run_git(root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError:
        return NONE
    if result.returncode != 0:
        return NONE
    value = result.stdout.strip()
    return value or NONE


def _actual_branch(root: Path) -> str:
    return _run_git(root, ["branch", "--show-current"])


def _actual_remote(root: Path) -> str:
    return _run_git(root, ["config", "--get", "remote.origin.url"])


def _is_package_root(root: Path) -> bool:
    return (
        (root / "agent-system" / "tools" / "aso" / "aso.py").is_file()
        and (root / "pyproject.toml").is_file()
    )


def _envelope(sidecar_type: str, content: dict[str, Any], *, updated_at: str) -> dict[str, Any]:
    return {
        "content": content,
        "markdown_source": MARKDOWN_SOURCES[sidecar_type],
        "runtime_schema_version": runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION,
        "schema_version": runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION,
        "sidecar_type": sidecar_type,
        "state_revision": 1,
        "updated_at": updated_at,
        "updated_by": UPDATED_BY,
    }


def _initial_sidecars(
    *,
    root: Path,
    project_name: str,
    project_slug: str,
    tz_path: Path,
    profile: str,
    repo_url: str,
    branch: str,
    package_version: str,
    runtime_schema_version: str,
    probe_git: bool = True,
    updated_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    timestamp = updated_at or utc_timestamp()
    root_text = str(root.resolve(strict=False))
    workspace_id = _workspace_id(project_slug)
    effective_repo_url = repo_url or NONE
    effective_branch = branch or NONE
    actual_remote = _actual_remote(root) if probe_git else NONE
    actual_branch = _actual_branch(root) if probe_git else NONE
    git_toplevel_actual = _run_git(root, ["rev-parse", "--show-toplevel"]) if probe_git else NONE

    return {
        "PROJECT_STATE.json": _envelope(
            "PROJECT_STATE",
            {
                "project_name": project_name,
                "project_slug": project_slug,
                "project_root": root_text,
                "tz_path": tz_path.as_posix(),
                "active_doc_root": "project-docs",
                "package_version": package_version,
                "governance_ruleset_version": runtime_schema_contracts.ACTIVE_GOVERNANCE_RULESET_VERSION,
                "runtime_schema_version": runtime_schema_version,
                "workspace_type": "project_workspace",
                "workspace_identity_ref": "project-runtime/state/WORKSPACE_IDENTITY.json",
                "repository_lock_ref": "project-runtime/state/REPOSITORY_LOCK.json",
                "project_root_expected": root_text,
                "git_toplevel_actual": git_toplevel_actual,
                "expected_remote": effective_repo_url,
                "actual_remote": actual_remote,
                "expected_git_remote": effective_repo_url,
                "actual_git_remote": actual_remote,
                "expected_branch": effective_branch,
                "actual_branch": actual_branch,
                "push_allowed": False,
                "identity_validation_status": "not_checked",
                "identity_validation_error": NONE,
                "identity_validation_evidence": "state init recorded local workspace identity without publishing.",
                "repository_lock_status": "draft",
                "baseline_tracking_status": "not_checked",
                "project_input_tracking_policy": "owner-private/untracked",
                "checkpoint_eligibility": "local_only",
                "audit_status": "not_applicable",
                "checkpoint_eligibility_status": "not_checked",
                "checkpoint_preflight_status": "not_run",
                "checkpoint_preflight_ref": NONE,
                "checkpoint_receipt_ref": NONE,
                "commit_status": "not_required",
                "last_commit_hash": NONE,
                "last_commit_branch": NONE,
                "push_status": "not_required",
                "last_push_remote": NONE,
                "last_push_branch": NONE,
                "last_push_target_status": "not_required",
                "project_checkpoint_status": "not_required",
                "checkpoint_blocked_by": [],
                "last_checkpoint_failure_reason": NONE,
                "current_phase": "bootstrap",
                "project_status": "active",
                "action_semantic": "normal",
                "semantic_reason": "Initial Runtime Schema 3.1.1 state created by aso state init.",
                "active_branches": [],
                "completed_milestones": [],
                "active_risks": [],
                "active_blockers": [],
                "active_gaps": [],
                "last_accepted_result": NONE,
            },
            updated_at=timestamp,
        ),
        "TASK_REGISTRY.json": _envelope("TASK_REGISTRY", {"registry_revision": 1, "tasks": []}, updated_at=timestamp),
        "NEXT_ACTION.json": _envelope(
            "NEXT_ACTION",
            {
                "action_id": "ACTION-BOOTSTRAP-PREP-001",
                "action_type": "correction",
                "target_role": "orchestrator",
                "task_id": NONE,
                "task_packet": NONE,
                "dependency_status": "ready",
                "blocked_by": [],
                "action_semantic": "normal",
                "workspace_identity_required": False,
                "repository_lock_required": False,
                "checkpoint_policy": "no_checkpoint",
                "checkpoint_preflight_required": False,
                "checkpoint_receipt_required": False,
                "checkpoint_receipt_ref": NONE,
                "requester_return_context": NONE,
                "blocking_or_resume_context": NONE,
                "required_universal_docs": [],
                "required_project_docs": [],
                "expected_result": [],
                "instruction_for_orchestrator": "Runtime state is initialized; materialize Markdown views, verify bootstrap inputs, then create exactly one valid bootstrap task packet before first profile-agent dispatch.",
            },
            updated_at=timestamp,
        ),
        "CURRENT_GATE.json": _envelope(
            "CURRENT_GATE",
            {
                "gate_id": "GATE-STATE-INIT-001",
                "gate_name": "Initial runtime state",
                "gate_type": "bootstrap",
                "status": "open",
                "owner_role": "orchestrator",
                "task_id": NONE,
                "task_packet": NONE,
                "action_semantic": "normal",
                "workspace_identity_status": "not_checked",
                "repository_lock_status": "draft",
                "baseline_tracking_status": "not_checked",
                "checkpoint_eligibility": "local_only",
                "checkpoint_eligibility_status": "not_checked",
                "project_checkpoint_status": "not_required",
                "entry_criteria": [],
                "exit_criteria": [],
                "required_next_role": "orchestrator",
                "gate_evidence": [],
                "blocking_status": NONE,
                "notes": [],
            },
            updated_at=timestamp,
        ),
        "WORKSPACE_IDENTITY.json": _envelope(
            "WORKSPACE_IDENTITY",
            {
                "workspace_id": workspace_id,
                "project_slug": project_slug,
                "workspace_type": "project_workspace",
                "expected_git_remote": effective_repo_url,
                "actual_git_remote": actual_remote,
                "expected_branch": effective_branch,
                "actual_branch": actual_branch,
                "identity_validation_status": "not_required",
                "repository_lock_status": "pending",
                "push_allowed": False,
                "validated_at": timestamp,
                "validation_errors": [],
            },
            updated_at=timestamp,
        ),
        "REPOSITORY_LOCK.json": _envelope(
            "REPOSITORY_LOCK",
            {
                "lock_status": "draft",
                "project_slug": project_slug,
                "repo_url": effective_repo_url,
                "branch": effective_branch,
                "push_allowed": False,
                "created_at": timestamp,
            },
            updated_at=timestamp,
        ),
        "ACCEPTED_ARTIFACTS.json": _envelope("ACCEPTED_ARTIFACTS", {"artifacts": []}, updated_at=timestamp),
        "CHECKPOINT_STATE.json": _envelope(
            "CHECKPOINT_STATE",
            {
                "checkpoint_status": "not_required",
                "checkpoint_receipts": [],
                "last_checkpoint_ref": NONE,
            },
            updated_at=timestamp,
        ),
        "SCHEMA_MANIFEST.json": _envelope(
            "SCHEMA_MANIFEST",
            {
                "state_root": runtime_schema_contracts.STATE_ROOT,
                "runtime_schema_version": runtime_schema_version,
                "package_version": package_version,
                "created_by_profile": profile,
                "sidecars": list(SIDECAR_FILENAMES),
            },
            updated_at=timestamp,
        ),
    }


def _json_bytes(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _build_plan(root: Path, sidecars: dict[str, dict[str, Any]], dry_run: bool, tz_path: Path) -> dict[str, Any]:
    state_root = root / "project-runtime" / "state"
    tz_abs = root / tz_path
    writes = []
    if not tz_abs.exists():
        writes.append(
            {
                "path": str(tz_abs),
                "sidecar_type": NONE,
                "state_revision": NONE,
            }
        )
    writes.extend(
        {
            "path": str(state_root / filename),
            "sidecar_type": payload["sidecar_type"],
            "state_revision": payload["state_revision"],
        }
        for filename, payload in sorted(sidecars.items())
    )
    return {
        "command": "state init",
        "dry_run": dry_run,
        "package_version": runtime_schema_contracts.ACTIVE_PACKAGE_VERSION,
        "root": str(root),
        "runtime_schema_version": runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION,
        "state_root": str(state_root),
        "status": "planned",
        "writes": writes,
    }


def _fail(message: str, exit_code: int = EXIT_UNSAFE) -> int:
    print(f"aso state init: {message}", file=sys.stderr)
    return exit_code


def _workspace_relative_existing_tz_path(root: Path, value: str) -> tuple[Path | None, str]:
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
    placeholder_error = _tz_placeholder_error(relpath, text)
    if placeholder_error:
        return None, placeholder_error
    return relpath, ""


def _metadata_value(line: str, key: str) -> str | None:
    prefix = f"{key}:"
    if not line.upper().startswith(prefix):
        return None
    return line[len(prefix):].strip()


def is_placeholder_tz_text(text: str) -> bool:
    status_placeholder = False
    must_replace = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        status = _metadata_value(line, PLACEHOLDER_STATUS_KEY)
        if status is not None and status.lower() == PLACEHOLDER_STATUS_VALUE:
            status_placeholder = True
        must_replace_value = _metadata_value(line, PLACEHOLDER_MUST_REPLACE_KEY)
        if must_replace_value is not None and must_replace_value.lower() == "true":
            must_replace = True
    return status_placeholder or must_replace


def _tz_placeholder_error(relpath: Path, text: str) -> str:
    if not is_placeholder_tz_text(text):
        return ""
    return (
        f"{relpath.as_posix()} is a placeholder TZ document; replace it with a real "
        "workspace-local TZ document before lifecycle bootstrap"
    )


def tz_placeholder_status(root: Path, relpath: Path) -> tuple[bool, str]:
    path = root / relpath
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"{relpath.as_posix()} is missing or unreadable: {exc}"
    error = _tz_placeholder_error(relpath, text)
    if error:
        return True, error
    return False, f"{relpath.as_posix()} is not marked as a placeholder"


def select_canonical_tz(root: Path, value: str | None) -> tuple[TzSelection | None, str]:
    canonical_abs = root / CANONICAL_TZ_PATH
    if not value:
        if canonical_abs.exists() and not canonical_abs.is_file():
            return None, f"{CANONICAL_TZ_PATH.as_posix()} exists but is not a file"
        if not canonical_abs.is_file():
            return None, "--tz is required when project-input/TZ.md is absent"
        try:
            canonical_text = canonical_abs.read_text(encoding="utf-8")
        except OSError as exc:
            return None, f"{CANONICAL_TZ_PATH.as_posix()} is not readable: {exc}"
        if not canonical_text.strip():
            return None, f"{CANONICAL_TZ_PATH.as_posix()} exists but is empty"
        placeholder_error = _tz_placeholder_error(CANONICAL_TZ_PATH, canonical_text)
        if placeholder_error:
            return None, placeholder_error
        return TzSelection(CANONICAL_TZ_PATH, canonical_abs, None, False, "canonical TZ path selected"), ""

    explicit_relpath, error = _workspace_relative_existing_tz_path(root, value)
    if explicit_relpath is None:
        return None, error
    if explicit_relpath == CANONICAL_TZ_PATH:
        return TzSelection(CANONICAL_TZ_PATH, canonical_abs, explicit_relpath, False, "canonical TZ path selected"), ""

    if canonical_abs.exists():
        if not canonical_abs.is_file():
            return None, f"{CANONICAL_TZ_PATH.as_posix()} exists but is not a file"
        try:
            canonical_text = canonical_abs.read_text(encoding="utf-8")
        except OSError as exc:
            return None, f"{CANONICAL_TZ_PATH.as_posix()} is not readable: {exc}"
        if not canonical_text.strip():
            return None, f"{CANONICAL_TZ_PATH.as_posix()} exists but is empty"
        if is_placeholder_tz_text(canonical_text):
            detail = (
                f"will replace placeholder project-input/TZ.md with explicit TZ "
                f"{explicit_relpath.as_posix()}"
            )
            return TzSelection(CANONICAL_TZ_PATH, root / explicit_relpath, explicit_relpath, True, detail), ""
        detail = (
            f"existing canonical TZ document preserved; explicit TZ {explicit_relpath.as_posix()} "
            f"validated but not copied"
        )
        return TzSelection(CANONICAL_TZ_PATH, canonical_abs, explicit_relpath, False, detail), ""

    detail = f"will copy explicit TZ {explicit_relpath.as_posix()} to project-input/TZ.md"
    return TzSelection(CANONICAL_TZ_PATH, root / explicit_relpath, explicit_relpath, True, detail), ""


def _normalize_init_timestamps(filename: str, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    normalized = json.loads(json.dumps(payload))
    if not isinstance(normalized, dict):
        return None, f"{filename} payload is not a JSON object"
    timestamp_paths: list[tuple[str, ...]] = [("updated_at",)]
    if filename == "WORKSPACE_IDENTITY.json":
        timestamp_paths.append(("content", "validated_at"))
    elif filename == "REPOSITORY_LOCK.json":
        timestamp_paths.append(("content", "created_at"))

    for path in timestamp_paths:
        target: dict[str, Any] = normalized
        for key in path[:-1]:
            value = target.get(key)
            if not isinstance(value, dict):
                return None, f"{filename}.{'.'.join(path)} parent is invalid"
            target = value
        key = path[-1]
        value = target.get(key)
        if not isinstance(value, str) or not RFC3339_UTC_RE.match(value):
            return None, f"{filename}.{'.'.join(path)} is not an RFC 3339 UTC timestamp"
        target[key] = TIMESTAMP_SENTINEL
    return normalized, ""


def _init_payload_matches(
    filename: str,
    existing: dict[str, Any],
    expected: dict[str, Any],
    *,
    compare_timestamps: bool,
) -> tuple[bool, str]:
    if compare_timestamps:
        return existing == expected, ""
    existing_normalized, error = _normalize_init_timestamps(filename, existing)
    if error:
        return False, error
    expected_normalized, error = _normalize_init_timestamps(filename, expected)
    if error:
        return False, error
    return existing_normalized == expected_normalized, ""


def _validate_existing_state(
    state_root: Path,
    sidecars: dict[str, dict[str, Any]],
    *,
    compare_timestamps: bool = False,
) -> tuple[bool, str]:
    if not state_root.exists():
        return True, "state root does not exist"
    if not state_root.is_dir():
        return False, f"{state_root} exists but is not a directory"

    expected = set(SIDECAR_FILENAMES)
    entries = sorted(path.name for path in state_root.iterdir())
    unexpected = sorted(set(entries) - expected)
    if unexpected:
        return False, "state root contains unsupported files: " + ", ".join(unexpected)

    present = sorted(set(entries) & expected)
    if not present:
        return True, "state root exists and is empty"
    if set(present) != expected:
        missing = sorted(expected - set(present))
        return False, "state root is partially initialized; missing: " + ", ".join(missing)

    for filename in SIDECAR_FILENAMES:
        path = state_root / filename
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            return False, f"failed to read existing {filename}: {exc}"
        except json.JSONDecodeError as exc:
            return False, f"existing {filename} is invalid JSON: {exc}"
        matches, error = _init_payload_matches(
            filename,
            existing,
            sidecars[filename],
            compare_timestamps=compare_timestamps,
        )
        if not matches:
            detail = error or "payload differs"
            return False, f"existing {filename} does not match init payload: {detail}"
    return True, "existing state already matches init payload"


def write_selected_tz_document(root: Path, selection: TzSelection) -> tuple[bool, str]:
    tz_path = selection.tz_path
    path = root / tz_path
    if path.exists():
        if not path.is_file():
            return False, f"{tz_path.as_posix()} exists but is not a file"
        if selection.copy_to_canonical:
            if selection.source_path is None:
                return False, "canonical TZ copy source is missing"
            path.write_text(selection.source_path.read_text(encoding="utf-8"), encoding="utf-8")
            return True, f"copied {selection.explicit_tz_path.as_posix()} to project-input/TZ.md"
        if selection.explicit_tz_path and selection.explicit_tz_path != tz_path:
            return True, selection.detail
        return True, "existing TZ document preserved"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if selection.copy_to_canonical:
            if selection.source_path is None:
                return False, "canonical TZ copy source is missing"
            path.write_text(selection.source_path.read_text(encoding="utf-8"), encoding="utf-8")
            return True, f"copied {selection.explicit_tz_path.as_posix()} to project-input/TZ.md"
    except OSError as exc:
        return False, str(exc)
    return False, f"{tz_path.as_posix()} is missing; provide --tz with a real workspace-local TZ document"


def _write_sidecars(state_root: Path, sidecars: dict[str, dict[str, Any]]) -> tuple[bool, str]:
    try:
        state_root.mkdir(parents=True, exist_ok=True)
        for filename in SIDECAR_FILENAMES:
            path = state_root / filename
            path.write_text(_json_bytes(sidecars[filename]), encoding="utf-8")
    except OSError as exc:
        return False, str(exc)
    return True, "wrote state sidecars"


def _write_json(path_text: str, payload: dict[str, Any]) -> bool:
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso state init: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(_json_bytes(payload), encoding="utf-8")
    except OSError as exc:
        print(f"aso state init: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    if not root.exists() or not root.is_dir():
        return _fail(f"--root must be an existing workspace directory: {root}", EXIT_USAGE)
    root = root.resolve(strict=False)
    if root == Path(root.anchor):
        return _fail("refusing to initialize filesystem root")
    if _is_package_root(root):
        return _fail("refusing to initialize the ASO package root as a runtime workspace")
    if args.runtime_schema_version != runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION:
        return _fail(
            f"--runtime-schema-version must be {runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION}",
            EXIT_USAGE,
        )
    if args.package_version != runtime_schema_contracts.ACTIVE_PACKAGE_VERSION:
        return _fail(f"--package-version must be {runtime_schema_contracts.ACTIVE_PACKAGE_VERSION}", EXIT_USAGE)
    if args.dry_run and args.confirm_write:
        return _fail("--dry-run and --confirm-write are mutually exclusive", EXIT_USAGE)
    if not args.dry_run and not args.confirm_write:
        return _fail("writes require --confirm-write; use --dry-run to print the plan without writes", EXIT_USAGE)

    project_slug = _slug(args.project_slug or root.name)
    project_name = args.project_name or project_slug.replace("-", " ").title()
    runtime_timestamp = utc_timestamp(deterministic=getattr(args, "deterministic_timestamps", False))
    tz_selection, tz_error = select_canonical_tz(root, getattr(args, "tz", None))
    if tz_selection is None:
        return _fail(tz_error, EXIT_USAGE)
    tz_path = tz_selection.tz_path
    branch = args.branch or _actual_branch(root)
    repo_url = args.repo_url or _actual_remote(root)
    sidecars = _initial_sidecars(
        root=root,
        project_name=project_name,
        project_slug=project_slug,
        tz_path=tz_path,
        profile=args.profile,
        repo_url=repo_url,
        branch=branch,
        package_version=args.package_version,
        runtime_schema_version=args.runtime_schema_version,
        updated_at=runtime_timestamp,
    )
    state_root = root / "project-runtime" / "state"
    ok, detail = _validate_existing_state(
        state_root,
        sidecars,
        compare_timestamps=getattr(args, "deterministic_timestamps", False),
    )
    if not ok:
        return _fail(detail)

    plan = _build_plan(root, sidecars, args.dry_run, tz_path)
    plan["safety"] = {
        "existing_state": detail,
        "package_root_refused": True,
        "writes_require_confirm_write": True,
    }
    if args.dry_run:
        if args.json_out and not _write_json(args.json_out, plan):
            return EXIT_WRITE_ERROR
        print(_json_bytes(plan), end="")
        return EXIT_OK

    wrote_tz, tz_detail = write_selected_tz_document(root, tz_selection)
    if not wrote_tz:
        return _fail(f"failed to write TZ document: {tz_detail}", EXIT_WRITE_ERROR)
    wrote, write_detail = _write_sidecars(state_root, sidecars)
    if not wrote:
        return _fail(f"failed to write sidecars: {write_detail}", EXIT_WRITE_ERROR)
    plan["dry_run"] = False
    plan["status"] = "written"
    plan["write_result"] = f"{tz_detail}; {write_detail}"
    if args.json_out and not _write_json(args.json_out, plan):
        return EXIT_WRITE_ERROR
    print(_json_bytes(plan), end="")
    return EXIT_OK
