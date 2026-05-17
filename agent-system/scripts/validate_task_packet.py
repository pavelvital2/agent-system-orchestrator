#!/usr/bin/env python3
"""Validate task packet markdown before dispatch or checkpoint.

This validator is intentionally documentation-first: it checks the mandatory
TASK_PACKET_TEMPLATE sections and the dispatch safety rules that can be
determined from one markdown file and its path.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


PROFILE_ROLES = {
    "requirements_analyst",
    "designer",
    "developer",
    "auditor",
    "tester",
    "technical_writer",
    "devops_setup_engineer",
    "release_manager",
}

CONTROL_ROLES = PROFILE_ROLES | {"orchestrator", "project_owner", "none"}

TASK_STATUS_VALUES = {"active", "completed", "superseded", "deprecated"}

TASK_KIND_VALUES = {
    "normal",
    "research_dependency",
    "design_continuation",
    "task_continuation",
    "correction",
    "audit",
    "testing",
    "setup",
    "launch",
    "handover",
}

FAILURE_TYPE_VALUES = {
    "governance",
    "workflow",
    "filesystem",
    "runtime_state",
    "audit",
    "testing",
    "gap",
    "blocked",
    "none",
}

REASONING_LEVEL_VALUES = {"low", "medium", "high", "xhigh"}
DEPRECATED_REASONING_LEVEL_VALUES = {
    "default",
    "maximum",
    "role_default",
    "standard",
    "analytical",
    "critical",
    "mechanical",
}
DEPENDENCY_STATUS_VALUES = {"ready", "blocked", "pending", "none"}
REQUIREMENT_VALUES = {"mandatory", "optional", "none"}
YES_NO_VALUES = {"yes", "no"}

MANDATORY_TASK_PACKET_SECTIONS = [
    "TASK_ID",
    "TASK_STATUS",
    "TASK_KIND",
    "SUPERSEDES",
    "SUPERSEDED_BY",
    "CORRECTION_OF",
    "SOURCE_RESULT_REF",
    "ATTEMPT_NO",
    "FAILURE_TYPE",
    "TASK_TITLE",
    "TASK_TYPE",
    "TARGET_ROLE",
    "REASONING_LEVEL",
    "DEPENDENCIES",
    "DEPENDENCY_STATUS",
    "REQUESTED_BY_ROLE",
    "REQUESTED_BY_TASK",
    "RESEARCH_QUESTION_ID",
    "RESEARCH_PURPOSE",
    "RESEARCH_QUESTIONS",
    "ALLOWED_SOURCES",
    "FORBIDDEN_SOURCES",
    "EXPECTED_EVIDENCE",
    "EXPECTED_OUTPUT",
    "RETURN_TO_REQUESTER_AFTER_AUDIT_PASS",
    "RETURN_TO_ROLE_AFTER_AUDIT_PASS",
    "RETURN_TASK_AFTER_AUDIT_PASS",
    "PURPOSE",
    "SOURCE_OF_TRUTH",
    "SCOPE_IN",
    "SCOPE_OUT",
    "REQUIRED_DOCS",
    "INPUTS",
    "READ_INPUTS",
    "EXPECTED_OUTPUTS",
    "ALLOWED_FILE_CHANGES",
    "FORBIDDEN_FILE_CHANGES",
    "ACCEPTANCE_CRITERIA",
    "EVIDENCE_REQUIREMENTS",
    "SETUP_HOOKS",
    "LAUNCH_HOOKS",
    "RESULT_PATH",
    "RISK_REQUIREMENTS",
    "MANDATORY_WORKFLOW",
    "NEXT_ROLE_ON_PASS",
    "NEXT_ROLE_ON_FAIL",
    "NEXT_ROLE_ON_BLOCKED",
    "NEXT_ROLE_ON_GAP",
    "AUDIT_REQUIREMENTS",
    "TESTING_REQUIREMENTS",
    "DOCUMENTATION_REQUIREMENTS",
    "FILESYSTEM_GOVERNANCE",
    "RUNTIME_GOVERNANCE",
    "RESULT_FORMAT",
    "TERMINAL_CONDITIONS",
    "NOTES",
]

MANDATORY_TASK_PROPOSAL_SECTIONS = [
    "PROPOSAL_ID",
    "PROPOSAL_STATUS",
    "PROPOSAL_TITLE",
    "REQUESTED_BY_ROLE",
    "PURPOSE",
    "PROPOSED_TASK_KIND",
    "PROPOSED_TARGET_ROLE",
    "PROPOSED_SCOPE",
    "OPEN_QUESTIONS",
    "DISPATCH_STATUS",
]

H1_TASK_PACKET_RE = re.compile(r"^#\s+TASK PACKET\s*$", re.MULTILINE)
H1_TASK_PROPOSAL_RE = re.compile(
    r"^#\s+(?:TASK PROPOSAL|TASK_PROPOSAL(?:_TEMPLATE)?)\s*$",
    re.MULTILINE,
)
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
FENCE_RE = re.compile(r"```(?:[A-Za-z0-9_-]+)?\n(.*?)\n```", re.DOTALL)


@dataclass
class ValidationResult:
    path: Path
    classification: str
    errors: List[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def normalize_heading(raw: str) -> str:
    heading = raw.strip().strip("`").strip()
    return re.sub(r"\s+", " ", heading).upper()


def parse_sections(text: str) -> Dict[str, str]:
    matches = list(H2_RE.finditer(text))
    sections: Dict[str, str] = {}
    for index, match in enumerate(matches):
        name = normalize_heading(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[name] = text[start:end].strip()
    return sections


def strip_fenced_blocks(text: str) -> str:
    return FENCE_RE.sub("", text)


def first_fenced_value(section_text: str) -> str:
    match = FENCE_RE.search(section_text)
    if match:
        return match.group(1).strip()
    lines = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue
        if stripped.endswith(":") and stripped.upper() in {"RULES:", "EXAMPLES:"}:
            continue
        lines.append(stripped)
    return "\n".join(lines).strip()


def scalar_value(sections: Dict[str, str], section: str) -> str:
    value = first_fenced_value(sections.get(section, ""))
    for line in value.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.strip("- ").strip()
    return ""


def lower_scalar(sections: Dict[str, str], section: str) -> str:
    return scalar_value(sections, section).lower()


def reasoning_value(sections: Dict[str, str]) -> str:
    value = first_fenced_value(sections.get("REASONING_LEVEL", ""))
    match = re.search(r"^VALUE:\s*([A-Za-z_]+)\s*$", value, re.MULTILINE)
    return match.group(1).lower() if match else ""


def has_nonempty_content(sections: Dict[str, str], section: str) -> bool:
    return bool(first_fenced_value(sections.get(section, "")).strip())


def add_error(errors: List[str], message: str) -> None:
    errors.append(f"invalid_task_packet_schema: {message}")


def require_enum(
    sections: Dict[str, str],
    section: str,
    allowed: Iterable[str],
    errors: List[str],
) -> None:
    value = lower_scalar(sections, section)
    if value not in set(allowed):
        add_error(errors, f"{section} has invalid value {value or '<empty>'}")


def require_task_packet_schema(sections: Dict[str, str], errors: List[str]) -> None:
    for section in MANDATORY_TASK_PACKET_SECTIONS:
        if section not in sections:
            add_error(errors, f"missing mandatory section {section}")
        elif not has_nonempty_content(sections, section):
            add_error(errors, f"empty mandatory section {section}")

    if errors:
        return

    require_enum(sections, "TASK_STATUS", TASK_STATUS_VALUES, errors)
    require_enum(sections, "TASK_KIND", TASK_KIND_VALUES, errors)
    require_enum(sections, "FAILURE_TYPE", FAILURE_TYPE_VALUES, errors)
    require_enum(sections, "TASK_TYPE", PROFILE_ROLES, errors)
    require_enum(sections, "TARGET_ROLE", PROFILE_ROLES, errors)
    require_enum(sections, "DEPENDENCY_STATUS", DEPENDENCY_STATUS_VALUES, errors)
    require_enum(sections, "RETURN_TO_REQUESTER_AFTER_AUDIT_PASS", YES_NO_VALUES, errors)
    require_enum(sections, "RETURN_TO_ROLE_AFTER_AUDIT_PASS", PROFILE_ROLES | {"none"}, errors)
    require_enum(sections, "NEXT_ROLE_ON_PASS", CONTROL_ROLES, errors)
    require_enum(sections, "NEXT_ROLE_ON_FAIL", CONTROL_ROLES, errors)
    require_enum(sections, "NEXT_ROLE_ON_BLOCKED", CONTROL_ROLES, errors)
    require_enum(sections, "NEXT_ROLE_ON_GAP", CONTROL_ROLES, errors)
    require_enum(sections, "AUDIT_REQUIREMENTS", REQUIREMENT_VALUES, errors)
    require_enum(sections, "TESTING_REQUIREMENTS", REQUIREMENT_VALUES, errors)
    require_enum(sections, "DOCUMENTATION_REQUIREMENTS", REQUIREMENT_VALUES, errors)

    attempt_no = lower_scalar(sections, "ATTEMPT_NO")
    if attempt_no != "none" and not attempt_no.isdigit():
        add_error(errors, "ATTEMPT_NO must be a number or NONE")

    level = reasoning_value(sections)
    if level in DEPRECATED_REASONING_LEVEL_VALUES:
        add_error(errors, f"REASONING_LEVEL VALUE uses deprecated level {level}")
    elif level not in REASONING_LEVEL_VALUES:
        add_error(errors, "REASONING_LEVEL VALUE has invalid or missing value")

    task_type = lower_scalar(sections, "TASK_TYPE")
    target_role = lower_scalar(sections, "TARGET_ROLE")
    if task_type != target_role:
        add_error(errors, "TASK_TYPE must match TARGET_ROLE for dispatchable profile tasks")

    required_docs = first_fenced_value(sections.get("REQUIRED_DOCS", ""))
    if "project-archive/" in required_docs or "# DEPRECATED" in required_docs:
        add_error(errors, "REQUIRED_DOCS must not include deprecated/archive documents")


def require_proposal_schema(sections: Dict[str, str], errors: List[str]) -> None:
    for section in MANDATORY_TASK_PROPOSAL_SECTIONS:
        if section not in sections:
            add_error(errors, f"missing mandatory TASK_PROPOSAL section {section}")
        elif not has_nonempty_content(sections, section):
            add_error(errors, f"empty mandatory TASK_PROPOSAL section {section}")

    if errors:
        return

    dispatch_status = lower_scalar(sections, "DISPATCH_STATUS")
    if dispatch_status != "non_dispatchable":
        add_error(errors, "TASK_PROPOSAL DISPATCH_STATUS must be non_dispatchable")


def relative_posix(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def is_under(rel_path: str, root: str) -> bool:
    clean_root = root.strip("/").rstrip("/")
    return rel_path == clean_root or rel_path.startswith(f"{clean_root}/")


def bootstrap_path_allowed(rel_path: str, target_role: str) -> bool:
    if target_role not in PROFILE_ROLES:
        return False
    expected = f"project-runtime/bootstrap/TASK_BOOTSTRAP_{target_role.upper()}_001.md"
    return rel_path == expected


def system_package_correction_allowed(rel_path: str, sections: Dict[str, str]) -> bool:
    if not rel_path.startswith("project-input/PATCH_"):
        return False
    if lower_scalar(sections, "TASK_KIND") != "correction":
        return False
    return lower_scalar(sections, "CORRECTION_OF") != "none"


def require_dispatchable_path(
    path: Path,
    sections: Dict[str, str],
    args: argparse.Namespace,
    errors: List[str],
) -> None:
    rel_path = relative_posix(path)
    target_role = lower_scalar(sections, "TARGET_ROLE")

    if is_under(rel_path, args.active_doc_root):
        return

    if args.allow_first_bootstrap and bootstrap_path_allowed(rel_path, target_role):
        return

    if args.allow_system_package_correction and system_package_correction_allowed(
        rel_path, sections
    ):
        return

    add_error(
        errors,
        "dispatchable task packet path must be inside ACTIVE_DOC_ROOT, "
        "the bounded first-bootstrap path, or explicit package-correction input",
    )


def validate_task_packet(path: Path, text: str, args: argparse.Namespace) -> ValidationResult:
    errors: List[str] = []
    sections = parse_sections(text)
    require_task_packet_schema(sections, errors)

    if not errors and args.mode == "dispatch":
        if lower_scalar(sections, "TASK_STATUS") != "active":
            add_error(errors, "create_agent requires TASK_STATUS active")
        require_dispatchable_path(path, sections, args, errors)

    if not errors and args.mode == "checkpoint":
        if lower_scalar(sections, "TASK_STATUS") == "active":
            require_dispatchable_path(path, sections, args, errors)

    return ValidationResult(path=path, classification="TASK_PACKET", errors=errors)


def validate_task_proposal(path: Path, text: str, args: argparse.Namespace) -> ValidationResult:
    errors: List[str] = []
    sections = parse_sections(text)
    require_proposal_schema(sections, errors)

    if args.mode == "dispatch":
        add_error(errors, "TASK_PROPOSAL is non-dispatchable and cannot create_agent")

    return ValidationResult(path=path, classification="TASK_PROPOSAL", errors=errors)


def validate_path(path: Path, args: argparse.Namespace) -> ValidationResult:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return ValidationResult(path=path, classification="unreadable", errors=[str(exc)])

    marker_text = strip_fenced_blocks(text)
    has_task_packet = bool(H1_TASK_PACKET_RE.search(marker_text))
    has_task_proposal = bool(H1_TASK_PROPOSAL_RE.search(marker_text))

    if has_task_packet and has_task_proposal:
        return ValidationResult(
            path=path,
            classification="ambiguous",
            errors=["invalid_task_packet_schema: file declares both TASK_PACKET and TASK_PROPOSAL"],
        )

    if has_task_packet:
        return validate_task_packet(path, text, args)

    if has_task_proposal:
        return validate_task_proposal(path, text, args)

    return ValidationResult(
        path=path,
        classification="unknown",
        errors=["invalid_task_packet_schema: missing # TASK PACKET or # TASK PROPOSAL marker"],
    )


def print_result(result: ValidationResult) -> None:
    if result.ok:
        if result.classification == "TASK_PROPOSAL":
            print(f"VALID: {result.path}: TASK_PROPOSAL non_dispatchable")
        else:
            print(f"VALID: {result.path}: {result.classification}")
        return

    print(f"INVALID: {result.path}: {result.classification}")
    for error in result.errors:
        print(f"ERROR: {error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate TASK_PACKET markdown schema and dispatch safety.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Task packet or task proposal markdown files to validate.",
    )
    parser.add_argument(
        "--mode",
        choices=("schema", "dispatch", "checkpoint"),
        default="schema",
        help=(
            "schema validates required sections; dispatch enforces create_agent "
            "rules; checkpoint validates changed task artifacts before git add."
        ),
    )
    parser.add_argument(
        "--active-doc-root",
        default="project-docs",
        help="Active documentation root for ordinary dispatchable task packets.",
    )
    parser.add_argument(
        "--allow-first-bootstrap",
        action="store_true",
        help=(
            "Allow only project-runtime/bootstrap/"
            "TASK_BOOTSTRAP_<TARGET_ROLE>_001.md outside ACTIVE_DOC_ROOT."
        ),
    )
    parser.add_argument(
        "--allow-system-package-correction",
        action="store_true",
        help="Allow explicit owner-authorized package correction packets under project-input/PATCH_*.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    results = [validate_path(path, args) for path in args.paths]
    for result in results:
        print_result(result)

    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
