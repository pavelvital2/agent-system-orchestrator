"""DG4 design governance command group."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..rules import design_governance
from . import output_policy


EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_IO_ERROR = 3


def run_verify(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    result = design_governance.validate_design_governance(root, strict=args.strict)
    report = _base_report("design verify", root, args.strict, result)
    _print_report("ASO design verify", report)
    return result.exit_code


def run_questions_next(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    result, question = design_governance.next_owner_question(root)
    report = _base_report("design questions next", root, True, result)
    report["question"] = question.payload if question is not None else None
    report["question_path"] = question.relpath if question is not None else "NONE"
    report["status"] = "ready" if question is not None and result.exit_code == EXIT_OK else report["status"]
    _print_report("ASO design questions next", report)
    if args.json_out:
        payload = question.payload if question is not None else report
        if not _write_json(root, args.json_out, payload, allowed=("project-runtime/reports", "project-runtime/owner-decisions")):
            return EXIT_IO_ERROR
    return EXIT_OK if question is not None and result.exit_code == EXIT_OK else EXIT_FAILED


def run_decision_record(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    if not args.dry_run and not args.confirm_write:
        print("aso design decision record: choose --dry-run or --confirm-write", file=sys.stderr)
        return EXIT_USAGE
    result = design_governance.validate_design_governance(root, strict=True)
    questions = {str(item.payload.get("question_id")): item for item in result.questions}
    question = questions.get(args.question_id)
    if question is None:
        report = _base_report("design decision record", root, True, result)
        report["status"] = "failed"
        report["blocked_reasons"] = [f"unknown question_id: {args.question_id}"]
        _print_report("ASO design decision record", report)
        return EXIT_FAILED
    if result.exit_code != EXIT_OK:
        report = _base_report("design decision record", root, True, result)
        report["status"] = "failed"
        report["blocked_reasons"] = ["design governance validation failed"]
        _print_report("ASO design decision record", report)
        return EXIT_FAILED
    if not design_governance.question_accepts_owner_answer(question):
        status = str(question.payload.get("status", "")).strip() or "MISSING"
        report = _base_report("design decision record", root, True, result)
        report["status"] = "failed"
        report["blocked_reasons"] = [
            f"{args.question_id} status {status} is not eligible for owner answer recording; expected presented or legacy presented_to_owner with presentation evidence"
        ]
        _print_report("ASO design decision record", report)
        return EXIT_FAILED
    option_ids = {
        str(option.get("id"))
        for option in question.payload.get("options", [])
        if isinstance(option, dict) and option.get("id")
    }
    if args.answer not in option_ids:
        report = _base_report("design decision record", root, True, result)
        report["status"] = "failed"
        report["blocked_reasons"] = [f"answer {args.answer} is not an option for {args.question_id}"]
        _print_report("ASO design decision record", report)
        return EXIT_FAILED

    now = datetime.now(timezone.utc).replace(microsecond=0)
    answer_record = {
        "schema_version": "1.0.0",
        "answer_record_id": f"ANS-{args.question_id.removeprefix('Q-')}-{args.answer}",
        "project_id": _project_id(result),
        "question_id": args.question_id,
        "gap_id": str(question.payload.get("gap_id")),
        "question_ref": question.relpath,
        "selected_option": args.answer,
        "owner_answer_summary": f"Owner selected option {args.answer} for {args.question_id}.",
        "answered_by": "owner",
        "answered_at": now.isoformat().replace("+00:00", "Z"),
        "status": "received",
        "design_update_required": True,
        "design_update_ref": "NONE",
        "accepted_source_of_truth_update": "PENDING",
        "audit_refs": "NONE",
    }
    out_path = root / "project-runtime" / "owner-decisions" / f"{answer_record['answer_record_id']}.json"
    report = _base_report("design decision record", root, True, result)
    report.update(
        {
            "status": "dry_run" if args.dry_run else "written",
            "dry_run": bool(args.dry_run),
            "mutations_performed": bool(args.confirm_write),
            "answer_record": answer_record,
            "target_path": _rel(root, out_path),
        }
    )
    files_written: list[str] = []
    if args.confirm_write:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            out_path.write_text(json.dumps(answer_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"aso design decision record: failed to write answer record: {exc}", file=sys.stderr)
            return EXIT_IO_ERROR
        files_written.append(_rel(root, out_path))
    report["files_written"] = files_written
    _print_report("ASO design decision record", report)
    return EXIT_OK


def run_gate_verify(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    result, blocked = design_governance.verify_stage_gate(root, stage=args.stage, strict=args.strict)
    report = _base_report("design gate verify", root, args.strict, result)
    report["stage"] = args.stage
    report["blocked_gaps"] = blocked
    _print_report("ASO design gate verify", report)
    return result.exit_code


def _base_report(command: str, root: Path, strict: bool, result: design_governance.GovernanceResult) -> dict[str, Any]:
    return {
        "tool": "aso",
        "command": command,
        "status": result.status,
        "root": str(root),
        "strict": strict,
        "summary": result.summary,
        "artifact_counts": {
            "gap_registers": len(result.gap_registers),
            "questions": len(result.questions),
            "answers": len(result.answers),
        },
        "findings": [finding.to_json() for finding in result.findings],
    }


def _print_report(label: str, report: dict[str, Any]) -> None:
    summary = report.get("summary", {})
    print(f"{label}: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    if "stage" in report:
        print(f"Stage: {report['stage']}")
    if isinstance(summary, dict):
        print(f"Errors: {summary.get('errors', 0)}")
        print(f"Warnings: {summary.get('warnings', 0)}")
    counts = report.get("artifact_counts", {})
    if isinstance(counts, dict):
        print(
            "Artifacts: "
            f"gap_registers={counts.get('gap_registers', 0)}, "
            f"questions={counts.get('questions', 0)}, "
            f"answers={counts.get('answers', 0)}"
        )
    if report.get("question_path"):
        print(f"Question: {report['question_path']}")
    if report.get("target_path"):
        print(f"Target: {report['target_path']}")
    if report.get("files_written") is not None:
        print(f"Files written: {len(report['files_written'])}")
    blocked = report.get("blocked_gaps")
    if isinstance(blocked, list) and blocked:
        print("Blocked gaps:")
        for gap in blocked:
            print(f"- {gap.get('gap_id')} via {gap.get('question_id')} at {gap.get('blocking_stage')}")
    reasons = report.get("blocked_reasons")
    if isinstance(reasons, list) and reasons:
        print("Blocked reasons:")
        for reason in reasons:
            print(f"- {reason}")
    findings = report.get("findings", [])
    if isinstance(findings, list):
        for finding in findings:
            if isinstance(finding, dict):
                print(f"- {finding['severity']} {finding['rule_id']}: {finding['title']}")


def _write_json(root: Path, path_text: str, payload: object, *, allowed: tuple[str, ...]) -> bool:
    path = output_policy.resolve_output_path(path_text)
    error = output_policy.validate_generated_output_path(root, path, allowed_workspace_subdirs=allowed)
    if error is not None:
        print(f"aso design: {error.rule_id}: {error.message}: {error.evidence}", file=sys.stderr)
        return False
    if not path.parent.exists():
        print(f"aso design: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso design: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def _project_id(result: design_governance.GovernanceResult) -> str:
    if result.gap_registers:
        return str(result.gap_registers[0].payload.get("project_id", "UNKNOWN"))
    return "UNKNOWN"


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()
