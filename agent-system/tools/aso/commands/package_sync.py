"""Read-only verification that direct and bundled ASO tool copies match."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3

SOURCE_TOOL_RELPATH = PurePosixPath("agent-system/tools/aso")
BUNDLED_TOOL_RELPATH = PurePosixPath("agent_system_orchestrator_aso/aso_tool")
GENERATED_ARTIFACT_PATTERNS = ("__pycache__/", "*.pyc")
EXCLUDED_RELPATH_PREFIXES = ("tests/",)


@dataclass(frozen=True)
class FileFingerprint:
    relpath: str
    sha256: str
    size: int


@dataclass(frozen=True)
class SyncMismatch:
    rule_id: str
    severity: str
    title: str
    details: str
    path: str
    source_sha256: str | None = None
    bundled_sha256: str | None = None

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "message": self.details,
            "details": self.details,
            "path": self.path,
        }
        if self.source_sha256 is not None:
            payload["source_sha256"] = self.source_sha256
        if self.bundled_sha256 is not None:
            payload["bundled_sha256"] = self.bundled_sha256
        return payload


def _normalize_relpath(path: Path, root: Path) -> str:
    return PurePosixPath(path.relative_to(root).as_posix()).as_posix()


def _is_generated_artifact(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    return "__pycache__" in rel.parts or path.name.endswith(".pyc")


def _is_excluded_relpath(relpath: str) -> bool:
    return any(
        relpath == prefix.rstrip("/") or relpath.startswith(prefix)
        for prefix in EXCLUDED_RELPATH_PREFIXES
    )


def _fingerprint_file(path: Path, relpath: str) -> FileFingerprint:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return FileFingerprint(relpath=relpath, sha256=digest.hexdigest(), size=size)


def _fingerprint_tree(root: Path) -> tuple[dict[str, FileFingerprint], list[SyncMismatch]]:
    files: dict[str, FileFingerprint] = {}
    mismatches: list[SyncMismatch] = []

    if not root.exists() or not root.is_dir():
        return files, [
            SyncMismatch(
                "PACKAGE_SYNC_IO_001",
                "error",
                "ASO sync root is unreadable",
                f"{root} is not an existing readable directory.",
                str(root),
            )
        ]

    for path in sorted(root.rglob("*")):
        if _is_generated_artifact(path, root):
            continue
        if not path.is_file():
            continue
        relpath = _normalize_relpath(path, root)
        if _is_excluded_relpath(relpath):
            continue
        try:
            files[relpath] = _fingerprint_file(path, relpath)
        except OSError as exc:
            mismatches.append(
                SyncMismatch(
                    "PACKAGE_SYNC_IO_002",
                    "error",
                    "ASO sync file is unreadable",
                    f"{relpath}: {exc}",
                    relpath,
                )
            )

    return files, mismatches


def _is_command_file(relpath: str) -> bool:
    return relpath.startswith("commands/") and relpath.endswith(".py")


def _compare_fingerprints(
    source_files: dict[str, FileFingerprint],
    bundled_files: dict[str, FileFingerprint],
) -> list[SyncMismatch]:
    mismatches: list[SyncMismatch] = []

    for relpath in sorted(set(source_files) - set(bundled_files)):
        source = source_files[relpath]
        mismatches.append(
            SyncMismatch(
                "PACKAGE_SYNC_001",
                "error",
                "Bundled ASO file is missing",
                f"{relpath} exists in direct ASO source but is missing from the bundled ASO copy.",
                relpath,
                source_sha256=source.sha256,
            )
        )

    for relpath in sorted(set(source_files) & set(bundled_files)):
        source = source_files[relpath]
        bundled = bundled_files[relpath]
        if source.sha256 == bundled.sha256:
            continue
        mismatches.append(
            SyncMismatch(
                "PACKAGE_SYNC_002",
                "error",
                "Bundled ASO file is stale",
                f"{relpath} content differs between direct ASO source and bundled ASO copy.",
                relpath,
                source_sha256=source.sha256,
                bundled_sha256=bundled.sha256,
            )
        )

    for relpath in sorted(set(bundled_files) - set(source_files)):
        bundled = bundled_files[relpath]
        if _is_command_file(relpath):
            rule_id = "PACKAGE_SYNC_003"
            title = "Bundled-only ASO command file"
            details = (
                f"{relpath} exists only in the bundled ASO copy. Bundled command files "
                "must have a matching direct ASO source file."
            )
        else:
            rule_id = "PACKAGE_SYNC_004"
            title = "Bundled-only ASO file"
            details = f"{relpath} exists only in the bundled ASO copy."
        mismatches.append(
            SyncMismatch(
                rule_id,
                "error",
                title,
                details,
                relpath,
                bundled_sha256=bundled.sha256,
            )
        )

    return mismatches


def _summary(
    source_files: dict[str, FileFingerprint],
    bundled_files: dict[str, FileFingerprint],
    mismatches: list[SyncMismatch],
) -> dict[str, object]:
    return {
        "source_files": len(source_files),
        "bundled_files": len(bundled_files),
        "mismatches": len(mismatches),
        "errors": sum(1 for mismatch in mismatches if mismatch.severity == "error"),
        "warnings": sum(1 for mismatch in mismatches if mismatch.severity == "warning"),
        "ignored_generated_artifacts": list(GENERATED_ARTIFACT_PATTERNS),
        "excluded_paths": list(EXCLUDED_RELPATH_PREFIXES),
    }


def build_report(root: Path, strict: bool) -> tuple[dict[str, object], int]:
    source_root = root / Path(SOURCE_TOOL_RELPATH)
    bundled_root = root / Path(BUNDLED_TOOL_RELPATH)

    source_files, source_mismatches = _fingerprint_tree(source_root)
    bundled_files, bundled_mismatches = _fingerprint_tree(bundled_root)
    mismatches = [
        *source_mismatches,
        *bundled_mismatches,
        *_compare_fingerprints(source_files, bundled_files),
    ]
    summary = _summary(source_files, bundled_files, mismatches)

    io_error = any(mismatch.rule_id.startswith("PACKAGE_SYNC_IO_") for mismatch in mismatches)
    failed = bool(mismatches)
    if io_error:
        status = "io_error"
        exit_code = EXIT_IO_ERROR
    elif failed:
        status = "failed"
        exit_code = EXIT_FINDINGS
    else:
        status = "passed"
        exit_code = EXIT_OK

    return {
        "tool": "aso",
        "command": "package-sync verify",
        "status": status,
        "root": str(root),
        "strict": strict,
        "source_root": str(source_root),
        "bundled_root": str(bundled_root),
        "summary": summary,
        "mismatches": [mismatch.to_json() for mismatch in mismatches],
    }, exit_code


def _print_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    if not isinstance(summary, dict):
        raise TypeError("internal package-sync report summary must be a dictionary")

    print(f"ASO package-sync verify: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    print(f"Strict: {report['strict']}")
    print(f"Source root: {report['source_root']}")
    print(f"Bundled root: {report['bundled_root']}")
    print(f"Source files: {summary['source_files']}")
    print(f"Bundled files: {summary['bundled_files']}")
    print(f"Mismatches: {summary['mismatches']}")
    for mismatch in report["mismatches"]:
        if not isinstance(mismatch, dict):
            continue
        print(f"- {mismatch['severity']} {mismatch['rule_id']}: {mismatch['title']}")


def run_verify(args: argparse.Namespace) -> int:
    """Run read-only package sync verification."""
    report, exit_code = build_report(args.root, args.strict)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_text(report)
    return exit_code
