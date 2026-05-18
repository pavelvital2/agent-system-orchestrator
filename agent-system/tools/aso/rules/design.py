"""Deterministic rules for read-only ASO design validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from parsers.markdown_design import (
    MarkdownDocument,
    MarkdownSection,
    all_field_values,
    has_non_none_field,
    has_substantive_body,
    is_none,
    parse_markdown,
)


REQUIRED_SECTIONS = (
    "REQUIREMENTS_TRACEABILITY_MATRIX",
    "MVP_BOUNDARY",
    "NON_GOALS",
    "ASSUMPTIONS_REGISTER",
    "GAP_REGISTER_UPDATES",
    "ARCHITECTURE_DECISIONS",
    "MODULE_CONTRACTS",
    "DATA_CONTRACTS",
    "RUNTIME_MODEL",
    "TESTING_STRATEGY",
    "TASK_DAG",
    "DISPATCHABLE_TASK_PACKETS",
    "AUDIT_PLAN",
    "RISK_REGISTER",
)

REQUIREMENT_FIELDS = (
    "REQUIREMENT_ID",
    "SOURCE_REF",
    "DESIGN_RESPONSE",
    "DOWNSTREAM_ARTIFACTS",
    "ACCEPTANCE_LINK",
    "STATUS",
)
TESTING_FIELDS = (
    "UNIT_OR_STATIC_CHECKS",
    "INTEGRATION_CHECKS",
    "RUNTIME_SMOKE_CHECKS",
    "ACCEPTANCE_SCENARIOS",
    "NEGATIVE_OR_FAILURE_CHECKS",
    "EVIDENCE_REQUIRED",
    "TESTING_TASK_REFS",
    "SOURCE_REFS",
)
CAPABILITY_FIELDS = (
    "PRODUCT_CAPABILITY_LEVEL",
    "CAPABILITY_SCOPE",
    "CAPABILITY_ACCEPTANCE_REF",
    "CAPABILITY_SOURCE_REF",
)
ALLOWED_CAPABILITY_LEVELS = {
    "skeleton",
    "task_complete",
    "product_slice",
    "mvp_candidate",
    "launch_candidate",
    "final_acceptance_candidate",
    "not_applicable",
}
DESIGN_GATE_MARKERS = {
    "design_audit_pass",
    "design_audit_pass_then_checkpoint",
    "accepted_design_artifact",
}
SOURCE_ONLY_FORBIDDEN_PREFIXES = (
    "ASSUMPTION",
    "ASSUMPTION_ID",
    "GAP",
    "GAP_ID",
    "RESEARCH",
    "RESEARCH_DEPENDENCY",
    "MEMORY",
    "CONVERSATION",
    "UNVERIFIED",
)
UNKNOWN_DEPENDENCY_MARKERS = {
    "TBD",
    "UNKNOWN",
    "MISSING",
    "LATER",
    "INFORMAL",
    "UNRESOLVED",
}
REPOSITORY_WIDE_AUTHORITY = {".", "*", "**", "**/*", "/", "repo", "repository", "repository-root"}
LIFECYCLE_ROLE_TERMS = {
    "developer",
    "auditor",
    "tester",
    "technical_writer",
    "devops_setup_engineer",
    "release_manager",
    "implementation",
    "testing",
    "documentation",
    "setup",
    "launch",
    "release",
}


@dataclass(frozen=True)
class DesignFinding:
    rule_id: str
    severity: str
    title: str
    details: str
    path: str
    section: str
    recommendation: str

    def to_json(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "message": self.details,
            "details": self.details,
            "path": self.path,
            "section": self.section,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class DesignValidationResult:
    status: str
    exit_code: int
    findings: list[DesignFinding]
    summary: dict[str, int]
    score: int
    document: dict[str, object]


def validate_design_file(path: Path, *, root: Path, strict: bool) -> DesignValidationResult:
    relpath = _rel(root, path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        finding = DesignFinding(
            "DESIGN_IO_001",
            "error",
            "Design file is unreadable",
            f"{relpath}: {exc}",
            relpath,
            "",
            "Pass a readable Markdown design file.",
        )
        return _result([finding], relpath, strict, section_count=0)

    document = parse_markdown(text)
    findings = _validate_document(document, relpath)
    return _result(findings, relpath, strict, section_count=len(document.sections))


def _validate_document(document: MarkdownDocument, relpath: str) -> list[DesignFinding]:
    findings: list[DesignFinding] = []
    findings.extend(_check_required_sections(document, relpath))
    findings.extend(_check_requirements_traceability(document, relpath))
    findings.extend(_check_decision_sources(document, relpath))
    findings.extend(_check_assumption_fact_separation(document, relpath))
    findings.extend(_check_owner_decision_markers(document, relpath))
    findings.extend(_check_downstream_tasks(document, relpath))
    findings.extend(_check_dependencies_and_gates(document, relpath))
    findings.extend(_check_testing_strategy(document, relpath))
    findings.extend(_check_product_capability(document, relpath))
    return sorted(findings, key=lambda item: (item.rule_id, item.section, item.details))


def _check_required_sections(document: MarkdownDocument, relpath: str) -> list[DesignFinding]:
    findings: list[DesignFinding] = []
    for duplicate in document.duplicate_sections:
        findings.append(
            DesignFinding(
                "DESIGN_CONTRACT_002",
                "error",
                "Design section is duplicated",
                f"Section {duplicate} appears more than once.",
                relpath,
                duplicate,
                "Keep one canonical section for each design contract heading.",
            )
        )
    for section_name in REQUIRED_SECTIONS:
        section = document.sections.get(section_name)
        if section is None:
            findings.append(
                DesignFinding(
                    "DESIGN_CONTRACT_001",
                    "error",
                    "Required design section is missing",
                    f"Missing required section ## {section_name}.",
                    relpath,
                    section_name,
                    "Add the required DESIGN_OUTPUT_CONTRACT section or return a blocked/gap result instead of design pass.",
                )
            )
        elif not has_substantive_body(section):
            findings.append(
                DesignFinding(
                    "DESIGN_CONTRACT_001",
                    "error",
                    "Required design section is empty",
                    f"Section ## {section.title} has no substantive auditable content.",
                    relpath,
                    section_name,
                    "Populate the section or state NONE with an auditable reason where the contract permits it.",
                )
            )
    return findings


def _check_requirements_traceability(document: MarkdownDocument, relpath: str) -> list[DesignFinding]:
    section = document.sections.get("REQUIREMENTS_TRACEABILITY_MATRIX")
    if section is None:
        return []
    findings: list[DesignFinding] = []
    entries = _entries(section, "REQUIREMENT_ID")
    if not entries:
        return [
            DesignFinding(
                "DESIGN_TRACE_001",
                "error",
                "Requirements traceability rows are missing",
                "REQUIREMENTS_TRACEABILITY_MATRIX has no REQUIREMENT_ID row.",
                relpath,
                section.normalized_title,
                "Map each accepted requirement to source, design response, downstream artifacts, and acceptance link.",
            )
        ]
    for entry in entries:
        missing = [field for field in REQUIREMENT_FIELDS if is_none(entry.get(field))]
        if missing:
            findings.append(
                DesignFinding(
                    "DESIGN_TRACE_001",
                    "error",
                    "Requirement traceability row is incomplete",
                    f"{entry.get('REQUIREMENT_ID', 'UNKNOWN')} is missing: {', '.join(missing)}.",
                    relpath,
                    section.normalized_title,
                    "Complete every required traceability row field.",
                )
            )
    return findings


def _check_decision_sources(document: MarkdownDocument, relpath: str) -> list[DesignFinding]:
    section = document.sections.get("ARCHITECTURE_DECISIONS")
    if section is None:
        return []
    findings: list[DesignFinding] = []
    entries = _entries(section, "DECISION_ID")
    if not entries:
        return [
            DesignFinding(
                "DRF-001",
                "error",
                "Architecture decision is missing source evidence",
                "ARCHITECTURE_DECISIONS has no DECISION_ID entries.",
                relpath,
                section.normalized_title,
                "Record each accepted or proposed decision with SOURCE_REFS.",
            )
        ]
    for entry in entries:
        status = entry.get("STATUS", "").lower()
        if status not in {"accepted", "proposed"}:
            continue
        source_refs = entry.get("SOURCE_REFS", "")
        if not _has_allowed_source(source_refs):
            findings.append(
                DesignFinding(
                    "DRF-001",
                    "error",
                    "Architecture decision lacks an allowed source",
                    (
                        f"{entry.get('DECISION_ID', 'UNKNOWN')} has STATUS={status or 'MISSING'} "
                        f"but SOURCE_REFS={source_refs or 'MISSING'}."
                    ),
                    relpath,
                    section.normalized_title,
                    "Cite allowed source-of-truth documents; assumptions, GAPs, research dependencies, and memory do not replace SOURCE_REFS.",
                )
            )
        missing = [field for field in ("DECISION_ID", "DECISION", "RATIONALE", "TASK_REFS", "STATUS") if is_none(entry.get(field))]
        if missing:
            findings.append(
                DesignFinding(
                    "DESIGN_TRACE_002",
                    "error",
                    "Architecture decision row is incomplete",
                    f"{entry.get('DECISION_ID', 'UNKNOWN')} is missing: {', '.join(missing)}.",
                    relpath,
                    section.normalized_title,
                    "Complete every required decision traceability field.",
                )
            )
    return findings


def _check_assumption_fact_separation(document: MarkdownDocument, relpath: str) -> list[DesignFinding]:
    findings: list[DesignFinding] = []
    decisions = document.sections.get("ARCHITECTURE_DECISIONS")
    if decisions is not None:
        for entry in _entries(decisions, "DECISION_ID"):
            if entry.get("STATUS", "").lower() not in {"accepted", "proposed"}:
                continue
            source_refs = entry.get("SOURCE_REFS", "")
            assumption_refs = entry.get("ASSUMPTION_REFS", "")
            if _source_is_only_assumption(source_refs) or _affirmative(entry.get("ASSUMPTION_USED_AS_FACT")):
                findings.append(
                    DesignFinding(
                        "DRF-002",
                        "error",
                        "Assumption is presented as accepted fact",
                        f"{entry.get('DECISION_ID', 'UNKNOWN')} uses assumption evidence as accepted decision source.",
                        relpath,
                        decisions.normalized_title,
                        "Keep assumptions in ASSUMPTIONS_REGISTER and cite allowed source refs for accepted or proposed decisions.",
                    )
                )
            if not is_none(assumption_refs) and not _has_allowed_source(source_refs):
                findings.append(
                    DesignFinding(
                        "DRF-002",
                        "error",
                        "Assumption replaces source evidence",
                        f"{entry.get('DECISION_ID', 'UNKNOWN')} has ASSUMPTION_REFS but no allowed SOURCE_REFS.",
                        relpath,
                        decisions.normalized_title,
                        "Use assumptions as risks or validation notes, not sole accepted decision evidence.",
                    )
                )

    marker_re = re.compile(r"^\s*-?\s*(ASSUMPTION_AS_FACT|ACCEPTED_FACT_FROM_ASSUMPTION):\s*(yes|true)\s*$", re.I | re.M)
    for section in document.sections.values():
        if marker_re.search(section.body):
            findings.append(
                DesignFinding(
                    "DRF-002",
                    "error",
                    "Design marks an assumption as accepted fact",
                    f"Section ## {section.title} contains an assumption-as-fact marker.",
                    relpath,
                    section.normalized_title,
                    "Promote blocking assumptions to GAPs or research dependencies, or provide source-backed evidence.",
                )
            )
    return findings


def _check_owner_decision_markers(document: MarkdownDocument, relpath: str) -> list[DesignFinding]:
    needs_owner = re.search(
        r"\b(owner input required|owner decision required|OWNER_DECISION_REQUIRED:\s*yes|scope approval required)\b",
        document.text,
        re.IGNORECASE,
    )
    if not needs_owner:
        return []
    gap_section = document.sections.get("GAP_REGISTER_UPDATES")
    entries = _entries(gap_section, "GAP_ID") if gap_section else []
    has_owner_gap = any(
        not is_none(entry.get("QUESTION_TO_OWNER"))
        and not is_none(entry.get("RECOMMENDED_OPTIONS"))
        and entry.get("STATUS", "").lower() in {"new", "update", "open"}
        for entry in entries
    )
    if has_owner_gap:
        return []
    return [
        DesignFinding(
            "DRF-007",
            "error",
            "Owner decision marker is missing",
            "The design says owner input or approval is required but GAP_REGISTER_UPDATES has no owner-facing GAP entry.",
            relpath,
            "GAP_REGISTER_UPDATES",
            "Add a GAP with question, options, recommendation, target register, and blocking status.",
        )
    ]


def _check_downstream_tasks(document: MarkdownDocument, relpath: str) -> list[DesignFinding]:
    section = document.sections.get("DISPATCHABLE_TASK_PACKETS")
    if section is None:
        return []
    findings: list[DesignFinding] = []
    entries = _entries(section, "ARTIFACT_REF")
    if not entries:
        return [
            DesignFinding(
                "DRF-003",
                "error",
                "Downstream task artifacts are missing acceptance evidence",
                "DISPATCHABLE_TASK_PACKETS has no ARTIFACT_REF entries.",
                relpath,
                section.normalized_title,
                "List each downstream task-like artifact with acceptance summary and validation status.",
            )
        ]

    for entry in entries:
        artifact = entry.get("ARTIFACT_REF", "UNKNOWN")
        classification = entry.get("CLASSIFICATION", "")
        if classification in {"task_packet", "task_proposal", "research_dependency", "design_continuation"}:
            if is_none(entry.get("ACCEPTANCE_SUMMARY")):
                findings.append(
                    DesignFinding(
                        "DRF-003",
                        "error",
                        "Task-like artifact lacks acceptance criteria",
                        f"{artifact} has no substantive ACCEPTANCE_SUMMARY.",
                        relpath,
                        section.normalized_title,
                        "Give every downstream task-like artifact task-specific acceptance criteria.",
                    )
                )
        if _is_oversized_task(entry):
            findings.append(
                DesignFinding(
                    "DRF-004",
                    "error",
                    "Task-like artifact has oversized scope",
                    f"{artifact} combines lifecycle ownership or broad file authority.",
                    relpath,
                    section.normalized_title,
                    "Split implementation, audit, testing, documentation, setup, launch, and release work into bounded tasks with narrow file authority.",
                )
            )
    return findings


def _check_dependencies_and_gates(document: MarkdownDocument, relpath: str) -> list[DesignFinding]:
    findings: list[DesignFinding] = []
    for section_name, start_key in (("TASK_DAG", "NODE_ID"), ("DISPATCHABLE_TASK_PACKETS", "ARTIFACT_REF")):
        section = document.sections.get(section_name)
        if section is None:
            continue
        for entry in _entries(section, start_key):
            ref = entry.get(start_key, "UNKNOWN")
            dependencies = entry.get("DEPENDENCIES", entry.get("DEPENDS_ON", ""))
            if _has_unresolved_dependency(dependencies):
                findings.append(
                    DesignFinding(
                        "DRF-006",
                        "error",
                        "Dependency is unresolved",
                        f"{ref} lists unresolved dependency text: {dependencies or 'MISSING'}.",
                        relpath,
                        section.normalized_title,
                        "Use resolved source references, upstream task refs, GAP_ID, research dependency refs, or explicit non-blocking rationale.",
                    )
                )
            dispatchable = entry.get("DISPATCH_STATUS", "").lower() == "dispatchable"
            role = entry.get("ROLE", entry.get("TARGET_ROLE", "")).lower()
            if dispatchable and _is_implementation_dependent(role, entry) and not _has_design_gate(entry.get("GATE_REQUIRED", "")):
                findings.append(
                    DesignFinding(
                        "DRF-009",
                        "error",
                        "Implementation work is dispatchable before design gate",
                        f"{ref} is dispatchable but GATE_REQUIRED={entry.get('GATE_REQUIRED', 'MISSING') or 'MISSING'}.",
                        relpath,
                        section.normalized_title,
                        "Require design_audit_pass, design_audit_pass_then_checkpoint, or accepted_design_artifact before implementation-dependent dispatch.",
                    )
                )
    return findings


def _check_testing_strategy(document: MarkdownDocument, relpath: str) -> list[DesignFinding]:
    section = document.sections.get("TESTING_STRATEGY")
    if section is None:
        return []
    missing = [field for field in TESTING_FIELDS if not has_non_none_field(section, field)]
    if missing:
        return [
            DesignFinding(
                "DRF-005",
                "error",
                "Testing strategy is incomplete",
                f"TESTING_STRATEGY is missing substantive fields: {', '.join(missing)}.",
                relpath,
                section.normalized_title,
                "Map MVP acceptance, high-risk decisions, downstream implementation checks, and required evidence to concrete verification.",
            )
        ]
    return []


def _check_product_capability(document: MarkdownDocument, relpath: str) -> list[DesignFinding]:
    fields = _document_fields(document)
    missing = [field for field in CAPABILITY_FIELDS if is_none(fields.get(field))]
    level = fields.get("PRODUCT_CAPABILITY_LEVEL", "").strip().lower()
    if missing or level not in ALLOWED_CAPABILITY_LEVELS:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if level and level not in ALLOWED_CAPABILITY_LEVELS:
            details.append(f"invalid PRODUCT_CAPABILITY_LEVEL={level}")
        return [
            DesignFinding(
                "DRF-008",
                "error",
                "Product capability level is unclear",
                "; ".join(details) or "product capability fields are incomplete",
                relpath,
                "PRODUCT_CAPABILITY_LEVEL",
                "Declare PRODUCT_CAPABILITY_LEVEL, CAPABILITY_SCOPE, CAPABILITY_ACCEPTANCE_REF, and CAPABILITY_SOURCE_REF.",
            )
        ]
    return []


def _result(findings: list[DesignFinding], relpath: str, strict: bool, *, section_count: int) -> DesignValidationResult:
    summary = {
        "errors": sum(1 for finding in findings if finding.severity == "error"),
        "warnings": sum(1 for finding in findings if finding.severity == "warning"),
        "info": sum(1 for finding in findings if finding.severity == "info"),
    }
    failed = summary["errors"] > 0 or (strict and summary["warnings"] > 0)
    status = "failed" if failed else ("warning" if summary["warnings"] else "passed")
    exit_code = 1 if failed else 0
    score = _rubric_score(findings)
    return DesignValidationResult(
        status=status,
        exit_code=exit_code,
        findings=findings,
        summary=summary,
        score=score,
        document={
            "path": relpath,
            "section_count": section_count,
            "required_sections": list(REQUIRED_SECTIONS),
        },
    )


def _rubric_score(findings: list[DesignFinding]) -> int:
    if any(finding.rule_id.startswith("DRF-") for finding in findings):
        return 0
    penalties = {
        "DESIGN_CONTRACT_001": 15,
        "DESIGN_CONTRACT_002": 15,
        "DESIGN_TRACE_001": 15,
        "DESIGN_TRACE_002": 15,
    }
    score = 100
    for rule_id in {finding.rule_id for finding in findings}:
        score -= penalties.get(rule_id, 5)
    return max(0, score)


def _entries(section: MarkdownSection | None, start_key: str) -> list[dict[str, str]]:
    if section is None:
        return []
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for key, value in all_field_values(section):
        if key == start_key:
            if current is not None:
                entries.append(current)
            current = {key: value}
        elif current is not None:
            current[key] = value
    if current is not None:
        entries.append(current)
    return entries


def _document_fields(document: MarkdownDocument) -> dict[str, str]:
    fields: dict[str, str] = {}
    for section in document.sections.values():
        for key, value in all_field_values(section):
            fields.setdefault(key, value)
    return fields


def _has_allowed_source(source_refs: str) -> bool:
    refs = _split_refs(source_refs)
    if not refs:
        return False
    return any(not _source_ref_forbidden(ref) for ref in refs)


def _source_is_only_assumption(source_refs: str) -> bool:
    refs = _split_refs(source_refs)
    return bool(refs) and all(ref.upper().startswith("ASSUMPTION") for ref in refs)


def _source_ref_forbidden(ref: str) -> bool:
    normalized = ref.strip().strip("`").upper()
    if is_none(normalized):
        return True
    return normalized.startswith(SOURCE_ONLY_FORBIDDEN_PREFIXES)


def _split_refs(value: str) -> list[str]:
    if is_none(value):
        return []
    return [
        chunk.strip().strip("`")
        for chunk in re.split(r"[,;\s]+", value)
        if chunk.strip().strip("`") and not is_none(chunk.strip().strip("`"))
    ]


def _affirmative(value: str | None) -> bool:
    return (value or "").strip().lower() in {"yes", "true", "accepted", "fact"}


def _is_oversized_task(entry: dict[str, str]) -> bool:
    allowed_changes = entry.get("ALLOWED_FILE_CHANGES", "")
    normalized_changes = {item.lower() for item in _split_refs(allowed_changes)}
    if normalized_changes.intersection(REPOSITORY_WIDE_AUTHORITY):
        return True

    role_text = " ".join(
        entry.get(field, "")
        for field in ("TARGET_ROLE", "ROLE", "RESPONSIBLE_ROLES", "ACCEPTANCE_SUMMARY", "SCOPE_SUMMARY")
    ).lower()
    roles_found = {term for term in LIFECYCLE_ROLE_TERMS if term in role_text}
    if len(roles_found.intersection({"implementation", "testing", "documentation", "setup", "launch", "release"})) > 1:
        return True
    if len(roles_found.intersection({"developer", "auditor", "tester", "technical_writer", "devops_setup_engineer", "release_manager"})) > 1:
        return True
    return False


def _has_unresolved_dependency(value: str) -> bool:
    if is_none(value):
        return False
    normalized = value.strip().upper()
    if normalized in {"NONE", "NO_DEPENDENCIES"}:
        return False
    return any(marker in normalized for marker in UNKNOWN_DEPENDENCY_MARKERS)


def _is_implementation_dependent(role: str, entry: dict[str, str]) -> bool:
    role = role.strip().lower()
    if role in {"developer", "tester", "technical_writer", "devops_setup_engineer", "release_manager"}:
        return True
    task_kind = entry.get("TASK_KIND", "").lower()
    return task_kind in {"normal", "testing", "setup", "launch", "handover"} and entry.get("CLASSIFICATION") == "task_packet"


def _has_design_gate(value: str) -> bool:
    normalized = value.strip().lower()
    return any(marker in normalized for marker in DESIGN_GATE_MARKERS)


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
