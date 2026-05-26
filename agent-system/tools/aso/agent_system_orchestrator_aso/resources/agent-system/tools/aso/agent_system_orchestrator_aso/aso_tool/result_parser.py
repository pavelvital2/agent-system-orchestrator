"""Canonical parser for ASO profile RESULT and AUDIT_RESULT artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import role_registry


RESULT_STATUSES = {"pass", "fail", "blocked", "gap"}
PROFILE_ROLES = set(role_registry.dispatchable_roles()) - {"auditor"}
LEGACY_LIFECYCLE_SYSTEM_ROLES = set(role_registry.legacy_lifecycle_system_roles())
LEGACY_PROFILE_RESULT_ROLES = {
    "requirements_analyst",
    "solution_architect",
    "designer",
    "developer",
    "tester",
    "technical_writer",
    "devops_setup_engineer",
    "release_manager",
}
VALID_ROLES = PROFILE_ROLES | LEGACY_LIFECYCLE_SYSTEM_ROLES | LEGACY_PROFILE_RESULT_ROLES | {"auditor"}
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

SCALAR_FIELDS = {
    "STATUS",
    "TASK_ID",
    "AGENT_INSTANCE_ID",
    "ROLE",
    "TASK",
    "REUSE_ALLOWED",
    "AGENT_TERMINATION_REQUIRED",
}
SOURCE_RESULT_LABELS = {
    "SOURCE_RESULT_REF",
    "AUDITED_RESULT_REF",
    "RESULT_REF",
    "ACCEPTED_RESULT_REF",
}
SOURCE_TASK_LABELS = {
    "SOURCE_TASK_REF",
    "SOURCE_TASK",
    "AUDITED_TASK_REF",
    "AUDITED_TASK",
    "TASK_REF",
}
AUDIT_FINDING_FIELDS = ("FINDINGS", "AUDIT_FINDINGS", "EVIDENCE", "SCOPE_VERIFICATION")
FAILED_CHECK_FIELDS = ("FAILED_CHECKS", "FAILED_CHECK", "FAILURES")

REASON_MISSING_ROLE = "missing_role"
REASON_MISSING_TASK_ID = "missing_task_id"
REASON_MISSING_AGENT_INSTANCE_ID = "missing_agent_instance_id"
REASON_MISSING_STATUS = "missing_status"
REASON_MALFORMED_SECTION = "malformed_section"
REASON_MISSING_REQUIRED_FIELD = "missing_required_field"

IDENTITY_REASON_BY_FIELD = {
    "ROLE": REASON_MISSING_ROLE,
    "TASK_ID": REASON_MISSING_TASK_ID,
    "AGENT_INSTANCE_ID": REASON_MISSING_AGENT_INSTANCE_ID,
    "STATUS": REASON_MISSING_STATUS,
}
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}
_FIELD_RE = re.compile(r"^([A-Z0-9_]+):\s*(.*?)\s*$")
_LABEL_RE = re.compile(r"\b([A-Z0-9_]+):\s*(\S+)")
_RESULT_TASK_RE = re.compile(
    r"(?:^|/)RESULT_([A-Za-z0-9_:-]+?)(?:_ATTEMPT_[0-9]+|_(?:PASS|FAIL|BLOCKED|GAP))?\.md$"
)


@dataclass(frozen=True)
class ResultParseIssue:
    reason_code: str
    rule_id: str
    severity: str
    message: str
    evidence: str
    field: str = ""

    def to_json(self) -> dict[str, str]:
        payload = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
            "reason_code": self.reason_code,
        }
        if self.field:
            payload["field"] = self.field
        return payload


@dataclass(frozen=True)
class AuditResultDetails:
    status: str
    findings: tuple[str, ...]
    failed_checks: tuple[str, ...]
    source_result_refs: tuple[str, ...]
    source_task_refs: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "status": self.status,
            "findings": list(self.findings),
            "failed_checks": list(self.failed_checks),
            "source_result_refs": list(self.source_result_refs),
            "source_task_refs": list(self.source_task_refs),
        }


@dataclass(frozen=True)
class ParsedResult:
    path: str
    marker: str
    result_type: str
    fields: Mapping[str, Any]
    issues: tuple[ResultParseIssue, ...]
    audit: AuditResultDetails

    @property
    def status(self) -> str:
        return as_string(self.fields, "STATUS").lower()

    @property
    def task_id(self) -> str:
        return as_string(self.fields, "TASK_ID")

    @property
    def agent_instance_id(self) -> str:
        return as_string(self.fields, "AGENT_INSTANCE_ID")

    @property
    def role(self) -> str:
        return as_string(self.fields, "ROLE")

    def as_string(self, key: str) -> str:
        return as_string(self.fields, key)

    def as_list(self, key: str) -> list[str]:
        return as_list(self.fields, key)

    def bool_field(self, key: str) -> bool | None:
        return bool_field(self.fields, key)

    @property
    def has_error(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)


def as_string(fields: Mapping[str, Any], key: str) -> str:
    value = fields.get(key)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return ""


def as_list(fields: Mapping[str, Any], key: str) -> list[str]:
    value = fields.get(key)
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str) and value.strip() and value.strip() not in NONE_VALUES:
        return [value.strip()]
    return []


def bool_field(fields: Mapping[str, Any], key: str) -> bool | None:
    value = as_string(fields, key).lower()
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def file_suggests_audit(path: Path, text: str) -> bool:
    first_heading = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            first_heading = stripped.upper()
            break
    return path.name.startswith("AUDIT_RESULT_") or "AUDIT_RESULT" in first_heading


def is_none(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in NONE_VALUES)


def parse_result_file(path: Path, *, strict: bool = False) -> ParsedResult:
    return parse_result(path.read_text(encoding="utf-8"), path=path, strict=strict)


def parse_result(text: str, *, path: Path | str | None = None, strict: bool = False) -> ParsedResult:
    path_text = str(path) if path is not None else ""
    fields, marker, structural_issues = _parse_fields(text, strict=strict, path_text=path_text)
    role = as_string(fields, "ROLE")
    result_type = _result_type(marker, path, text, role)
    issues = list(structural_issues)
    if strict:
        issues.extend(_strict_identity_issues(fields))
    audit = _audit_details(fields, result_type)
    return ParsedResult(
        path=path_text,
        marker=marker,
        result_type=result_type,
        fields=fields,
        issues=tuple(issues),
        audit=audit,
    )


def audit_details_from_fields(fields: Mapping[str, Any]) -> AuditResultDetails:
    return _audit_details(fields, "audit_result")


def inspect_audit_references(
    root: Path,
    refs: Iterable[str],
    *,
    task_id: str = "",
    strict: bool = True,
) -> dict[str, object]:
    parsed_refs: list[dict[str, object]] = []
    invalid_refs: list[dict[str, object]] = []
    passed_refs: list[str] = []
    unparsed_refs: list[str] = []

    for ref in _dedupe(refs):
        path = _workspace_ref_path(root, ref)
        if path is None or not path.is_file():
            unparsed_refs.append(ref)
            continue
        try:
            parsed = parse_result_file(path, strict=strict)
        except (OSError, UnicodeError) as exc:
            invalid_refs.append(
                {
                    "ref": ref,
                    "reason": "audit_result_unreadable",
                    "evidence": f"{type(exc).__name__}: {exc}",
                }
            )
            continue

        issue_payloads = [issue.to_json() for issue in parsed.issues if issue.severity == "error"]
        task_matches = not task_id or parsed.task_id == task_id or task_id in parsed.audit.source_task_refs
        payload = {
            "ref": ref,
            "result_type": parsed.result_type,
            "status": parsed.status,
            "task_id": parsed.task_id,
            "source_task_refs": list(parsed.audit.source_task_refs),
            "source_result_refs": list(parsed.audit.source_result_refs),
            "failed_checks": list(parsed.audit.failed_checks),
            "findings": list(parsed.audit.findings),
            "issues": issue_payloads,
            "task_matches": task_matches,
        }
        parsed_refs.append(payload)
        if parsed.result_type != "audit_result":
            invalid_refs.append({**payload, "reason": "audit_ref_not_audit_result"})
        elif issue_payloads:
            invalid_refs.append({**payload, "reason": "audit_result_malformed"})
        elif parsed.status != "pass":
            invalid_refs.append({**payload, "reason": "audit_result_status_not_pass"})
        elif not task_matches:
            invalid_refs.append({**payload, "reason": "audit_result_task_mismatch"})
        else:
            passed_refs.append(ref)

    return {
        "parsed_refs": parsed_refs,
        "invalid_refs": invalid_refs,
        "passed_refs": passed_refs,
        "unparsed_refs": unparsed_refs,
    }


def _workspace_ref_path(root: Path, ref: str) -> Path | None:
    ref_path = Path(ref)
    if ref_path.is_absolute():
        try:
            ref_path.resolve(strict=False).relative_to(root.resolve(strict=False))
        except ValueError:
            return None
        return ref_path
    candidate = root / ref_path
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return None
    return candidate


def _parse_fields(text: str, *, strict: bool, path_text: str) -> tuple[dict[str, Any], str, list[ResultParseIssue]]:
    fields: dict[str, Any] = {}
    issues: list[ResultParseIssue] = []
    current_key: str | None = None
    current_lines: list[str] = []
    marker = ""
    saw_field = False

    def flush() -> None:
        nonlocal current_key, current_lines
        if current_key is None:
            current_lines = []
            return
        fields[current_key] = _field_value(current_key, current_lines)
        current_key = None
        current_lines = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if not marker and stripped in {"RESULT:", "AUDIT_RESULT:"}:
            marker = stripped
            continue
        if not marker and stripped in {"# RESULT", "# AUDIT_RESULT"}:
            marker = stripped
            if strict:
                issues.append(
                    ResultParseIssue(
                        REASON_MALFORMED_SECTION,
                        "RESULT_PARSE_MALFORMED_SECTION",
                        "error",
                        "Result file must start with RESULT: or AUDIT_RESULT:.",
                        stripped,
                    )
                )
            continue

        match = _FIELD_RE.match(line)
        if match:
            flush()
            key = match.group(1)
            value = match.group(2).strip()
            if key in fields and strict:
                issues.append(
                    ResultParseIssue(
                        REASON_MALFORMED_SECTION,
                        "RESULT_PARSE_MALFORMED_SECTION",
                        "error",
                        "Result field appears more than once.",
                        key,
                        field=key,
                    )
                )
            saw_field = True
            if value:
                fields[key] = value
                current_key = None
                current_lines = []
            else:
                current_key = key
                current_lines = []
            continue

        if current_key is not None:
            current_lines.append(line)
            continue

        if strict and not saw_field and not stripped.startswith(("```", "#")):
            issues.append(
                ResultParseIssue(
                    REASON_MALFORMED_SECTION,
                    "RESULT_PARSE_MALFORMED_SECTION",
                    "error",
                    "Non-field content appears before RESULT fields.",
                    stripped,
                )
            )

    flush()
    if strict and not text.strip():
        issues.append(
            ResultParseIssue(
                REASON_MALFORMED_SECTION,
                "RESULT_PARSE_MALFORMED_SECTION",
                "error",
                "Result file is empty.",
                path_text,
            )
        )
    elif strict and marker not in {"RESULT:", "AUDIT_RESULT:"}:
        issues.append(
            ResultParseIssue(
                REASON_MALFORMED_SECTION,
                "RESULT_PARSE_MALFORMED_SECTION",
                "error",
                "Result file must start with RESULT: or AUDIT_RESULT:.",
                marker or path_text,
            )
        )
    return fields, marker, issues


def _field_value(key: str, lines: list[str]) -> Any:
    values = [_normalize_section_line(line) for line in lines]
    values = [value for value in values if value]
    if not values:
        return "NONE"
    if key in SCALAR_FIELDS:
        return values[0]
    return values


def _normalize_section_line(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("- "):
        return stripped[2:].strip()
    return stripped


def _result_type(marker: str, path: Path | str | None, text: str, role: str) -> str:
    if marker == "AUDIT_RESULT:" or marker == "# AUDIT_RESULT":
        return "audit_result"
    if role == "auditor":
        return "audit_result"
    if path is not None and file_suggests_audit(Path(path), text):
        return "audit_result"
    if marker == "RESULT:" or marker == "# RESULT":
        return "profile_result"
    return "unknown"


def _strict_identity_issues(fields: Mapping[str, Any]) -> list[ResultParseIssue]:
    issues: list[ResultParseIssue] = []
    for field in REQUIRED_RESULT_FIELDS:
        if field in fields:
            continue
        reason = IDENTITY_REASON_BY_FIELD.get(field, REASON_MISSING_REQUIRED_FIELD)
        issues.append(
            ResultParseIssue(
                reason,
                f"RESULT_PARSE_{field}_MISSING",
                "error",
                f"Result is missing {field}.",
                f"{field}=MISSING",
                field=field,
            )
        )
    seen_identity_missing = {issue.field for issue in issues}
    for field, reason in IDENTITY_REASON_BY_FIELD.items():
        if field in seen_identity_missing:
            continue
        value = as_string(fields, field)
        if is_none(value):
            issues.append(
                ResultParseIssue(
                    reason,
                    f"RESULT_PARSE_{field}_MISSING",
                    "error",
                    f"Result is missing {field}.",
                    f"{field}=MISSING",
                    field=field,
                )
            )
    return issues


def _audit_details(fields: Mapping[str, Any], result_type: str) -> AuditResultDetails:
    if result_type != "audit_result":
        return AuditResultDetails("", (), (), (), ())
    findings = _audit_findings(fields)
    failed_checks = _failed_checks(fields)
    source_result_refs = _source_result_refs(fields)
    source_task_refs = _source_task_refs(fields, source_result_refs)
    return AuditResultDetails(
        status=as_string(fields, "STATUS").lower(),
        findings=tuple(findings),
        failed_checks=tuple(failed_checks),
        source_result_refs=tuple(source_result_refs),
        source_task_refs=tuple(source_task_refs),
    )


def _audit_findings(fields: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for field in AUDIT_FINDING_FIELDS:
        for item in as_list(fields, field):
            if item.upper() == "NONE":
                continue
            values.append(item)
    return _dedupe(values)


def _failed_checks(fields: Mapping[str, Any]) -> list[str]:
    checks: list[str] = []
    for field in FAILED_CHECK_FIELDS:
        checks.extend(as_list(fields, field))
    for field in ("EVIDENCE", "SCOPE_VERIFICATION", "FORBIDDEN_CHANGES_CHECK"):
        for item in as_list(fields, field):
            label, value = _label_value(item)
            if label and value.lower() in {"fail", "failed"}:
                checks.append(label)
            elif not label and "failed" in item.lower():
                checks.append(item)
    return _dedupe(check for check in checks if check and check.upper() != "NONE")


def _source_result_refs(fields: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    for item in _iter_field_items(fields):
        label, value = _label_value(item)
        if label in SOURCE_RESULT_LABELS and value:
            refs.append(value)
    return _dedupe(refs)


def _source_task_refs(fields: Mapping[str, Any], source_result_refs: Iterable[str]) -> list[str]:
    refs: list[str] = []
    for item in _iter_field_items(fields):
        label, value = _label_value(item)
        if label in SOURCE_TASK_LABELS and value:
            refs.append(value)
    for result_ref in source_result_refs:
        match = _RESULT_TASK_RE.search(result_ref.strip())
        if match:
            refs.append(match.group(1))
    task_id = as_string(fields, "TASK_ID")
    if task_id:
        refs.append(task_id)
    return _dedupe(refs)


def _iter_field_items(fields: Mapping[str, Any]) -> Iterable[str]:
    for value in fields.values():
        if isinstance(value, str):
            yield value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    yield item


def _label_value(item: str) -> tuple[str, str]:
    match = _LABEL_RE.search(item)
    if not match:
        return "", ""
    return match.group(1), match.group(2).strip()


def _dedupe(items: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
