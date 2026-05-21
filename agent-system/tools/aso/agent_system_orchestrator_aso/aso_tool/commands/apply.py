"""P3 guarded proposal apply dry-run command."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

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
        reasons.append(
            "confirm_apply_not_implemented: P3 dry-run guard is implemented; "
            "mutation is reserved for a later task"
        )

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
        allowed_workspace_subdirs=("project-runtime/reports",),
    )
    if error is not None:
        return None, f"{error.rule_id}: {error.message}: {error.evidence}"
    if not path.parent.exists():
        return None, f"json-out parent does not exist: {path.parent}"
    return path, None


def _write_json(path: Path, payload: dict[str, Any]) -> tuple[bool, str]:
    try:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        return False, str(exc)
    return True, ""


def _print_text(plan: dict[str, Any]) -> None:
    status = "READY" if plan.get("would_apply") else "BLOCKED"
    print(f"ASO apply dry-run: {status}")
    print(f"status: {status.lower()}")
    print(f"proposal_id: {plan.get('proposal_id')}")
    print(f"proposal_type: {plan.get('proposal_type')}")
    print(f"validators_run: {', '.join(str(item) for item in plan.get('validators_run', []))}")
    print("files_written: 0")
    reasons = plan.get("blocked_reasons")
    if isinstance(reasons, list) and reasons:
        print("blocked_reasons:")
        for reason in reasons:
            print(f"- {reason}")


def run(args: argparse.Namespace) -> int:
    """Run guarded P3 proposal apply dry-run."""

    root = Path(args.root).expanduser()
    proposal_path = Path(args.proposal).expanduser()
    confirm_apply = bool(getattr(args, "confirm_apply", False))
    plan, exit_code = _build_plan(root, proposal_path, confirm_apply=confirm_apply)

    if args.json_out:
        path, error = _validate_json_out(root, str(args.json_out))
        if error is not None or path is None:
            print(f"aso apply: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
        ok, write_error = _write_json(path, plan)
        if not ok:
            print(f"aso apply: failed to write json-out: {write_error}", file=sys.stderr)
            return EXIT_IO_ERROR

    if args.format == "json":
        print(json.dumps(plan, indent=2, sort_keys=True))
    elif not args.json_out:
        _print_text(plan)

    return exit_code
