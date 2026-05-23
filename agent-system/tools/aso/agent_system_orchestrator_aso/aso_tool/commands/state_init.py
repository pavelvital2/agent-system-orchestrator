"""Guarded Runtime Schema 3.1.0 workspace state initializer."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from .. import runtime_schema_contracts


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_UNSAFE = 3
EXIT_WRITE_ERROR = 4

UPDATED_AT = "2026-05-21T00:00:00Z"
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
DEFAULT_TZ_TEXT = "# TZ\n\nTIMEZONE: UTC\n"

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


def _envelope(sidecar_type: str, content: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": content,
        "markdown_source": MARKDOWN_SOURCES[sidecar_type],
        "runtime_schema_version": runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION,
        "schema_version": runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION,
        "sidecar_type": sidecar_type,
        "state_revision": 1,
        "updated_at": UPDATED_AT,
        "updated_by": UPDATED_BY,
    }


def _initial_sidecars(
    *,
    root: Path,
    project_name: str,
    project_slug: str,
    profile: str,
    repo_url: str,
    branch: str,
    package_version: str,
    runtime_schema_version: str,
    probe_git: bool = True,
) -> dict[str, dict[str, Any]]:
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
                "tz_path": CANONICAL_TZ_PATH.as_posix(),
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
                "semantic_reason": "Initial Runtime Schema 3.1.0 state created by aso state init.",
                "active_branches": [],
                "completed_milestones": [],
                "active_risks": [],
                "active_blockers": [],
                "active_gaps": [],
                "last_accepted_result": NONE,
            },
        ),
        "TASK_REGISTRY.json": _envelope("TASK_REGISTRY", {"registry_revision": 1, "tasks": []}),
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
                "validated_at": UPDATED_AT,
                "validation_errors": [],
            },
        ),
        "REPOSITORY_LOCK.json": _envelope(
            "REPOSITORY_LOCK",
            {
                "lock_status": "draft",
                "project_slug": project_slug,
                "repo_url": effective_repo_url,
                "branch": effective_branch,
                "push_allowed": False,
                "created_at": UPDATED_AT,
            },
        ),
        "ACCEPTED_ARTIFACTS.json": _envelope("ACCEPTED_ARTIFACTS", {"artifacts": []}),
        "CHECKPOINT_STATE.json": _envelope(
            "CHECKPOINT_STATE",
            {
                "checkpoint_status": "not_required",
                "checkpoint_receipts": [],
                "last_checkpoint_ref": NONE,
            },
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
        ),
    }


def _json_bytes(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _build_plan(root: Path, sidecars: dict[str, dict[str, Any]], dry_run: bool) -> dict[str, Any]:
    state_root = root / "project-runtime" / "state"
    tz_path = root / CANONICAL_TZ_PATH
    writes = []
    if not tz_path.exists():
        writes.append(
            {
                "path": str(tz_path),
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


def _validate_existing_state(state_root: Path, sidecars: dict[str, dict[str, Any]]) -> tuple[bool, str]:
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
            existing = path.read_text(encoding="utf-8")
        except OSError as exc:
            return False, f"failed to read existing {filename}: {exc}"
        if existing != _json_bytes(sidecars[filename]):
            return False, f"existing {filename} is not the deterministic init payload"
    return True, "existing state already matches deterministic init payload"


def _write_tz_document(root: Path) -> tuple[bool, str]:
    path = root / CANONICAL_TZ_PATH
    if path.exists():
        if not path.is_file():
            return False, f"{CANONICAL_TZ_PATH.as_posix()} exists but is not a file"
        return True, "existing TZ document preserved"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_TZ_TEXT, encoding="utf-8")
    except OSError as exc:
        return False, str(exc)
    return True, "wrote default TZ document"


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
    branch = args.branch or _actual_branch(root)
    repo_url = args.repo_url or _actual_remote(root)
    sidecars = _initial_sidecars(
        root=root,
        project_name=project_name,
        project_slug=project_slug,
        profile=args.profile,
        repo_url=repo_url,
        branch=branch,
        package_version=args.package_version,
        runtime_schema_version=args.runtime_schema_version,
    )
    state_root = root / "project-runtime" / "state"
    ok, detail = _validate_existing_state(state_root, sidecars)
    if not ok:
        return _fail(detail)

    plan = _build_plan(root, sidecars, args.dry_run)
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

    wrote_tz, tz_detail = _write_tz_document(root)
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
