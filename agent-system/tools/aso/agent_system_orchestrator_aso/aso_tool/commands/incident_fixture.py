"""Dry-run incident regression fixture proposal command."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import output_policy


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3

REQUIRED_STRICT_FIELDS = ("INCIDENT_ID", "INCIDENT_CLASS", "TRIGGERING_RULE_IDS", "EXPECTED_FAILURE_STATUS")
ALLOWED_EXPECTED_FAILURE_STATUSES = {"failed", "blocked", "rejected", "gap"}
OWNER_APPROVAL_MARKERS = (
    "AUTO_APPROVE",
    "AUTO_APPROVAL",
    "APPROVE_OWNER_DECISION",
    "OWNER_APPROVAL: true",
    "OWNER_DECISION_APPROVED: true",
)
VALIDATOR_WEAKENING_MARKERS = (
    "WEAKEN_VALIDATOR",
    "LOWER_SEVERITY",
    "DISABLE_VALIDATOR",
    "RELAX_SCHEMA",
    "CHANGE_SEVERITY",
)


@dataclass(frozen=True)
class IncidentFinding:
    rule_id: str
    severity: str
    message: str
    evidence: str

    def to_json(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
        }


def _read_incident(path: Path) -> tuple[str, list[IncidentFinding]]:
    try:
        return path.read_text(encoding="utf-8"), []
    except OSError as exc:
        return "", [
            IncidentFinding(
                "INCIDENT_IO_001",
                "error",
                "Incident file is unreadable.",
                f"{path}: {exc}",
            )
        ]


def _parse_fields(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] = []

    def flush_list() -> None:
        nonlocal current_key, current_list
        if current_key is not None:
            fields[current_key] = current_list if current_list else "NONE"
        current_key = None
        current_list = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        match = re.match(r"^([A-Z0-9_]+):\s*(.*?)\s*$", line)
        if match:
            flush_list()
            key = match.group(1)
            value = match.group(2).strip()
            if value:
                fields[key] = value
            else:
                current_key = key
                current_list = []
            continue

        if current_key is not None:
            stripped = line.strip()
            if stripped.startswith("- "):
                current_list.append(stripped[2:].strip())
            elif stripped:
                current_list.append(stripped)

    flush_list()
    return fields


def _as_string(fields: dict[str, Any], key: str) -> str:
    value = fields.get(key)
    return value.strip() if isinstance(value, str) else ""


def _as_list(fields: dict[str, Any], key: str) -> list[str]:
    value = fields.get(key)
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str) and value.strip() and value.strip().upper() != "NONE":
        return [item.strip() for item in re.split(r"[, ]+", value) if item.strip()]
    return []


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "incident"


def _contains_marker(text: str, markers: tuple[str, ...]) -> str:
    upper_text = text.upper()
    for marker in markers:
        if marker.upper() in upper_text:
            return marker
    return ""


def _validate_incident(text: str, fields: dict[str, Any], strict: bool) -> list[IncidentFinding]:
    findings: list[IncidentFinding] = []
    if not text.strip():
        return [
            IncidentFinding(
                "INCIDENT_FORMAT_001",
                "error",
                "Incident file is empty.",
                "empty incident input",
            )
        ]

    if strict:
        for field in REQUIRED_STRICT_FIELDS:
            value = fields.get(field)
            if value is None or value == "NONE" or value == []:
                findings.append(
                    IncidentFinding(
                        "INCIDENT_FORMAT_002",
                        "error",
                        "Strict incident fixture proposals require explicit incident metadata.",
                        field,
                    )
                )

    if not _as_list(fields, "TRIGGERING_RULE_IDS"):
        findings.append(
            IncidentFinding(
                "INCIDENT_RULE_001",
                "error",
                "Incident must identify at least one triggering rule id.",
                "TRIGGERING_RULE_IDS missing",
            )
        )

    expected_failure_status = _as_string(fields, "EXPECTED_FAILURE_STATUS")
    if expected_failure_status and expected_failure_status not in ALLOWED_EXPECTED_FAILURE_STATUSES:
        findings.append(
            IncidentFinding(
                "INCIDENT_STATUS_001",
                "error",
                "Expected failure status is not a validator failure outcome.",
                f"EXPECTED_FAILURE_STATUS={expected_failure_status}",
            )
        )

    owner_marker = _contains_marker(text, OWNER_APPROVAL_MARKERS)
    if owner_marker:
        findings.append(
            IncidentFinding(
                "INCIDENT_SAFETY_001",
                "error",
                "Incident fixture proposals cannot approve owner decisions.",
                owner_marker,
            )
        )

    weakening_marker = _contains_marker(text, VALIDATOR_WEAKENING_MARKERS)
    if weakening_marker:
        findings.append(
            IncidentFinding(
                "INCIDENT_SAFETY_002",
                "error",
                "Incident fixture proposals cannot weaken validators, severities, or schemas.",
                weakening_marker,
            )
        )

    return findings


def _proposed_fixture_paths(incident_id: str) -> list[dict[str, str]]:
    slug = _slug(incident_id)
    return [
        {
            "kind": "incident_fixture",
            "path": f"agent-system/tests/fixtures/incidents/{slug}.md",
            "purpose": "Structured incident input used by regression tests.",
        },
        {
            "kind": "expected_proposal",
            "path": f"agent-system/tests/fixtures/incidents/{slug}.proposal.json",
            "purpose": "Golden proposal output for deterministic comparison.",
        },
        {
            "kind": "unit_test",
            "path": f"agent-system/tools/aso/tests/test_{slug}_incident_fixture.py",
            "purpose": "Command-level regression coverage for the triggering rule ids.",
        },
    ]


def _coverage_notes(rule_ids: list[str]) -> list[str]:
    return [
        (
            f"Add a strict regression assertion for {rule_id}; expected outcome remains a "
            "validator failure or blocker, with no rule severity, schema, or owner-approval change."
        )
        for rule_id in rule_ids
    ]


def build_report(incident_path: Path, strict: bool) -> tuple[dict[str, Any], int]:
    text, io_errors = _read_incident(incident_path)
    fields = _parse_fields(text) if text else {}
    validation_errors = [*io_errors, *([] if io_errors else _validate_incident(text, fields, strict))]

    incident_id = _as_string(fields, "INCIDENT_ID")
    rule_ids = _as_list(fields, "TRIGGERING_RULE_IDS")
    report_status = "rejected" if validation_errors else "ready"
    exit_code = EXIT_IO_ERROR if io_errors else EXIT_FINDINGS if validation_errors else EXIT_OK

    return {
        "tool": "aso",
        "command": "incident fixture",
        "report_status": report_status,
        "proposal_mode": "dry_run",
        "dry_run": True,
        "read_only": True,
        "mutations_performed": False,
        "incident_path": str(incident_path),
        "strict": strict,
        "incident_id": incident_id,
        "incident_class": _as_string(fields, "INCIDENT_CLASS"),
        "triggering_rule_ids": rule_ids,
        "proposed_fixture_paths": _proposed_fixture_paths(incident_id),
        "expected_failure_status": _as_string(fields, "EXPECTED_FAILURE_STATUS"),
        "validator_coverage_notes": _coverage_notes(rule_ids),
        "safety_controls": {
            "validator_weakened": False,
            "owner_decision_approved": False,
            "dispatch_performed": False,
            "checkpoint_performed": False,
            "commit_performed": False,
            "push_performed": False,
            "runtime_mutated": False,
        },
        "evidence": {
            "parsed_fields": sorted(fields),
            "affected_paths": _as_list(fields, "AFFECTED_PATHS"),
            "summary": _as_string(fields, "SUMMARY"),
        },
        "validation_errors": [finding.to_json() for finding in validation_errors],
    }, exit_code


def _output_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve(strict=False)


def _validate_output_path(root: Path, path: Path) -> IncidentFinding | None:
    error = output_policy.validate_generated_output_path(
        root,
        path,
        allowed_workspace_subdirs=("project-runtime/proposals", "project-runtime/reports"),
    )
    if error is None:
        return None
    return IncidentFinding(
        error.rule_id,
        "error",
        error.message,
        error.evidence,
    )


def _validated_output_path(root: Path, value: str) -> tuple[Path, IncidentFinding | None]:
    path = _output_path(root, value)
    return path, _validate_output_path(root, path)


def _output_label(error: IncidentFinding, label: str) -> IncidentFinding:
    return IncidentFinding(error.rule_id, error.severity, error.message, f"{label}: {error.evidence}")


def _collect_output_targets(
    root: Path,
    json_out: object,
    out: object,
) -> tuple[Path | None, Path | None, list[IncidentFinding]]:
    errors: list[IncidentFinding] = []
    json_path: Path | None = None
    out_path: Path | None = None
    if json_out:
        json_path, error = _validated_output_path(root, str(json_out))
        if error:
            errors.append(_output_label(error, "--json-out"))
    if out:
        out_path, error = _validated_output_path(root, str(out))
        if error:
            errors.append(_output_label(error, "--out"))
    return json_path, out_path, errors


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ASO Incident Fixture Proposal",
        "",
        f"REPORT_STATUS: {report['report_status']}",
        f"INCIDENT_ID: {report['incident_id'] or 'MISSING'}",
        f"EXPECTED_FAILURE_STATUS: {report['expected_failure_status'] or 'MISSING'}",
        "DRY_RUN: true",
        "READ_ONLY: true",
        "MUTATIONS_PERFORMED: false",
        "",
        "## Triggering Rule IDs",
    ]
    rule_ids = report["triggering_rule_ids"]
    if isinstance(rule_ids, list) and rule_ids:
        lines.extend(f"- {rule_id}" for rule_id in rule_ids)
    else:
        lines.append("- NONE")
    lines.extend(["", "## Proposed Fixture Paths"])
    for item in report["proposed_fixture_paths"]:
        if isinstance(item, dict):
            lines.append(f"- {item['kind']}: {item['path']}")
    lines.extend(["", "## Validator Coverage Notes"])
    notes = report["validator_coverage_notes"]
    if isinstance(notes, list) and notes:
        lines.extend(f"- {note}" for note in notes)
    else:
        lines.append("- NONE")
    lines.extend(["", "## Safety"])
    safety = report["safety_controls"]
    if isinstance(safety, dict):
        for key in sorted(safety):
            lines.append(f"- {key}: {str(safety[key]).lower()}")
    return "\n".join(lines) + "\n"


def _write_text(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_markdown(report), encoding="utf-8")


def run_fixture(args: argparse.Namespace) -> int:
    """Run dry-run incident fixture proposal generation."""

    root = Path(getattr(args, "root", Path("."))).expanduser()
    incident_path = Path(args.incident).expanduser()
    report, exit_code = build_report(incident_path, bool(args.strict))

    json_out = getattr(args, "json_out", None)
    out = getattr(args, "out", None)
    json_path, out_path, output_errors = _collect_output_targets(root, json_out, out)

    if output_errors:
        report["report_status"] = "rejected"
        report["validation_errors"].extend(error.to_json() for error in output_errors)
        exit_code = EXIT_FINDINGS

    if exit_code == EXIT_OK:
        if json_path is not None:
            _write_json(json_path, report)
        if out_path is not None:
            _write_text(out_path, report)

    if not json_out and not out:
        stream = json.dumps(report, indent=2, sort_keys=True)
        print(stream)

    return exit_code
