"""Design gap, owner question, answer, and stage gate validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_FAILED = 1

QUESTION_STATUSES_FLOW = {
    "draft",
    "audit_pending",
    "ready_for_owner",
    "presented",
    "answered",
    "integrated",
    "superseded",
    "blocked",
}
LEGACY_QUESTION_STATUS_ALIASES = {
    "ready_for_audit": "audit_pending",
    "presented_to_owner": "presented",
    "closed": "integrated",
    "audit_failed": "blocked",
}
QUESTION_STATUSES_SUPPORTED = QUESTION_STATUSES_FLOW | set(LEGACY_QUESTION_STATUS_ALIASES)
QUESTION_STATUSES_AUDIT_REQUIRED = {"ready_for_owner", "presented", "presented_to_owner"}
DOCUMENT_STATUSES = {"draft", "ready_for_audit", "accepted", "superseded"}
GAP_TYPES = {
    "functionality",
    "functional_workflow",
    "user_workflow",
    "user_roles",
    "business_rules",
    "interface_behavior",
    "information_visualization",
    "reports_exports",
    "notifications",
    "approval_behavior",
    "operational_constraints",
    "content_text",
    "priority_scope",
    "acceptance_expectations",
    "source_conflict",
    "missing_source",
    "out_of_scope",
    "other_product_gap",
}
BLOCKING_TYPES = {"blocking_now", "deferred_until_stage", "non_blocking_assumption", "optional"}
GAP_STATUSES = {
    "open",
    "question_needed",
    "question_drafted",
    "question_ready",
    "waiting_for_owner",
    "answered",
    "assumption_active",
    "deferred",
    "closed",
    "superseded",
}
TECHNICAL_TERMS_RE = re.compile(
    r"(^|[^A-Za-z0-9])("
    r"fastapi|django|postgres(?:ql)?|sqlite|webhooks?|polling|rbac|celery|"
    r"apscheduler|orm|rest[ -]?api|api|database|framework|queue|worker|"
    r"scheduler|deployment|hosting"
    r")([^A-Za-z0-9]|$)",
    re.IGNORECASE,
)
ID_PATTERNS = {
    "gap_id": re.compile(r"^GAP-[A-Za-z0-9._-]+$"),
    "question_id": re.compile(r"^Q-[A-Za-z0-9._-]+$"),
    "answer_record_id": re.compile(r"^ANS-[A-Za-z0-9._-]+$"),
}
STAGES = [
    "intake",
    "requirements",
    "design",
    "ux_design",
    "architecture",
    "implementation",
    "testing",
    "setup",
    "run",
    "launch",
    "documentation",
    "handover",
    "final_acceptance",
    "terminal",
]
STAGE_INDEX = {stage: index for index, stage in enumerate(STAGES)}
QUESTION_DIRS = (
    "project-docs/design/questions",
    "project-docs/questions",
    "project-runtime/design/questions",
)
GAP_REGISTER_PATHS = (
    "project-docs/design/gap_register.json",
    "project-docs/gap_register.json",
    "project-runtime/design/gap_register.json",
)
GAP_REGISTER_DIRS = (
    "project-docs/design/gap_registers",
    "project-runtime/design/gap_registers",
)
ANSWER_DIRS = (
    "project-runtime/owner-decisions",
    "project-runtime/design/owner-decisions",
)


@dataclass(frozen=True)
class GovernanceFinding:
    rule_id: str
    severity: str
    title: str
    message: str
    path: str
    artifact_id: str
    recommendation: str

    def to_json(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "details": self.message,
            "path": self.path,
            "artifact_id": self.artifact_id,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class Artifact:
    root: Path
    path: Path
    relpath: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class GovernanceResult:
    status: str
    exit_code: int
    findings: list[GovernanceFinding]
    summary: dict[str, int]
    gap_registers: list[Artifact]
    questions: list[Artifact]
    answers: list[Artifact]


def validate_design_governance(root: Path, *, strict: bool) -> GovernanceResult:
    gap_registers, questions, answers, findings = load_design_artifacts(root)
    question_by_id = _index_by_id(questions, "question_id", findings)
    gap_by_id = _index_gaps(gap_registers, findings)
    answer_by_question, answer_by_id = _answer_indexes(answers, findings)

    if not gap_registers:
        findings.append(_finding("DG4_GAP_001", "error", "Gap register is missing", "No gap register JSON artifact was found.", root, "NONE", "Add a project designer-authored gap_register.json."))
    if not questions:
        findings.append(_finding("DG4_QUESTION_001", "error", "Owner question cards are missing", "No owner question card JSON artifacts were found.", root, "NONE", "Add audited owner question cards authored by the project designer."))

    for artifact in gap_registers:
        findings.extend(_validate_gap_register_shape(artifact))
        for gap in _gaps(artifact):
            gap_id = str(gap.get("gap_id", "UNKNOWN"))
            question_id = str(gap.get("question_card_id", "NONE"))
            if gap.get("owner_input_required") is True:
                if question_id == "NONE":
                    findings.append(_artifact_finding("DG4_LINK_001", "error", "Owner-input gap has no question card", f"{gap_id} requires owner input but question_card_id is NONE.", artifact, gap_id, "Link the gap to an audited owner question card."))
                elif question_id not in question_by_id:
                    findings.append(_artifact_finding("DG4_LINK_002", "error", "Gap links to unknown question", f"{gap_id} links to missing question_card_id {question_id}.", artifact, gap_id, "Create or restore the linked question card artifact."))
            answer_id = str(gap.get("owner_answer_record_id", "NONE"))
            if answer_id != "NONE":
                answer = answer_by_id.get(answer_id)
                if answer is None:
                    findings.append(_artifact_finding("DG4_ANSWER_005", "error", "Gap links to unknown owner answer", f"{gap_id} references missing owner_answer_record_id {answer_id}.", artifact, gap_id, "Link only to an existing owner answer record artifact."))
                elif str(answer.payload.get("question_id", "NONE")) != question_id or str(answer.payload.get("gap_id", "NONE")) != gap_id:
                    findings.append(_artifact_finding("DG4_ANSWER_006", "error", "Gap owner answer linkage is invalid", f"{gap_id} references {answer_id}, but the answer does not match both question_id {question_id} and gap_id {gap_id}.", artifact, gap_id, "Record answer linkage with matching gap_id and question_id."))
            if _missing_stage(gap.get("blocking_stage")) or _missing_stage(gap.get("can_continue_until")):
                findings.append(_artifact_finding("DG4_GAP_002", "error", "Gap blocking stage is incomplete", f"{gap_id} must define blocking_stage and can_continue_until.", artifact, gap_id, "Declare when this gap blocks stage progression."))

    for artifact in questions:
        findings.extend(_validate_question_shape(artifact))
        question_id = str(artifact.payload.get("question_id", "UNKNOWN"))
        gap_id = str(artifact.payload.get("gap_id", "NONE"))
        if gap_id not in gap_by_id:
            findings.append(_artifact_finding("DG4_LINK_003", "error", "Question links to unknown gap", f"{question_id} links to missing gap_id {gap_id}.", artifact, question_id, "Link every question to an existing gap record."))
        elif str(gap_by_id[gap_id].get("question_card_id", "NONE")) not in {question_id, "NONE"}:
            findings.append(_artifact_finding("DG4_LINK_004", "error", "Gap/question linkage is inconsistent", f"{question_id} links to {gap_id}, but the gap references {gap_by_id[gap_id].get('question_card_id')}.", artifact, question_id, "Make the gap and question card reference each other."))
        answer = answer_by_question.get(question_id)
        if answer is not None:
            answer_gap = str(answer.payload.get("gap_id", "NONE"))
            if answer_gap != gap_id:
                findings.append(_artifact_finding("DG4_ANSWER_002", "error", "Owner decision gap linkage is invalid", f"Answer for {question_id} links to {answer_gap}, expected {gap_id}.", answer, question_id, "Record owner answers with both the matching question_id and gap_id."))

    for answer in answers:
        question_id = str(answer.payload.get("question_id", "UNKNOWN"))
        if question_id not in question_by_id:
            findings.append(_artifact_finding("DG4_ANSWER_004", "error", "Owner answer references unknown question", f"Answer {answer.payload.get('answer_record_id', 'UNKNOWN')} references missing question_id {question_id}.", answer, question_id, "Record owner answers only for existing owner question cards."))

    findings.extend(_validate_design_intake_completion(root))
    findings.extend(_validate_one_question_at_a_time(questions))
    findings = _sorted_findings(findings)
    return _result(findings, strict, gap_registers, questions, answers)


def verify_stage_gate(root: Path, *, stage: str, strict: bool) -> tuple[GovernanceResult, list[dict[str, str]]]:
    result = validate_design_governance(root, strict=strict)
    target_stage = _normalize_stage(stage)
    blocked: list[dict[str, str]] = []
    findings = list(result.findings)
    if target_stage not in STAGE_INDEX:
        findings.append(_finding("DG4_GATE_001", "error", "Unknown stage", f"Stage {stage} is not a known lifecycle stage.", root, "NONE", "Use a supported ASO stage name."))
        updated = _result(_sorted_findings(findings), strict, result.gap_registers, result.questions, result.answers)
        return updated, blocked

    answer_by_question, answer_by_id = _answer_indexes(result.answers, findings)
    for register in result.gap_registers:
        for gap in _gaps(register):
            gap_id = str(gap.get("gap_id", "UNKNOWN"))
            if not _gap_blocks_stage(gap, target_stage):
                continue
            question_id = str(gap.get("question_card_id", "NONE"))
            answered = _gap_has_valid_answer(gap, answer_by_question, answer_by_id)
            has_assumption = str(gap.get("assumption_id", "NONE")) != "NONE" and gap.get("blocking_type") == "non_blocking_assumption"
            if gap.get("owner_input_required") is True and not answered and not has_assumption:
                blocked.append(
                    {
                        "gap_id": gap_id,
                        "question_id": question_id,
                        "blocking_stage": str(gap.get("blocking_stage", "UNKNOWN")),
                        "can_continue_until": str(gap.get("can_continue_until", "UNKNOWN")),
                    }
                )
                findings.append(_artifact_finding("DG4_GATE_002", "error", "Stage gate blocked by unanswered gap", f"{gap_id} blocks crossing into {target_stage} until {question_id} is answered.", register, gap_id, "Resolve the owner question or record an accepted owner-visible assumption before crossing this stage."))
    updated = _result(_sorted_findings(findings), strict, result.gap_registers, result.questions, result.answers)
    return updated, blocked


def next_owner_question(root: Path) -> tuple[GovernanceResult, Artifact | None]:
    result = validate_design_governance(root, strict=True)
    if result.exit_code != EXIT_OK:
        return result, None
    active = _active_questions(result.questions)
    if active:
        ids = ", ".join(str(item.payload.get("question_id", "UNKNOWN")) for item in active)
        findings = list(result.findings)
        findings.append(GovernanceFinding("DG4_ROUTING_003", "error", "Owner question is already presented", f"No next question can be selected while a question is current/presented: {ids}.", ", ".join(item.relpath for item in active), ids, "Record or resolve the active presented question before routing another one."))
        updated = _result(_sorted_findings(findings), True, result.gap_registers, result.questions, result.answers)
        return updated, None
    candidates = [
        item
        for item in result.questions
        if str(item.payload.get("status", "")).lower() == "ready_for_owner"
        and _audit_passed(item)
        and str(item.payload.get("question_id")) not in {str(answer.payload.get("question_id")) for answer in result.answers}
    ]
    candidates.sort(key=lambda item: (int(_routing(item).get("queue_position", 999999)), str(item.payload.get("question_id", ""))))
    return result, candidates[0] if candidates else None


def load_design_artifacts(root: Path) -> tuple[list[Artifact], list[Artifact], list[Artifact], list[GovernanceFinding]]:
    findings: list[GovernanceFinding] = []
    gap_registers = _load_known_json(root, GAP_REGISTER_PATHS, GAP_REGISTER_DIRS, findings, "DG4_IO_GAP")
    questions = _load_known_json(root, (), QUESTION_DIRS, findings, "DG4_IO_QUESTION")
    answers = _load_known_json(root, (), ANSWER_DIRS, findings, "DG4_IO_ANSWER")
    return gap_registers, questions, answers, findings


def _load_known_json(root: Path, files: tuple[str, ...], dirs: tuple[str, ...], findings: list[GovernanceFinding], rule_prefix: str) -> list[Artifact]:
    artifacts: list[Artifact] = []
    seen: set[Path] = set()
    for relpath in files:
        path = root / relpath
        if path.exists():
            _load_one(root, path, artifacts, findings, rule_prefix, seen)
    for relpath in dirs:
        path = root / relpath
        if path.is_dir():
            for child in sorted(path.glob("*.json")):
                _load_one(root, child, artifacts, findings, rule_prefix, seen)
    return artifacts


def _load_one(root: Path, path: Path, artifacts: list[Artifact], findings: list[GovernanceFinding], rule_prefix: str, seen: set[Path]) -> None:
    resolved = path.resolve(strict=False)
    if resolved in seen:
        return
    seen.add(resolved)
    relpath = _rel(root, path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(GovernanceFinding(f"{rule_prefix}_001", "error", "JSON artifact is unreadable", f"{relpath}: {exc}", relpath, "UNKNOWN", "Provide valid UTF-8 JSON artifacts."))
        return
    if not isinstance(payload, dict):
        findings.append(GovernanceFinding(f"{rule_prefix}_002", "error", "JSON artifact is not an object", f"{relpath} must contain a JSON object.", relpath, "UNKNOWN", "Use the DG4 object schema for this artifact."))
        return
    artifacts.append(Artifact(root, path, relpath, payload))


def _validate_gap_register_shape(artifact: Artifact) -> list[GovernanceFinding]:
    payload = artifact.payload
    findings: list[GovernanceFinding] = []
    for field in ("schema_version", "project_id", "document_id", "status", "source_refs", "gaps"):
        if field not in payload:
            findings.append(_artifact_finding("DG4_SCHEMA_GAP_001", "error", "Gap register required field is missing", f"{artifact.relpath} is missing {field}.", artifact, str(payload.get("document_id", "UNKNOWN")), "Conform to gap_register.schema.json."))
    if payload.get("schema_version") != "1.0.0":
        findings.append(_artifact_finding("DG4_SCHEMA_GAP_002", "error", "Gap register schema version is invalid", "schema_version must be 1.0.0.", artifact, str(payload.get("document_id", "UNKNOWN")), "Use the current DG4 gap register schema."))
    if not isinstance(payload.get("source_refs"), list) or not payload.get("source_refs"):
        findings.append(_artifact_finding("DG4_SCHEMA_GAP_003", "error", "Gap register source refs are missing", "source_refs must be a non-empty list.", artifact, str(payload.get("document_id", "UNKNOWN")), "Link the gap register to source evidence."))
    if str(payload.get("status", "")).lower() not in DOCUMENT_STATUSES:
        findings.append(_artifact_finding("DG4_SCHEMA_GAP_007", "error", "Gap register status is unsupported", f"{artifact.relpath} status must match gap_register.schema.json.", artifact, str(payload.get("document_id", "UNKNOWN")), "Use a supported gap register document status."))
    if not isinstance(payload.get("gaps"), list) or not payload.get("gaps"):
        findings.append(_artifact_finding("DG4_SCHEMA_GAP_004", "error", "Gap records are missing", "gaps must be a non-empty array.", artifact, str(payload.get("document_id", "UNKNOWN")), "Record at least one explicit gap or provide a no-gap artifact outside this command."))
    for gap in _gaps(artifact):
        gap_id = str(gap.get("gap_id", "UNKNOWN"))
        for field in ("gap_id", "description", "source_ref", "gap_type", "user_impact", "blocking_type", "blocking_stage", "can_continue_until", "owner_input_required", "question_card_id", "assumption_id", "status"):
            if field not in gap:
                findings.append(_artifact_finding("DG4_SCHEMA_GAP_005", "error", "Gap required field is missing", f"{gap_id} is missing {field}.", artifact, gap_id, "Complete the gap record shape."))
        if not ID_PATTERNS["gap_id"].match(gap_id):
            findings.append(_artifact_finding("DG4_SCHEMA_GAP_006", "error", "Gap id is invalid", f"{gap_id} must match GAP-*.", artifact, gap_id, "Use a stable GAP-* id."))
        gap_type = str(gap.get("gap_type", "")).lower()
        blocking_type = str(gap.get("blocking_type", "")).lower()
        blocking_stage = str(gap.get("blocking_stage", "")).lower()
        can_continue_until = str(gap.get("can_continue_until", "")).lower()
        status = str(gap.get("status", "")).lower()
        if gap_type not in GAP_TYPES:
            findings.append(_artifact_finding("DG4_SCHEMA_GAP_008", "error", "Gap type is unsupported", f"{gap_id} uses unsupported gap_type {gap_type or 'MISSING'}.", artifact, gap_id, "Use a gap_type from gap_register.schema.json."))
        if blocking_type not in BLOCKING_TYPES:
            findings.append(_artifact_finding("DG4_SCHEMA_GAP_009", "error", "Gap blocking type is unsupported", f"{gap_id} uses unsupported blocking_type {blocking_type or 'MISSING'}.", artifact, gap_id, "Use a blocking_type from gap_register.schema.json so gates cannot infer permissive behavior."))
        if blocking_stage not in STAGE_INDEX and blocking_stage != "not_applicable":
            findings.append(_artifact_finding("DG4_SCHEMA_GAP_010", "error", "Gap blocking stage is unsupported", f"{gap_id} uses unsupported blocking_stage {blocking_stage or 'MISSING'}.", artifact, gap_id, "Use a lifecycle stage from gap_register.schema.json."))
        if can_continue_until not in STAGE_INDEX and can_continue_until != "not_applicable":
            findings.append(_artifact_finding("DG4_SCHEMA_GAP_011", "error", "Gap continuation stage is unsupported", f"{gap_id} uses unsupported can_continue_until {can_continue_until or 'MISSING'}.", artifact, gap_id, "Use a lifecycle stage from gap_register.schema.json."))
        if status not in GAP_STATUSES:
            findings.append(_artifact_finding("DG4_SCHEMA_GAP_012", "error", "Gap status is unsupported", f"{gap_id} uses unsupported status {status or 'MISSING'}.", artifact, gap_id, "Use a gap status from gap_register.schema.json."))
        if blocking_type in {"blocking_now", "deferred_until_stage"} and _missing_stage(blocking_stage):
            findings.append(_artifact_finding("DG4_SCHEMA_GAP_013", "error", "Blocking gap uses non-stage blocker", f"{gap_id} must use a named blocking_stage for {blocking_type}.", artifact, gap_id, "Use a concrete lifecycle stage for blocking gaps."))
        if blocking_type == "deferred_until_stage" and _missing_stage(can_continue_until):
            findings.append(_artifact_finding("DG4_SCHEMA_GAP_014", "error", "Deferred gap uses non-stage continuation", f"{gap_id} must use a named can_continue_until for deferred_until_stage.", artifact, gap_id, "Use a concrete lifecycle stage for deferred gaps."))
    return findings


def _validate_question_shape(artifact: Artifact) -> list[GovernanceFinding]:
    payload = artifact.payload
    findings: list[GovernanceFinding] = []
    question_id = str(payload.get("question_id", "UNKNOWN"))
    for field in ("schema_version", "question_id", "gap_id", "question", "why_it_matters", "question_category", "options", "recommended_option", "recommendation_reason", "blocking_stage", "can_continue_until", "owner_impact", "routing", "status", "audit_ref"):
        if field not in payload:
            findings.append(_artifact_finding("DG4_SCHEMA_QUESTION_001", "error", "Question required field is missing", f"{question_id} is missing {field}.", artifact, question_id, "Conform to owner_question_card.schema.json."))
    if payload.get("schema_version") != "1.0.0":
        findings.append(_artifact_finding("DG4_SCHEMA_QUESTION_002", "error", "Question schema version is invalid", "schema_version must be 1.0.0.", artifact, question_id, "Use the current DG4 owner question schema."))
    if not ID_PATTERNS["question_id"].match(question_id):
        findings.append(_artifact_finding("DG4_SCHEMA_QUESTION_003", "error", "Question id is invalid", f"{question_id} must match Q-*.", artifact, question_id, "Use a stable Q-* id."))
    options = payload.get("options")
    if not isinstance(options, list) or len(options) < 2:
        findings.append(_artifact_finding("DG4_QUESTION_002", "error", "Question options are incomplete", f"{question_id} must have at least two options.", artifact, question_id, "Provide owner-facing options."))
    else:
        option_ids: set[str] = set()
        for option in options:
            if isinstance(option, dict):
                option_id = str(option.get("id", ""))
                option_ids.add(option_id)
                for field in ("id", "label", "owner_effect"):
                    if not str(option.get(field, "")).strip():
                        findings.append(_artifact_finding("DG4_QUESTION_003", "error", "Question option is incomplete", f"{question_id} has an option missing {field}.", artifact, question_id, "Complete each option id, label, and owner_effect."))
        recommended = str(payload.get("recommended_option", "")).strip()
        if not recommended:
            findings.append(_artifact_finding("DG4_QUESTION_004", "error", "Recommended option is missing", f"{question_id} has no recommended_option.", artifact, question_id, "Include the project designer's recommended option."))
        elif recommended not in option_ids and recommended not in {str(option.get("label", "")).strip() for option in options if isinstance(option, dict)}:
            findings.append(_artifact_finding("DG4_QUESTION_005", "error", "Recommended option does not match options", f"{question_id} recommends {recommended}, which is not an option id or label.", artifact, question_id, "Set recommended_option to an option id or exact label."))
    if not str(payload.get("recommendation_reason", "")).strip():
        findings.append(_artifact_finding("DG4_QUESTION_006", "error", "Recommendation reason is missing", f"{question_id} has no recommendation_reason.", artifact, question_id, "Explain the recommendation in plain language."))
    if _missing_stage(payload.get("blocking_stage")) or _missing_stage(payload.get("can_continue_until")):
        findings.append(_artifact_finding("DG4_QUESTION_007", "error", "Question blocking stage is incomplete", f"{question_id} must define blocking_stage and can_continue_until.", artifact, question_id, "Declare when the linked gap blocks progression."))
    for field in ("question", "why_it_matters", "recommended_option", "recommendation_reason", "owner_impact"):
        if TECHNICAL_TERMS_RE.search(str(payload.get(field, ""))):
            findings.append(_artifact_finding("DG4_QUESTION_008", "error", "Question contains technical implementation language", f"{question_id} field {field} contains forbidden engineering terminology.", artifact, question_id, "Rewrite as a non-technical product, workflow, UX, or business decision."))
    for option in options if isinstance(options, list) else []:
        if isinstance(option, dict) and TECHNICAL_TERMS_RE.search(" ".join(str(option.get(field, "")) for field in ("label", "owner_effect"))):
            findings.append(_artifact_finding("DG4_QUESTION_008", "error", "Question contains technical implementation language", f"{question_id} option {option.get('id', 'UNKNOWN')} contains forbidden engineering terminology.", artifact, question_id, "Rewrite option text in owner-facing language."))
    status = _question_status(artifact)
    if status not in QUESTION_STATUSES_SUPPORTED:
        findings.append(_artifact_finding("DG4_STATUS_001", "error", "Question status is unsupported", f"{question_id} uses unsupported status {status or 'MISSING'}.", artifact, question_id, "Use draft, audit_pending, ready_for_owner, presented, answered, integrated, superseded, or blocked; legacy aliases are accepted only where documented."))
    if status in QUESTION_STATUSES_AUDIT_REQUIRED and not _audit_passed(artifact):
        findings.append(_artifact_finding("DG4_AUDIT_001", "error", "Question is ready without audit pass evidence", f"{question_id} is ready/presented but lacks audit.status=passed and project-runtime/audits/*_PASS.md evidence.", artifact, question_id, "Route only auditor-approved question cards."))
    if status == "presented_to_owner" and not _has_presentation_evidence(artifact):
        findings.append(_artifact_finding("DG4_STATUS_002", "error", "Legacy presented question lacks presentation evidence", f"{question_id} uses legacy status presented_to_owner without routing.presentation_state current or presented.", artifact, question_id, "Use corrected status presented or preserve explicit presentation routing evidence for legacy cards."))
    if status == "closed" and not _has_integrated_evidence(artifact):
        findings.append(_artifact_finding("DG4_STATUS_003", "error", "Legacy closed question lacks integration evidence", f"{question_id} uses legacy status closed without accepted source-of-truth evidence.", artifact, question_id, "Use integrated only after accepted source-of-truth evidence is recorded, or keep the card answered."))
    routing = _routing(artifact)
    if routing.get("routing_mode") != "one_question_at_a_time":
        findings.append(_artifact_finding("DG4_ROUTING_001", "error", "Question routing mode is invalid", f"{question_id} must use one_question_at_a_time routing.", artifact, question_id, "Do not bulk-present owner questions."))
    return findings


def _validate_one_question_at_a_time(questions: list[Artifact]) -> list[GovernanceFinding]:
    active = _active_questions(questions)
    if len(active) <= 1:
        return []
    ids = ", ".join(str(item.payload.get("question_id", "UNKNOWN")) for item in active)
    return [GovernanceFinding("DG4_ROUTING_002", "error", "Multiple owner questions are active", f"Only one owner question may be current/presented; active questions: {ids}.", ", ".join(item.relpath for item in active), ids, "Present one audited owner question at a time.")]


def _active_questions(questions: list[Artifact]) -> list[Artifact]:
    return [
        item
        for item in questions
        if _canonical_question_status(item) == "presented"
        or _presentation_state(item) in {"current", "presented"}
    ]


def _validate_design_intake_completion(root: Path) -> list[GovernanceFinding]:
    intake_path = root / "project-docs" / "design" / "design_intake.json"
    if not intake_path.exists():
        return []
    try:
        payload = json.loads(intake_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [GovernanceFinding("DG4_INTAKE_001", "error", "Design intake marker is unreadable", f"{_rel(root, intake_path)}: {exc}", _rel(root, intake_path), "design_intake", "Provide valid design intake JSON or remove the completion marker.")]
    if not isinstance(payload, dict):
        return [GovernanceFinding("DG4_INTAKE_001", "error", "Design intake marker is invalid", f"{_rel(root, intake_path)} must contain a JSON object.", _rel(root, intake_path), "design_intake", "Provide valid design intake JSON.")]
    complete = payload.get("design_intake_complete") is True or str(payload.get("status", "")).lower() == "complete"
    if not complete:
        return []
    findings: list[GovernanceFinding] = []
    required = {
        "project_type_decision": root / "project-docs" / "design" / "project_type_decision.json",
        "template_selection": root / "project-docs" / "design" / "template_selection.json",
    }
    for label, path in required.items():
        ref_value = str(payload.get(f"{label}_ref", "")).strip()
        if not ref_value and not path.exists():
            findings.append(GovernanceFinding("DG4_INTAKE_002", "error", "Completed design intake is missing required record", f"design_intake is complete but {label} is missing.", _rel(root, intake_path), label, "Record the project type decision and template selection before marking design intake complete."))
    return findings


def _answer_indexes(answers: list[Artifact], findings: list[GovernanceFinding]) -> tuple[dict[str, Artifact], dict[str, Artifact]]:
    by_question: dict[str, Artifact] = {}
    by_id: dict[str, Artifact] = {}
    for answer in answers:
        question_id = str(answer.payload.get("question_id", "UNKNOWN"))
        answer_id = str(answer.payload.get("answer_record_id", "UNKNOWN"))
        if not ID_PATTERNS["answer_record_id"].match(answer_id):
            findings.append(_artifact_finding("DG4_ANSWER_001", "error", "Owner answer id is invalid", f"{answer_id} must match ANS-*.", answer, answer_id, "Use a stable ANS-* id."))
        if not ID_PATTERNS["question_id"].match(question_id):
            findings.append(_artifact_finding("DG4_ANSWER_003", "error", "Owner answer references unknown question shape", f"{answer_id} has invalid question_id {question_id}.", answer, answer_id, "Record owner answers against an existing Q-* question."))
        if answer_id in by_id:
            findings.append(_artifact_finding("DG4_SCHEMA_DUPLICATE_ID", "error", "Owner answer id is duplicated", f"answer_record_id {answer_id} appears more than once.", answer, answer_id, "Keep one canonical owner answer record for each id."))
        if question_id in by_question:
            findings.append(_artifact_finding("DG4_SCHEMA_DUPLICATE_ID", "error", "Owner answer question is duplicated", f"question_id {question_id} has more than one owner answer record.", answer, answer_id, "Keep one canonical owner answer record for each question until superseded by an audited integration."))
        by_question[question_id] = answer
        by_id[answer_id] = answer
    return by_question, by_id


def _gap_has_valid_answer(gap: dict[str, Any], answer_by_question: dict[str, Artifact], answer_by_id: dict[str, Artifact]) -> bool:
    gap_id = str(gap.get("gap_id", "UNKNOWN"))
    question_id = str(gap.get("question_card_id", "NONE"))
    answer_id = str(gap.get("owner_answer_record_id", "NONE"))
    if answer_id != "NONE":
        answer = answer_by_id.get(answer_id)
        return answer is not None and str(answer.payload.get("question_id", "NONE")) == question_id and str(answer.payload.get("gap_id", "NONE")) == gap_id
    answer = answer_by_question.get(question_id)
    return answer is not None and str(answer.payload.get("gap_id", "NONE")) == gap_id


def _index_by_id(artifacts: list[Artifact], field: str, findings: list[GovernanceFinding]) -> dict[str, Artifact]:
    indexed: dict[str, Artifact] = {}
    for artifact in artifacts:
        value = str(artifact.payload.get(field, "UNKNOWN"))
        if value in indexed:
            findings.append(_artifact_finding("DG4_SCHEMA_DUPLICATE_ID", "error", "Artifact id is duplicated", f"{field} {value} appears more than once.", artifact, value, "Keep one canonical artifact for each id."))
        indexed[value] = artifact
    return indexed


def _index_gaps(registers: list[Artifact], findings: list[GovernanceFinding]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for register in registers:
        for gap in _gaps(register):
            gap_id = str(gap.get("gap_id", "UNKNOWN"))
            if gap_id in indexed:
                findings.append(_artifact_finding("DG4_SCHEMA_DUPLICATE_ID", "error", "Gap id is duplicated", f"{gap_id} appears more than once.", register, gap_id, "Keep one canonical gap record for each id."))
            indexed[gap_id] = gap
    return indexed


def _gaps(artifact: Artifact) -> list[dict[str, Any]]:
    gaps = artifact.payload.get("gaps")
    return [gap for gap in gaps if isinstance(gap, dict)] if isinstance(gaps, list) else []


def _routing(artifact: Artifact) -> dict[str, Any]:
    routing = artifact.payload.get("routing")
    return routing if isinstance(routing, dict) else {}


def _question_status(artifact: Artifact) -> str:
    return str(artifact.payload.get("status", "")).strip().lower()


def _canonical_question_status(artifact: Artifact) -> str:
    status = _question_status(artifact)
    return LEGACY_QUESTION_STATUS_ALIASES.get(status, status)


def _presentation_state(artifact: Artifact) -> str:
    return str(_routing(artifact).get("presentation_state", "")).strip().lower()


def question_accepts_owner_answer(artifact: Artifact) -> bool:
    status = _question_status(artifact)
    if status == "presented":
        return True
    return status == "presented_to_owner" and _has_presentation_evidence(artifact)


def _has_presentation_evidence(artifact: Artifact) -> bool:
    return _presentation_state(artifact) in {"current", "presented"}


def _has_integrated_evidence(artifact: Artifact) -> bool:
    for field in ("accepted_source_of_truth_update", "accepted_source_of_truth_ref", "integration_ref"):
        value = str(artifact.payload.get(field, "")).strip()
        if value and value.upper() not in {"NONE", "PENDING"}:
            return True
    return False


def _audit_passed(artifact: Artifact) -> bool:
    audit = artifact.payload.get("audit")
    audit_ref = str(artifact.payload.get("audit_ref", ""))
    if not isinstance(audit, dict):
        return False
    evidence_ref = str(audit.get("evidence_ref", ""))
    evidence_exists = (artifact.root / evidence_ref).exists()
    return (
        audit.get("status") == "passed"
        and evidence_ref.startswith("project-runtime/audits/AUDIT_")
        and evidence_ref.endswith("_PASS.md")
        and evidence_ref == audit_ref
        and evidence_exists
    )


def _missing_stage(value: object) -> bool:
    text = str(value or "").strip().lower()
    return not text or text in {"none", "not_applicable"}


def _normalize_stage(stage: str) -> str:
    return stage.strip().lower()


def _gap_blocks_stage(gap: dict[str, Any], target_stage: str) -> bool:
    blocking_type = str(gap.get("blocking_type", "")).lower()
    blocking_stage = str(gap.get("blocking_stage", "")).lower()
    if blocking_type == "blocking_now":
        return True
    if blocking_type != "deferred_until_stage":
        return False
    if blocking_stage not in STAGE_INDEX:
        return False
    return STAGE_INDEX[target_stage] >= STAGE_INDEX[blocking_stage]


def _result(findings: list[GovernanceFinding], strict: bool, gap_registers: list[Artifact], questions: list[Artifact], answers: list[Artifact]) -> GovernanceResult:
    errors = sum(1 for finding in findings if finding.severity == "error")
    warnings = sum(1 for finding in findings if finding.severity == "warning")
    failed = errors > 0 or (strict and warnings > 0)
    return GovernanceResult(
        status="failed" if failed else "passed",
        exit_code=EXIT_FAILED if failed else EXIT_OK,
        findings=findings,
        summary={"errors": errors, "warnings": warnings, "info": sum(1 for finding in findings if finding.severity == "info")},
        gap_registers=gap_registers,
        questions=questions,
        answers=answers,
    )


def _sorted_findings(findings: list[GovernanceFinding]) -> list[GovernanceFinding]:
    return sorted(findings, key=lambda item: (item.rule_id, item.path, item.artifact_id, item.message))


def _finding(rule_id: str, severity: str, title: str, message: str, root: Path, artifact_id: str, recommendation: str) -> GovernanceFinding:
    return GovernanceFinding(rule_id, severity, title, message, _rel(root, root), artifact_id, recommendation)


def _artifact_finding(rule_id: str, severity: str, title: str, message: str, artifact: Artifact, artifact_id: str, recommendation: str) -> GovernanceFinding:
    return GovernanceFinding(rule_id, severity, title, message, artifact.relpath, artifact_id, recommendation)


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()
