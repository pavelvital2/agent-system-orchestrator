"""Runtime Schema state report and compatibility-view renderer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from .. import state_materialization
from .. import runtime_schema_contracts
from . import output_policy, state_verify


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3
MATERIALIZED_VIEW_TYPES = runtime_schema_contracts.ALL_SIDECARS
NEXT_ACTION_REFRESH_BLOCKING_RULES = {
    "SIDECAR_JSON_PARSE_ERROR",
    "SIDECAR_TOP_LEVEL_NOT_OBJECT",
    "SIDECAR_REQUIRED_SIDECAR_MISSING",
    "SIDECAR_REQUIRED_FIELD_MISSING",
    "SIDECAR_REQUIRED_FIELD_EMPTY",
    "SIDECAR_TYPE_INVALID",
    "SIDECAR_BOOLEAN_VALUE_INVALID",
    "SIDECAR_ENUM_VALUE_INVALID",
    "SIDECAR_UNKNOWN_GOVERNED_FIELD",
    "SIDECAR_SCHEMA_VERSION_MISSING_OR_INVALID",
    "SIDECAR_RUNTIME_SCHEMA_VERSION_INVALID",
    "SIDECAR_TYPE_MISMATCH",
    "SIDECAR_MARKDOWN_SOURCE_MISMATCH",
    "SIDECAR_STATE_REVISION_INVALID",
    "SIDECAR_TIMESTAMP_INVALID",
}


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


def _load_all_sidecars(root: Path) -> dict[str, dict[str, object]]:
    sidecars = _load_sidecars(root)
    state_root = root / runtime_schema_contracts.STATE_ROOT
    for sidecar_type in MATERIALIZED_VIEW_TYPES:
        if sidecar_type in sidecars:
            continue
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


def _materialized_relpath(sidecar_type: str, payload: dict[str, object]) -> str:
    source = payload.get("markdown_source")
    expected = f"project-runtime/{sidecar_type}.md"
    if source == expected:
        return source
    return expected


def _field_lines(key: str, value: object) -> list[str]:
    field = key.upper()
    if isinstance(value, list):
        if not value:
            return [f"{field}: NONE"]
        lines: list[str] = []
        for item in value:
            if isinstance(item, dict):
                for item_key, item_value in item.items():
                    lines.extend(_field_lines(str(item_key), item_value))
                lines.append("")
            else:
                lines.append(f"{field}: {_as_text(item)}")
        return lines
    if isinstance(value, dict):
        if not value:
            return [f"{field}: NONE"]
        return [f"{field}: {_as_text(value)}"]
    text = _as_text(value)
    return [f"{field}: {text if text else 'NONE'}"]


def render_compatibility_view(sidecar_type: str, payload: dict[str, object]) -> str:
    content = _content(payload)
    source = f"project-runtime/state/{sidecar_type}.json"
    lines = [
        "DERIVED VIEW.",
        f"Source: {source}",
        "Do not edit this file directly.",
        "Canonical state is JSON sidecar.",
        "",
        f"# {sidecar_type}",
        "",
    ]
    for key, value in sorted(content.items()):
        lines.extend(_field_lines(key, value))
        if isinstance(value, list) and value and isinstance(value[0], dict):
            continue
    return "\n".join(line for line in lines if line is not None).rstrip() + "\n"


def _refresh_blocked_by_structural_findings(verify_report: dict[str, object]) -> list[dict[str, object]]:
    findings = verify_report.get("findings")
    if not isinstance(findings, list):
        return []
    blocked: list[dict[str, object]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        if finding.get("severity") != "error":
            continue
        if str(finding.get("rule_id", "")) in NEXT_ACTION_REFRESH_BLOCKING_RULES:
            blocked.append(finding)
    return blocked


def _refresh_next_action_cache(root: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    verify_report, _ = state_verify._report(root, True)
    blocked = _refresh_blocked_by_structural_findings(verify_report)
    if blocked:
        return [], [
            {
                "rule_id": "STATE_RENDER_NEXT_ACTION_REFRESH_BLOCKED",
                "severity": "error",
                "title": "NEXT_ACTION cache refresh blocked by invalid state",
                "details": "NEXT_ACTION cache refresh requires structurally valid sidecars.",
                "path": "project-runtime/state",
                "recommendation": "Repair sidecar schema/type/enum findings before refreshing the derived NEXT_ACTION cache.",
                "blocked_by": [
                    {
                        "rule_id": item.get("rule_id", ""),
                        "path": item.get("path", ""),
                        "field": item.get("field", ""),
                    }
                    for item in blocked
                ],
            }
        ]

    result = state_materialization.refresh_next_action_cache(root)
    if not result.ok:
        return [], [
            {
                "rule_id": "STATE_RENDER_NEXT_ACTION_REFRESH_FAILED",
                "severity": "error",
                "title": "NEXT_ACTION cache refresh failed",
                "details": result.error or "NEXT_ACTION cache refresh failed.",
                "path": "project-runtime/state/NEXT_ACTION.json",
                "recommendation": "Repair runtime state and rerun aso state render --confirm-write.",
            }
        ]
    writes = [
        {
            "path": relpath,
            "sidecar_type": "NEXT_ACTION",
            "source": "canonical_derivation_inputs",
            "changed": True,
        }
        for relpath in result.files_written
    ]
    return writes, []


def materialize_compatibility_views(root: Path) -> tuple[dict[str, object], int]:
    cache_writes, cache_findings = _refresh_next_action_cache(root)
    sidecars = _load_all_sidecars(root)
    writes: list[dict[str, object]] = []
    findings: list[dict[str, object]] = list(cache_findings)

    for sidecar_type in MATERIALIZED_VIEW_TYPES:
        payload = sidecars.get(sidecar_type)
        if not isinstance(payload, dict):
            findings.append(
                {
                    "rule_id": "STATE_RENDER_MATERIALIZE_001",
                    "severity": "error",
                    "title": "Required sidecar is missing",
                    "details": f"project-runtime/state/{sidecar_type}.json is required to render {sidecar_type}.md.",
                    "path": f"project-runtime/state/{sidecar_type}.json",
                    "recommendation": "Restore or initialize the JSON sidecar before materializing Markdown compatibility views.",
                }
            )
            continue
        expected_relpath = f"project-runtime/{sidecar_type}.md"
        source_relpath = payload.get("markdown_source")
        if source_relpath not in (None, expected_relpath):
            findings.append(
                {
                    "rule_id": "STATE_RENDER_MATERIALIZE_002",
                    "severity": "error",
                    "title": "Markdown view path is not allowed",
                    "details": f"{sidecar_type}.markdown_source={source_relpath!r} must be {expected_relpath!r}.",
                    "path": f"project-runtime/state/{sidecar_type}.json",
                    "recommendation": "Set markdown_source to the matching project-runtime/<SIDE_CAR>.md compatibility view.",
                }
            )
            continue
        relpath = _materialized_relpath(sidecar_type, payload)
        if relpath != f"project-runtime/{Path(relpath).name}" or not relpath.endswith(".md"):
            findings.append(
                {
                    "rule_id": "STATE_RENDER_MATERIALIZE_002",
                    "severity": "error",
                    "title": "Markdown view path is not allowed",
                    "details": f"{sidecar_type}.markdown_source={relpath!r} is outside project-runtime/*.md.",
                    "path": f"project-runtime/state/{sidecar_type}.json",
                    "recommendation": "Set markdown_source to the matching project-runtime/<SIDE_CAR>.md compatibility view.",
                }
            )
            continue
        path = root / relpath
        rendered = render_compatibility_view(sidecar_type, payload)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            before = path.read_text(encoding="utf-8") if path.exists() else None
            path.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            findings.append(
                {
                    "rule_id": "STATE_RENDER_MATERIALIZE_003",
                    "severity": "error",
                    "title": "Markdown view write failed",
                    "details": f"{relpath}: {exc}",
                    "path": relpath,
                    "recommendation": "Repair workspace permissions and rerun aso state render --confirm-write.",
                }
            )
            continue
        writes.append(
            {
                "path": relpath,
                "sidecar_type": sidecar_type,
                "source": f"project-runtime/state/{sidecar_type}.json",
                "changed": before != rendered,
            }
        )

    status = "failed" if findings else "written"
    return {
        "tool": "aso",
        "command": "state render",
        "mode": "workspace",
        "root": str(root),
        "materialization": "markdown_compatibility_views",
        "status": status,
        "canonical_state": runtime_schema_contracts.STATE_ROOT,
        "mutations_performed": bool(writes or cache_writes),
        "state_cache_writes": cache_writes,
        "writes": writes,
        "findings": findings,
        "summary": {
            "errors": len(findings),
            "state_cache_writes": len(cache_writes),
            "views_written": len(writes),
            "views_changed": sum(1 for item in writes if item.get("changed")),
        },
    }, EXIT_FINDINGS if findings else EXIT_OK


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    if getattr(args, "confirm_write", False):
        if args.out:
            print("aso state render: --confirm-write cannot be combined with --out", file=sys.stderr)
            return EXIT_IO_ERROR
        report, exit_code = materialize_compatibility_views(root)
        print(_json_bytes(report), end="")
        return exit_code

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
