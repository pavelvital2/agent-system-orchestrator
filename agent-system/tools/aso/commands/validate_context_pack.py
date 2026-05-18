"""Read-only context pack validator."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3

REQUIRED_TOP_LEVEL_FIELDS = (
    "task_id",
    "required_docs",
    "forbidden_docs",
    "source_of_truth",
    "context_budget",
)
REQUIRED_DOC_FIELDS = ("path", "sections", "why_needed")
BUDGET_FIELDS = ("max_docs", "max_sections_per_doc", "max_chars_total")
ARCHIVE_PREFIXES = ("project-archive",)
DEPRECATED_MARKERS = ("deprecated", "superseded")


@dataclass(frozen=True)
class ContextPackFinding:
    rule_id: str
    severity: str
    title: str
    details: str
    path: str
    field: str
    recommendation: str

    def to_json(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "message": self.details,
            "details": self.details,
            "path": self.path,
            "field": self.field,
            "recommendation": self.recommendation,
        }


def _resolve_context_pack_path(root: Path, context_pack_path: str) -> Path:
    path = Path(context_pack_path).expanduser()
    if path.is_absolute():
        return path
    root_candidate = root / path
    if root_candidate.exists():
        return root_candidate
    return path


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _summary(findings: Iterable[ContextPackFinding]) -> dict[str, int]:
    finding_list = list(findings)
    return {
        "errors": sum(1 for finding in finding_list if finding.severity == "error"),
        "warnings": sum(1 for finding in finding_list if finding.severity == "warning"),
        "info": sum(1 for finding in finding_list if finding.severity == "info"),
    }


def _status(summary: dict[str, int], strict: bool, *, io_error: bool = False) -> tuple[str, int]:
    if io_error:
        return "io_error", EXIT_IO_ERROR
    if summary["errors"] > 0 or (strict and summary["warnings"] > 0):
        return "failed", EXIT_FINDINGS
    if summary["warnings"] > 0:
        return "warning", EXIT_OK
    return "passed", EXIT_OK


def _finding(
    rule_id: str,
    title: str,
    details: str,
    relpath: str,
    field: str,
    recommendation: str,
    *,
    severity: str = "error",
) -> ContextPackFinding:
    return ContextPackFinding(rule_id, severity, title, details, relpath, field, recommendation)


def _normalize_context_path(value: object, *, relpath: str, field: str) -> tuple[str, ContextPackFinding | None]:
    if not _is_non_empty_string(value):
        return "", _finding(
            "CPP-001",
            "Context path is missing or invalid",
            f"{field} must be a non-empty repository-relative path string.",
            relpath,
            field,
            "Use repository-relative paths such as agent-system/README.md.",
        )

    raw_path = str(value).strip()
    if "\\" in raw_path or "://" in raw_path or Path(raw_path).is_absolute():
        return "", _finding(
            "CPP-001",
            "Context path is unsafe",
            f"{field} uses an absolute path, URL, or platform-specific separator: {raw_path}",
            relpath,
            field,
            "Use portable repository-relative paths only.",
        )

    has_trailing_slash = raw_path.endswith("/")
    parts = [part for part in raw_path.split("/") if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        return "", _finding(
            "CPP-001",
            "Context path escapes the repository root",
            f"{field} must not be empty or contain '..': {raw_path}",
            relpath,
            field,
            "Keep context references inside the repository root.",
        )

    normalized = "/".join(parts)
    if has_trailing_slash:
        normalized = f"{normalized}/"
    return normalized, None


def _matches_path_prefix(path: str, prefix: str) -> bool:
    clean_prefix = prefix.rstrip("/")
    clean_path = path.rstrip("/")
    return clean_path == clean_prefix or clean_path.startswith(f"{clean_prefix}/")


def _is_archive_path(path: str) -> bool:
    return any(_matches_path_prefix(path, prefix) for prefix in ARCHIVE_PREFIXES)


def _is_deprecated_path(path: str) -> bool:
    lowered_parts = [part.lower() for part in path.split("/")]
    return any(any(marker in part for marker in DEPRECATED_MARKERS) for part in lowered_parts)


def _required_doc_paths(payload: dict[str, object]) -> list[str]:
    docs = payload.get("required_docs")
    if not isinstance(docs, list):
        return []
    paths: list[str] = []
    for item in docs:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            paths.append(item["path"].strip())
    return paths


def _validate_top_level(payload: object, relpath: str) -> tuple[dict[str, object] | None, list[ContextPackFinding]]:
    if not isinstance(payload, dict):
        return None, [
            _finding(
                "CPS-001",
                "Context pack root must be a JSON object",
                "The context pack JSON root is not an object.",
                relpath,
                "",
                "Use the CONTEXT_PACK_TEMPLATE.json object structure.",
            )
        ]

    findings: list[ContextPackFinding] = []
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in payload:
            findings.append(
                _finding(
                    "CPS-002",
                    "Required context pack field is missing",
                    f"Missing top-level field: {field}.",
                    relpath,
                    field,
                    "Populate every required top-level context pack field.",
                )
            )
    return payload, findings


def _validate_required_docs(
    payload: dict[str, object],
    relpath: str,
    root: Path,
    forbidden_prefixes: list[str],
) -> list[ContextPackFinding]:
    findings: list[ContextPackFinding] = []
    docs = payload.get("required_docs")
    if not isinstance(docs, list) or not docs:
        return [
            _finding(
                "CPS-003",
                "required_docs must be a non-empty list",
                "Context packs must identify at least one bounded required document.",
                relpath,
                "required_docs",
                "Add required_docs entries with path, sections, and why_needed.",
            )
        ]

    root_exists = root.exists() and root.is_dir()
    if not root_exists:
        findings.append(
            _finding(
                "CPS-006",
                "Project root is not readable",
                f"--root does not point to a readable directory: {root}",
                relpath,
                "root",
                "Pass --root pointing at the repository or workspace root.",
            )
        )

    for index, item in enumerate(docs):
        field_prefix = f"required_docs[{index}]"
        if not isinstance(item, dict):
            findings.append(
                _finding(
                    "CPS-004",
                    "required_docs entry must be an object",
                    f"{field_prefix} is not an object.",
                    relpath,
                    field_prefix,
                    "Use objects with path, sections, why_needed, and optional sha256.",
                )
            )
            continue

        for field in REQUIRED_DOC_FIELDS:
            if field not in item:
                findings.append(
                    _finding(
                        "CPS-004",
                        "Required document field is missing",
                        f"{field_prefix}.{field} is missing.",
                        relpath,
                        f"{field_prefix}.{field}",
                        "Populate path, sections, and why_needed for every required doc.",
                    )
                )

        doc_path, path_finding = _normalize_context_path(item.get("path"), relpath=relpath, field=f"{field_prefix}.path")
        if path_finding:
            findings.append(path_finding)
            continue

        sections = item.get("sections")
        if not isinstance(sections, list) or not sections or not all(_is_non_empty_string(section) for section in sections):
            findings.append(
                _finding(
                    "CPS-004",
                    "Required document sections are invalid",
                    f"{field_prefix}.sections must be a non-empty list of section names.",
                    relpath,
                    f"{field_prefix}.sections",
                    "List only the bounded sections needed by the receiving agent.",
                )
            )
        if not _is_non_empty_string(item.get("why_needed")):
            findings.append(
                _finding(
                    "CPS-004",
                    "Required document reason is missing",
                    f"{field_prefix}.why_needed must explain why the document is included.",
                    relpath,
                    f"{field_prefix}.why_needed",
                    "Add a bounded reason for each document reference.",
                )
            )

        findings.extend(_validate_context_path_policy(doc_path, relpath, f"{field_prefix}.path", forbidden_prefixes))

        if root_exists:
            absolute_doc = (root / doc_path).resolve(strict=False)
            try:
                absolute_doc.relative_to(root.resolve(strict=False))
            except ValueError:
                findings.append(
                    _finding(
                        "CPP-001",
                        "Required document escapes the repository root",
                        f"{field_prefix}.path resolves outside --root: {doc_path}",
                        relpath,
                        f"{field_prefix}.path",
                        "Use repository-relative paths inside --root.",
                    )
                )
                continue
            if not absolute_doc.is_file():
                findings.append(
                    _finding(
                        "CPP-005",
                        "Required document is missing",
                        f"{field_prefix}.path does not exist as a file under --root: {doc_path}",
                        relpath,
                        f"{field_prefix}.path",
                        "Reference only existing source-of-truth documents.",
                    )
                )

    return findings


def _validate_context_path_policy(
    path: str,
    relpath: str,
    field: str,
    forbidden_prefixes: list[str],
) -> list[ContextPackFinding]:
    findings: list[ContextPackFinding] = []
    if _is_archive_path(path):
        findings.append(
            _finding(
                "CPP-002",
                "Context pack references archive material",
                f"{field} points at archived material: {path}",
                relpath,
                field,
                "Do not use project-archive content as active inter-agent context.",
            )
        )
    if _is_deprecated_path(path):
        findings.append(
            _finding(
                "CPP-003",
                "Context pack references deprecated material",
                f"{field} points at deprecated or superseded material: {path}",
                relpath,
                field,
                "Replace deprecated or superseded references with current source-of-truth docs.",
            )
        )
    for forbidden in forbidden_prefixes:
        if _matches_path_prefix(path, forbidden):
            findings.append(
                _finding(
                    "CPP-004",
                    "Required context is forbidden by the pack policy",
                    f"{field}={path} is covered by forbidden_docs entry {forbidden}.",
                    relpath,
                    field,
                    "Remove the forbidden document from required_docs/source_of_truth or narrow forbidden_docs.",
                )
            )
    return findings


def _validate_forbidden_docs(payload: dict[str, object], relpath: str) -> tuple[list[str], list[ContextPackFinding]]:
    findings: list[ContextPackFinding] = []
    forbidden_docs = payload.get("forbidden_docs")
    if not isinstance(forbidden_docs, list):
        return [], [
            _finding(
                "CPS-003",
                "forbidden_docs must be a list",
                "forbidden_docs must be a list of repository-relative path prefixes.",
                relpath,
                "forbidden_docs",
                "List path prefixes that must not appear in required_docs.",
            )
        ]

    normalized: list[str] = []
    for index, value in enumerate(forbidden_docs):
        path, path_finding = _normalize_context_path(value, relpath=relpath, field=f"forbidden_docs[{index}]")
        if path_finding:
            findings.append(path_finding)
            continue
        normalized.append(path)
    return sorted(set(normalized)), findings


def _validate_source_of_truth(
    payload: dict[str, object],
    relpath: str,
    forbidden_prefixes: list[str],
) -> list[ContextPackFinding]:
    findings: list[ContextPackFinding] = []
    values = payload.get("source_of_truth")
    if not isinstance(values, list) or not values:
        return [
            _finding(
                "CPS-003",
                "source_of_truth must be a non-empty list",
                "Context packs must identify the source-of-truth paths they depend on.",
                relpath,
                "source_of_truth",
                "List the authoritative source documents for the bounded context.",
            )
        ]

    required_paths = set(_required_doc_paths(payload))
    for index, value in enumerate(values):
        field = f"source_of_truth[{index}]"
        path, path_finding = _normalize_context_path(value, relpath=relpath, field=field)
        if path_finding:
            findings.append(path_finding)
            continue
        findings.extend(_validate_context_path_policy(path, relpath, field, forbidden_prefixes))
        if path not in required_paths:
            findings.append(
                _finding(
                    "CPS-007",
                    "source_of_truth is outside required_docs",
                    f"{field}={path} is not included in required_docs.",
                    relpath,
                    field,
                    "Include every source_of_truth document in required_docs with bounded sections.",
                    severity="warning",
                )
            )
    return findings


def _validate_budget(payload: dict[str, object], relpath: str, raw_text: str) -> list[ContextPackFinding]:
    findings: list[ContextPackFinding] = []
    budget = payload.get("context_budget")
    if not isinstance(budget, dict):
        return [
            _finding(
                "CPS-005",
                "context_budget must be an object",
                "context_budget must define max_docs, max_sections_per_doc, and max_chars_total.",
                relpath,
                "context_budget",
                "Use the context_budget object from CONTEXT_PACK_TEMPLATE.json.",
            )
        ]

    parsed_budget: dict[str, int] = {}
    for field in BUDGET_FIELDS:
        value = budget.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            findings.append(
                _finding(
                    "CPS-005",
                    "Context budget field is invalid",
                    f"context_budget.{field} must be a positive integer.",
                    relpath,
                    f"context_budget.{field}",
                    "Set every context budget limit to a positive integer.",
                )
            )
            continue
        parsed_budget[field] = value

    docs = payload.get("required_docs")
    doc_count = len(docs) if isinstance(docs, list) else 0
    if (max_docs := parsed_budget.get("max_docs")) is not None and doc_count > max_docs:
        findings.append(
            _finding(
                "CPB-001",
                "Context pack exceeds max_docs",
                f"required_docs has {doc_count} entries; context_budget.max_docs is {max_docs}.",
                relpath,
                "required_docs",
                "Reduce required_docs or raise the explicit budget with audit-visible justification.",
            )
        )

    if isinstance(docs, list) and (max_sections := parsed_budget.get("max_sections_per_doc")) is not None:
        for index, item in enumerate(docs):
            sections = item.get("sections") if isinstance(item, dict) else None
            section_count = len(sections) if isinstance(sections, list) else 0
            if section_count > max_sections:
                findings.append(
                    _finding(
                        "CPB-002",
                        "Context pack exceeds max_sections_per_doc",
                        (
                            f"required_docs[{index}].sections has {section_count} entries; "
                            f"context_budget.max_sections_per_doc is {max_sections}."
                        ),
                        relpath,
                        f"required_docs[{index}].sections",
                        "Keep each document reference bounded to the sections actually needed.",
                    )
                )

    if (max_chars_total := parsed_budget.get("max_chars_total")) is not None and len(raw_text) > max_chars_total:
        findings.append(
            _finding(
                "CPB-003",
                "Context pack exceeds max_chars_total",
                f"Context pack JSON has {len(raw_text)} characters; context_budget.max_chars_total is {max_chars_total}.",
                relpath,
                "context_budget.max_chars_total",
                "Reduce copied context or raise the explicit budget with audit-visible justification.",
            )
        )
    return findings


def _validate_payload(payload: dict[str, object], relpath: str, root: Path, raw_text: str) -> list[ContextPackFinding]:
    findings: list[ContextPackFinding] = []
    if not _is_non_empty_string(payload.get("task_id")):
        findings.append(
            _finding(
                "CPS-003",
                "task_id must be a non-empty string",
                "task_id is required for traceability to the bounded task.",
                relpath,
                "task_id",
                "Set task_id to the receiving bounded task id.",
            )
        )

    forbidden_prefixes, forbidden_findings = _validate_forbidden_docs(payload, relpath)
    findings.extend(forbidden_findings)
    findings.extend(_validate_required_docs(payload, relpath, root, forbidden_prefixes))
    findings.extend(_validate_source_of_truth(payload, relpath, forbidden_prefixes))
    findings.extend(_validate_budget(payload, relpath, raw_text))
    return sorted(findings, key=lambda item: (item.rule_id, item.field, item.details))


def _context_summary(payload: dict[str, object] | None, raw_text: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {
            "task_id": "",
            "required_docs_count": 0,
            "source_of_truth_count": 0,
            "forbidden_docs_count": 0,
            "context_chars_total": len(raw_text),
            "context_budget": {},
        }
    return {
        "task_id": str(payload.get("task_id", "")),
        "required_docs_count": len(payload.get("required_docs", [])) if isinstance(payload.get("required_docs"), list) else 0,
        "source_of_truth_count": len(payload.get("source_of_truth", [])) if isinstance(payload.get("source_of_truth"), list) else 0,
        "forbidden_docs_count": len(payload.get("forbidden_docs", [])) if isinstance(payload.get("forbidden_docs"), list) else 0,
        "context_chars_total": len(raw_text),
        "context_budget": payload.get("context_budget", {}) if isinstance(payload.get("context_budget"), dict) else {},
    }


def _report(path: Path, root: Path, strict: bool) -> tuple[dict[str, object], int]:
    relpath = _rel(root, path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        finding = _finding(
            "CPS-001",
            "Context pack is unreadable",
            f"{relpath}: {exc}",
            relpath,
            "",
            "Pass a readable JSON context pack.",
        )
        summary = _summary([finding])
        status, exit_code = _status(summary, strict)
        return _build_report(status, root, path, strict, summary, [finding], None, ""), exit_code

    try:
        loaded = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        finding = _finding(
            "CPS-001",
            "Context pack JSON is invalid",
            f"{relpath}: {exc.msg} at line {exc.lineno}, column {exc.colno}.",
            relpath,
            "",
            "Fix the JSON syntax before validation.",
        )
        summary = _summary([finding])
        status, exit_code = _status(summary, strict)
        return _build_report(status, root, path, strict, summary, [finding], None, raw_text), exit_code

    payload, findings = _validate_top_level(loaded, relpath)
    if payload is not None:
        findings.extend(_validate_payload(payload, relpath, root, raw_text))
    findings = sorted(findings, key=lambda item: (item.rule_id, item.field, item.details))
    summary = _summary(findings)
    status, exit_code = _status(summary, strict)
    return _build_report(status, root, path, strict, summary, findings, payload, raw_text), exit_code


def _build_report(
    status: str,
    root: Path,
    path: Path,
    strict: bool,
    summary: dict[str, int],
    findings: list[ContextPackFinding],
    payload: dict[str, object] | None,
    raw_text: str,
) -> dict[str, object]:
    return {
        "tool": "aso",
        "command": "validate-context-pack",
        "status": status,
        "root": str(root),
        "path": str(path),
        "strict": strict,
        "summary": summary,
        "findings": [finding.to_json() for finding in findings],
        "context_pack": _context_summary(payload, raw_text),
        "read_only": True,
    }


def _print_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    if not isinstance(summary, dict):
        raise TypeError("internal validate-context-pack report summary must be a dictionary")

    context_pack = report["context_pack"]
    if not isinstance(context_pack, dict):
        raise TypeError("internal validate-context-pack report context_pack must be a dictionary")

    print(f"ASO validate-context-pack: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    print(f"Path: {report['path']}")
    print(f"Strict: {report['strict']}")
    print(f"Task ID: {context_pack['task_id']}")
    print(f"Required docs: {context_pack['required_docs_count']}")
    print(f"Source of truth docs: {context_pack['source_of_truth_count']}")
    print(f"Context chars: {context_pack['context_chars_total']}")
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Info: {summary['info']}")
    print(f"Findings: {len(report['findings'])}")
    for finding in report["findings"]:
        if not isinstance(finding, dict):
            continue
        print(f"- {finding['severity']} {finding['rule_id']}: {finding['title']}")


def _write_json(path_text: str, report: dict[str, object]) -> bool:
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso validate-context-pack: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso validate-context-pack: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def run(args: argparse.Namespace) -> int:
    """Run the validate-context-pack command."""

    root = Path(args.root).expanduser()
    context_pack_path = _resolve_context_pack_path(root, args.context_pack_path)
    report, exit_code = _report(context_pack_path, root, args.strict)
    _print_text(report)
    if args.json_out and not _write_json(args.json_out, report):
        return EXIT_IO_ERROR
    return exit_code
