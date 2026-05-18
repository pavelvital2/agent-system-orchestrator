"""Read-only package repository checks for ASO CLI package mode."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


GENERATED_ROOTS = ("project-runtime", "project-input", "project-archive")
REQUIRED_GITIGNORE_PATTERNS = tuple(f"/{name}/" for name in GENERATED_ROOTS)
README_PATHS = ("README.md", "agent-system/README.md")
README_REQUIRED_TERMS = (
    ("ASO CLI path", "agent-system/tools/aso/aso.py"),
    ("package mode", "--mode package"),
    ("workspace mode", "--mode workspace"),
    ("status command", "status"),
    ("lint command", "lint"),
    ("read-only behavior", "read-only"),
    ("no mutation/dispatch/checkpoint commands", "mutation, dispatch, or checkpoint"),
)


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
class PackageInspection:
    findings: list[Finding]
    files: dict[str, dict[str, object]]
    generated_roots: dict[str, str]
    readmes: dict[str, str]
    git_tracked_generated_files: list[str]


def inspect_package(root: Path) -> PackageInspection:
    findings: list[Finding] = []
    files: dict[str, dict[str, object]] = {}
    generated_roots: dict[str, str] = {}
    readmes: dict[str, str] = {}
    tracked_generated_files: list[str] = []

    if not root.exists() or not root.is_dir():
        findings.append(
            Finding(
                "PACKAGE_IO_001",
                "error",
                "Package root is unreadable",
                f"{root} is not an existing readable directory.",
                [str(root)],
                "Pass --root pointing at the ASO package repository root.",
            )
        )
        return PackageInspection(findings, files, generated_roots, readmes, tracked_generated_files)

    _check_required_dirs(root, files, findings)
    tracked_generated_files = _tracked_generated_files(root, findings)
    _check_generated_roots(root, tracked_generated_files, generated_roots, findings)
    _check_readmes(root, files, readmes, findings)
    _check_gitignore(root, files, findings)

    return PackageInspection(findings, files, generated_roots, readmes, tracked_generated_files)


def consistency(findings: list[Finding]) -> str:
    severities = {finding.severity for finding in findings}
    if "error" in severities:
        return "FAIL"
    if "warning" in severities:
        return "WARN"
    return "PASS"


def _check_required_dirs(
    root: Path,
    files: dict[str, dict[str, object]],
    findings: list[Finding],
) -> None:
    required_dirs = (
        ("agent-system", "PACKAGE_LAYOUT_001", "agent-system directory is missing"),
        ("agent-system/tools/aso", "PACKAGE_LAYOUT_002", "ASO tool directory is missing"),
    )
    for relpath, rule_id, title in required_dirs:
        path = root / relpath
        exists = path.exists()
        is_dir = path.is_dir()
        files[relpath] = {"exists": exists, "type": "directory" if is_dir else "missing"}
        if not is_dir:
            findings.append(
                Finding(
                    rule_id,
                    "error",
                    title,
                    f"Required package directory {relpath}/ is not present.",
                    [relpath],
                    "Run package mode from the repository root that contains agent-system/.",
                )
            )


def _tracked_generated_files(root: Path, findings: list[Finding]) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", *GENERATED_ROOTS],
            check=False,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        findings.append(
            Finding(
                "PACKAGE_GIT_001",
                "error",
                "Git is unavailable",
                "git executable was not found, so package mode cannot verify generated root tracking.",
                list(GENERATED_ROOTS),
                "Run package mode in an environment with git available.",
            )
        )
        return []

    if result.returncode != 0:
        if "not a git repository" in result.stderr.lower():
            return []
        findings.append(
            Finding(
                "PACKAGE_GIT_002",
                "error",
                "Generated root tracking check failed",
                (result.stderr or result.stdout or "git ls-files failed").strip(),
                list(GENERATED_ROOTS),
                "Repair the Git worktree before running package mode lint.",
            )
        )
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _check_generated_roots(
    root: Path,
    tracked_files: list[str],
    generated_roots: dict[str, str],
    findings: list[Finding],
) -> None:
    tracked_by_root: dict[str, list[str]] = {name: [] for name in GENERATED_ROOTS}
    for relpath in tracked_files:
        first_part = relpath.split("/", 1)[0]
        if first_part in tracked_by_root:
            tracked_by_root[first_part].append(relpath)

    for name in GENERATED_ROOTS:
        path = root / name
        if tracked_by_root[name]:
            generated_roots[name] = "tracked"
            findings.append(
                Finding(
                    "PACKAGE_TRACKING_001",
                    "error",
                    "Generated workspace root is tracked",
                    (
                        f"{name}/ is a generated workspace artifact root, but Git tracks: "
                        f"{', '.join(sorted(tracked_by_root[name])[:5])}"
                    ),
                    sorted(tracked_by_root[name]),
                    f"Remove {name}/ from package tracking; it may exist locally only as ignored workspace data.",
                )
            )
        elif path.exists():
            generated_roots[name] = "present-untracked"
        else:
            generated_roots[name] = "absent"


def _check_readmes(
    root: Path,
    files: dict[str, dict[str, object]],
    readmes: dict[str, str],
    findings: list[Finding],
) -> None:
    for relpath in README_PATHS:
        path = root / relpath
        if not path.is_file():
            files[relpath] = {"exists": path.exists(), "type": "missing"}
            readmes[relpath] = "missing"
            findings.append(
                Finding(
                    "PACKAGE_DOCS_001",
                    "error",
                    "README file is missing",
                    f"{relpath} is required for package CLI guidance.",
                    [relpath],
                    "Restore the README and document ASO package/workspace CLI mode usage.",
                )
            )
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            files[relpath] = {"exists": True, "type": "file", "error": str(exc)}
            readmes[relpath] = "unreadable"
            findings.append(
                Finding(
                    "PACKAGE_DOCS_002",
                    "error",
                    "README file is unreadable",
                    f"{relpath}: {exc}",
                    [relpath],
                    "Repair README permissions or encoding and rerun package mode lint.",
                )
            )
            continue

        files[relpath] = {"exists": True, "type": "file", "bytes": len(text.encode("utf-8"))}
        missing_terms = [
            label
            for label, term in README_REQUIRED_TERMS
            if term.lower() not in text.lower()
        ]
        if missing_terms:
            readmes[relpath] = "inconsistent"
            findings.append(
                Finding(
                    "PACKAGE_DOCS_003",
                    "error",
                    "README CLI wording is inconsistent",
                    f"{relpath} is missing ASO CLI wording for: {', '.join(missing_terms)}.",
                    [relpath],
                    "Document read-only status/lint usage with --mode package and --mode workspace.",
                )
            )
        else:
            readmes[relpath] = "consistent"


def _check_gitignore(
    root: Path,
    files: dict[str, dict[str, object]],
    findings: list[Finding],
) -> None:
    path = root / ".gitignore"
    if not path.is_file():
        files[".gitignore"] = {"exists": path.exists(), "type": "missing"}
        findings.append(
            Finding(
                "PACKAGE_IGNORE_001",
                "error",
                ".gitignore is missing",
                ".gitignore must ignore generated workspace artifact roots.",
                [".gitignore"],
                "Restore .gitignore with root project-runtime/, project-input/, and project-archive/ rules.",
            )
        )
        return

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        files[".gitignore"] = {"exists": True, "type": "file", "error": str(exc)}
        findings.append(
            Finding(
                "PACKAGE_IGNORE_002",
                "error",
                ".gitignore is unreadable",
                f".gitignore: {exc}",
                [".gitignore"],
                "Repair .gitignore permissions or encoding and rerun package mode lint.",
            )
        )
        return

    files[".gitignore"] = {"exists": True, "type": "file", "bytes": len(text.encode("utf-8"))}
    active_patterns = {
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    missing_patterns = [
        pattern for pattern in REQUIRED_GITIGNORE_PATTERNS if pattern not in active_patterns
    ]
    if missing_patterns:
        findings.append(
            Finding(
                "PACKAGE_IGNORE_003",
                "error",
                ".gitignore lacks generated workspace artifact rules",
                f".gitignore is missing: {', '.join(missing_patterns)}.",
                [".gitignore"],
                "Add root ignore rules for generated workspace artifact directories.",
            )
        )
