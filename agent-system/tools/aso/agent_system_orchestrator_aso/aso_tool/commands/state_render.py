"""Read-only Runtime Schema state report renderer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from .. import runtime_schema_contracts
from . import output_policy, state_verify


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3


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


def _content(payload: dict[str, object]) -> dict[str, object]:
    content = payload.get("content")
    return content if isinstance(content, dict) else {}


def _load_sidecars(root: Path) -> dict[str, dict[str, object]]:
    sidecars: dict[str, dict[str, object]] = {}
    state_root = root / runtime_schema_contracts.STATE_ROOT
    for sidecar_type in runtime_schema_contracts.ALL_SIDECARS:
        path = state_root / f"{sidecar_type}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            sidecars[sidecar_type] = payload
    return dict(sorted(sidecars.items()))


def _schema_versions(sidecars: dict[str, dict[str, object]]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for sidecar_type, payload in sorted(sidecars.items()):
        schema_version = payload.get("schema_version")
        content = _content(payload)
        runtime_version = payload.get("runtime_schema_version") or content.get("runtime_schema_version")
        if schema_version == runtime_version or not runtime_version:
            versions[sidecar_type] = _as_text(schema_version) or "missing"
        else:
            versions[sidecar_type] = f"{_as_text(schema_version) or 'missing'}/{_as_text(runtime_version)}"
    return versions


def _compatibility(sidecars: dict[str, dict[str, object]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for sidecar_type, payload in sorted(sidecars.items()):
        result[sidecar_type] = runtime_schema_contracts.compatibility_status(payload.get("schema_version"))
    return result


def _sidecar_summary(sidecar_type: str, payload: dict[str, object]) -> dict[str, object]:
    content = _content(payload)
    summary: dict[str, object] = {
        "schema_version": payload.get("schema_version", ""),
        "runtime_schema_version": payload.get("runtime_schema_version", ""),
        "compatibility_status": runtime_schema_contracts.compatibility_status(payload.get("schema_version")),
        "state_revision": payload.get("state_revision", ""),
        "updated_at": payload.get("updated_at", ""),
        "updated_by": payload.get("updated_by", ""),
        "content_fields": sorted(content),
    }
    if sidecar_type == "PROJECT_STATE":
        summary["project_slug"] = content.get("project_slug", "")
        summary["project_status"] = content.get("project_status", "")
        summary["current_phase"] = content.get("current_phase", "")
    elif sidecar_type == "TASK_REGISTRY":
        tasks = content.get("tasks")
        summary["task_count"] = len(tasks) if isinstance(tasks, list) else 0
    elif sidecar_type == "NEXT_ACTION":
        summary["action_type"] = content.get("action_type", "")
        summary["target_role"] = content.get("target_role", "")
        summary["task_id"] = content.get("task_id", "")
    elif sidecar_type == "CURRENT_GATE":
        summary["gate_id"] = content.get("gate_id", "")
        summary["status"] = content.get("status", "")
        summary["task_id"] = content.get("task_id", "")
    elif sidecar_type == "SCHEMA_MANIFEST":
        summary["state_root"] = content.get("state_root", "")
        summary["package_version"] = content.get("package_version", "")
    return summary


def build_report(root: Path) -> dict[str, object]:
    verify_report, verify_exit_code = state_verify._report(root, False)
    sidecars = _load_sidecars(root)
    state = verify_report.get("state") if isinstance(verify_report.get("state"), dict) else {}
    summary = verify_report.get("summary") if isinstance(verify_report.get("summary"), dict) else {}
    compatibility = _compatibility(sidecars)
    migration_available = sorted(
        sidecar_type
        for sidecar_type, status in compatibility.items()
        if status == "compatible_migration_available"
    )
    unsupported = sorted(
        sidecar_type
        for sidecar_type, status in compatibility.items()
        if status in {"unsupported", "malformed"}
    )

    return {
        "tool": "aso",
        "command": "state render",
        "mode": "workspace",
        "root": str(root),
        "read_only": True,
        "mutations_performed": False,
        "runtime_schema": {
            "active_version": runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION,
            "current_p2_state": state.get("runtime_schema_current_p2", False),
            "verification_status": verify_report.get("status", ""),
            "verification_exit_code": verify_exit_code,
            "verification_summary": summary,
            "sidecar_schema_versions": _schema_versions(sidecars),
            "compatibility_status": compatibility,
            "migration_available_sidecars": migration_available,
            "unsupported_sidecars": unsupported,
            "required_sidecars_missing": state.get("required_sidecars_missing", []),
            "optional_sidecars_missing": state.get("optional_sidecars_missing", []),
        },
        "sidecars": {
            sidecar_type: _sidecar_summary(sidecar_type, payload)
            for sidecar_type, payload in sidecars.items()
        },
        "state_verify": verify_report,
    }


def _markdown_list(values: Iterable[object]) -> str:
    rendered = [f"- {_as_text(value)}" for value in values]
    return "\n".join(rendered) if rendered else "- NONE"


def render_markdown(report: dict[str, object]) -> str:
    runtime = report["runtime_schema"] if isinstance(report.get("runtime_schema"), dict) else {}
    sidecars = report["sidecars"] if isinstance(report.get("sidecars"), dict) else {}
    lines = [
        "# ASO Runtime State Report",
        "",
        f"Root: {_as_text(report.get('root'))}",
        f"Read only: {_as_text(report.get('read_only'))}",
        f"Runtime schema: {_as_text(runtime.get('active_version'))}",
        f"Verification status: {_as_text(runtime.get('verification_status'))}",
        f"Current P2 state: {_as_text(runtime.get('current_p2_state'))}",
        "",
        "## Schema And Migration Health",
        "",
        "Required sidecars missing:",
        _markdown_list(runtime.get("required_sidecars_missing", []) if isinstance(runtime.get("required_sidecars_missing"), list) else []),
        "",
        "Optional sidecars missing:",
        _markdown_list(runtime.get("optional_sidecars_missing", []) if isinstance(runtime.get("optional_sidecars_missing"), list) else []),
        "",
        "Migration available:",
        _markdown_list(runtime.get("migration_available_sidecars", []) if isinstance(runtime.get("migration_available_sidecars"), list) else []),
        "",
        "Unsupported sidecars:",
        _markdown_list(runtime.get("unsupported_sidecars", []) if isinstance(runtime.get("unsupported_sidecars"), list) else []),
        "",
        "## Sidecars",
        "",
    ]
    for sidecar_type, raw in sorted(sidecars.items()):
        if not isinstance(raw, dict):
            continue
        lines.extend(
            [
                f"### {sidecar_type}",
                "",
                f"- schema_version: {_as_text(raw.get('schema_version'))}",
                f"- runtime_schema_version: {_as_text(raw.get('runtime_schema_version'))}",
                f"- compatibility_status: {_as_text(raw.get('compatibility_status'))}",
                f"- state_revision: {_as_text(raw.get('state_revision'))}",
                f"- updated_at: {_as_text(raw.get('updated_at'))}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _resolve_output_path(root: Path, path_text: str) -> tuple[Path | None, str]:
    resolved = output_policy.resolve_output_path(path_text)
    error = output_policy.validate_generated_output_path(
        root,
        resolved,
        allowed_workspace_subdirs=("project-runtime/reports", "project-runtime/rendered"),
    )
    if error is None:
        return resolved, ""
    return None, f"{error.rule_id}: {error.message}"


def _write_allowed(root: Path, path_text: str, content: str) -> bool:
    path, error = _resolve_output_path(root, path_text)
    if path is None:
        print(f"aso state render: forbidden output path: {error}: {path_text}", file=sys.stderr)
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        print(f"aso state render: failed to write output: {exc}", file=sys.stderr)
        return False
    return True


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    report = build_report(root)
    if args.format == "json":
        rendered = _json_bytes(report)
    else:
        rendered = render_markdown(report)

    if args.out:
        if not _write_allowed(root, str(args.out), rendered):
            return EXIT_IO_ERROR
        print(f"ASO state render written: {Path(args.out).expanduser()}")
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")

    runtime = report.get("runtime_schema") if isinstance(report.get("runtime_schema"), dict) else {}
    summary = runtime.get("verification_summary") if isinstance(runtime.get("verification_summary"), dict) else {}
    return EXIT_FINDINGS if summary.get("errors", 0) else EXIT_OK
