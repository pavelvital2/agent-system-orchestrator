"""Dry-run context pack proposal builder."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3

DEFAULT_FORBIDDEN_DOCS = (
    "project-archive/",
    "project-input/",
    "project-runtime/",
    ".tmp/",
    "tmp/",
)
ARCHIVE_PREFIXES = ("project-archive",)
DEPRECATED_MARKERS = ("deprecated", "superseded")
WHOLE_PROJECT_TOKENS = {"", ".", "./", "/", "*", "**", "<project-root>", "project-root", "repo", "repository"}
GENERATED_PARTS = {"__pycache__"}
GENERATED_SUFFIXES = (".pyc",)
SECTION_PATTERN = re.compile(r"^(#{2,6})\s+(.+?)\s*$", re.MULTILINE)
TASK_ID_PATTERN = re.compile(r"^\s*TASK_ID\s*:\s*([A-Za-z0-9_.:-]+)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class BuildFinding:
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


def _finding(
    rule_id: str,
    title: str,
    details: str,
    path: str,
    field: str,
    recommendation: str,
    *,
    severity: str = "error",
) -> BuildFinding:
    return BuildFinding(rule_id, severity, title, details, path, field, recommendation)


def _resolve_input_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
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


def _matches_path_prefix(path: str, prefix: str) -> bool:
    clean_prefix = prefix.rstrip("/")
    clean_path = path.rstrip("/")
    return clean_path == clean_prefix or clean_path.startswith(f"{clean_prefix}/")


def _is_archive_path(path: str) -> bool:
    return any(_matches_path_prefix(path, prefix) for prefix in ARCHIVE_PREFIXES)


def _is_deprecated_path(path: str) -> bool:
    lowered_parts = [part.lower() for part in path.split("/")]
    return any(any(marker in part for marker in DEPRECATED_MARKERS) for part in lowered_parts)


def _canonical_path(value: str) -> str:
    text = value.strip().strip("`'\"")
    if not text:
        return ""
    text = text.split("#", 1)[0].strip()
    if text in WHOLE_PROJECT_TOKENS:
        return text
    text = text.removesuffix("/**").removesuffix("/*")
    text = text.replace("\\", "/")
    has_trailing_slash = text.endswith("/")
    parts = [part for part in text.split("/") if part not in {"", "."}]
    normalized = "/".join(parts)
    if has_trailing_slash and normalized:
        normalized = f"{normalized}/"
    return normalized


def _forbidden_prefix(value: str) -> str:
    text = _canonical_path(value)
    text = text.removesuffix("/**").removesuffix("/*")
    if text and not Path(text).suffix and not text.endswith("/"):
        text = f"{text}/"
    return text


def _section_body(text: str, section_names: Iterable[str]) -> str:
    wanted = {_normalize_heading(name) for name in section_names}
    matches = list(SECTION_PATTERN.finditer(text))
    for index, match in enumerate(matches):
        if _normalize_heading(match.group(2)) not in wanted:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        return text[start:end].strip()
    return ""


def _normalize_heading(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _extract_path_candidates(body: str) -> list[str]:
    paths: list[str] = []
    in_fence = False
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not line or line.startswith("#"):
            continue
        if in_fence:
            paths.extend(_extract_paths_from_text(line, prefer_whole_line=True))
            continue
        if line.startswith(("- ", "* ")):
            line = line[2:].strip()
        paths.extend(_extract_paths_from_text(line, prefer_whole_line=False))
    return _dedupe(paths)


def _extract_paths_from_text(text: str, *, prefer_whole_line: bool) -> list[str]:
    coded = re.findall(r"`([^`]+)`", text)
    if coded:
        return [_canonical_path(value) for value in coded if _canonical_path(value)]
    if prefer_whole_line:
        value = _canonical_path(text)
        return [value] if value else []

    token = re.split(r"\s+-\s+|\s+--\s+|\s+#\s+", text, maxsplit=1)[0].strip()
    token = token.rstrip(".,;:")
    value = _canonical_path(token)
    if _looks_like_path(value):
        return [value]
    return []


def _looks_like_path(value: str) -> bool:
    if value in WHOLE_PROJECT_TOKENS:
        return True
    return (
        "/" in value
        or value.endswith((".md", ".json", ".py", ".yaml", ".yml", ".toml", ".txt"))
        or value.endswith(("/**", "/*"))
    )


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _parse_task_id(text: str) -> str:
    match = TASK_ID_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return ""


def _parse_acceptance_criteria(text: str) -> list[str]:
    body = _section_body(text, ("Acceptance criteria", "Acceptance Criteria"))
    criteria: list[str] = []
    for line in body.splitlines():
        clean = line.strip()
        if clean.startswith(("- ", "* ")):
            clean = clean[2:].strip()
        if clean:
            criteria.append(clean)
    return criteria


def _parse_required_docs(text: str) -> list[str]:
    body = _section_body(text, ("Required docs", "Required Docs", "REQUIRED_DOCS"))
    return _extract_path_candidates(body)


def _parse_source_of_truth(text: str) -> list[str]:
    body = _section_body(
        text,
        (
            "Source of truth",
            "Source-of-truth",
            "Source-of-truth docs",
            "Source of truth docs",
            "SOURCE_OF_TRUTH",
        ),
    )
    return _extract_path_candidates(body)


def _parse_forbidden_docs(text: str) -> list[str]:
    body = _section_body(
        text,
        (
            "Forbidden paths",
            "Forbidden write paths",
            "Forbidden docs",
            "Forbidden files",
            "FORBIDDEN_PATHS",
        ),
    )
    parsed = [_forbidden_prefix(value) for value in _extract_path_candidates(body)]
    return _dedupe([*DEFAULT_FORBIDDEN_DOCS, *[value for value in parsed if value]])


def _parse_allowed_files(text: str) -> list[str]:
    body = _section_body(
        text,
        (
            "Allowed files",
            "Allowed write paths",
            "Allowed paths",
            "ALLOWED_FILES",
        ),
    )
    return _extract_path_candidates(body)


def _is_whole_project_reference(path: str) -> bool:
    if path in WHOLE_PROJECT_TOKENS:
        return True
    stripped = path.rstrip("/")
    if stripped in {"agent-system", "project-input", "project-runtime", "project-archive"}:
        return True
    return stripped in {"tmp", ".tmp"}


def _is_generated_artifact(path: Path) -> bool:
    return any(part in GENERATED_PARTS for part in path.parts) or path.name.endswith(GENERATED_SUFFIXES)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _section_hints(path: str) -> list[str]:
    name = Path(path).name
    if name == "TASK_PACKET_TEMPLATE.md":
        return ["TASK PACKET", "Required docs", "Allowed write paths", "Forbidden write paths"]
    if name.startswith("CONTEXT_PACK_TEMPLATE"):
        return ["Required fields", "Context budget", "Source of truth"]
    if name == "validate_context_pack.py":
        return ["Required fields", "Path policy", "Budget validation"]
    if "/fixtures/" in path:
        return ["Fixture coverage"]
    return ["Bounded task-relevant sections"]


def _expanded_required_docs(
    root: Path,
    task_relpath: str,
    required_paths: list[str],
    forbidden_prefixes: list[str],
    strict: bool,
) -> tuple[list[dict[str, object]], list[BuildFinding]]:
    docs: list[dict[str, object]] = []
    findings: list[BuildFinding] = []

    for index, doc_path in enumerate(required_paths):
        field = f"required_docs[{index}]"
        if _is_whole_project_reference(doc_path):
            findings.append(
                _finding(
                    "CPB-BUILD-003",
                    "Required context is too broad",
                    f"{field} references whole-project or top-level context: {doc_path}",
                    task_relpath,
                    field,
                    "Replace broad context with bounded source documents or fixture files.",
                )
            )
            continue
        if _is_archive_path(doc_path) or _is_deprecated_path(doc_path):
            findings.append(
                _finding(
                    "CPB-BUILD-004",
                    "Required context is archived or deprecated",
                    f"{field} references archived, deprecated, or superseded context: {doc_path}",
                    task_relpath,
                    field,
                    "Use current source-of-truth documents only.",
                )
            )
            continue
        matched_forbidden = [prefix for prefix in forbidden_prefixes if _matches_path_prefix(doc_path, prefix)]
        if matched_forbidden:
            findings.append(
                _finding(
                    "CPB-BUILD-002",
                    "Required context is forbidden by task policy",
                    f"{field}={doc_path} matches forbidden path {matched_forbidden[0]}.",
                    task_relpath,
                    field,
                    "Remove forbidden roots from Required docs or narrow the task packet.",
                )
            )
            continue

        absolute = (root / doc_path).resolve(strict=False)
        try:
            absolute.relative_to(root.resolve(strict=False))
        except ValueError:
            findings.append(
                _finding(
                    "CPB-BUILD-001",
                    "Required context escapes repository root",
                    f"{field} resolves outside --root: {doc_path}",
                    task_relpath,
                    field,
                    "Use repository-relative context paths inside the project root.",
                )
            )
            continue

        if absolute.is_dir():
            docs.append(_directory_entry(root, absolute, doc_path))
            continue
        if absolute.is_file():
            docs.append(_doc_entry(root, absolute, doc_path, "Declared under Required docs in the task packet."))
            continue

        severity = "error" if strict else "warning"
        findings.append(
            _finding(
                "CPB-BUILD-005",
                "Required context document is missing",
                f"{field} does not exist under --root: {doc_path}",
                task_relpath,
                field,
                "Reference only existing source-of-truth docs, or rerun with non-strict only for exploratory diagnostics.",
                severity=severity,
            )
        )

    return _dedupe_doc_entries(docs), findings


def _directory_entry(root: Path, absolute_dir: Path, requested_path: str) -> dict[str, object]:
    return {
        "path": requested_path if requested_path.endswith("/") else f"{requested_path}/",
        "sections": _section_hints(requested_path),
        "why_needed": "Declared as a bounded Required docs directory in the task packet.",
        "required_docs_reason": "Declared as a bounded Required docs directory in the task packet.",
        "sha256": _directory_sha256(root, absolute_dir),
        "estimated_chars": _directory_size(absolute_dir),
    }


def _directory_sha256(root: Path, absolute_dir: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(absolute_dir.rglob("*")):
        if not child.is_file() or _is_generated_artifact(child):
            continue
        relpath = _rel(root, child)
        digest.update(relpath.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_file_sha256(child).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _directory_size(absolute_dir: Path) -> int:
    total = 0
    for child in absolute_dir.rglob("*"):
        if child.is_file() and not _is_generated_artifact(child):
            total += child.stat().st_size
    return total


def _doc_entry(root: Path, absolute_path: Path, relpath: str, reason: str) -> dict[str, object]:
    return {
        "path": relpath,
        "sections": _section_hints(relpath),
        "why_needed": reason,
        "required_docs_reason": reason,
        "sha256": _file_sha256(absolute_path),
        "estimated_chars": absolute_path.stat().st_size,
    }


def _dedupe_doc_entries(entries: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    result: list[dict[str, object]] = []
    for entry in entries:
        path = str(entry["path"])
        if path in seen:
            continue
        seen.add(path)
        result.append(entry)
    return result


def _summary(findings: Iterable[BuildFinding]) -> dict[str, int]:
    items = list(findings)
    return {
        "errors": sum(1 for finding in items if finding.severity == "error"),
        "warnings": sum(1 for finding in items if finding.severity == "warning"),
        "info": sum(1 for finding in items if finding.severity == "info"),
    }


def _status(summary: dict[str, int], strict: bool, *, io_error: bool = False) -> tuple[str, int]:
    if io_error:
        return "io_error", EXIT_IO_ERROR
    if summary["errors"] > 0 or (strict and summary["warnings"] > 0):
        return "failed", EXIT_FINDINGS
    return "passed", EXIT_OK


def _budget_for(docs: list[dict[str, object]], proposal_chars_estimate: int) -> dict[str, int]:
    max_sections = max((len(doc.get("sections", [])) for doc in docs), default=1)
    return {
        "max_docs": max(len(docs), 1),
        "max_sections_per_doc": max(max_sections, 1),
        "max_chars_total": max(proposal_chars_estimate + 2000, 4000),
    }


def _build_context_pack(
    root: Path,
    task_packet_path: Path,
    strict: bool,
) -> tuple[dict[str, object] | None, dict[str, object], int]:
    task_relpath = _rel(root, task_packet_path)
    try:
        text = task_packet_path.read_text(encoding="utf-8")
    except OSError as exc:
        finding = _finding(
            "CPB-BUILD-IO",
            "Task packet is unreadable",
            f"{task_relpath}: {exc}",
            task_relpath,
            "task_packet",
            "Pass a readable Markdown task packet.",
        )
        report = _build_report("io_error", root, task_packet_path, strict, [finding], None)
        return None, report, EXIT_IO_ERROR

    task_id = _parse_task_id(text)
    required_paths = _parse_required_docs(text)
    forbidden_docs = _parse_forbidden_docs(text)
    allowed_files = _parse_allowed_files(text)
    source_of_truth = _parse_source_of_truth(text)
    acceptance_criteria = _parse_acceptance_criteria(text)

    findings: list[BuildFinding] = []
    if not task_id:
        findings.append(
            _finding(
                "CPB-BUILD-006",
                "Task packet is missing TASK_ID",
                "The builder could not find a TASK_ID field.",
                task_relpath,
                "TASK_ID",
                "Add TASK_ID to the task packet metadata.",
            )
        )
    if not required_paths:
        findings.append(
            _finding(
                "CPB-BUILD-007",
                "Task packet has no Required docs",
                "The builder could not find bounded Required docs in the task packet.",
                task_relpath,
                "required_docs",
                "Add a Required docs section with repository-relative paths.",
            )
        )

    docs, doc_findings = _expanded_required_docs(root, task_relpath, required_paths, forbidden_docs, strict)
    findings.extend(doc_findings)
    doc_paths = [str(doc["path"]) for doc in docs]
    if source_of_truth:
        source_paths = [path for path in source_of_truth if path in set(doc_paths)]
    else:
        source_paths = doc_paths
    if not source_paths and doc_paths:
        source_paths = doc_paths

    proposal: dict[str, object] | None = None
    if docs and not any(finding.severity == "error" for finding in findings):
        draft: dict[str, object] = {
            "task_id": task_id,
            "required_docs": docs,
            "forbidden_docs": forbidden_docs,
            "source_of_truth": source_paths,
            "required_docs_reason": "Derived from the task packet Required docs section for bounded agent handoff.",
            "section_hints": {str(doc["path"]): doc["sections"] for doc in docs},
            "task_packet": task_relpath,
            "allowed_files": allowed_files,
            "acceptance_criteria": acceptance_criteria,
            "proposal_mode": "dry_run",
            "read_only": True,
        }
        draft_text = json.dumps({**draft, "context_budget": _budget_for(docs, 4000)}, indent=2, sort_keys=True)
        draft["context_budget"] = _budget_for(docs, len(draft_text))
        proposal = draft

    summary = _summary(findings)
    status, exit_code = _status(summary, strict)
    if proposal is None and status == "passed":
        status = "failed"
        exit_code = EXIT_FINDINGS
    report = _build_report(status, root, task_packet_path, strict, findings, proposal)
    return proposal if exit_code == EXIT_OK else None, report, exit_code


def _build_report(
    status: str,
    root: Path,
    task_packet_path: Path,
    strict: bool,
    findings: list[BuildFinding],
    proposal: dict[str, object] | None,
) -> dict[str, object]:
    summary = _summary(findings)
    return {
        "tool": "aso",
        "command": "context-pack build",
        "status": status,
        "root": str(root),
        "task_packet": str(task_packet_path),
        "strict": strict,
        "summary": {
            **summary,
            "required_docs_count": len(proposal.get("required_docs", [])) if isinstance(proposal, dict) else 0,
        },
        "findings": [finding.to_json() for finding in findings],
        "read_only": True,
    }


def _write_json(path_text: str, payload: dict[str, object], root: Path) -> bool:
    path = Path(path_text).expanduser()
    relpath = _rel(root, path)
    if any(_matches_path_prefix(relpath, forbidden) for forbidden in DEFAULT_FORBIDDEN_DOCS):
        print(f"aso context-pack build: refusing to write json-out under forbidden root: {relpath}", file=sys.stderr)
        return False
    if not path.parent.exists():
        print(f"aso context-pack build: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso context-pack build: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def run_build(args: argparse.Namespace) -> int:
    """Run the dry-run context pack build command."""

    root = Path(args.root).expanduser()
    task_packet_path = _resolve_input_path(root, args.task_packet)
    proposal, report, exit_code = _build_context_pack(root, task_packet_path, args.strict)
    if exit_code != EXIT_OK or proposal is None:
        print(json.dumps(report, indent=2, sort_keys=True), file=sys.stderr)
        return exit_code
    if args.json_out:
        if not _write_json(args.json_out, proposal, root):
            return EXIT_IO_ERROR
        return EXIT_OK
    print(json.dumps(proposal, indent=2, sort_keys=True))
    return EXIT_OK
