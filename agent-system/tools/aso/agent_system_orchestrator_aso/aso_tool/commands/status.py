"""Read-only status command."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from . import mode_guard, package_checks, repair_hints


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3

RUNTIME_FILES = (
    "PROJECT_STATE.md",
    "CURRENT_GATE.md",
    "NEXT_ACTION.md",
    "TASK_REGISTRY.md",
    "ACCEPTED_ARTIFACTS.md",
    "REPOSITORY_LOCK.md",
    "WORKSPACE_IDENTITY.md",
)

FIELD_RE = re.compile(r"^([A-Z][A-Z0-9_]*):(?:[ \t]*(.*))?$")
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RuntimeFile:
    relpath: str
    exists: bool
    fields: dict[str, str]
    error: str | None = None


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    title: str
    details: str
    files: list[str]
    recommendation: str

    def to_json(self, mode: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.details,
            "path": self.files[0] if self.files else "",
            "title": self.title,
            "details": self.details,
            "files": self.files,
            "recommendation": self.recommendation,
        }
        if mode is not None:
            payload["mode"] = mode
        return payload


def _runtime_path(root: Path, name: str) -> Path:
    return root / "project-runtime" / name


def _read_runtime_file(root: Path, name: str) -> RuntimeFile:
    relpath = f"project-runtime/{name}"
    path = _runtime_path(root, name)
    if not path.exists():
        return RuntimeFile(relpath=relpath, exists=False, fields={})
    if not path.is_file():
        return RuntimeFile(
            relpath=relpath,
            exists=False,
            fields={},
            error="path exists but is not a regular file",
        )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return RuntimeFile(relpath=relpath, exists=True, fields={}, error=str(exc))
    return RuntimeFile(relpath=relpath, exists=True, fields=_parse_fields(text))


def _parse_fields(text: str) -> dict[str, str]:
    """Parse simple ASO markdown state fields.

    Runtime files in existing workspaces use both `KEY: value` and a two-line
    `KEY:\nvalue` form, so status accepts both and keeps the first non-empty
    value for each key.
    """
    fields: dict[str, str] = {}
    pending_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = FIELD_RE.match(line)
        if match:
            if pending_key and pending_key not in fields:
                fields[pending_key] = ""
            key, value = match.group(1), (match.group(2) or "").strip()
            if value:
                fields.setdefault(key, value)
                pending_key = None
            else:
                pending_key = key
            continue

        if pending_key is None:
            continue
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        fields.setdefault(pending_key, line)
        pending_key = None

    if pending_key and pending_key not in fields:
        fields[pending_key] = ""

    return fields


def _value(files: dict[str, RuntimeFile], file_name: str, *keys: str) -> str:
    runtime_file = files[file_name]
    for key in keys:
        value = runtime_file.fields.get(key, "").strip()
        if value:
            return value
    return UNKNOWN


def _project(files: dict[str, RuntimeFile]) -> str:
    return _first_known(
        _value(files, "PROJECT_STATE.md", "PROJECT_SLUG", "PROJECT_NAME"),
        _value(files, "WORKSPACE_IDENTITY.md", "PROJECT_SLUG", "PROJECT_NAME"),
    )


def _branch(files: dict[str, RuntimeFile]) -> str:
    return _first_known(
        _value(files, "PROJECT_STATE.md", "ACTUAL_BRANCH", "EXPECTED_BRANCH"),
        _value(files, "WORKSPACE_IDENTITY.md", "ACTUAL_BRANCH", "EXPECTED_BRANCH"),
        _value(files, "REPOSITORY_LOCK.md", "ACTUAL_BRANCH_AT_LOCK", "EXPECTED_BRANCH"),
    )


def _first_known(*values: str) -> str:
    for value in values:
        if value and value != UNKNOWN:
            return value
    return UNKNOWN


def _next_action(files: dict[str, RuntimeFile]) -> str:
    action_type = _value(files, "NEXT_ACTION.md", "ACTION_TYPE")
    task_id = _value(files, "NEXT_ACTION.md", "TASK_ID")
    target_role = _value(files, "NEXT_ACTION.md", "TARGET_ROLE")
    task_packet = _value(files, "NEXT_ACTION.md", "TASK_PACKET")

    if action_type == UNKNOWN:
        return UNKNOWN

    parts = [action_type]
    if target_role != UNKNOWN:
        parts.append(f"target={target_role}")
    if task_id != UNKNOWN and task_id != "NONE":
        parts.append(f"task={task_id}")
    elif task_packet != UNKNOWN and task_packet != "NONE":
        parts.append(f"task_packet={task_packet}")
    return " ".join(parts)


def _push_allowed_values(files: dict[str, RuntimeFile]) -> dict[str, str]:
    return {
        "PROJECT_STATE": _value(files, "PROJECT_STATE.md", "PUSH_ALLOWED"),
        "REPOSITORY_LOCK": _value(files, "REPOSITORY_LOCK.md", "PUSH_ALLOWED"),
        "WORKSPACE_IDENTITY": _value(files, "WORKSPACE_IDENTITY.md", "PUSH_ALLOWED"),
    }


def _push_allowed_line(push_values: dict[str, str]) -> str:
    return ", ".join(f"{name}={value}" for name, value in push_values.items())


def _findings(root: Path, files: dict[str, RuntimeFile], push_values: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []

    missing_runtime_files: list[RuntimeFile] = []
    for name in RUNTIME_FILES:
        runtime_file = files[name]
        if runtime_file.error:
            findings.append(
                Finding(
                    rule_id="STATUS_001",
                    severity="error",
                    title="Runtime file unreadable",
                    details=f"{runtime_file.relpath}: {runtime_file.error}",
                    files=[runtime_file.relpath],
                    recommendation="Repair the runtime path or permissions and rerun aso status.",
                )
            )
        elif not runtime_file.exists:
            missing_runtime_files.append(runtime_file)

    missing_names = [Path(runtime_file.relpath).name for runtime_file in missing_runtime_files]
    if missing_runtime_files:
        missing_relpaths = [runtime_file.relpath for runtime_file in missing_runtime_files]
        materializable = repair_hints.missing_runtime_views_with_valid_sidecars(root, missing_names)
        findings.append(
            Finding(
                rule_id="STATUS_002",
                severity="error" if materializable else "warning",
                title=(
                    repair_hints.MISSING_RUNTIME_VIEWS_TITLE
                    if materializable
                    else "Runtime file missing"
                ),
                details=(
                    f"{repair_hints.MISSING_RUNTIME_VIEWS_TITLE} Missing views: {', '.join(missing_relpaths)}."
                    if materializable
                    else f"Missing runtime files: {', '.join(missing_relpaths)}."
                ),
                files=missing_relpaths,
                recommendation=(
                    repair_hints.MISSING_RUNTIME_VIEWS_RECOMMENDATION
                    if materializable
                    else "Initialize or restore the missing runtime file if this workspace is active."
                ),
            )
        )

    known_push_values = {
        source: value
        for source, value in push_values.items()
        if value not in ("", UNKNOWN, "NONE")
    }
    if len(set(known_push_values.values())) > 1:
        findings.append(
            Finding(
                rule_id="STATUS_003",
                severity="error",
                title="Conflicting PUSH_ALLOWED values",
                details=_push_allowed_line(push_values),
                files=[
                    "project-runtime/PROJECT_STATE.md",
                    "project-runtime/REPOSITORY_LOCK.md",
                    "project-runtime/WORKSPACE_IDENTITY.md",
                ],
                recommendation="Reconcile PUSH_ALLOWED across project state, repository lock, and workspace identity.",
            )
        )

    checkpoint_status = _value(files, "PROJECT_STATE.md", "PROJECT_CHECKPOINT_STATUS")
    gate_status = _value(files, "CURRENT_GATE.md", "STATUS")
    if checkpoint_status == "passed" and gate_status not in {
        "passed",
        "skipped",
        "closed",
        "completed",
        "inactive",
        UNKNOWN,
    }:
        findings.append(
            Finding(
                rule_id="STATUS_004",
                severity="error",
                title="Checkpoint passed while current gate is active",
                details=(
                    f"PROJECT_CHECKPOINT_STATUS={checkpoint_status}; "
                    f"CURRENT_GATE.STATUS={gate_status}"
                ),
                files=[
                    "project-runtime/PROJECT_STATE.md",
                    "project-runtime/CURRENT_GATE.md",
                ],
                recommendation="Close the current gate or repair stale checkpoint state.",
            )
        )

    return findings


def _runtime_consistency(findings: list[Finding]) -> str:
    severities = {finding.severity for finding in findings}
    if "error" in severities:
        return "FAIL"
    if "warning" in severities:
        return "WARN"
    return "PASS"


def _report(root: Path) -> dict[str, object]:
    files = {name: _read_runtime_file(root, name) for name in RUNTIME_FILES}
    push_values = _push_allowed_values(files)
    findings = _findings(root, files, push_values)
    consistency = _runtime_consistency(findings)

    status_by_consistency = {
        "PASS": "passed",
        "WARN": "warning",
        "FAIL": "failed",
    }

    return {
        "tool": "aso",
        "command": "status",
        "mode": "workspace",
        "status": status_by_consistency[consistency],
        "root": str(root),
        "summary": {
            "project": _project(files),
            "branch": _branch(files),
            "project_status": _value(files, "PROJECT_STATE.md", "PROJECT_STATUS"),
            "current_gate": _value(files, "CURRENT_GATE.md", "STATUS"),
            "checkpoint_status": _value(files, "PROJECT_STATE.md", "PROJECT_CHECKPOINT_STATUS"),
            "next_action": _next_action(files),
            "push_allowed_values": push_values,
            "runtime_consistency": consistency,
            "finding_count": len(findings),
        },
        "files": {
            runtime_file.relpath: {
                "exists": runtime_file.exists,
                "field_count": len(runtime_file.fields),
                "error": runtime_file.error,
            }
            for runtime_file in files.values()
        },
        "findings": [finding.to_json(mode="workspace") for finding in findings],
    }


def _package_report(root: Path) -> dict[str, object]:
    guard_finding = mode_guard.package_mode_guard(root)
    if guard_finding is not None:
        return {
            "tool": "aso",
            "command": "status",
            "mode": "package",
            "status": "failed",
            "root": str(root),
            "summary": {
                "package_consistency": "FAIL",
                "finding_count": 1,
                "generated_roots": {},
                "readmes": {},
                "git_tracked_generated_files": [],
            },
            "files": {},
            "findings": [guard_finding.to_json(mode="package")],
        }

    inspection = package_checks.inspect_package(root)
    consistency = package_checks.consistency(inspection.findings)
    status_by_consistency = {
        "PASS": "passed",
        "WARN": "warning",
        "FAIL": "failed",
    }

    return {
        "tool": "aso",
        "command": "status",
        "mode": "package",
        "status": status_by_consistency[consistency],
        "root": str(root),
        "summary": {
            "package_consistency": consistency,
            "finding_count": len(inspection.findings),
            "generated_roots": inspection.generated_roots,
            "readmes": inspection.readmes,
            "git_tracked_generated_files": inspection.git_tracked_generated_files,
        },
        "files": inspection.files,
        "findings": [finding.to_json(mode="package") for finding in inspection.findings],
    }


def _print_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    if not isinstance(summary, dict):
        raise TypeError("internal status report summary must be a dictionary")

    push_values = summary["push_allowed_values"]
    if not isinstance(push_values, dict):
        raise TypeError("internal push_allowed_values must be a dictionary")

    print(f"Project: {summary['project']}")
    print(f"Branch: {summary['branch']}")
    print(f"Project status: {summary['project_status']}")
    print(f"Current gate: {summary['current_gate']}")
    print(f"Checkpoint status: {summary['checkpoint_status']}")
    print(f"Next action: {summary['next_action']}")
    print(f"Push allowed values: {_push_allowed_line(push_values)}")
    print(f"Runtime consistency: {summary['runtime_consistency']}")
    print(f"Findings: {summary['finding_count']}")
    for finding in report["findings"]:
        if not isinstance(finding, dict):
            continue
        print(f"- {finding['severity']} {finding['rule_id']}: {finding['title']}")
        recommendation = str(finding.get("recommendation", "")).strip()
        if recommendation:
            print(f"  Recommendation: {recommendation}")


def _print_package_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    if not isinstance(summary, dict):
        raise TypeError("internal package status summary must be a dictionary")

    generated_roots = summary["generated_roots"]
    if not isinstance(generated_roots, dict):
        raise TypeError("internal generated_roots must be a dictionary")

    root_states = ", ".join(
        f"{name}={generated_roots.get(name, 'UNKNOWN')}"
        for name in package_checks.GENERATED_ROOTS
    )

    print(f"ASO package status: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    print(f"Package consistency: {summary['package_consistency']}")
    print(f"Generated roots: {root_states}")
    print(f"Findings: {summary['finding_count']}")
    for finding in report["findings"]:
        if not isinstance(finding, dict):
            continue
        print(f"- {finding['severity']} {finding['rule_id']}: {finding['title']}")
        recommendation = str(finding.get("recommendation", "")).strip()
        if recommendation:
            print(f"  Recommendation: {recommendation}")


def _write_json(path_text: str, report: dict[str, object]) -> bool:
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso status: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso status: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def run(args: argparse.Namespace) -> int:
    """Run the status command."""
    if args.mode == "package":
        report = _package_report(args.root)
        _print_package_text(report)
    else:
        report = _report(args.root)
        _print_text(report)
    if args.json_out and not _write_json(args.json_out, report):
        return EXIT_IO_ERROR
    if args.mode == "package" and report.get("status") == "failed":
        return EXIT_FINDINGS
    return EXIT_OK
