"""P5 governed artifact storage CLI commands."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import artifact_storage, runtime_schema_contracts
from . import output_policy


EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_IO_ERROR = 3

SCHEMA_RELPATH = "agent-system/09_validators/schemas/artifact_package_manifest.schema.json"
ARTIFACT_ID_RE = re.compile(r"^[A-Z][A-Z0-9_:-]+$")
PACKAGE_FORBIDDEN_ROOTS = (".venv", "project-input", "project-runtime", "project-archive")
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
        "recommendation": "Conform the artifact package manifest to P5 schema 1.0.0.",
    }


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


def _validate_manifest_payload(payload: dict[str, Any], root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    schema = _load_manifest_schema(root)
    schema_types = (
        schema.get("$defs", {}).get("artifactType", {}).get("enum")
        if isinstance(schema.get("$defs"), dict)
        else None
    )
    allowed_types = tuple(schema_types) if isinstance(schema_types, list) else ALLOWED_ARTIFACT_TYPES

    missing = [field for field in REQUIRED_MANIFEST_FIELDS if field not in payload]
    extra = sorted(set(payload) - set(REQUIRED_MANIFEST_FIELDS))
    for field in missing:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_001", "Manifest required field is missing", f"{field} is required.", field))
    for field in extra:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_002", "Manifest field is not allowed", f"{field} is not declared by the P5 manifest schema.", field))

    if payload.get("artifact_package_schema_version") != runtime_schema_contracts.ACTIVE_ARTIFACT_PACKAGE_SCHEMA_VERSION:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_003", "Artifact package schema version is invalid", "artifact_package_schema_version must be 1.0.0.", "artifact_package_schema_version"))
    if payload.get("artifact_type") not in allowed_types:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_004", "Artifact type is unsupported", f"artifact_type must be one of: {', '.join(allowed_types)}.", "artifact_type"))
    artifact_id = payload.get("artifact_id")
    if not isinstance(artifact_id, str) or not ARTIFACT_ID_RE.fullmatch(artifact_id):
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_005", "Artifact id is invalid", "artifact_id must match ^[A-Z][A-Z0-9_:-]+$.", "artifact_id"))
    if not isinstance(payload.get("task_id"), str) or not str(payload.get("task_id", "")).strip():
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_006", "Task id is invalid", "task_id must be a non-empty string.", "task_id"))
    if payload.get("role") not in ALLOWED_ROLES:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_007", "Role is unsupported", f"role must be one of: {', '.join(ALLOWED_ROLES)}.", "role"))
    if not isinstance(payload.get("attempt_no"), int) or isinstance(payload.get("attempt_no"), bool) or payload.get("attempt_no", 0) < 1:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_008", "Attempt number is invalid", "attempt_no must be an integer >= 1.", "attempt_no"))
    if payload.get("status") not in ALLOWED_STATUSES:
        findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_009", "Status is unsupported", f"status must be one of: {', '.join(ALLOWED_STATUSES)}.", "status"))
    for error in _package_path_errors(payload.get("main_document"), "main_document"):
        findings.append(_finding("ARTIFACT_VALIDATE_PATH_001", "Main document path is invalid", error, "main_document"))
    for field in ("structured_artifacts", "evidence_refs"):
        for error in _artifact_refs_errors(payload.get(field), field):
            findings.append(_finding("ARTIFACT_VALIDATE_PATH_002", "Artifact reference path is invalid", error, field))
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
        if producer.get("role") not in ALLOWED_ROLES:
            findings.append(_finding("ARTIFACT_VALIDATE_SCHEMA_014", "Producer role is unsupported", f"producer.role must be one of: {', '.join(ALLOWED_ROLES)}.", "producer.role"))
    return findings


def _validate_path(root: Path, artifact_path: Path, expected_type: str | None = None, strict: bool = False) -> dict[str, object]:
    payload, findings = _read_json_object(artifact_path)
    if payload is not None:
        findings.extend(_validate_manifest_payload(payload, root))
        if expected_type is not None and payload.get("artifact_type") != expected_type:
            findings.append(
                _finding(
                    "ARTIFACT_VALIDATE_TYPE_001",
                    "Artifact type does not match requested type",
                    f"artifact_type must be {expected_type}.",
                    "artifact_type",
                )
            )
    status = "pass" if not findings else "blocked"
    return {
        "tool": "aso",
        "command": "artifact validate",
        "root": str(root),
        "artifact": str(artifact_path),
        "schema_path": SCHEMA_RELPATH,
        "artifact_package_schema_version": runtime_schema_contracts.ACTIVE_ARTIFACT_PACKAGE_SCHEMA_VERSION,
        "status": status,
        "strict": strict,
        "read_only": True,
        "mutations_performed": False,
        "validators_run": ["json_parse", "artifact_package_manifest_schema", "package_path_boundary"],
        "findings": findings,
        "summary": {"errors": len(findings)},
    }


def _resolve_workspace_artifact(root: Path, value: str, bucket: str | None = None) -> tuple[Path | None, str | None, str | None]:
    raw = Path(value).expanduser()
    workspace = root.expanduser().resolve(strict=False)
    if raw.is_absolute():
        resolved = raw.resolve(strict=False)
        try:
            rel = resolved.relative_to(workspace)
        except ValueError:
            return None, None, "artifact path must be inside --root"
        rel_text = rel.as_posix()
    else:
        rel_text = value
        resolved = (workspace / rel_text).resolve(strict=False)

    parts = rel_text.split("/")
    if len(parts) < 4 or parts[:2] != ["project-runtime", "artifacts"]:
        return None, None, "artifact path must be under project-runtime/artifacts"
    found_bucket = parts[2]
    if bucket is not None and found_bucket != bucket:
        return None, None, f"artifact path must be under project-runtime/artifacts/{bucket}"
    try:
        location = artifact_storage.safe_artifact_path(found_bucket, "/".join(parts[3:]))
    except artifact_storage.ArtifactPathError as exc:
        return None, None, str(exc)
    if location.relative_path != rel_text:
        return None, None, "artifact path is not canonical"
    try:
        resolved.relative_to(workspace)
    except ValueError:
        return None, None, "artifact path escapes --root"
    return resolved, location.relative_path, None


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


def _classification_plan(root: Path, source_text: str, target_bucket: str, confirmed: bool, reason: str | None = None) -> tuple[dict[str, object], Path | None, Path | None]:
    source_path, source_relpath, error = _resolve_workspace_artifact(root, source_text, "candidates")
    findings: list[dict[str, str]] = []
    target_path: Path | None = None
    source_abs: Path | None = source_path
    if error is not None or source_path is None or source_relpath is None:
        findings.append(_finding("ARTIFACT_CLASSIFY_PATH_001", "Candidate artifact path is invalid", error or "invalid artifact path", source_text))
    else:
        target_relpath, target_error = _target_for_classification(source_relpath, target_bucket)
        if target_error is not None or target_relpath is None:
            findings.append(_finding("ARTIFACT_CLASSIFY_TRANSITION_001", "Artifact transition is not allowed", target_error or "invalid transition", source_relpath))
        else:
            target_path = root / target_relpath
        if not source_path.is_file():
            findings.append(_finding("ARTIFACT_CLASSIFY_READ_001", "Candidate artifact does not exist", "Candidate artifact must exist before classification.", source_relpath))
        elif source_path.suffix == ".json":
            validation = _validate_path(root, source_path)
            for finding in validation.get("findings", []):
                if isinstance(finding, dict):
                    findings.append(dict(finding))
        if target_path is not None and target_path.exists():
            findings.append(_finding("ARTIFACT_CLASSIFY_IMMUTABLE_001", "Target artifact already exists", "Artifact buckets are immutable; refusing overwrite.", target_path.relative_to(root).as_posix()))

    blocked_without_confirm = not confirmed
    status = "blocked" if findings or blocked_without_confirm else "ready"
    report = {
        "tool": "aso",
        "command": f"artifact {target_bucket[:-2] if target_bucket == 'accepted' else 'reject'}",
        "root": str(root),
        "source": source_text,
        "target_bucket": target_bucket,
        "target": target_path.relative_to(root).as_posix() if target_path is not None else None,
        "status": status,
        "dry_run": not confirmed,
        "read_only": not confirmed,
        "mutations_performed": False,
        "reason": reason.strip() if isinstance(reason, str) and reason.strip() else None,
        "blocked_reasons": (["--confirm-write is required for artifact classification writes"] if blocked_without_confirm else []),
        "validators_run": ["candidate_path_guard", "storage_transition_guard", "immutability_guard", "manifest_validation_if_json"],
        "findings": findings,
        "summary": {"errors": len(findings) + (1 if blocked_without_confirm else 0)},
    }
    return report, source_abs, target_path


def _acceptance_receipt_payload(
    root: Path,
    source_path: Path,
    target_path: Path,
) -> tuple[dict[str, object], dict[str, object], str]:
    manifest, _findings = _read_json_object(source_path)
    manifest = manifest or {}
    artifact_id = _as_text(manifest.get("artifact_id")) or target_path.stem.upper()
    task_id = _as_text(manifest.get("task_id"))
    role = _as_text(manifest.get("role"))
    producer = manifest.get("producer") if isinstance(manifest.get("producer"), dict) else {}
    agent_instance_id = _as_text(producer.get("agent_instance_id") if isinstance(producer, dict) else "")
    accepted_at = _now_utc()
    source_ref = source_path.relative_to(root).as_posix()
    target_ref = target_path.relative_to(root).as_posix()
    receipt_relpath = f"project-runtime/receipts/artifacts/{task_id or 'UNKNOWN'}/{artifact_id}.acceptance.json"
    receipt = {
        "receipt_type": "ARTIFACT_ACCEPTANCE_RECEIPT",
        "receipt_schema_version": "1.0.0",
        "receipt_id": f"ARTIFACT_ACCEPTED-{artifact_id}",
        "artifact_id": artifact_id,
        "artifact_ref": target_ref,
        "candidate_ref": source_ref,
        "task_id": task_id,
        "role": role,
        "agent_instance_id": agent_instance_id,
        "accepted_at": accepted_at,
        "accepted_by": "orchestrator",
        "storage_transition": "candidates -> accepted",
    }
    event = {
        "event": "artifact_accepted",
        "event_type": "ARTIFACT_ACCEPTED",
        "task_id": task_id,
        "role": role,
        "agent_role": role,
        "agent_instance_id": agent_instance_id,
        "artifact_id": artifact_id,
        "artifact_ref": target_ref,
        "candidate_ref": source_ref,
        "receipt_ref": receipt_relpath,
        "accepted_at": accepted_at,
        "timestamp_utc": accepted_at,
        "created_by": "orchestrator",
    }
    return receipt, event, receipt_relpath


def _append_lifecycle_event(root: Path, event: dict[str, object]) -> None:
    events_path = root / "project-runtime" / "agents" / "instances.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def _run_classify(args: argparse.Namespace, target_bucket: str) -> int:
    root = Path(args.root).expanduser()
    report, source_path, target_path = _classification_plan(
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
            shutil.copyfile(source_path, target_path)
            if target_bucket == "accepted":
                receipt, event, receipt_relpath = _acceptance_receipt_payload(root, source_path, target_path)
                receipt_path = root / receipt_relpath
                receipt_path.parent.mkdir(parents=True, exist_ok=True)
                receipt_path.write_text(_json_bytes(receipt), encoding="utf-8")
                _append_lifecycle_event(root, event)
                report["receipt"] = receipt
                report["receipt_ref"] = receipt_relpath
                report["event"] = event
        except OSError as exc:
            print(f"aso {report['command']}: failed to write artifact: {exc}", file=sys.stderr)
            return EXIT_IO_ERROR
        files_written.append(target_path.relative_to(root).as_posix())
        if target_bucket == "accepted" and isinstance(report.get("receipt_ref"), str):
            files_written.append(str(report["receipt_ref"]))
        report["status"] = "written"
        report["read_only"] = False
        report["mutations_performed"] = True
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
    path, relpath, error = _resolve_workspace_artifact(root, value)
    if error is not None or path is None or relpath is None or not path.is_file():
        return None
    return {
        "bucket": relpath.split("/")[2],
        "path": relpath,
        "bytes": path.stat().st_size,
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
