"""Guarded Runtime Schema 3.1.1 state sidecar migration."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from .. import runtime_schema_contracts
from . import state_init, state_verify


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_UNSAFE = 3
EXIT_WRITE_ERROR = 4

SOURCE_SCHEMA_VERSION = state_verify.LEGACY_SCHEMA_VERSION
TARGET_SCHEMA_VERSION = runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION
UPDATED_AT = state_init.UPDATED_AT
UPDATED_BY = state_init.UPDATED_BY

LEGACY_SIDECARS = tuple(state_verify.SIDECARS)
LEGACY_FILENAMES = tuple(spec.filename for spec in LEGACY_SIDECARS)
CURRENT_FILENAMES = tuple(f"{sidecar_type}.json" for sidecar_type in runtime_schema_contracts.ALL_SIDECARS)


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _is_package_root(root: Path) -> bool:
    return state_init._is_package_root(root)


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _finding(
    rule_id: str,
    title: str,
    message: str,
    *,
    path: str = "",
    field: str = "",
    severity: str = "error",
    recommendation: str = "Inspect the migration input state and rerun with compatible sidecars.",
) -> dict[str, object]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "title": title,
        "message": message,
        "details": message,
        "path": path,
        "field": field,
        "recommendation": recommendation,
    }


def _envelope(sidecar_type: str, content: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": content,
        "markdown_source": state_init.MARKDOWN_SOURCES[sidecar_type],
        "migration_source_schema": SOURCE_SCHEMA_VERSION,
        "runtime_schema_version": TARGET_SCHEMA_VERSION,
        "schema_version": TARGET_SCHEMA_VERSION,
        "sidecar_type": sidecar_type,
        "state_revision": 1,
        "updated_at": UPDATED_AT,
        "updated_by": UPDATED_BY,
    }


def _migrated_payload(payload: dict[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(payload)
    old_revision = migrated.get("state_revision")
    revision = old_revision + 1 if isinstance(old_revision, int) and not isinstance(old_revision, bool) else 1
    migrated["schema_version"] = TARGET_SCHEMA_VERSION
    migrated["runtime_schema_version"] = TARGET_SCHEMA_VERSION
    migrated["state_revision"] = revision
    migrated["updated_at"] = UPDATED_AT
    migrated["updated_by"] = UPDATED_BY
    migrated["migration_source_schema"] = SOURCE_SCHEMA_VERSION
    content = migrated.get("content")
    if isinstance(content, dict):
        if "runtime_schema_version" in content:
            content["runtime_schema_version"] = TARGET_SCHEMA_VERSION
        if "package_version" in content:
            content["package_version"] = runtime_schema_contracts.ACTIVE_PACKAGE_VERSION
        if "governance_ruleset_version" in content:
            content["governance_ruleset_version"] = runtime_schema_contracts.ACTIVE_GOVERNANCE_RULESET_VERSION
        if migrated.get("sidecar_type") == "PROJECT_STATE":
            content["workspace_identity_ref"] = "project-runtime/state/WORKSPACE_IDENTITY.json"
            content["repository_lock_ref"] = "project-runtime/state/REPOSITORY_LOCK.json"
    return migrated


def _repository_lock(project_state: dict[str, Any], workspace_identity: dict[str, Any]) -> dict[str, Any]:
    project_content = project_state.get("content") if isinstance(project_state.get("content"), dict) else {}
    identity_content = workspace_identity.get("content") if isinstance(workspace_identity.get("content"), dict) else {}
    if not isinstance(project_content, dict):
        project_content = {}
    if not isinstance(identity_content, dict):
        identity_content = {}
    return _envelope(
        "REPOSITORY_LOCK",
        {
            "branch": str(project_content.get("expected_branch") or identity_content.get("expected_branch") or state_init.NONE),
            "created_at": UPDATED_AT,
            "lock_status": str(project_content.get("repository_lock_status") or identity_content.get("repository_lock_status") or "draft"),
            "project_slug": str(project_content.get("project_slug") or identity_content.get("project_slug") or "workspace"),
            "push_allowed": bool(project_content.get("push_allowed") is True and identity_content.get("push_allowed") is True),
            "repo_url": str(project_content.get("expected_git_remote") or identity_content.get("expected_git_remote") or state_init.NONE),
        },
    )


def _checkpoint_state(project_state: dict[str, Any]) -> dict[str, Any]:
    project_content = project_state.get("content") if isinstance(project_state.get("content"), dict) else {}
    if not isinstance(project_content, dict):
        project_content = {}
    checkpoint_ref = project_content.get("checkpoint_receipt_ref")
    return _envelope(
        "CHECKPOINT_STATE",
        {
            "checkpoint_receipts": [] if state_verify._is_none(checkpoint_ref) else [checkpoint_ref],
            "checkpoint_status": str(project_content.get("project_checkpoint_status") or "not_required"),
            "last_checkpoint_ref": str(checkpoint_ref or state_init.NONE),
        },
    )


def _schema_manifest(filenames: tuple[str, ...]) -> dict[str, Any]:
    return _envelope(
        "SCHEMA_MANIFEST",
        {
            "created_by_profile": "orchestrator",
            "package_version": runtime_schema_contracts.ACTIVE_PACKAGE_VERSION,
            "runtime_schema_version": TARGET_SCHEMA_VERSION,
            "sidecars": sorted(filenames),
            "state_root": runtime_schema_contracts.STATE_ROOT,
        },
    )


def _reconcile_legacy_next_action(migrated: dict[str, dict[str, Any]]) -> None:
    next_payload = migrated.get("NEXT_ACTION.json", {})
    next_content = next_payload.get("content") if isinstance(next_payload.get("content"), dict) else {}
    registry_payload = migrated.get("TASK_REGISTRY.json", {})
    registry_content = registry_payload.get("content") if isinstance(registry_payload.get("content"), dict) else {}
    if not isinstance(next_content, dict) or not isinstance(registry_content, dict):
        return
    if next_content.get("action_type") != "create_agent":
        return
    task_id = next_content.get("task_id")
    if not isinstance(task_id, str) or state_verify._is_none(task_id):
        return
    tasks = registry_content.get("tasks")
    if not isinstance(tasks, list):
        return
    for task in tasks:
        if not isinstance(task, dict) or task.get("task_id") != task_id:
            continue
        has_result_refs = isinstance(task.get("result_refs"), list) and bool(task.get("result_refs"))
        has_audit_refs = isinstance(task.get("audit_refs"), list) and bool(task.get("audit_refs"))
        if task.get("status") == "running" and not has_result_refs and not has_audit_refs:
            task["status"] = "ready"


def _load_legacy_sidecars(root: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, object]]]:
    state_root = root / runtime_schema_contracts.STATE_ROOT
    findings: list[dict[str, object]] = []
    loaded: dict[str, dict[str, Any]] = {}
    if not state_root.is_dir():
        return {}, [
            _finding(
                "STATE_MIGRATE_STATE_ROOT_MISSING",
                "State root is missing",
                f"{runtime_schema_contracts.STATE_ROOT} must exist before migration.",
                path=runtime_schema_contracts.STATE_ROOT,
            )
        ]

    entries = sorted(path.name for path in state_root.iterdir())
    expected = set(LEGACY_FILENAMES)
    unexpected = sorted(set(entries) - expected)
    missing = sorted(expected - set(entries))
    for filename in missing:
        findings.append(
            _finding(
                "STATE_MIGRATE_LEGACY_SIDECAR_MISSING",
                "Required legacy sidecar is missing",
                f"{runtime_schema_contracts.STATE_ROOT}/{filename} is required for deterministic migration.",
                path=f"{runtime_schema_contracts.STATE_ROOT}/{filename}",
            )
        )
    for filename in unexpected:
        findings.append(
            _finding(
                "STATE_MIGRATE_UNSUPPORTED_STATE_FILE",
                "State root contains an unsupported file",
                f"{runtime_schema_contracts.STATE_ROOT}/{filename} makes migration ambiguous.",
                path=f"{runtime_schema_contracts.STATE_ROOT}/{filename}",
                recommendation="Remove unsupported state files or initialize a clean Runtime Schema 3.1.1 workspace.",
            )
        )
    if findings:
        return {}, findings

    for spec in LEGACY_SIDECARS:
        path = state_root / spec.filename
        relpath = _rel(root, path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            findings.append(
                _finding(
                    "STATE_MIGRATE_JSON_PARSE_ERROR",
                    "Legacy sidecar JSON is invalid",
                    f"{relpath}: {exc.msg} at line {exc.lineno}, column {exc.colno}.",
                    path=relpath,
                    recommendation="Fix JSON syntax before migration.",
                )
            )
            continue
        except OSError as exc:
            findings.append(
                _finding(
                    "STATE_MIGRATE_SIDECAR_UNREADABLE",
                    "Legacy sidecar is unreadable",
                    f"{relpath}: {exc}",
                    path=relpath,
                )
            )
            continue
        if not isinstance(payload, dict):
            findings.append(
                _finding(
                    "STATE_MIGRATE_TOP_LEVEL_NOT_OBJECT",
                    "Legacy sidecar is not a JSON object",
                    f"{relpath} must contain a sidecar envelope object.",
                    path=relpath,
                )
            )
            continue
        schema_version = payload.get("schema_version")
        if schema_version != SOURCE_SCHEMA_VERSION:
            status = runtime_schema_contracts.compatibility_status(schema_version)
            findings.append(
                _finding(
                    "STATE_MIGRATE_SCHEMA_UNSUPPORTED",
                    "Sidecar schema version is not migratable by this command",
                    f"{relpath}.schema_version={schema_version!r} has compatibility status {status!r}; expected {SOURCE_SCHEMA_VERSION!r}.",
                    path=relpath,
                    field="schema_version",
                    recommendation="Use this command only for compatible Runtime Schema 2.0.0 sidecars.",
                )
            )
            continue
        loaded[spec.sidecar_type] = payload
    return loaded, findings


def _build_migrated_sidecars(legacy: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    migrated = {
        spec.filename: _migrated_payload(legacy[spec.sidecar_type])
        for spec in sorted(LEGACY_SIDECARS, key=lambda item: item.filename)
    }
    migrated["REPOSITORY_LOCK.json"] = _repository_lock(legacy["PROJECT_STATE"], legacy["WORKSPACE_IDENTITY"])
    migrated["CHECKPOINT_STATE.json"] = _checkpoint_state(legacy["PROJECT_STATE"])
    migrated["SCHEMA_MANIFEST.json"] = _schema_manifest(tuple(sorted(set(CURRENT_FILENAMES))))
    _reconcile_legacy_next_action(migrated)
    return dict(sorted(migrated.items()))


def _receipt_path(root: Path) -> Path:
    return root / "project-runtime" / "reports" / "state-migration-2_0_0-to-3_1_0.json"


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(base.resolve(strict=False))
    except ValueError:
        return False
    return True


def _safe_json_out(root: Path, path_text: str) -> tuple[Path | None, str]:
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if path.suffix.lower() != ".json":
        return None, "--json-out must end with .json"
    tmp_root = Path("/tmp")
    reports_root = root / "project-runtime" / "reports"
    receipts_root = root / "project-runtime" / "receipts"
    if _is_relative_to(path, tmp_root) or _is_relative_to(path, reports_root) or _is_relative_to(path, receipts_root):
        return path, ""
    return None, "--json-out must be under /tmp, project-runtime/reports, or project-runtime/receipts"


def _write_json(path: Path, payload: dict[str, Any]) -> tuple[bool, str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_json_text(payload), encoding="utf-8")
    except OSError as exc:
        return False, str(exc)
    return True, "wrote json"


def _plan(root: Path, migrated: dict[str, dict[str, Any]], dry_run: bool) -> dict[str, Any]:
    state_root = root / runtime_schema_contracts.STATE_ROOT
    writes: list[dict[str, object]] = []
    for filename, payload in sorted(migrated.items()):
        action = "create" if filename not in LEGACY_FILENAMES else "migrate"
        writes.append(
            {
                "action": action,
                "from_schema_version": SOURCE_SCHEMA_VERSION if action == "migrate" else None,
                "path": str(state_root / filename),
                "sidecar_type": payload["sidecar_type"],
                "state_revision": payload["state_revision"],
                "to_schema_version": TARGET_SCHEMA_VERSION,
            }
        )
    return {
        "command": "state migrate",
        "dry_run": dry_run,
        "from_schema_version": SOURCE_SCHEMA_VERSION,
        "migration_plan_version": 1,
        "package_version": runtime_schema_contracts.ACTIVE_PACKAGE_VERSION,
        "receipt_path": str(_receipt_path(root)) if not dry_run else None,
        "root": str(root),
        "runtime_schema_version": TARGET_SCHEMA_VERSION,
        "state_root": str(state_root),
        "status": "planned",
        "to_schema_version": TARGET_SCHEMA_VERSION,
        "writes": writes,
    }


def _failure_report(root: Path, findings: list[dict[str, object]]) -> dict[str, Any]:
    return {
        "command": "state migrate",
        "dry_run": True,
        "findings": sorted(findings, key=lambda item: (str(item["rule_id"]), str(item["path"]), str(item["field"]), str(item["message"]))),
        "from_schema_version": SOURCE_SCHEMA_VERSION,
        "root": str(root),
        "runtime_schema_version": TARGET_SCHEMA_VERSION,
        "status": "failed",
        "summary": {
            "errors": sum(1 for finding in findings if finding.get("severity") == "error"),
            "warnings": sum(1 for finding in findings if finding.get("severity") == "warning"),
        },
        "to_schema_version": TARGET_SCHEMA_VERSION,
    }


def _print_report(report: dict[str, Any]) -> None:
    print(_json_text(report), end="")


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    if not root.exists() or not root.is_dir():
        _print_report(
            _failure_report(
                root,
                [
                    _finding(
                        "STATE_MIGRATE_ROOT_UNREADABLE",
                        "Workspace root is not readable",
                        f"--root does not point to a readable directory: {root}",
                        path="root",
                    )
                ],
            )
        )
        return EXIT_USAGE
    root = root.resolve(strict=False)
    if args.to != TARGET_SCHEMA_VERSION:
        print(f"aso state migrate: --to must be {TARGET_SCHEMA_VERSION}", file=sys.stderr)
        return EXIT_USAGE
    if args.dry_run and args.confirm_write:
        print("aso state migrate: --dry-run and --confirm-write are mutually exclusive", file=sys.stderr)
        return EXIT_USAGE
    if not args.dry_run and not args.confirm_write:
        print("aso state migrate: writes require --confirm-write; use --dry-run for a migration plan", file=sys.stderr)
        return EXIT_USAGE
    if args.confirm_write and _is_package_root(root):
        print("aso state migrate: refusing to migrate the ASO package root as runtime state", file=sys.stderr)
        return EXIT_UNSAFE

    json_out: Path | None = None
    if args.json_out:
        json_out, reason = _safe_json_out(root, args.json_out)
        if json_out is None:
            print(f"aso state migrate: unsafe json-out: {reason}", file=sys.stderr)
            return EXIT_UNSAFE

    legacy, findings = _load_legacy_sidecars(root)
    if not findings:
        verify_report, verify_exit = state_verify._report(root, True)
        if verify_exit != 0:
            verify_findings = verify_report.get("findings")
            if isinstance(verify_findings, list):
                findings.extend(finding for finding in verify_findings if isinstance(finding, dict))
            else:
                findings.append(
                    _finding(
                        "STATE_MIGRATE_VERIFY_FAILED",
                        "Legacy state failed strict verification",
                        "State verify rejected the source sidecars before migration.",
                    )
                )
    if findings:
        report = _failure_report(root, findings)
        if json_out:
            ok, detail = _write_json(json_out, report)
            if not ok:
                print(f"aso state migrate: failed to write json-out: {detail}", file=sys.stderr)
                return EXIT_WRITE_ERROR
        _print_report(report)
        return EXIT_FINDINGS

    migrated = _build_migrated_sidecars(legacy)
    report = _plan(root, migrated, args.dry_run)
    report["safety"] = {
        "dry_run_writes_no_files": True,
        "fail_closed_for_malformed_or_ambiguous_state": True,
        "writes_require_confirm_write": True,
    }
    if args.dry_run:
        if json_out:
            ok, detail = _write_json(json_out, report)
            if not ok:
                print(f"aso state migrate: failed to write json-out: {detail}", file=sys.stderr)
                return EXIT_WRITE_ERROR
        _print_report(report)
        return EXIT_OK

    state_root = root / runtime_schema_contracts.STATE_ROOT
    try:
        for filename, payload in sorted(migrated.items()):
            (state_root / filename).write_text(_json_text(payload), encoding="utf-8")
    except OSError as exc:
        print(f"aso state migrate: failed to write migrated sidecars: {exc}", file=sys.stderr)
        return EXIT_WRITE_ERROR

    report["dry_run"] = False
    report["status"] = "written"
    receipt = _receipt_path(root)
    report["receipt_path"] = str(receipt)
    ok, detail = _write_json(receipt, report)
    if not ok:
        print(f"aso state migrate: failed to write migration receipt: {detail}", file=sys.stderr)
        return EXIT_WRITE_ERROR
    if json_out and json_out.resolve(strict=False) != receipt.resolve(strict=False):
        ok, detail = _write_json(json_out, report)
        if not ok:
            print(f"aso state migrate: failed to write json-out: {detail}", file=sys.stderr)
            return EXIT_WRITE_ERROR
    _print_report(report)
    return EXIT_OK
