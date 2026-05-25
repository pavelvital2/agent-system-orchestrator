"""Dry-run RESULT routing proposal command."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import runtime_schema_contracts
from .. import result_parser
from .. import transition_engine


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3

RESULT_STATUSES = result_parser.RESULT_STATUSES
PROFILE_ROLES = result_parser.PROFILE_ROLES
VALID_ROLES = result_parser.VALID_ROLES
REQUIRED_RESULT_FIELDS = result_parser.REQUIRED_RESULT_FIELDS
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
ACCEPTED_ARTIFACTS_RELPATH = "project-runtime/state/ACCEPTED_ARTIFACTS.json"
ACCEPTED_RESULT_PACKAGE_REF_RE = re.compile(
    r"^project-runtime/artifacts/accepted/RESULT_PACKAGE_[A-Za-z0-9_:-]+\.json$"
)
RESULT_PACKAGE_TYPES = {"RESULT_PACKAGE", "result_package"}
REQUIRED_RESULT_PACKAGE_FIELDS = (
    "package_id",
    "schema_version",
    "package_version",
    "governance_ruleset_version",
    "runtime_schema_version",
    "artifact_package_schema_version",
    "result_ref",
    "task_id",
    "agent_instance_id",
    "role",
    "status",
    "acceptance_status",
    "changed_files",
    "created_files",
    "deleted_files",
    "structured_artifacts",
    "commands_run",
    "tests_run",
    "evidence",
    "scope_verification",
    "forbidden_changes_check",
    "risks",
    "limitations",
    "blockers",
    "gaps",
    "next_recommended_action",
    "reuse_allowed",
    "agent_termination_required",
    "validation",
)
RESULT_PACKAGE_CONSTANTS = {
    "schema_version": "1.0.0",
    "package_version": runtime_schema_contracts.ACTIVE_PACKAGE_VERSION,
    "governance_ruleset_version": runtime_schema_contracts.ACTIVE_GOVERNANCE_RULESET_VERSION,
    "runtime_schema_version": runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION,
    "artifact_package_schema_version": runtime_schema_contracts.ACTIVE_ARTIFACT_PACKAGE_SCHEMA_VERSION,
    "acceptance_status": "accepted",
    "reuse_allowed": False,
    "agent_termination_required": True,
}


@dataclass(frozen=True)
class Rule:
    rule_id: str
    severity: str
    message: str
    evidence: str
    reason_code: str = ""

    def to_json(self) -> dict[str, str]:
        payload = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
        }
        if self.reason_code:
            payload["reason_code"] = self.reason_code
        return payload


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
    return dict(result_parser.parse_result(text).fields)


def _as_string(fields: dict[str, Any], key: str) -> str:
    return result_parser.as_string(fields, key)


def _as_list(fields: dict[str, Any], key: str) -> list[str]:
    return result_parser.as_list(fields, key)


def _bool_field(fields: dict[str, Any], key: str) -> bool | None:
    return result_parser.bool_field(fields, key)


def _file_suggests_audit(path: Path, text: str) -> bool:
    return result_parser.file_suggests_audit(path, text)


def _result_type(path: Path, text: str, role: str) -> str:
    if role == "auditor" or _file_suggests_audit(path, text):
        return "audit_result"
    return "profile_result"


def _source_result_refs(fields: dict[str, Any]) -> list[str]:
    return list(result_parser.audit_details_from_fields(fields).source_result_refs)


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


def _result_root(path: Path) -> Path | None:
    for parent in path.parents:
        if parent.name == "project-runtime":
            return parent.parent
    return None


def _result_ref(root: Path, result_path: Path) -> str:
    try:
        return result_path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return result_path.as_posix()


def _load_json_object(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, str(exc)
    except json.JSONDecodeError as exc:
        return None, f"{exc.msg} at line {exc.lineno} column {exc.colno}"
    if not isinstance(payload, dict):
        return None, "JSON root is not an object"
    return payload, ""


def _accepted_package_path(root: Path, package_ref: str) -> tuple[Path | None, str]:
    if not package_ref or package_ref.upper() == "NONE":
        return None, "artifact_ref is missing"
    if Path(package_ref).is_absolute():
        return None, "artifact_ref must be workspace-relative"
    if not ACCEPTED_RESULT_PACKAGE_REF_RE.fullmatch(package_ref):
        return None, "artifact_ref must match project-runtime/artifacts/accepted/RESULT_PACKAGE_*.json"

    root_resolved = root.resolve(strict=False)
    package_path = root / package_ref
    try:
        package_path.resolve(strict=False).relative_to(root_resolved)
    except ValueError:
        return None, "artifact_ref resolves outside workspace"
    return package_path, ""


def _result_package_errors(root: Path, package_ref: str, fields: dict[str, Any], result_ref: str) -> list[str]:
    package_path, path_error = _accepted_package_path(root, package_ref)
    if path_error:
        return [path_error]
    assert package_path is not None
    payload, error = _load_json_object(package_path)
    if error:
        return [f"{package_ref}: {error}"]

    expected = {
        "result_ref": result_ref,
        "task_id": _as_string(fields, "TASK_ID"),
        "agent_instance_id": _as_string(fields, "AGENT_INSTANCE_ID"),
        "role": _as_string(fields, "ROLE"),
        "status": _as_string(fields, "STATUS"),
        "acceptance_status": "accepted",
        "reuse_allowed": False,
        "agent_termination_required": True,
    }
    errors: list[str] = []
    for field in REQUIRED_RESULT_PACKAGE_FIELDS:
        if field not in payload:
            errors.append(f"{field} is required")
    for field, expected_value in RESULT_PACKAGE_CONSTANTS.items():
        if payload.get(field) != expected_value:
            errors.append(f"{field}={payload.get(field)!r}, expected {expected_value!r}")
    package_id = payload.get("package_id")
    if not isinstance(package_id, str) or not re.fullmatch(r"RESULT_PACKAGE_[A-Za-z0-9_:-]+", package_id):
        errors.append("package_id must match RESULT_PACKAGE_*")
    for field, expected_value in expected.items():
        if payload.get(field) != expected_value:
            errors.append(f"{field}={payload.get(field)!r}, expected {expected_value!r}")
    return errors


def _accepted_result_package(root: Path, fields: dict[str, Any], result_path: Path) -> tuple[bool, str]:
    accepted_path = root / ACCEPTED_ARTIFACTS_RELPATH
    payload, error = _load_json_object(accepted_path)
    if error:
        return False, f"{ACCEPTED_ARTIFACTS_RELPATH}: {error}"

    content = payload.get("content")
    artifacts = content.get("artifacts") if isinstance(content, dict) else None
    if not isinstance(artifacts, list):
        return False, f"{ACCEPTED_ARTIFACTS_RELPATH}.content.artifacts must be a list"

    task_id = _as_string(fields, "TASK_ID")
    result_ref = _result_ref(root, result_path)
    candidate_details: list[str] = []
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            continue
        if artifact.get("status") != "accepted":
            continue
        if artifact.get("artifact_type") not in RESULT_PACKAGE_TYPES:
            continue
        if artifact.get("source_task") != task_id:
            continue
        if artifact.get("source_result_ref") != result_ref:
            candidate_details.append(f"content.artifacts[{index}].source_result_ref={artifact.get('source_result_ref')!r}")
            continue
        package_ref = str(artifact.get("artifact_ref", "")).strip()
        package_errors = _result_package_errors(root, package_ref, fields, result_ref)
        if package_errors:
            return False, "; ".join(package_errors)
        return True, package_ref

    detail = "; ".join(candidate_details) if candidate_details else f"no accepted RESULT_PACKAGE entry for {result_ref}"
    return False, detail


def _has_matching_termination(root: Path, fields: dict[str, Any], result_path: Path) -> bool:
    events_path = root / "project-runtime" / "agents" / "instances.jsonl"
    if not events_path.is_file():
        return False
    try:
        lines = events_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    try:
        result_ref = result_path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        result_ref = result_path.as_posix()
    expected_event_type = "AUDITOR_AGENT_TERMINATED" if _as_string(fields, "ROLE") == "auditor" else "AGENT_TERMINATED"
    for raw_line in lines:
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        event_type = str(payload.get("event_type", payload.get("event", ""))).strip()
        if event_type not in {expected_event_type, "agent_instance_terminated", "auditor_agent_terminated"}:
            continue
        if str(payload.get("agent_instance_id", "")).strip() != _as_string(fields, "AGENT_INSTANCE_ID"):
            continue
        if str(payload.get("task_id", "")).strip() != _as_string(fields, "TASK_ID"):
            continue
        if str(payload.get("result_ref", "")).strip() != result_ref:
            continue
        return True
    return False


def _blocking_rule(rule_id: str, message: str, evidence: str) -> Rule:
    return Rule(rule_id, "error", message, evidence)


def _validate_common(
    path: Path,
    text: str,
    fields: dict[str, Any],
    parsed: result_parser.ParsedResult,
    strict: bool,
) -> list[Rule]:
    errors: list[Rule] = []
    if not text.strip():
        errors.append(
            Rule(
                "RESULT_FORMAT_001",
                "error",
                "Result file is empty.",
                str(path),
                result_parser.REASON_MALFORMED_SECTION,
            )
        )
        return errors
    lines = text.splitlines()
    first_line = next((line.strip() for line in lines if line.strip()), "")
    if first_line not in {"RESULT:", "AUDIT_RESULT:"}:
        errors.append(
            Rule(
                "RESULT_FORMAT_002",
                "error",
                "Result file must start with the canonical RESULT: or AUDIT_RESULT: marker.",
                first_line or str(path),
                result_parser.REASON_MALFORMED_SECTION,
            )
        )
    if not strict:
        return errors

    for issue in parsed.issues:
        if issue.reason_code != result_parser.REASON_MALFORMED_SECTION:
            continue
        if issue.evidence == first_line:
            continue
        errors.append(
            Rule(
                "RESULT_FORMAT_002",
                issue.severity,
                issue.message,
                issue.evidence,
                issue.reason_code,
            )
        )

    for field in REQUIRED_RESULT_FIELDS:
        if field not in fields:
            errors.append(
                Rule(
                    "RESULT_FORMAT_003",
                    "error",
                    "Strict RESULT parsing requires every template field.",
                    field,
                    result_parser.IDENTITY_REASON_BY_FIELD.get(field, "missing_required_field"),
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
                result_parser.REASON_MISSING_STATUS if not status else "invalid_status",
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
                result_parser.REASON_MISSING_ROLE if not role else "invalid_role",
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


def _route_guardrails(
    fields: dict[str, Any],
    result_type: str,
    strict: bool,
    *,
    terminated: bool,
    accepted_result_package: bool,
    accepted_result_package_detail: str,
) -> tuple[list[Rule], list[Rule], bool]:
    status = _as_string(fields, "STATUS")
    role = _as_string(fields, "ROLE")
    task_id = _as_string(fields, "TASK_ID")
    claims = _claimed_next_actions(fields)
    blocking_rules: list[Rule] = []
    validation_errors: list[Rule] = []
    suppress_route = False

    if result_type == "audit_result":
        if strict and not terminated:
            validation_errors.append(
                Rule(
                    "RESULT_LIFECYCLE_001",
                    "error",
                    "Audit RESULT cannot route to checkpoint preflight before auditor termination event.",
                    "Run aso lifecycle terminate-agent --root WORKSPACE --from-result RESULT_PATH --confirm-write before checkpoint preflight.",
                )
            )
            return blocking_rules, validation_errors, True
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
                suppress_route = True
        elif status == "fail":
            blocking_rules.append(
                _blocking_rule(
                    "GOV-AUDIT-FAIL-NO-CHECKPOINT",
                    "Audit fail forbids checkpoint, commit, push, and normal next-task routing.",
                    f"TASK_ID={task_id}",
                )
            )
        elif status == "blocked":
            blocking_rules.append(
                _blocking_rule(
                    "GOV-AUDIT-BLOCKED-NO-CHECKPOINT",
                    "Audit blocked forbids checkpoint until the blocker is resolved.",
                    f"TASK_ID={task_id}",
                )
            )
        elif status == "gap":
            blocking_rules.append(
                _blocking_rule(
                    "GOV-AUDIT-GAP-NO-CHECKPOINT",
                    "Audit gap forbids checkpoint until owner/GAP routing resolves.",
                    f"TASK_ID={task_id}",
                )
            )
        return blocking_rules, validation_errors, suppress_route

    audit_required = role in PROFILE_ROLES
    if status == "pass" and audit_required:
        if strict and not terminated:
            validation_errors.append(
                Rule(
                    "RESULT_LIFECYCLE_001",
                    "error",
                    "Profile RESULT cannot route to audit before agent termination event.",
                    "Run aso lifecycle terminate-agent --root WORKSPACE --from-result RESULT_PATH --confirm-write before audit route.",
                )
            )
            return blocking_rules, validation_errors, True
        if strict and not accepted_result_package:
            validation_errors.append(
                Rule(
                    "RESULT_PACKAGE_ACCEPTANCE_001",
                    "error",
                    "Profile RESULT cannot route to audit before its RESULT package is accepted.",
                    accepted_result_package_detail,
                )
            )
            return blocking_rules, validation_errors, True
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
    elif status == "fail":
        blocking_rules.append(
            _blocking_rule(
                "GOV-PROFILE-FAIL-NO-CHECKPOINT",
                "Profile RESULT fail forbids checkpoint and routes to correction.",
                f"TASK_ID={task_id}",
            )
        )
    elif status == "blocked":
        blocking_rules.append(
            _blocking_rule(
                "GOV-PROFILE-BLOCKED-NO-CHECKPOINT",
                "Profile RESULT blocked forbids checkpoint until orchestrator routing resolves.",
                f"TASK_ID={task_id}",
            )
        )
    elif status == "gap":
        blocking_rules.append(
            _blocking_rule(
                "GOV-PROFILE-GAP-NO-CHECKPOINT",
                "Profile RESULT gap forbids checkpoint until GAP routing resolves.",
                f"TASK_ID={task_id}",
            )
        )
    return blocking_rules, validation_errors, suppress_route


def _transition_findings_as_rules(findings: tuple[transition_engine.TransitionFinding, ...]) -> list[Rule]:
    rules: list[Rule] = []
    for finding in findings:
        if finding.severity != "error":
            continue
        evidence = finding.evidence
        if finding.recommendation:
            evidence = f"{evidence}; recommendation={finding.recommendation}"
        rules.append(Rule(finding.rule_id, finding.severity, finding.message, evidence))
    return rules


def _transition_contract_load_failure(exc: BaseException) -> dict[str, object]:
    return {
        "allowed": False,
        "findings": [
            {
                "rule_id": "RUNTIME_CONTRACT_LOAD_FAILED",
                "severity": "error",
                "message": "Runtime contract could not be loaded.",
                "evidence": str(exc),
                "recommendation": "Restore ORCHESTRATOR_RUNTIME_CONTRACT.json before routing RESULTs.",
            }
        ],
        "reference_docs_used": [transition_engine.CONTRACT_RELATIVE_PATH.as_posix()],
        "canonical_recommended_next_action": "NONE",
        "contract_authoritative": True,
    }


def _canonical_transition_route(
    fields: dict[str, Any],
    result_type: str,
) -> tuple[dict[str, object], str, list[Rule]]:
    try:
        contract = transition_engine.load_runtime_contract()
    except (OSError, transition_engine.RuntimeContractError) as exc:
        return _transition_contract_load_failure(exc), "NONE", [
            Rule(
                "RUNTIME_CONTRACT_LOAD_FAILED",
                "error",
                "Runtime contract could not be loaded.",
                str(exc),
            )
        ]

    task_id = _as_string(fields, "TASK_ID")
    status = _as_string(fields, "STATUS")
    decision = transition_engine.derive_result_route(
        contract,
        result_type,
        status,
        task_id=task_id,
    )
    payload = decision.to_json()
    errors = _transition_findings_as_rules(decision.findings)
    candidate_next_action = str(decision.next_action.get("recommended_next_action") or "NONE").strip() or "NONE"
    canonical_next_action = "NONE" if errors else candidate_next_action
    payload["candidate_recommended_next_action"] = candidate_next_action
    payload["canonical_recommended_next_action"] = canonical_next_action
    payload["contract_authoritative"] = True
    return payload, "NONE" if errors else canonical_next_action, errors


def _transition_not_run_evidence(reason: str) -> dict[str, object]:
    return {
        "allowed": False,
        "findings": [],
        "reference_docs_used": [transition_engine.CONTRACT_RELATIVE_PATH.as_posix()],
        "canonical_recommended_next_action": "NONE",
        "command_recommended_next_action": "NONE",
        "contract_authoritative": True,
        "route_suppressed_by": reason,
    }


def build_report(result_path: Path, strict: bool) -> tuple[dict[str, Any], int]:
    text, io_errors = _read_result(result_path)
    parsed = result_parser.parse_result(text, path=result_path, strict=strict) if text else result_parser.parse_result("")
    fields = dict(parsed.fields)
    role = parsed.role
    result_type = parsed.result_type if text else "unknown"
    validation_errors = [*io_errors, *_validate_common(result_path, text, fields, parsed, strict)]

    recommended_next_action = "NONE"
    checkpoint_candidate = False
    blocking_rules: list[Rule] = []
    accepted_result_package = True
    accepted_result_package_detail = "not required"
    transition_evidence = _transition_not_run_evidence("pre_route_validation_errors")
    if not io_errors and not validation_errors:
        root = _result_root(result_path)
        terminated = True if root is None else _has_matching_termination(root, fields, result_path)
        if root is not None and result_type == "profile_result" and role in PROFILE_ROLES:
            accepted_result_package, accepted_result_package_detail = _accepted_result_package(root, fields, result_path)
        transition_evidence, canonical_next_action, transition_errors = _canonical_transition_route(fields, result_type)
        blocking_rules, route_errors, route_suppressed = _route_guardrails(
            fields,
            result_type,
            strict,
            terminated=terminated,
            accepted_result_package=accepted_result_package,
            accepted_result_package_detail=accepted_result_package_detail,
        )
        validation_errors.extend(route_errors)
        validation_errors.extend(transition_errors)
        if not route_suppressed and not transition_errors:
            recommended_next_action = canonical_next_action
            checkpoint_candidate = recommended_next_action == "CHECKPOINT_PREFLIGHT"
        transition_evidence["command_recommended_next_action"] = recommended_next_action
        if route_suppressed or transition_errors:
            transition_evidence["route_suppressed_by"] = (
                "transition_engine_errors" if transition_errors else "record_result_guardrail_errors"
            )

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
            "accepted_result_package": accepted_result_package,
            "accepted_result_package_ref": accepted_result_package_detail if accepted_result_package else "",
            "source_result_refs": _source_result_refs(fields),
            "claimed_next_actions": _claimed_next_actions(fields),
            "parsed_fields": sorted(fields),
            "audit_result": parsed.audit.to_json() if result_type == "audit_result" else {},
            "transition_engine": transition_evidence,
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
