"""P3 guarded proposal apply command."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

from .. import proposal_contracts
from . import output_policy, state_verify
from .propose_next_task import _base_state_hashes, _canonical_json_bytes


EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_IO_ERROR = 3

SUPPORTED_PROPOSAL_TYPES = {"next_task", "transition", "checkpoint"}
ALLOWED_OPERATION_TYPES = set(proposal_contracts.OPERATION_TYPES)
FORBIDDEN_EXECUTION_PATTERNS = (
    (
        "git command execution",
        re.compile(
            r"\bgit\s+"
            r"(?:add|am|apply|bisect|branch|checkout|cherry-pick|clean|clone|commit|fetch|merge|"
            r"mv|pull|push|rebase|reset|restore|revert|rm|stash|submodule|switch|tag|worktree)\b"
        ),
    ),
    ("github execution", re.compile(r"\bgithub\b")),
    ("github cli execution", re.compile(r"\bgh(?:\s|$)")),
    (
        "agent dispatch execution",
        re.compile(r"\b(?:dispatch|launch|reuse|start|create|spawn|execute|run)\s+(?:an?\s+)?agent\b"),
    ),
    (
        "agent dispatch execution",
        re.compile(r"\bagent\s+(?:dispatch|launch|reuse|start|execution|execute|run)\b"),
    ),
    ("agent dispatch execution", re.compile(r"\bcreate_agent\b")),
    (
        "checkpoint execution",
        re.compile(r"\b(?:execute|run|perform|prepare|apply)\s+(?:the\s+)?checkpoint\b"),
    ),
    (
        "checkpoint execution",
        re.compile(
            r"\bcheckpoint(?:_execution_performed|[\s_-]+(?:execution|execute|run|preparation|prepare))\b"
        ),
    ),
)
NEGATED_EXECUTION_PHRASES = (
    re.compile(r"\bdoes not dispatch or reuse an agent\b"),
    re.compile(r"\bdoes not dispatch (?:an?\s+)?agent\b"),
    re.compile(r"\bdoes not reuse (?:an?\s+)?agent\b"),
    re.compile(r"\bno agent dispatch\b"),
)
DRY_RUN_VALIDATORS = (
    "proposal_json_parse",
    "proposal_schema",
    "proposal_type_supported",
    "proposal_status_proposed",
    "root_matches_proposal",
    "workspace_identity",
    "repository_lock",
    "runtime_schema_compatible",
    "state_verify_before_apply",
    "base_hash_staleness",
    "operation_allowlist",
    "operation_path_guard",
    "forbidden_execution_guard",
)
CONFIRMED_APPLY_VALIDATORS = (
    *DRY_RUN_VALIDATORS,
    "confirmed_apply_supported_scope",
    "atomic_write_preflight",
    "state_verify_after_apply",
    "receipt_schema",
)
SUPPORTED_CONFIRMED_OPERATION_TYPES = {"report_write"}


class PreparedWrite(NamedTuple):
    path: Path
    payload: dict[str, Any]
    overwrite: bool
    applied_operation: dict[str, object] | None


class CompletedWrite(NamedTuple):
    path: Path
    existed_before: bool
    original_bytes: bytes | None


def _blocked_plan(root: Path, proposal_path: Path, reasons: list[str], validators_run: list[str]) -> dict[str, Any]:
    return {
        "tool": "aso",
        "command": "apply",
        "mode": "dry-run",
        "root": str(root),
        "proposal_path": str(proposal_path),
        "proposal_id": None,
        "proposal_type": None,
        "would_apply": False,
        "blocked_reasons": reasons,
        "validators_run": validators_run,
        "planned_operations": [],
        "base_hashes": {},
        "expected_result_hashes": {},
        "dry_run": True,
        "read_only": True,
        "mutations_performed": False,
    }


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"proposal_read_error: {exc}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"malformed_json: {exc.msg} at line {exc.lineno} column {exc.colno}"
    if not isinstance(payload, dict):
        return None, "malformed_json: proposal root must be a JSON object"
    return payload, None


def _load_sidecar_content(root: Path, filename: str) -> dict[str, Any]:
    path = root / "project-runtime" / "state" / filename
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    content = payload.get("content")
    return content if isinstance(content, dict) else {}


def _normalized_root(value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(value).expanduser().resolve(strict=False)


def _identity_mismatches(proposal_identity: object, current_identity: dict[str, Any]) -> list[str]:
    if not isinstance(proposal_identity, dict) or not proposal_identity:
        return []
    mismatches: list[str] = []
    for key in (
        "workspace_id",
        "project_slug",
        "workspace_type",
        "expected_git_remote",
        "expected_branch",
        "push_allowed",
    ):
        if (
            key in proposal_identity
            and key in current_identity
            and proposal_identity.get(key) != current_identity.get(key)
        ):
            mismatches.append(f"workspace_identity_mismatch: {key}")
    return mismatches


def _repository_lock_mismatches(root: Path, proposal_identity: object) -> list[str]:
    lock = _load_sidecar_content(root, "REPOSITORY_LOCK.json")
    if not lock or not isinstance(proposal_identity, dict):
        return []
    pairs = (
        ("project_slug", "project_slug"),
        ("expected_git_remote", "repo_url"),
        ("expected_branch", "branch"),
        ("push_allowed", "push_allowed"),
    )
    mismatches: list[str] = []
    for proposal_key, lock_key in pairs:
        proposal_value = proposal_identity.get(proposal_key)
        lock_value = lock.get(lock_key)
        if proposal_value in (None, "", "NONE") or lock_value in (None, "", "NONE"):
            continue
        if proposal_value != lock_value:
            mismatches.append(f"repository_lock_mismatch: {proposal_key} != {lock_key}")
    return mismatches


def _runtime_schema_reasons(root: Path, proposal: dict[str, Any], verify_report: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    expected = proposal_contracts.RUNTIME_SCHEMA_VERSION
    if proposal.get("runtime_schema_version") != expected:
        reasons.append(f"runtime_schema_mismatch: proposal runtime_schema_version must be {expected}")
    manifest = _load_sidecar_content(root, "SCHEMA_MANIFEST.json")
    manifest_version = manifest.get("runtime_schema_version")
    if manifest_version and manifest_version != expected:
        reasons.append(f"runtime_schema_mismatch: workspace runtime_schema_version is {manifest_version!r}")
    contract = verify_report.get("runtime_schema_contract")
    contract_version = contract.get("runtime_schema_version") if isinstance(contract, dict) else expected
    if contract_version != expected:
        reasons.append("runtime_schema_mismatch: verifier active runtime schema differs from proposal contract")
    return reasons


def _base_hash_reasons(root: Path, proposal: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    current_hashes = _base_state_hashes(root)
    base_hashes = proposal.get("base_state_hashes")
    if not isinstance(base_hashes, dict):
        return current_hashes, ["base_hash_stale: base_state_hashes is not an object"]
    reasons: list[str] = []
    for relpath, expected_hash in sorted(base_hashes.items()):
        actual_hash = current_hashes.get(str(relpath))
        if actual_hash != expected_hash:
            reasons.append(f"base_hash_stale: {relpath}")
    return current_hashes, reasons


def _target_is_under(root: Path, rel_target: str, allowed_roots: tuple[str, ...]) -> bool:
    if rel_target.startswith("/") or "\x00" in rel_target:
        return False
    target = (root / rel_target).resolve(strict=False)
    workspace = root.resolve(strict=False)
    try:
        target.relative_to(workspace)
    except ValueError:
        return False
    for allowed_root in allowed_roots:
        allowed = (root / allowed_root).resolve(strict=False)
        try:
            target.relative_to(allowed)
        except ValueError:
            continue
        return target != allowed
    return False


def _operation_reasons(proposal: dict[str, Any], root: Path) -> list[str]:
    operations = proposal.get("operations")
    if not isinstance(operations, list):
        return ["operation_allowlist: operations must be an array"]
    reasons: list[str] = []
    for index, operation in enumerate(operations):
        location = f"operations[{index}]"
        if not isinstance(operation, dict):
            reasons.append(f"operation_allowlist: {location} must be an object")
            continue
        operation_type = operation.get("operation_type")
        target = operation.get("target")
        if operation_type not in ALLOWED_OPERATION_TYPES:
            reasons.append(f"operation_allowlist: {location}.operation_type is not supported")
        if not isinstance(target, str) or not target.strip():
            reasons.append(f"operation_path_guard: {location}.target must be a non-empty relative path")
            continue
        if operation_type in {"sidecar_replace", "sidecar_patch"}:
            if not _target_is_under(root, target, ("project-runtime/state",)):
                reasons.append(f"operation_path_guard: {target} is outside project-runtime/state")
        elif operation_type == "receipt_write":
            if not _target_is_under(root, target, ("project-runtime/receipts",)):
                reasons.append(f"operation_path_guard: {target} is outside project-runtime/receipts")
        elif operation_type == "report_write":
            if not _target_is_under(root, target, ("project-runtime/reports",)):
                reasons.append(f"operation_path_guard: {target} is outside project-runtime/reports")
        text = json.dumps(operation, sort_keys=True).lower()
        for negated_pattern in NEGATED_EXECUTION_PHRASES:
            text = negated_pattern.sub("", text)
        for label, pattern in FORBIDDEN_EXECUTION_PATTERNS:
            if pattern.search(text):
                reasons.append(f"forbidden_execution_guard: {location} requests {label}")
                break
    return reasons


def _expected_result_hashes(proposal: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    operations = proposal.get("operations")
    if not isinstance(operations, list):
        return result
    for operation in operations:
        if not isinstance(operation, dict):
            continue
        operation_type = operation.get("operation_type")
        target = operation.get("target")
        if operation_type not in {"sidecar_replace", "receipt_write", "report_write"} or not isinstance(target, str):
            continue
        payload = operation.get("payload")
        if payload is None:
            payload = operation.get("content")
        if payload is not None:
            result[target] = f"sha256:{hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()}"
    return result


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_id_part(value: object) -> str:
    text = str(value or "UNKNOWN").strip()
    safe = re.sub(r"[^A-Za-z0-9_.:-]+", "-", text).strip("-")
    return safe or "UNKNOWN"


def _planned_operations(proposal: dict[str, Any]) -> list[dict[str, object]]:
    operations = proposal.get("operations")
    if not isinstance(operations, list):
        return []
    planned: list[dict[str, object]] = []
    for operation in operations:
        if not isinstance(operation, dict):
            continue
        planned.append(
            {
                "operation_id": operation.get("operation_id"),
                "operation_type": operation.get("operation_type"),
                "target": operation.get("target"),
                "description": operation.get("description"),
                "fields": operation.get("fields", []),
            }
        )
    return planned


def _confirmed_operation_reasons(proposal: dict[str, Any], root: Path) -> list[str]:
    operations = proposal.get("operations")
    if not isinstance(operations, list):
        return ["confirmed_apply_supported_scope: operations must be an array"]
    reasons: list[str] = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            continue
        operation_type = operation.get("operation_type")
        target = operation.get("target")
        location = f"operations[{index}]"
        if operation_type not in SUPPORTED_CONFIRMED_OPERATION_TYPES:
            reasons.append(
                f"confirmed_apply_supported_scope: {location}.operation_type is not supported for confirmed apply"
            )
            continue
        if operation_type == "report_write" and isinstance(target, str):
            if not _target_is_under(root, target, ("project-runtime/reports",)):
                reasons.append(f"operation_path_guard: {target} is outside project-runtime/reports")
    return reasons


def _operation_payload(proposal: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
    operation_type = operation.get("operation_type")
    payload = operation.get("payload")
    if payload is None:
        payload = operation.get("content")
    if isinstance(payload, dict):
        return payload
    if operation_type == "report_write":
        return {
            "tool": "aso",
            "command": "apply",
            "proposal_id": proposal.get("proposal_id"),
            "proposal_type": proposal.get("proposal_type"),
            "operation_id": operation.get("operation_id"),
            "operation_type": operation_type,
            "target": operation.get("target"),
            "description": operation.get("description"),
            "fields": operation.get("fields", []),
            "outcome": "applied",
            "generated_at": _utc_timestamp(),
            "execution_performed": False,
            "git_mutation_performed": False,
            "agent_dispatch_performed": False,
            "checkpoint_execution_performed": False,
        }
    return {}


def _atomic_write_json(path: Path, payload: dict[str, Any], *, overwrite: bool) -> tuple[bool, str]:
    tmp: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            return False, f"target already exists: {path}"
        tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        if tmp is not None:
            try:
                tmp.unlink()
            except OSError:
                pass
        return False, str(exc)
    return True, ""


def _preflight_write_target(path: Path, *, overwrite: bool) -> str | None:
    if path.exists() and not overwrite:
        return f"target already exists: {path}"
    if path.exists() and not path.is_file():
        return f"target is not a file: {path}"
    parent = path.parent
    if parent.exists():
        if not parent.is_dir():
            return f"target parent is not a directory: {parent}"
        if not os.access(parent, os.W_OK):
            return f"target parent is not writable: {parent}"
        return None
    ancestor = parent
    while not ancestor.exists():
        if ancestor == ancestor.parent:
            break
        ancestor = ancestor.parent
    if ancestor.exists() and not ancestor.is_dir():
        return f"target ancestor is not a directory: {ancestor}"
    if ancestor.exists() and not os.access(ancestor, os.W_OK):
        return f"target ancestor is not writable: {ancestor}"
    return None


def _capture_write_state(path: Path) -> CompletedWrite:
    if path.exists() and path.is_file():
        return CompletedWrite(path=path, existed_before=True, original_bytes=path.read_bytes())
    return CompletedWrite(path=path, existed_before=False, original_bytes=None)


def _restore_completed_writes(completed_writes: list[CompletedWrite]) -> None:
    for completed in reversed(completed_writes):
        try:
            if completed.existed_before:
                if completed.original_bytes is not None:
                    completed.path.parent.mkdir(parents=True, exist_ok=True)
                    completed.path.write_bytes(completed.original_bytes)
            elif completed.path.exists():
                completed.path.unlink()
        except OSError:
            pass


def _receipt_path(root: Path, proposal: dict[str, Any]) -> Path:
    receipt_id = f"RECEIPT-{_safe_id_part(proposal.get('proposal_id'))}-{_safe_id_part(_utc_timestamp())}"
    return root / "project-runtime" / "receipts" / f"{receipt_id}.json"


def _build_receipt(
    root: Path,
    proposal: dict[str, Any],
    validators_passed: list[str],
    result_state_hashes: dict[str, str],
    applied_operations: list[dict[str, object]],
    receipt_path: Path,
) -> dict[str, Any]:
    receipt_id = receipt_path.stem
    return {
        "receipt_id": receipt_id,
        "proposal_id": proposal.get("proposal_id"),
        "proposal_type": proposal.get("proposal_type"),
        "schema_version": proposal_contracts.CONTRACT_SCHEMA_VERSION,
        "package_version": proposal_contracts.PACKAGE_VERSION,
        "runtime_schema_version": proposal_contracts.RUNTIME_SCHEMA_VERSION,
        "applied_at": _utc_timestamp(),
        "applied_by": "aso apply --confirm-apply",
        "target_root": str(root.resolve(strict=False)),
        "validators_passed": validators_passed,
        "base_state_hashes": proposal.get("base_state_hashes", {}),
        "result_state_hashes": result_state_hashes,
        "applied_operations": applied_operations,
        "outcome": "applied",
    }


def _prepare_writes(
    root: Path, proposal: dict[str, Any]
) -> tuple[list[PreparedWrite], list[str]]:
    operations = proposal.get("operations")
    if not isinstance(operations, list):
        return [], ["confirmed_apply_supported_scope: operations must be an array"]
    writes: list[PreparedWrite] = []
    reasons: list[str] = []
    seen_targets: set[Path] = set()
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            continue
        operation_type = operation.get("operation_type")
        target = operation.get("target")
        if operation_type not in SUPPORTED_CONFIRMED_OPERATION_TYPES or not isinstance(target, str):
            continue
        payload = _operation_payload(proposal, operation)
        if not payload:
            reasons.append(f"confirmed_apply_supported_scope: operations[{index}] has no applyable payload")
            continue
        path = (root / target).resolve(strict=False)
        overwrite = False
        if path in seen_targets:
            reasons.append(f"atomic_write_preflight: duplicate target {target}")
            continue
        seen_targets.add(path)
        preflight_error = _preflight_write_target(path, overwrite=overwrite)
        if preflight_error is not None:
            reasons.append(f"atomic_write_preflight: {preflight_error}")
            continue
        applied = {
            "operation_id": operation.get("operation_id"),
            "operation_type": operation_type,
            "target": target,
            "status": "applied",
            "description": operation.get("description", ""),
        }
        writes.append(PreparedWrite(path, payload, overwrite, applied))
    return writes, reasons


def _build_plan(root: Path, proposal_path: Path, *, confirm_apply: bool) -> tuple[dict[str, Any], int]:
    validators_run: list[str] = []
    proposal, read_error = _read_json(proposal_path)
    validators_run.append("proposal_json_parse")
    if read_error is not None or proposal is None:
        return _blocked_plan(root, proposal_path, [read_error or "malformed_json"], validators_run), EXIT_BLOCKED

    reasons: list[str] = []
    contract = proposal_contracts.validate_proposal_artifact(proposal)
    validators_run.append("proposal_schema")
    reasons.extend(f"proposal_schema: {error}" for error in contract.errors)

    validators_run.append("proposal_type_supported")
    if proposal.get("proposal_type") not in SUPPORTED_PROPOSAL_TYPES:
        reasons.append(f"unsupported_proposal_type: {proposal.get('proposal_type')!r}")

    validators_run.append("proposal_status_proposed")
    if proposal.get("status") != "proposed":
        reasons.append(f"proposal_status_not_applyable: {proposal.get('status')!r}")

    validators_run.append("root_matches_proposal")
    proposal_root = _normalized_root(proposal.get("target_root"))
    current_root = root.expanduser().resolve(strict=False)
    if proposal_root is None or proposal_root != current_root:
        reasons.append("wrong_root: --root does not match proposal target_root")

    current_identity = _load_sidecar_content(root, "WORKSPACE_IDENTITY.json")
    validators_run.append("workspace_identity")
    reasons.extend(_identity_mismatches(proposal.get("target_workspace_identity"), current_identity))

    validators_run.append("repository_lock")
    reasons.extend(_repository_lock_mismatches(root, proposal.get("target_workspace_identity")))

    validators_run.append("runtime_schema_compatible")
    verify_report, verify_exit_code = state_verify._report(root, True)
    reasons.extend(_runtime_schema_reasons(root, proposal, verify_report))

    validators_run.append("state_verify_before_apply")
    if verify_exit_code != 0:
        reasons.append(f"state_verify_before_apply_failed: {verify_report.get('status')}")

    validators_run.append("base_hash_staleness")
    current_hashes, hash_reasons = _base_hash_reasons(root, proposal)
    reasons.extend(hash_reasons)

    validators_run.append("operation_allowlist")
    validators_run.append("operation_path_guard")
    validators_run.append("forbidden_execution_guard")
    reasons.extend(_operation_reasons(proposal, root))

    if confirm_apply:
        validators_run.append("confirmed_apply_supported_scope")
        reasons.extend(_confirmed_operation_reasons(proposal, root))

    blocked_reasons = sorted(set(reason for reason in reasons if reason))
    plan: dict[str, Any] = {
        "tool": "aso",
        "command": "apply",
        "mode": "dry-run",
        "root": str(root),
        "proposal_path": str(proposal_path),
        "proposal_id": proposal.get("proposal_id"),
        "proposal_type": proposal.get("proposal_type"),
        "would_apply": not blocked_reasons,
        "blocked_reasons": blocked_reasons,
        "validators_run": validators_run,
        "planned_operations": _planned_operations(proposal),
        "base_hashes": current_hashes,
        "expected_result_hashes": _expected_result_hashes(proposal),
        "dry_run": True,
        "read_only": True,
        "mutations_performed": False,
        "state_verify": {
            "status": verify_report.get("status"),
            "summary": verify_report.get("summary"),
        },
    }
    return plan, EXIT_OK if plan["would_apply"] else EXIT_BLOCKED


def _validate_json_out(root: Path, path_text: str) -> tuple[Path | None, str | None]:
    path = output_policy.resolve_output_path(path_text)
    error = output_policy.validate_generated_output_path(
        root,
        path,
        allowed_workspace_subdirs=("project-runtime/reports", "project-runtime/receipts"),
    )
    if error is not None:
        return None, f"{error.rule_id}: {error.message}: {error.evidence}"
    if not path.parent.exists():
        return None, f"json-out parent does not exist: {path.parent}"
    return path, None


def _is_workspace_generated_output(root: Path, path: Path) -> bool:
    workspace = root.expanduser().resolve(strict=False)
    target = path.resolve(strict=False)
    for rel_root in ("project-runtime/reports", "project-runtime/receipts"):
        try:
            target.relative_to((workspace / rel_root).resolve(strict=False))
        except ValueError:
            continue
        return True
    return False


def _write_json(path: Path, payload: dict[str, Any]) -> tuple[bool, str]:
    return _atomic_write_json(path, payload, overwrite=True)


def _run_confirmed_apply(
    root: Path, proposal_path: Path, json_out_path: Path | None = None
) -> tuple[dict[str, Any], int]:
    plan, plan_exit = _build_plan(root, proposal_path, confirm_apply=True)
    if plan_exit != EXIT_OK:
        return plan, plan_exit

    proposal, read_error = _read_json(proposal_path)
    if read_error is not None or proposal is None:
        return _blocked_plan(root, proposal_path, [read_error or "malformed_json"], ["proposal_json_parse"]), EXIT_BLOCKED

    writes, write_reasons = _prepare_writes(root, proposal)
    if write_reasons:
        plan["would_apply"] = False
        plan["blocked_reasons"] = sorted(set([*plan.get("blocked_reasons", []), *write_reasons]))
        return plan, EXIT_BLOCKED

    receipt_path = _receipt_path(root, proposal)
    receipt_preflight_error = _preflight_write_target(receipt_path, overwrite=False)
    if receipt_preflight_error is not None:
        plan["would_apply"] = False
        plan["blocked_reasons"] = [f"receipt_write_preflight: {receipt_preflight_error}"]
        return plan, EXIT_IO_ERROR

    json_out_overwrite = True
    if json_out_path is not None:
        resolved_json_out = json_out_path.resolve(strict=False)
        if any(write.path == resolved_json_out for write in writes):
            plan["would_apply"] = False
            plan["blocked_reasons"] = [f"json_out_preflight: duplicate target {json_out_path}"]
            return plan, EXIT_BLOCKED
        json_out_overwrite = not _is_workspace_generated_output(root, json_out_path)
        json_out_preflight_error = _preflight_write_target(json_out_path, overwrite=json_out_overwrite)
        if json_out_preflight_error is not None:
            plan["would_apply"] = False
            plan["blocked_reasons"] = [f"json_out_preflight: {json_out_preflight_error}"]
            return plan, EXIT_IO_ERROR

    applied_operations = [write.applied_operation for write in writes if write.applied_operation is not None]
    completed_writes: list[CompletedWrite] = []

    for write in writes:
        try:
            before_write = _capture_write_state(write.path)
        except OSError as exc:
            _restore_completed_writes(completed_writes)
            failed = dict(plan)
            failed["would_apply"] = False
            failed["blocked_reasons"] = [f"atomic_write_preflight: {exc}"]
            failed["mutations_performed"] = False
            return failed, EXIT_IO_ERROR
        ok, error = _atomic_write_json(write.path, write.payload, overwrite=write.overwrite)
        if not ok:
            _restore_completed_writes(completed_writes)
            failed = dict(plan)
            failed["would_apply"] = False
            failed["blocked_reasons"] = [f"atomic_write_failed: {error}"]
            failed["mutations_performed"] = False
            return failed, EXIT_IO_ERROR
        completed_writes.append(before_write)

    verify_after_report, verify_after_exit = state_verify._report(root, True)
    if verify_after_exit != 0:
        _restore_completed_writes(completed_writes)
        failed = dict(plan)
        failed["would_apply"] = False
        failed["blocked_reasons"] = [f"state_verify_after_apply_failed: {verify_after_report.get('status')}"]
        failed["state_verify_after_apply"] = {
            "status": verify_after_report.get("status"),
            "summary": verify_after_report.get("summary"),
        }
        failed["mutations_performed"] = False
        return failed, EXIT_BLOCKED

    result_hashes = _base_state_hashes(root)
    for write in writes:
        rel = write.path.relative_to(root.resolve(strict=False)).as_posix()
        result_hashes[rel] = f"sha256:{hashlib.sha256(_canonical_json_bytes(write.payload)).hexdigest()}"

    validators_passed = list(CONFIRMED_APPLY_VALIDATORS)
    receipt = _build_receipt(root, proposal, validators_passed, result_hashes, applied_operations, receipt_path)
    receipt_contract = proposal_contracts.validate_apply_receipt(receipt)
    if not receipt_contract.passed:
        _restore_completed_writes(completed_writes)
        failed = dict(plan)
        failed["would_apply"] = False
        failed["blocked_reasons"] = [f"receipt_schema: {error}" for error in receipt_contract.errors]
        failed["mutations_performed"] = False
        return failed, EXIT_BLOCKED

    try:
        receipt_before = _capture_write_state(receipt_path)
    except OSError as exc:
        _restore_completed_writes(completed_writes)
        failed = dict(plan)
        failed["would_apply"] = False
        failed["blocked_reasons"] = [f"receipt_write_preflight: {exc}"]
        failed["mutations_performed"] = False
        return failed, EXIT_IO_ERROR
    ok, error = _atomic_write_json(receipt_path, receipt, overwrite=False)
    if not ok:
        _restore_completed_writes(completed_writes)
        failed = dict(plan)
        failed["would_apply"] = False
        failed["blocked_reasons"] = [f"receipt_write_failed: {error}"]
        failed["mutations_performed"] = False
        return failed, EXIT_IO_ERROR
    completed_writes.append(receipt_before)

    if json_out_path is not None:
        try:
            json_out_before = _capture_write_state(json_out_path)
        except OSError as exc:
            _restore_completed_writes(completed_writes)
            failed = dict(plan)
            failed["would_apply"] = False
            failed["blocked_reasons"] = [f"json_out_preflight: {exc}"]
            failed["mutations_performed"] = False
            return failed, EXIT_IO_ERROR
        ok, error = _atomic_write_json(json_out_path, receipt, overwrite=json_out_overwrite)
        if not ok:
            _restore_completed_writes(completed_writes)
            failed = dict(plan)
            failed["would_apply"] = False
            failed["blocked_reasons"] = [f"json_out_write_failed: {error}"]
            failed["mutations_performed"] = False
            return failed, EXIT_IO_ERROR
        completed_writes.append(json_out_before)

    return receipt, EXIT_OK


def _print_text(plan: dict[str, Any]) -> None:
    confirmed = plan.get("mode") == "confirmed" or plan.get("outcome") == "applied"
    status = "APPLIED" if confirmed else ("READY" if plan.get("would_apply") else "BLOCKED")
    print(f"ASO apply {'confirmed' if confirmed else 'dry-run'}: {status}")
    print(f"status: {status.lower()}")
    print(f"proposal_id: {plan.get('proposal_id')}")
    print(f"proposal_type: {plan.get('proposal_type')}")
    validators = plan.get("validators_run", plan.get("validators_passed", []))
    print(f"validators_run: {', '.join(str(item) for item in validators)}")
    files_written = plan.get("files_written")
    if isinstance(files_written, list):
        print(f"files_written: {len(files_written)}")
        for path in files_written:
            print(f"- {path}")
    else:
        print(f"files_written: {'yes' if confirmed else '0'}")
    reasons = plan.get("blocked_reasons")
    if isinstance(reasons, list) and reasons:
        print("blocked_reasons:")
        for reason in reasons:
            print(f"- {reason}")


def run(args: argparse.Namespace) -> int:
    """Run guarded P3 proposal apply."""

    root = Path(args.root).expanduser()
    proposal_path = Path(args.proposal).expanduser()
    confirm_apply = bool(getattr(args, "confirm_apply", False))
    json_out_path: Path | None = None
    if args.json_out:
        json_out_path, error = _validate_json_out(root, str(args.json_out))
        if error is not None or json_out_path is None:
            print(f"aso apply: {error}", file=sys.stderr)
            return EXIT_IO_ERROR

    if confirm_apply:
        plan, exit_code = _run_confirmed_apply(root, proposal_path, json_out_path)
    else:
        plan, exit_code = _build_plan(root, proposal_path, confirm_apply=False)

    if json_out_path is not None and (
        not confirm_apply
        or (exit_code != EXIT_OK and not _is_workspace_generated_output(root, json_out_path))
    ):
        ok, write_error = _write_json(json_out_path, plan)
        if not ok:
            print(f"aso apply: failed to write json-out: {write_error}", file=sys.stderr)
            return EXIT_IO_ERROR

    if args.format == "json":
        print(json.dumps(plan, indent=2, sort_keys=True))
    elif not args.json_out:
        _print_text(plan)

    return exit_code
