"""Dry-run RESULT routing proposal command."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3

RESULT_STATUSES = {"pass", "fail", "blocked", "gap"}
PROFILE_ROLES = {
    "requirements_analyst",
    "solution_architect",
    "designer",
    "developer",
    "tester",
    "technical_writer",
    "devops_setup_engineer",
    "release_manager",
}
VALID_ROLES = PROFILE_ROLES | {"auditor"}
REQUIRED_RESULT_FIELDS = (
    "STATUS",
    "TASK_ID",
    "AGENT_INSTANCE_ID",
    "ROLE",
    "TASK",
    "SUMMARY",
    "READ_DOCS",
    "READ_INPUTS",
    "CHANGED_FILES",
    "CREATED_FILES",
    "DELETED_FILES",
    "COMMANDS_RUN",
    "TESTS_RUN",
    "EVIDENCE",
    "SCOPE_VERIFICATION",
    "FORBIDDEN_CHANGES_CHECK",
    "RISKS",
    "LIMITATIONS",
    "BLOCKERS",
    "GAPS",
    "NEXT_RECOMMENDED_ACTION",
    "REUSE_ALLOWED",
    "AGENT_TERMINATION_REQUIRED",
)
BYPASS_ACTION_MARKERS = {
    "CHECKPOINT",
    "CHECKPOINT_PREFLIGHT",
    "COMMIT",
    "PUSH",
    "FINALIZE",
    "FINALIZATION",
    "COMPLETED",
    "COMPLETE_PROJECT",
    "TESTER",
    "TECHNICAL_WRITER",
}


@dataclass(frozen=True)
class Rule:
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


def _read_result(path: Path) -> tuple[str, list[Rule]]:
    try:
        return path.read_text(encoding="utf-8"), []
    except OSError as exc:
        return "", [
            Rule(
                "RESULT_IO_001",
                "error",
                "Result file is unreadable.",
                f"{path}: {exc}",
            )
        ]


def _parse_result_fields(text: str) -> dict[str, Any]:
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
        return [value.strip()]
    return []


def _bool_field(fields: dict[str, Any], key: str) -> bool | None:
    value = _as_string(fields, key).lower()
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def _file_suggests_audit(path: Path, text: str) -> bool:
    first_heading = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            first_heading = stripped.upper()
            break
    return path.name.startswith("AUDIT_RESULT_") or "AUDIT_RESULT" in first_heading


def _result_type(path: Path, text: str, role: str) -> str:
    if role == "auditor" or _file_suggests_audit(path, text):
        return "audit_result"
    return "profile_result"


def _source_result_refs(fields: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for item in _as_list(fields, "EVIDENCE") + _as_list(fields, "SCOPE_VERIFICATION"):
        match = re.search(r"SOURCE_RESULT_REF:\s*(\S+)", item)
        if match:
            refs.append(match.group(1))
    return refs


def _claimed_next_actions(fields: dict[str, Any]) -> list[str]:
    claims: list[str] = []
    for item in _as_list(fields, "NEXT_RECOMMENDED_ACTION"):
        normalized = item.strip()
        if normalized and normalized.upper() != "NONE":
            claims.append(normalized)
    return claims


def _contains_bypass_claim(actions: list[str]) -> bool:
    joined = " ".join(actions).upper()
    return any(marker in joined for marker in BYPASS_ACTION_MARKERS)


def _blocking_rule(rule_id: str, message: str, evidence: str) -> Rule:
    return Rule(rule_id, "error", message, evidence)


def _validate_common(path: Path, text: str, fields: dict[str, Any], strict: bool) -> list[Rule]:
    errors: list[Rule] = []
    if not text.strip():
        errors.append(Rule("RESULT_FORMAT_001", "error", "Result file is empty.", str(path)))
        return errors
    lines = text.splitlines()
    first_line = lines[0].upper() if lines else ""
    if "RESULT" not in first_line:
        errors.append(
            Rule(
                "RESULT_FORMAT_002",
                "error",
                "Result file must start with a RESULT or AUDIT_RESULT heading.",
                str(path),
            )
        )
    if not strict:
        return errors

    for field in REQUIRED_RESULT_FIELDS:
        if field not in fields:
            errors.append(
                Rule(
                    "RESULT_FORMAT_003",
                    "error",
                    "Strict RESULT parsing requires every template field.",
                    field,
                )
            )

    status = _as_string(fields, "STATUS")
    if status not in RESULT_STATUSES:
        errors.append(
            Rule(
                "RESULT_FORMAT_004",
                "error",
                "STATUS must be one of pass, fail, blocked, or gap.",
                f"STATUS={status or 'MISSING'}",
            )
        )

    role = _as_string(fields, "ROLE")
    if role not in VALID_ROLES:
        errors.append(
            Rule(
                "RESULT_FORMAT_005",
                "error",
                "ROLE must be a canonical profile role or auditor.",
                f"ROLE={role or 'MISSING'}",
            )
        )

    reuse_allowed = _bool_field(fields, "REUSE_ALLOWED")
    if reuse_allowed is not False:
        errors.append(
            Rule(
                "RESULT_FORMAT_006",
                "error",
                "REUSE_ALLOWED must be false.",
                f"REUSE_ALLOWED={_as_string(fields, 'REUSE_ALLOWED') or 'MISSING'}",
            )
        )

    termination_required = _bool_field(fields, "AGENT_TERMINATION_REQUIRED")
    if termination_required is not True:
        errors.append(
            Rule(
                "RESULT_FORMAT_007",
                "error",
                "AGENT_TERMINATION_REQUIRED must be true.",
                f"AGENT_TERMINATION_REQUIRED={_as_string(fields, 'AGENT_TERMINATION_REQUIRED') or 'MISSING'}",
            )
        )

    if _file_suggests_audit(path, text) and role and role != "auditor":
        errors.append(
            Rule(
                "RESULT_FORMAT_008",
                "error",
                "AUDIT_RESULT files must use ROLE: auditor.",
                f"ROLE={role}",
            )
        )

    return errors


def _route(fields: dict[str, Any], result_type: str, strict: bool) -> tuple[str, bool, list[Rule], list[Rule]]:
    status = _as_string(fields, "STATUS")
    role = _as_string(fields, "ROLE")
    task_id = _as_string(fields, "TASK_ID")
    claims = _claimed_next_actions(fields)
    blocking_rules: list[Rule] = []
    validation_errors: list[Rule] = []

    if result_type == "audit_result":
        if status == "pass":
            refs = _source_result_refs(fields)
            if strict and not refs:
                validation_errors.append(
                    Rule(
                        "RESULT_AUDIT_001",
                        "error",
                        "Auditor pass must identify the checked profile RESULT.",
                        "SOURCE_RESULT_REF missing",
                    )
                )
                return "NONE", False, blocking_rules, validation_errors
            return "CHECKPOINT_PREFLIGHT", True, blocking_rules, validation_errors
        if status == "fail":
            blocking_rules.append(
                _blocking_rule(
                    "GOV-AUDIT-FAIL-NO-CHECKPOINT",
                    "Audit fail forbids checkpoint, commit, push, and normal next-task routing.",
                    f"TASK_ID={task_id}",
                )
            )
            return "ROUTE_CORRECTION", False, blocking_rules, validation_errors
        if status == "blocked":
            blocking_rules.append(
                _blocking_rule(
                    "GOV-AUDIT-BLOCKED-NO-CHECKPOINT",
                    "Audit blocked forbids checkpoint until the blocker is resolved.",
                    f"TASK_ID={task_id}",
                )
            )
            return "ORCHESTRATOR_BLOCKED_ROUTING", False, blocking_rules, validation_errors
        if status == "gap":
            blocking_rules.append(
                _blocking_rule(
                    "GOV-AUDIT-GAP-NO-CHECKPOINT",
                    "Audit gap forbids checkpoint until owner/GAP routing resolves.",
                    f"TASK_ID={task_id}",
                )
            )
            return "REGISTER_GAP", False, blocking_rules, validation_errors
        return "NONE", False, blocking_rules, validation_errors

    audit_required = role in PROFILE_ROLES
    if status == "pass" and audit_required:
        if strict and _contains_bypass_claim(claims):
            validation_errors.append(
                Rule(
                    "RESULT_BYPASS_001",
                    "error",
                    "Profile RESULT overclaims a post-audit or downstream action.",
                    "; ".join(claims),
                )
            )
        blocking_rules.append(
            _blocking_rule(
                "GOV-CHECKPOINT-AUDIT-GATE",
                "Profile RESULT pass requires independent auditor pass before checkpoint eligibility.",
                f"TASK_ID={task_id}",
            )
        )
        return "CREATE_AUDITOR", False, blocking_rules, validation_errors
    if status == "fail":
        blocking_rules.append(
            _blocking_rule(
                "GOV-PROFILE-FAIL-NO-CHECKPOINT",
                "Profile RESULT fail forbids checkpoint and routes to correction.",
                f"TASK_ID={task_id}",
            )
        )
        return "ROUTE_CORRECTION", False, blocking_rules, validation_errors
    if status == "blocked":
        blocking_rules.append(
            _blocking_rule(
                "GOV-PROFILE-BLOCKED-NO-CHECKPOINT",
                "Profile RESULT blocked forbids checkpoint until orchestrator routing resolves.",
                f"TASK_ID={task_id}",
            )
        )
        return "ORCHESTRATOR_BLOCKED_ROUTING", False, blocking_rules, validation_errors
    if status == "gap":
        blocking_rules.append(
            _blocking_rule(
                "GOV-PROFILE-GAP-NO-CHECKPOINT",
                "Profile RESULT gap forbids checkpoint until GAP routing resolves.",
                f"TASK_ID={task_id}",
            )
        )
        return "REGISTER_GAP", False, blocking_rules, validation_errors
    return "NONE", False, blocking_rules, validation_errors


def build_report(result_path: Path, strict: bool) -> tuple[dict[str, Any], int]:
    text, io_errors = _read_result(result_path)
    fields = _parse_result_fields(text) if text else {}
    role = _as_string(fields, "ROLE")
    result_type = _result_type(result_path, text, role) if text else "unknown"
    validation_errors = [*io_errors, *_validate_common(result_path, text, fields, strict)]

    recommended_next_action = "NONE"
    checkpoint_candidate = False
    blocking_rules: list[Rule] = []
    if not io_errors and not validation_errors:
        recommended_next_action, checkpoint_candidate, blocking_rules, route_errors = _route(
            fields,
            result_type,
            strict,
        )
        validation_errors.extend(route_errors)

    report_status = "rejected" if validation_errors else "ready"
    exit_code = EXIT_IO_ERROR if io_errors else EXIT_FINDINGS if validation_errors else EXIT_OK
    audit_required = result_type == "profile_result" and role in PROFILE_ROLES
    return {
        "tool": "aso",
        "command": "record-result",
        "report_status": report_status,
        "result_path": str(result_path),
        "strict": strict,
        "dry_run": True,
        "read_only": True,
        "mutations_performed": False,
        "result_type": result_type,
        "task_id": _as_string(fields, "TASK_ID"),
        "role": role,
        "status": _as_string(fields, "STATUS"),
        "audit_required": audit_required,
        "checkpoint_candidate": checkpoint_candidate,
        "recommended_next_action": recommended_next_action,
        "blocking_rules": [rule.to_json() for rule in blocking_rules],
        "validation_errors": [rule.to_json() for rule in validation_errors],
        "evidence": {
            "agent_instance_id": _as_string(fields, "AGENT_INSTANCE_ID"),
            "task": _as_string(fields, "TASK"),
            "source_result_refs": _source_result_refs(fields),
            "claimed_next_actions": _claimed_next_actions(fields),
            "parsed_fields": sorted(fields),
        },
    }, exit_code


def _print_text(report: dict[str, Any]) -> None:
    print(f"ASO record-result: {str(report['report_status']).upper()} (dry-run/read-only)")
    print(f"Result type: {report['result_type']}")
    print(f"Task: {report['task_id'] or 'NONE'}")
    print(f"Role: {report['role'] or 'NONE'}")
    print(f"Status: {report['status'] or 'NONE'}")
    print(f"Recommended next action: {report['recommended_next_action']}")
    print(f"Checkpoint candidate: {str(report['checkpoint_candidate']).lower()}")
    print(f"Blocking rules: {len(report['blocking_rules'])}")
    print(f"Validation errors: {len(report['validation_errors'])}")


def run(args: argparse.Namespace) -> int:
    """Run dry-run RESULT routing proposal."""

    result_path = Path(args.result).expanduser()
    report, exit_code = build_report(result_path, bool(args.strict))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_text(report)
    return exit_code
