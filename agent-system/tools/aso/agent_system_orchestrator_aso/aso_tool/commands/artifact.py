"""P5 governed artifact storage CLI commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import artifact_storage, runtime_schema_contracts, state_materialization, transition_engine
from . import output_policy


EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_IO_ERROR = 3

SCHEMA_RELPATH = "agent-system/09_validators/schemas/artifact_package_manifest.schema.json"
CANONICAL_MANIFEST_FILENAME = "manifest.json"
LEGACY_MANIFEST_FILENAMES = ("artifact_package_manifest.json",)
SUPPORTED_MANIFEST_FILENAMES = (CANONICAL_MANIFEST_FILENAME, *LEGACY_MANIFEST_FILENAMES)
ARTIFACT_ID_RE = re.compile(r"^[A-Z][A-Z0-9_:-]+$")
PACKAGE_FORBIDDEN_ROOTS = (".git", ".github", ".venv", "agent-system", "project-input", "project-runtime", "project-archive")
REQUIRED_MANIFEST_FIELDS = (
    "artifact_package_schema_version",
    "artifact_type",
    "artifact_id",
    "task_id",
    "role",
    "attempt_no",
    "status",
    "main_document",
    "structured_artifacts",
    "evidence_refs",
    "created_at",
    "producer",
)
ALLOWED_ARTIFACT_TYPES = (
    "RESULT",
    "AUDIT_RESULT",
    "TASK_PACKET",
    "GAP_REGISTER",
    "OWNER_QUESTION_CARD",
    "OWNER_DECISION",
    "LIFECYCLE_EVENT",
    "EVIDENCE_PACK",
)
ALLOWED_ROLES = (
    "requirements_analyst",
    "solution_architect",
    "designer",
    "developer",
    "auditor",
    "tester",
    "technical_writer",
    "devops_setup_engineer",
    "release_manager",
    "orchestrator",
    "owner",
)
ALLOWED_STATUSES = ("pass", "fail", "blocked", "gap", "pending")


def _allowed_roles_from_contract() -> tuple[str, ...]:
    try:
        contract = transition_engine.load_runtime_contract()
    except (OSError, transition_engine.RuntimeContractError):
        return ALLOWED_ROLES
    roles = transition_engine.contract_roles(contract)
    values = [
        *[str(role) for role in roles.get("allowed_roles", [])],
        *[str(role) for role in roles.get("forbidden_dispatch_roles", [])],
    ]
    return tuple(dict.fromkeys(role for role in values if role))


def _allowed_statuses_from_contract() -> tuple[str, ...]:
    try:
        contract = transition_engine.load_runtime_contract()
    except (OSError, transition_engine.RuntimeContractError):
        return ALLOWED_STATUSES
    lifecycle = transition_engine.lifecycle_status_contract(contract)
    values = [
        *[str(status) for status in lifecycle.get("profile_result_statuses", [])],
        *[str(status) for status in lifecycle.get("audit_result_statuses", [])],
        "blocked",
        "gap",
        "pending",
    ]
    return tuple(dict.fromkeys(status for status in values if status))


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, sort_keys=True)


def _finding(rule_id: str, title: str, details: str, path: str = "") -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "severity": "error",
        "title": title,
        "details": details,
        "path": path,
        "recommendation": "Conform the artifact package manifest to P5.1 schema 1.1.0.",
    }


def _warning(rule_id: str, title: str, details: str, path: str = "") -> dict[str, str]:
    finding = _finding(rule_id, title, details, path)
    finding["severity"] = "warning"
    return finding


def _is_error_finding(finding: object) -> bool:
    return isinstance(finding, dict) and finding.get("severity", "error") == "error"


def _finding_counts(findings: list[dict[str, str]]) -> dict[str, int]:
    errors = sum(1 for finding in findings if _is_error_finding(finding))
    return {"errors": errors, "warnings": len(findings) - errors}


def _blocked_reason(findings: list[dict[str, str]], extra_reasons: list[str] | None = None) -> str | None:
    reasons = list(extra_reasons or [])
    reasons.extend(
        f"{finding.get('rule_id')}: {finding.get('details')}"
        for finding in findings
        if _is_error_finding(finding)
    )
    return "; ".join(reason for reason in reasons if reason) or None


def _manifest_filename_findings(path: Path) -> list[dict[str, str]]:
    if path.name not in LEGACY_MANIFEST_FILENAMES:
        return []
    return [
        _warning(
            "ARTIFACT_MANIFEST_COMPAT_001",
            "Legacy artifact manifest filename is accepted",
            f"{path.name} is a legacy compatibility alias; use {CANONICAL_MANIFEST_FILENAME} for new candidate and accepted packages.",
            str(path),
        )
    ]


def _read_json_object(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [_finding("ARTIFACT_VALIDATE_READ_001", "Artifact read failed", str(exc), str(path))]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, [
            _finding(
                "ARTIFACT_VALIDATE_JSON_001",
                "Artifact JSON is malformed",
                f"{exc.msg} at line {exc.lineno} column {exc.colno}",
                str(path),
            )
        ]
    if not isinstance(payload, dict):
        return None, [_finding("ARTIFACT_VALIDATE_JSON_002", "Artifact JSON root is not an object", "Manifest root must be a JSON object.", str(path))]
    return payload, []


def _load_manifest_schema(root: Path) -> dict[str, Any]:
    path = root / SCHEMA_RELPATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _package_path_errors(value: object, field: str) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return [f"{field} must be a non-empty package path string"]
    if "\x00" in value or "\\" in value:
        return [f"{field} must be a POSIX package path without NUL bytes"]
    path = value.strip()
    parts = tuple(part for part in path.split("/") if part)
    if path.startswith("/") or not parts:
        return [f"{field} must be relative"]
    if any(part in ("", ".", "..") for part in path.split("/")):
        return [f"{field} must not contain empty, current-directory, or parent traversal segments"]
    if parts[0] in PACKAGE_FORBIDDEN_ROOTS:
        return [f"{field} must not reference workspace-local root {parts[0]}"]
    return []


def _artifact_refs_errors(value: object, field: str) -> list[str]:
    if value == "NONE":
        return []
    if not isinstance(value, list):
        return [f"{field} must be NONE or an array of package paths"]
    errors: list[str] = []
    for index, item in enumerate(value):
        errors.extend(_package_path_errors(item, f"{field}[{index}]"))
    return errors


def _select_manifest_path(package_root: Path) -> Path:
    canonical = package_root / CANONICAL_MANIFEST_FILENAME
    if canonical.is_file():
        return canonical
    for filename in LEGACY_MANIFEST_FILENAMES:
        legacy = package_root / filename
        if legacy.is_file():
            return legacy
    return canonical


def _resolve_package_input(root: Path, value: str) -> tuple[Path | None, Path | None, str | None]:
    raw = Path(value).expanduser()
    workspace = root.expanduser().resolve(strict=False)
    candidate = raw if raw.is_absolute() else workspace / raw
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(workspace)
    except ValueError:
        return None, None, "artifact package path must be inside --root"

    if resolved.name in SUPPORTED_MANIFEST_FILENAMES:
        package_root = resolved.parent
        manifest_path = resolved
    else:
        package_root = resolved
        manifest_path = _select_manifest_path(package_root)
    return package_root, manifest_path, None


def _existing_package_path_errors(package_root: Path, value: object, field: str) -> list[str]:
    errors = _package_path_errors(value, field)
    if errors:
        return errors
    assert isinstance(value, str)
    resolved = (package_root / value.strip()).resolve(strict=False)
    try:
        resolved.relative_to(package_root.resolve(strict=False))
    except ValueError:
        return [f"{field} resolves outside package root"]
    if not resolved.is_file():
        return [f"{field} does not exist inside package root: {value.strip()}"]
    return []


def _structured_artifact_content_errors(package_root: Path, value: object) -> list[str]:
    if value == "NONE":
        return []
    if not isinstance(value, list):
        return []
    errors: list[str] = []
    for index, item in enumerate(value):
        path_errors = _existing_package_path_errors(package_root, item, f"structured_artifacts[{index}]")
        errors.extend(path_errors)
        if path_errors or not isinstance(item, str) or not item.strip().endswith(".json"):
            continue
        path = package_root / item.strip()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            errors.append(f"structured_artifacts[{index}] is unreadable: {exc}")
            continue
        except json.JSONDecodeError as exc:
            errors.append(
                f"structured_artifacts[{index}] JSON is malformed at line {exc.lineno} column {exc.colno}: {exc.msg}"
            )
            continue
        if not isinstance(payload, dict):
            errors.append(f"structured_artifacts[{index}] JSON root must be an object")
    return errors


def _validate_manifest_payload(payload: dict[str, Any], root: Path, package_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    schema = _load_manifest_schema(root)
    schema_types = (
        schema.get("$defs", {}).get("artifactType", {}).get("enum")
        if isinstance(schema.get("$defs"), dict)
        else None
    )
    allowed_types = tuple(schema_types) if isinstance(schema_types, list) else ALLOWED_ARTIFACT_TYPES
    allowed_roles = _allowed_roles_from_contract()
    allowed_statuses = _allowed_statuses_from_contract()

    missing = [field for field in REQUIRED_MANIFEST_FIELDS if field not in payload]
    extra = sorted(set(payload) - set(REQUIRED_MANIFEST_FIELDS))
    for field in missing:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_001", "Manifest required field is missing", f"{field} is required.", field))
    for field in extra:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_002", "Manifest field is not allowed", f"{field} is not declared by the P5 manifest schema.", field))

    if payload.get("artifact_package_schema_version") != runtime_schema_contracts.ACTIVE_ARTIFACT_PACKAGE_SCHEMA_VERSION:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_003", "Artifact package schema version is invalid", "artifact_package_schema_version must be 1.1.0.", "artifact_package_schema_version"))
    if payload.get("artifact_type") not in allowed_types:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_004", "Artifact type is unsupported", f"artifact_type must be one of: {', '.join(allowed_types)}.", "artifact_type"))
    artifact_id = payload.get("artifact_id")
    if not isinstance(artifact_id, str) or not ARTIFACT_ID_RE.fullmatch(artifact_id):
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_005", "Artifact id is invalid", "artifact_id must match ^[A-Z][A-Z0-9_:-]+$.", "artifact_id"))
    if not isinstance(payload.get("task_id"), str) or not str(payload.get("task_id", "")).strip():
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_006", "Task id is invalid", "task_id must be a non-empty string.", "task_id"))
    if payload.get("role") not in allowed_roles:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_007", "Role is unsupported", f"role must be one of: {', '.join(allowed_roles)}.", "role"))
    if not isinstance(payload.get("attempt_no"), int) or isinstance(payload.get("attempt_no"), bool) or payload.get("attempt_no", 0) < 1:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_008", "Attempt number is invalid", "attempt_no must be an integer >= 1.", "attempt_no"))
    if payload.get("status") not in allowed_statuses:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_009", "Status is unsupported", f"status must be one of: {', '.join(allowed_statuses)}.", "status"))
    for error in _existing_package_path_errors(package_root, payload.get("main_document"), "main_document"):
        findings.append(_finding("ARTIFACT_VALIDATE_PATH_001", "Main document path is invalid", error, "main_document"))
    for field in ("structured_artifacts", "evidence_refs"):
        for error in _artifact_refs_errors(payload.get(field), field):
            findings.append(_finding("ARTIFACT_VALIDATE_PATH_002", "Artifact reference path is invalid", error, field))
    for error in _structured_artifact_content_errors(package_root, payload.get("structured_artifacts")):
        findings.append(_finding("ARTIFACT_VALIDATE_JSON_003", "Structured artifact JSON is invalid", error, "structured_artifacts"))
    if not isinstance(payload.get("created_at"), str) or not str(payload.get("created_at", "")).strip():
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_010", "Created timestamp is invalid", "created_at must be a non-empty date-time string.", "created_at"))

    producer = payload.get("producer")
    if not isinstance(producer, dict):
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_011", "Producer is invalid", "producer must be an object.", "producer"))
    else:
        if sorted(producer) != ["agent_instance_id", "role"]:
            findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_012", "Producer fields are invalid", "producer must contain only agent_instance_id and role.", "producer"))
        if not isinstance(producer.get("agent_instance_id"), str) or not str(producer.get("agent_instance_id", "")).strip():
            findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_013", "Producer agent id is invalid", "producer.agent_instance_id must be non-empty.", "producer.agent_instance_id"))
        if producer.get("role") not in allowed_roles:
            findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_014", "Producer role is unsupported", f"producer.role must be one of: {', '.join(allowed_roles)}.", "producer.role"))
    return findings


def _validate_manifest_selection(
    root: Path,
    package_root: Path,
    manifest_path: Path,
    expected_type: str | None = None,
    expected_task_id: str | None = None,
    expected_role: str | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    findings.extend(_manifest_filename_findings(manifest_path))
    payload, read_findings = _read_json_object(manifest_path)
    findings.extend(read_findings)
    if payload is None:
        return None, findings

    findings.extend(_validate_manifest_payload(payload, root, package_root))
    if expected_type is not None and payload.get("artifact_type") != expected_type:
        findings.append(
            _finding(
                "ARTIFACT_VALIDATE_TYPE_001",
                "Artifact type does not match requested type",
                f"artifact_type must be {expected_type}.",
                "artifact_type",
            )
        )
    if expected_task_id is not None and payload.get("task_id") != expected_task_id:
        findings.append(
            _finding(
                "ARTIFACT_VALIDATE_TASK_001",
                "Task id does not match requested task",
                f"task_id must be {expected_task_id}.",
                "task_id",
            )
        )
    if expected_role is not None and payload.get("role") != expected_role:
        findings.append(
            _finding(
                "ARTIFACT_VALIDATE_ROLE_001",
                "Role does not match requested role",
                f"role must be {expected_role}.",
                "role",
            )
        )
    return payload, findings


def _validate_path(
    root: Path,
    artifact_path: Path,
    expected_type: str | None = None,
    expected_task_id: str | None = None,
    expected_role: str | None = None,
    strict: bool = False,
) -> dict[str, object]:
    package_root, manifest_path, package_error = _resolve_package_input(root, artifact_path.as_posix())
    findings: list[dict[str, str]] = []
    if package_error is not None or package_root is None or manifest_path is None:
        findings.append(_finding("ARTIFACT_VALIDATE_PACKAGE_001", "Artifact package path is invalid", package_error or "invalid package path", str(artifact_path)))
        payload = None
    else:
        payload, manifest_findings = _validate_manifest_selection(
            root,
            package_root,
            manifest_path,
            expected_type=expected_type,
            expected_task_id=expected_task_id,
            expected_role=expected_role,
        )
        findings.extend(manifest_findings)
    counts = _finding_counts(findings)
    status = "pass" if counts["errors"] == 0 else "blocked"
    return {
        "tool": "aso",
        "command": "artifact validate",
        "root": str(root),
        "package_root": str(package_root) if package_root is not None else None,
        "manifest": str(manifest_path) if manifest_path is not None else str(artifact_path),
        "schema_path": SCHEMA_RELPATH,
        "artifact_package_schema_version": runtime_schema_contracts.ACTIVE_ARTIFACT_PACKAGE_SCHEMA_VERSION,
        "status": status,
        "strict": strict,
        "requested_write_mode": "read_only",
        "read_only": True,
        "mutations_performed": False,
        "blocked_reason": _blocked_reason(findings),
        "actual_read_outcome": "completed" if payload is not None else "blocked",
        "actual_write_outcome": "not_requested",
        "validators_run": ["json_parse", "artifact_package_manifest_schema", "package_path_boundary"],
        "findings": findings,
        "summary": counts,
    }


def _resolve_workspace_package(root: Path, value: str, bucket: str | None = None) -> tuple[Path | None, str | None, Path | None, str | None]:
    package_root, manifest_path, error = _resolve_package_input(root, value)
    if error is not None or package_root is None or manifest_path is None:
        return None, None, None, error or "invalid artifact package path"
    workspace = root.expanduser().resolve(strict=False)
    try:
        rel_text = package_root.resolve(strict=False).relative_to(workspace).as_posix()
    except ValueError:
        return None, None, None, "artifact package path must be inside --root"

    parts = rel_text.split("/")
    if len(parts) < 4 or parts[:2] != ["project-runtime", "artifacts"]:
        return None, None, None, "artifact package path must be under project-runtime/artifacts"
    found_bucket = parts[2]
    if bucket is not None and found_bucket != bucket:
        return None, None, None, f"artifact package path must be under project-runtime/artifacts/{bucket}"
    try:
        location = artifact_storage.safe_artifact_path(found_bucket, "/".join(parts[3:]))
    except artifact_storage.ArtifactPathError as exc:
        return None, None, None, str(exc)
    if location.relative_path != rel_text:
        return None, None, None, "artifact package path is not canonical"
    return package_root, location.relative_path, manifest_path, None


def _target_for_classification(source_relpath: str, target_bucket: str) -> tuple[Path | None, str | None]:
    parts = source_relpath.split("/")
    source_bucket = parts[2]
    member = "/".join(parts[3:])
    if not artifact_storage.is_allowed_storage_transition(source_bucket, target_bucket):
        return None, f"storage transition {source_bucket} -> {target_bucket} is not allowed"
    try:
        location = artifact_storage.safe_artifact_path(target_bucket, member)
    except artifact_storage.ArtifactPathError as exc:
        return None, str(exc)
    return Path(location.relative_path), None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_inventory(package_root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(package_root.rglob("*")):
        if not path.is_file():
            continue
        rows.append(
            {
                "path": path.relative_to(package_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
        )
    return rows


def _read_package_manifest(package_root: Path) -> dict[str, Any]:
    manifest, _findings = _read_json_object(_select_manifest_path(package_root))
    return manifest or {}


def _materialize_canonical_manifest(package_root: Path, manifest: dict[str, Any]) -> None:
    canonical = package_root / CANONICAL_MANIFEST_FILENAME
    canonical.write_text(_json_bytes(manifest), encoding="utf-8")
    for filename in LEGACY_MANIFEST_FILENAMES:
        legacy = package_root / filename
        if legacy.exists():
            legacy.unlink()


def _write_json_out(root: Path, path_text: str, payload: dict[str, object], allowed: tuple[str, ...]) -> tuple[bool, str]:
    path = output_policy.resolve_output_path(path_text)
    error = output_policy.validate_generated_output_path(root, path, allowed_workspace_subdirs=allowed)
    if error is not None:
        return False, f"{error.rule_id}: {error.message}: {error.evidence}"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_json_bytes(payload), encoding="utf-8")
    except OSError as exc:
        return False, str(exc)
    return True, ""


def _print_report(report: dict[str, object], fmt: str) -> None:
    if fmt == "json":
        print(_json_bytes(report), end="")
        return
    print(f"ASO {report['command']}: {str(report['status']).upper()}")
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    print(f"errors: {_as_text(summary.get('errors', 0))}")
    findings = report.get("findings")
    if isinstance(findings, list) and findings:
        print("findings:")
        for finding in findings:
            if isinstance(finding, dict):
                print(f"- {finding.get('rule_id')}: {finding.get('details')}")


def run_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    artifact_path = Path(args.artifact).expanduser()
    if not artifact_path.is_absolute():
        artifact_path = root / artifact_path
    report = _validate_path(
        root,
        artifact_path,
        expected_type=getattr(args, "artifact_type", None),
        expected_task_id=getattr(args, "task_id", None),
        expected_role=getattr(args, "role", None),
        strict=bool(getattr(args, "strict", False)),
    )
    if args.json_out:
        ok, error = _write_json_out(root, str(args.json_out), report, ("project-runtime/reports",))
        if not ok:
            print(f"aso artifact validate: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
    if not args.json_out or args.format == "json":
        _print_report(report, args.format)
    return EXIT_OK if report["status"] == "pass" else EXIT_BLOCKED


def _classification_plan(
    root: Path,
    source_text: str,
    target_bucket: str,
    confirmed: bool,
    reason: str | None = None,
) -> tuple[dict[str, object], Path | None, Path | None, dict[str, Any] | None]:
    source_path, source_relpath, manifest_path, error = _resolve_workspace_package(root, source_text, "candidates")
    findings: list[dict[str, str]] = []
    target_path: Path | None = None
    source_abs: Path | None = source_path
    selected_manifest: dict[str, Any] | None = None
    if error is not None or source_path is None or source_relpath is None:
        findings.append(_finding("ARTIFACT_CLASSIFY_PATH_001", "Candidate artifact path is invalid", error or "invalid artifact path", source_text))
    else:
        target_relpath, target_error = _target_for_classification(source_relpath, target_bucket)
        if target_error is not None or target_relpath is None:
            findings.append(_finding("ARTIFACT_CLASSIFY_TRANSITION_001", "Artifact transition is not allowed", target_error or "invalid transition", source_relpath))
        else:
            target_path = root / target_relpath
        if not source_path.is_dir():
            findings.append(_finding("ARTIFACT_CLASSIFY_READ_001", "Candidate package does not exist", "Candidate package directory must exist before classification.", source_relpath))
        elif manifest_path is None or not manifest_path.is_file():
            findings.append(_finding("ARTIFACT_CLASSIFY_READ_002", "Candidate package manifest is missing", "Candidate package must contain manifest.json.", source_relpath))
        else:
            selected_manifest, manifest_findings = _validate_manifest_selection(root, source_path, manifest_path)
            findings.extend(manifest_findings)
        if target_path is not None and target_path.exists():
            findings.append(_finding("ARTIFACT_CLASSIFY_IMMUTABLE_001", "Target artifact already exists", "Artifact buckets are immutable; refusing overwrite.", target_path.relative_to(root).as_posix()))

    blocked_without_confirm = not confirmed
    counts = _finding_counts(findings)
    blocked_reasons = ["--confirm-write is required for artifact classification writes"] if blocked_without_confirm else []
    status = "blocked" if counts["errors"] or blocked_without_confirm else "ready"
    actual_read_outcome = (
        "completed"
        if source_path is not None and source_path.is_dir() and manifest_path is not None and manifest_path.is_file()
        else "blocked"
    )
    report = {
        "tool": "aso",
        "command": f"artifact {target_bucket[:-2] if target_bucket == 'accepted' else 'reject'}",
        "root": str(root),
        "source": source_text,
        "target_bucket": target_bucket,
        "target": target_path.relative_to(root).as_posix() if target_path is not None else None,
        "status": status,
        "dry_run": not confirmed,
        "requested_write_mode": "confirmed_write" if confirmed else "dry_run",
        "read_only": not confirmed,
        "mutations_performed": False,
        "blocked_reason": _blocked_reason(findings, blocked_reasons),
        "actual_read_outcome": actual_read_outcome,
        "actual_write_outcome": "not_requested" if not confirmed else ("blocked" if status == "blocked" else "pending"),
        "reason": reason.strip() if isinstance(reason, str) and reason.strip() else None,
        "blocked_reasons": blocked_reasons,
        "validators_run": ["candidate_package_path_guard", "storage_transition_guard", "immutability_guard", "manifest_validation", "package_inventory_hash"],
        "findings": findings,
        "summary": {"errors": counts["errors"] + (1 if blocked_without_confirm else 0), "warnings": counts["warnings"]},
    }
    return report, source_abs, target_path, selected_manifest


def _acceptance_receipt_payload(
    root: Path,
    source_path: Path,
    target_path: Path,
    manifest: dict[str, Any],
) -> tuple[dict[str, object], dict[str, object], str]:
    artifact_id = _as_text(manifest.get("artifact_id")) or target_path.name.upper()
    task_id = _as_text(manifest.get("task_id"))
    role = _as_text(manifest.get("role"))
    producer = manifest.get("producer") if isinstance(manifest.get("producer"), dict) else {}
    agent_instance_id = _as_text(producer.get("agent_instance_id") if isinstance(producer, dict) else "")
    accepted_at = _now_utc()
    source_ref = source_path.relative_to(root).as_posix()
    target_ref = target_path.relative_to(root).as_posix()
    target_manifest_ref = (target_path / CANONICAL_MANIFEST_FILENAME).relative_to(root).as_posix()
    receipt_relpath = f"project-runtime/receipts/artifacts/{task_id or 'UNKNOWN'}/{artifact_id}.acceptance.json"
    receipt = {
        "receipt_type": "ARTIFACT_ACCEPTANCE_RECEIPT",
        "receipt_schema_version": "1.0.0",
        "receipt_id": f"ARTIFACT_ACCEPTED-{artifact_id}",
        "artifact_id": artifact_id,
        "artifact_ref": target_manifest_ref,
        "artifact_package_ref": target_ref,
        "candidate_ref": source_ref,
        "task_id": task_id,
        "role": role,
        "agent_instance_id": agent_instance_id,
        "accepted_at": accepted_at,
        "accepted_by": "orchestrator",
        "storage_transition": "candidates -> accepted",
        "inventory": _package_inventory(target_path),
    }
    event = {
        "event": "artifact_accepted",
        "event_type": "ARTIFACT_ACCEPTED",
        "task_id": task_id,
        "role": role,
        "agent_role": role,
        "agent_instance_id": agent_instance_id,
        "artifact_id": artifact_id,
        "artifact_ref": target_manifest_ref,
        "artifact_package_ref": target_ref,
        "candidate_ref": source_ref,
        "receipt_ref": receipt_relpath,
        "accepted_at": accepted_at,
        "timestamp_utc": accepted_at,
        "created_by": "orchestrator",
    }
    return receipt, event, receipt_relpath


def _rejection_report_payload(root: Path, source_path: Path, target_path: Path, reason: str | None) -> tuple[dict[str, object], str]:
    manifest = _read_package_manifest(source_path)
    artifact_id = _as_text(manifest.get("artifact_id")) or target_path.name.upper()
    task_id = _as_text(manifest.get("task_id"))
    rejected_at = _now_utc()
    report_relpath = f"project-runtime/receipts/artifacts/{task_id or 'UNKNOWN'}/{artifact_id}.rejection.json"
    return (
        {
            "receipt_type": "ARTIFACT_REJECTION_REPORT",
            "receipt_schema_version": "1.0.0",
            "receipt_id": f"ARTIFACT_REJECTED-{artifact_id}",
            "artifact_id": artifact_id,
            "artifact_ref": target_path.relative_to(root).as_posix(),
            "candidate_ref": source_path.relative_to(root).as_posix(),
            "task_id": task_id,
            "rejected_at": rejected_at,
            "rejected_by": "orchestrator",
            "reason": reason,
            "storage_transition": "candidates -> rejected",
            "inventory": _package_inventory(target_path),
        },
        report_relpath,
    )


def _append_lifecycle_event(root: Path, event: dict[str, object]) -> None:
    events_path = root / "project-runtime" / "agents" / "instances.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def _run_classify(args: argparse.Namespace, target_bucket: str) -> int:
    root = Path(args.root).expanduser()
    report, source_path, target_path, selected_manifest = _classification_plan(
        root,
        str(args.artifact),
        target_bucket,
        bool(args.confirm_write),
        getattr(args, "reason", None),
    )
    files_written: list[str] = []
    if args.confirm_write and report["status"] == "ready":
        assert source_path is not None
        assert target_path is not None
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_path, target_path)
            if target_bucket == "accepted":
                assert selected_manifest is not None
                _materialize_canonical_manifest(target_path, selected_manifest)
                receipt, event, receipt_relpath = _acceptance_receipt_payload(root, source_path, target_path, selected_manifest)
                receipt_path = root / receipt_relpath
                receipt_path.parent.mkdir(parents=True, exist_ok=True)
                receipt_path.write_text(_json_bytes(receipt), encoding="utf-8")
                _append_lifecycle_event(root, event)
                materialization = state_materialization.materialize_after_confirmed_write(root)
                report["state_materialization"] = materialization.to_json()
                if not materialization.ok:
                    print(f"aso {report['command']}: failed to materialize state sidecars: {materialization.error}", file=sys.stderr)
                    return EXIT_IO_ERROR
                report["receipt"] = receipt
                report["receipt_ref"] = receipt_relpath
                report["event"] = event
            else:
                rejection, rejection_relpath = _rejection_report_payload(root, source_path, target_path, report.get("reason") if isinstance(report.get("reason"), str) else None)
                rejection_path = root / rejection_relpath
                rejection_path.parent.mkdir(parents=True, exist_ok=True)
                rejection_path.write_text(_json_bytes(rejection), encoding="utf-8")
                report["rejection_report"] = rejection
                report["rejection_report_ref"] = rejection_relpath
        except OSError as exc:
            print(f"aso {report['command']}: failed to write artifact: {exc}", file=sys.stderr)
            return EXIT_IO_ERROR
        files_written.append(target_path.relative_to(root).as_posix())
        if target_bucket == "accepted" and isinstance(report.get("receipt_ref"), str):
            files_written.append(str(report["receipt_ref"]))
        if target_bucket == "rejected" and isinstance(report.get("rejection_report_ref"), str):
            files_written.append(str(report["rejection_report_ref"]))
        report["status"] = "written"
        report["read_only"] = False
        report["mutations_performed"] = True
        report["blocked_reason"] = None
        report["actual_write_outcome"] = "completed"
        report["files_written"] = files_written
    if getattr(args, "json_out", None):
        ok, error = _write_json_out(root, str(args.json_out), report, ("project-runtime/reports",))
        if not ok:
            print(f"aso {report['command']}: {error}", file=sys.stderr)
            return EXIT_IO_ERROR
    _print_report(report, args.format)
    if report["status"] in {"ready", "written"}:
        return EXIT_OK
    return EXIT_BLOCKED


def run_accept(args: argparse.Namespace) -> int:
    return _run_classify(args, "accepted")


def run_reject(args: argparse.Namespace) -> int:
    return _run_classify(args, "rejected")


def _iter_artifacts(root: Path, bucket: str | None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    buckets = (bucket,) if bucket else artifact_storage.ARTIFACT_STORAGE_BUCKETS
    for item_bucket in buckets:
        base = root / artifact_storage.artifact_storage_roots()[item_bucket]
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file():
                rows.append(
                    {
                        "bucket": item_bucket,
                        "path": path.relative_to(root).as_posix(),
                        "bytes": path.stat().st_size,
                    }
                )
    return rows


def _artifact_row(root: Path, value: str) -> dict[str, object] | None:
    path, relpath, _manifest_path, error = _resolve_workspace_package(root, value)
    if error is not None or path is None or relpath is None or not path.is_dir():
        return None
    return {
        "bucket": relpath.split("/")[2],
        "path": relpath,
        "bytes": sum(item.stat().st_size for item in path.rglob("*") if item.is_file()),
    }


def run_list(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    rows = _iter_artifacts(root, args.bucket)
    report = {
        "tool": "aso",
        "command": "artifact list",
        "root": str(root),
        "bucket": args.bucket or "all",
        "status": "pass",
        "read_only": True,
        "mutations_performed": False,
        "artifacts": rows,
        "summary": {"count": len(rows)},
    }
    if args.format == "json":
        print(_json_bytes(report), end="")
    else:
        print(f"ASO artifact list: {len(rows)}")
        for row in rows:
            print(f"- {row['bucket']} {row['path']} ({row['bytes']} bytes)")
    return EXIT_OK


def _render_markdown(report: dict[str, object]) -> str:
    artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), list) else []
    lines = [
        "# ASO Artifact Storage Report",
        "",
        f"Root: {_as_text(report.get('root'))}",
        f"Bucket: {_as_text(report.get('bucket'))}",
        f"Count: {len(artifacts)}",
        "",
        "## Artifacts",
        "",
    ]
    if not artifacts:
        lines.append("- NONE")
    for item in artifacts:
        if isinstance(item, dict):
            lines.append(f"- `{_as_text(item.get('bucket'))}` `{_as_text(item.get('path'))}` ({_as_text(item.get('bytes'))} bytes)")
    return "\n".join(lines).rstrip() + "\n"


def run_render(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    if getattr(args, "artifact", None):
        row = _artifact_row(root, str(args.artifact))
        rows = [] if row is None else [row]
    else:
        rows = _iter_artifacts(root, args.bucket)
    report = {
        "tool": "aso",
        "command": "artifact render",
        "root": str(root),
        "bucket": args.bucket or "all",
        "status": "pass",
        "read_only": True,
        "mutations_performed": False,
        "artifacts": rows,
        "summary": {"count": len(rows)},
    }
    rendered = _json_bytes(report) if args.format == "json" else _render_markdown(report)
    if args.out:
        path = output_policy.resolve_output_path(str(args.out))
        error = output_policy.validate_generated_output_path(root, path, allowed_workspace_subdirs=("project-runtime/reports", "project-runtime/rendered"))
        if error is not None:
            print(f"aso artifact render: {error.rule_id}: {error.message}: {error.evidence}", file=sys.stderr)
            return EXIT_IO_ERROR
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            print(f"aso artifact render: failed to write output: {exc}", file=sys.stderr)
            return EXIT_IO_ERROR
        print(f"ASO artifact render written: {path}")
        return EXIT_OK
    print(rendered, end="" if rendered.endswith("\n") else "\n")
    return EXIT_OK
