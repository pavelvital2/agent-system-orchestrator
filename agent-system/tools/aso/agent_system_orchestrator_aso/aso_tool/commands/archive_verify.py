"""Read-only archive completeness verifier."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_IO_ERROR = 3

FIELD_RE = re.compile(r"^([A-Z][A-Z0-9_]*):(?:[ \t]*(.*))?$")
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}
ARCHIVE_MANIFEST_CANDIDATES = {
    "manifest.json",
    "archive_manifest.json",
    "archive-manifest.json",
    "project-runtime/archive/manifest.json",
    "project-runtime/archive/archive_manifest.json",
    "project-runtime/reports/archive_manifest.json",
    "project-runtime/ARCHIVE_MANIFEST.json",
}
PROJECT_DIRS = {"project-runtime", "project-docs", "project-input"}
NON_PRODUCT_TOP_LEVELS = PROJECT_DIRS | {".git", ".github", "agent-system"}
SUPPORTED_SUFFIXES = (".zip", ".tgz", ".tar.gz", ".tar")


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    title: str
    details: str
    files: list[str]
    recommendation: str

    def to_json(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "details": self.details,
            "files": self.files,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class ArchiveData:
    path: Path
    format: str
    raw_names: set[str]
    names: set[str]
    prefix: str
    text_files: dict[str, str]


def _is_none(value: str | None) -> bool:
    return value is None or value.strip() in NONE_VALUES


def _normalize_member(name: str) -> str:
    path = PurePosixPath(name.replace("\\", "/"))
    parts = []
    for part in path.parts:
        if part in {"", ".", "/"}:
            continue
        if part == "..":
            return ""
        parts.append(part)
    return "/".join(parts).rstrip("/")


def _strip_prefix(name: str, prefix: str) -> str:
    if not prefix:
        return name
    if name == prefix:
        return ""
    prefix_text = f"{prefix}/"
    if name.startswith(prefix_text):
        return name[len(prefix_text) :]
    return name


def _common_archive_prefix(names: set[str]) -> str:
    first_parts = {name.split("/", 1)[0] for name in names if name}
    if len(first_parts) != 1:
        return ""
    prefix = next(iter(first_parts))
    if prefix in PROJECT_DIRS or prefix in ARCHIVE_MANIFEST_CANDIDATES:
        return ""
    stripped = {_strip_prefix(name, prefix) for name in names}
    if any(name.split("/", 1)[0] in PROJECT_DIRS for name in stripped if name):
        return prefix
    if any(name in ARCHIVE_MANIFEST_CANDIDATES for name in stripped):
        return prefix
    return ""


def _archive_kind(path: Path) -> str | None:
    name = path.name.lower()
    if name.endswith(".zip"):
        return "zip"
    if name.endswith(".tgz") or name.endswith(".tar.gz"):
        return "gztar"
    if name.endswith(".tar"):
        return "tar"
    return None


def _read_archive(path_text: str) -> tuple[ArchiveData | None, Finding | None, int]:
    path = Path(path_text).expanduser()
    kind = _archive_kind(path)
    if kind is None:
        return (
            None,
            Finding(
                "ARCHIVE_IO_001",
                "error",
                "Unsupported archive type",
                f"{path} is not one of: {', '.join(SUPPORTED_SUFFIXES)}.",
                [str(path)],
                "Pass a .zip, .tgz, .tar.gz, or .tar archive.",
            ),
            EXIT_USAGE,
        )
    if not path.exists() or not path.is_file():
        return (
            None,
            Finding(
                "ARCHIVE_IO_002",
                "error",
                "Archive is missing",
                f"{path} is not an existing readable file.",
                [str(path)],
                "Pass --archive pointing at an existing archive file.",
            ),
            EXIT_IO_ERROR,
        )

    try:
        if kind == "zip":
            raw_names, text_files = _read_zip(path)
        else:
            raw_names, text_files = _read_tar(path, mode="r:gz" if kind == "gztar" else "r:")
    except (OSError, UnicodeDecodeError, tarfile.TarError, zipfile.BadZipFile) as exc:
        return (
            None,
            Finding(
                "ARCHIVE_IO_003",
                "error",
                "Archive is unreadable",
                f"{path}: {exc}",
                [str(path)],
                "Recreate the archive and rerun archive verification.",
            ),
            EXIT_IO_ERROR,
        )

    normalized = {name for name in (_normalize_member(raw_name) for raw_name in raw_names) if name}
    prefix = _common_archive_prefix(normalized)
    names = {_strip_prefix(name, prefix) for name in normalized if _strip_prefix(name, prefix)}
    stripped_text = {_strip_prefix(_normalize_member(name), prefix): text for name, text in text_files.items()}
    stripped_text = {name: text for name, text in stripped_text.items() if name}

    return ArchiveData(path=path, format=kind, raw_names=normalized, names=names, prefix=prefix, text_files=stripped_text), None, EXIT_OK


def _read_zip(path: Path) -> tuple[set[str], dict[str, str]]:
    raw_names: set[str] = set()
    text_files: dict[str, str] = {}
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise zipfile.BadZipFile(f"bad CRC for {bad_member}")
        for info in archive.infolist():
            if info.is_dir():
                raw_names.add(info.filename)
                continue
            raw_names.add(info.filename)
            normalized = _normalize_member(info.filename)
            if _should_read_text(normalized):
                data = archive.read(info)
                text_files[info.filename] = data.decode("utf-8")
    return raw_names, text_files


def _read_tar(path: Path, mode: str) -> tuple[set[str], dict[str, str]]:
    raw_names: set[str] = set()
    text_files: dict[str, str] = {}
    with tarfile.open(path, mode) as archive:
        for member in archive.getmembers():
            raw_names.add(member.name)
            normalized = _normalize_member(member.name)
            if not member.isfile() or not _should_read_text(normalized):
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            text_files[member.name] = extracted.read().decode("utf-8")
    return raw_names, text_files


def _should_read_text(name: str) -> bool:
    return name in ARCHIVE_MANIFEST_CANDIDATES or name in {
        "project-runtime/ACCEPTED_ARTIFACTS.md",
        "project-runtime/PROJECT_STATE.md",
        "project-runtime/TASK_REGISTRY.md",
    }


def _parse_occurrences(text: str) -> list[tuple[str, str]]:
    occurrences: list[tuple[str, str]] = []
    pending_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = FIELD_RE.match(line)
        if match:
            if pending_key is not None:
                occurrences.append((pending_key, ""))
            pending_key = match.group(1)
            value = (match.group(2) or "").strip()
            if value:
                occurrences.append((pending_key, value))
                pending_key = None
            continue

        if pending_key is None:
            continue
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        occurrences.append((pending_key, line))
        pending_key = None

    if pending_key is not None:
        occurrences.append((pending_key, ""))
    return occurrences


def _entries(occurrences: Iterable[tuple[str, str]], start_key: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for key, value in occurrences:
        if key == start_key:
            if current:
                entries.append(current)
            current = {key: value}
            continue
        if current is not None:
            current.setdefault(key, value)
    if current:
        entries.append(current)
    return entries


def _read_root_text(root: Path, relpath: str) -> str | None:
    path = root / relpath
    if not path.exists() or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _accepted_artifacts(root: Path, archive: ArchiveData) -> tuple[list[dict[str, str]], str | None]:
    relpath = "project-runtime/ACCEPTED_ARTIFACTS.md"
    text = _read_root_text(root, relpath)
    source = relpath if text is not None else None
    if text is None:
        text = archive.text_files.get(relpath)
        source = f"{archive.path}:{relpath}" if text is not None else None
    if text is None:
        return [], None
    entries = [entry for entry in _entries(_parse_occurrences(text), "ARTIFACT_ID") if entry.get("STATUS") == "accepted"]
    return entries, source


def _runtime_commit_hashes(root: Path, archive: ArchiveData, accepted: list[dict[str, str]]) -> set[str]:
    hashes: set[str] = set()
    for entry in accepted:
        _add_hash(hashes, entry.get("COMMIT_HASH"))

    for relpath in ("project-runtime/PROJECT_STATE.md", "project-runtime/TASK_REGISTRY.md"):
        text = _read_root_text(root, relpath)
        if text is None:
            text = archive.text_files.get(relpath)
        if text is None:
            continue
        for key, value in _parse_occurrences(text):
            if key in {"LAST_COMMIT_HASH", "COMMIT_HASH"}:
                _add_hash(hashes, value)
    return hashes


def _add_hash(values: set[str], value: str | None) -> None:
    if _is_none(value):
        return
    clean = str(value).strip()
    if re.fullmatch(r"[0-9a-fA-F]{7,64}", clean):
        values.add(clean.lower())


def _find_manifest(archive: ArchiveData) -> tuple[str | None, dict[str, object] | None, str | None]:
    for candidate in sorted(ARCHIVE_MANIFEST_CANDIDATES):
        text = archive.text_files.get(candidate)
        if text is None:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            return candidate, None, str(exc)
        if isinstance(payload, dict):
            return candidate, payload, None
        return candidate, None, "manifest JSON root is not an object"
    return None, None, None


def _path_exists(names: set[str], relpath: str) -> bool:
    path = _normalize_member(relpath)
    if not path:
        return False
    return path in names or any(name.startswith(f"{path}/") for name in names)


def _manifest_path_values(manifest: dict[str, object] | None, keys: Iterable[str]) -> set[str]:
    if manifest is None:
        return set()
    paths: set[str] = set()
    for key in keys:
        _collect_path_values(manifest.get(key), paths)
    return {_normalize_member(path) for path in paths if _normalize_member(path)}


def _collect_path_values(value: object, paths: set[str]) -> None:
    if isinstance(value, str):
        if not _is_none(value):
            paths.add(value)
        return
    if isinstance(value, list):
        for item in value:
            _collect_path_values(item, paths)
        return
    if isinstance(value, dict):
        for key in ("path", "file", "ref", "artifact_ref", "ARTIFACT_REF"):
            item = value.get(key)
            if isinstance(item, str) and not _is_none(item):
                paths.add(item)


def _manifest_exclusions(manifest: dict[str, object] | None) -> dict[str, str]:
    if manifest is None:
        return {}
    exclusions: dict[str, str] = {}
    for key in ("excluded_paths", "excluded_artifacts", "exclusions", "EXCLUDED_PATHS", "EXCLUDED_ARTIFACTS"):
        _collect_exclusions(manifest.get(key), exclusions)
    return exclusions


def _collect_exclusions(value: object, exclusions: dict[str, str]) -> None:
    if isinstance(value, str):
        path = _normalize_member(value)
        if path:
            exclusions[path] = "unspecified"
        return
    if isinstance(value, list):
        for item in value:
            _collect_exclusions(item, exclusions)
        return
    if isinstance(value, dict):
        path = ""
        for key in ("path", "file", "ref", "artifact_ref", "ARTIFACT_REF"):
            item = value.get(key)
            if isinstance(item, str):
                path = _normalize_member(item)
                break
        reason = str(value.get("reason") or value.get("REASON") or "").strip()
        if path and reason:
            exclusions[path] = reason
        elif path:
            exclusions[path] = ""


def _is_excluded(path: str, exclusions: dict[str, str]) -> bool:
    path = _normalize_member(path)
    for excluded, reason in exclusions.items():
        if not reason:
            continue
        if path == excluded or path.startswith(f"{excluded}/"):
            return True
    return False


def _archive_commit_hash(manifest: dict[str, object] | None) -> str | None:
    if manifest is None:
        return None
    for key in ("commit_hash", "last_commit_hash", "LAST_COMMIT_HASH", "COMMIT_HASH", "git_commit"):
        value = manifest.get(key)
        if isinstance(value, str) and not _is_none(value):
            clean = value.strip()
            if re.fullmatch(r"[0-9a-fA-F]{7,64}", clean):
                return clean.lower()
    git = manifest.get("git")
    if isinstance(git, dict):
        for key in ("commit", "commit_hash", "sha"):
            value = git.get(key)
            if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{7,64}", value.strip()):
                return value.strip().lower()
    return None


def _artifact_ref(entry: dict[str, str]) -> str:
    return _normalize_member(entry.get("ARTIFACT_REF", ""))


def _artifact_label(entry: dict[str, str]) -> str:
    return entry.get("ARTIFACT_ID") or entry.get("ARTIFACT_REF") or "UNKNOWN_ARTIFACT"


def _is_product_or_code_artifact(entry: dict[str, str]) -> bool:
    ref = _artifact_ref(entry)
    if not ref:
        return False
    top = ref.split("/", 1)[0]
    if top in NON_PRODUCT_TOP_LEVELS:
        return False
    artifact_type = entry.get("ARTIFACT_TYPE", "").lower()
    if artifact_type and any(marker in artifact_type for marker in ("code", "product", "generated", "source")):
        return True
    return "/" in ref


def _expected_project_input(root: Path) -> bool:
    path = root / "project-input"
    return path.exists() and path.is_dir()


def _verify(root: Path, archive: ArchiveData) -> tuple[dict[str, object], int]:
    findings: list[Finding] = []
    manifest_path, manifest, manifest_error = _find_manifest(archive)
    accepted, accepted_source = _accepted_artifacts(root, archive)

    required_dirs = ["project-runtime", "project-docs"]
    if _expected_project_input(root):
        required_dirs.append("project-input")

    for relpath in required_dirs:
        if not _path_exists(archive.names, relpath):
            findings.append(
                Finding(
                    "archive_missing_path",
                    "error",
                    "Expected archive directory is missing",
                    f"{relpath}/ is expected but is not present in the archive.",
                    [relpath],
                    "Recreate the archive with all expected ASO project directories.",
                )
            )

    if manifest_path is None:
        findings.append(
            Finding(
                "manifest_missing",
                "error",
                "Archive manifest is missing",
                "No archive manifest was found at a supported manifest path.",
                sorted(ARCHIVE_MANIFEST_CANDIDATES),
                "Add an archive manifest with commit evidence, generated_at, and any explicit exclusions.",
            )
        )
    elif manifest_error:
        findings.append(
            Finding(
                "manifest_missing",
                "error",
                "Archive manifest is unreadable",
                f"{manifest_path}: {manifest_error}",
                [manifest_path],
                "Write the archive manifest as a JSON object.",
            )
        )

    exclusions = _manifest_exclusions(manifest)
    included_paths = _manifest_path_values(manifest, ("files", "included_paths", "paths", "archive_members"))
    excluded_artifacts: list[str] = []

    if accepted_source is None:
        findings.append(
            Finding(
                "inconclusive",
                "warning",
                "Accepted artifacts registry is unavailable",
                "No project-runtime/ACCEPTED_ARTIFACTS.md was found in --root or the archive.",
                ["project-runtime/ACCEPTED_ARTIFACTS.md"],
                "Include runtime state or run from a workspace with runtime state to verify accepted artifacts.",
            )
        )

    for entry in accepted:
        ref = _artifact_ref(entry)
        if not ref:
            findings.append(
                Finding(
                    "accepted_artifact_missing",
                    "error",
                    "Accepted artifact has no archive path",
                    f"{_artifact_label(entry)} is accepted but ARTIFACT_REF is empty.",
                    [accepted_source or "project-runtime/ACCEPTED_ARTIFACTS.md"],
                    "Record a bounded ARTIFACT_REF or supersede the accepted artifact.",
                )
            )
            continue
        if _path_exists(archive.names, ref):
            continue
        if _is_excluded(ref, exclusions):
            excluded_artifacts.append(ref)
            continue
        if ref in included_paths:
            findings.append(
                Finding(
                    "packaging_error",
                    "error",
                    "Manifest says accepted artifact is included but archive path is absent",
                    f"{_artifact_label(entry)} is listed for inclusion but {ref} is missing from archive members.",
                    [ref, manifest_path or "archive manifest"],
                    "Regenerate the archive from the manifest input set.",
                )
            )
            continue
        top = ref.split("/", 1)[0]
        if _is_product_or_code_artifact(entry) and not _path_exists(archive.names, top):
            findings.append(
                Finding(
                    "packaging_error",
                    "error",
                    "Accepted product/code folder is missing from archive",
                    f"{_artifact_label(entry)} points to {ref}, but top-level folder {top}/ is absent.",
                    [ref],
                    "Include the product/code folder or explicitly exclude the accepted artifact with a reason in the manifest.",
                )
            )
        else:
            findings.append(
                Finding(
                    "accepted_artifact_missing",
                    "error",
                    "Accepted artifact is missing from archive",
                    f"{_artifact_label(entry)} points to {ref}, which is not present and is not explicitly excluded.",
                    [ref],
                    "Include the accepted artifact or add a manifest exclusion with a reason.",
                )
            )

    runtime_hashes = _runtime_commit_hashes(root, archive, accepted)
    archive_hash = _archive_commit_hash(manifest)
    if runtime_hashes and archive_hash and archive_hash not in runtime_hashes:
        findings.append(
            Finding(
                "commit_mismatch",
                "error",
                "Archive commit hash differs from runtime evidence",
                f"Archive commit {archive_hash} does not match runtime commit evidence: {', '.join(sorted(runtime_hashes))}.",
                [manifest_path or "archive manifest"],
                "Package the archive from the checkpoint commit recorded in runtime state.",
            )
        )
    elif runtime_hashes and archive_hash is None and manifest is not None:
        findings.append(
            Finding(
                "inconclusive",
                "warning",
                "Archive commit evidence is unavailable",
                f"Runtime records commit evidence ({', '.join(sorted(runtime_hashes))}) but the archive manifest has no commit hash.",
                [manifest_path or "archive manifest"],
                "Record commit_hash or git.commit in the archive manifest.",
            )
        )

    summary = _summary(findings)
    status = "failed" if summary["errors"] else ("warning" if summary["warnings"] else "passed")
    report = {
        "tool": "aso",
        "command": "archive verify",
        "status": status,
        "root": str(root),
        "archive": str(archive.path),
        "archive_format": archive.format,
        "archive_prefix": archive.prefix,
        "manifest": {
            "path": manifest_path,
            "present": manifest_path is not None,
            "valid": manifest is not None,
        },
        "accepted_artifacts": {
            "source": accepted_source,
            "count": len(accepted),
            "excluded": sorted(excluded_artifacts),
        },
        "summary": summary,
        "findings": [finding.to_json() for finding in findings],
    }
    return report, EXIT_FINDINGS if summary["errors"] else EXIT_OK


def _summary(findings: list[Finding]) -> dict[str, int]:
    return {
        "errors": sum(1 for finding in findings if finding.severity == "error"),
        "warnings": sum(1 for finding in findings if finding.severity == "warning"),
        "info": sum(1 for finding in findings if finding.severity == "info"),
    }


def _print_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    if not isinstance(summary, dict):
        raise TypeError("internal archive verification summary must be a dictionary")

    print(f"ASO archive verify: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    print(f"Archive: {report['archive']}")
    print(f"Format: {report['archive_format']}")
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
        print(f"aso archive verify: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso archive verify: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def _io_report(root: Path, archive_path: str, finding: Finding) -> dict[str, object]:
    return {
        "tool": "aso",
        "command": "archive verify",
        "status": "io_error" if finding.rule_id.startswith("ARCHIVE_IO") else "failed",
        "root": str(root),
        "archive": archive_path,
        "summary": _summary([finding]),
        "findings": [finding.to_json()],
    }


def run(args: argparse.Namespace) -> int:
    """Run the archive verify command."""
    archive, finding, exit_code = _read_archive(args.archive)
    if archive is None:
        if finding is None:
            raise RuntimeError("archive read failed without a finding")
        report = _io_report(args.root, args.archive, finding)
        _print_text(
            {
                **report,
                "archive_format": "UNKNOWN",
            }
        )
        if args.json_out and not _write_json(args.json_out, report):
            return EXIT_IO_ERROR
        return exit_code

    report, exit_code = _verify(args.root, archive)
    _print_text(report)
    if args.json_out and not _write_json(args.json_out, report):
        return EXIT_IO_ERROR
    return exit_code
