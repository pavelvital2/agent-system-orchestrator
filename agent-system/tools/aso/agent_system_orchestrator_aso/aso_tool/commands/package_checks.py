"""Read-only package repository checks for ASO CLI package mode."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .. import resources

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib


GENERATED_ROOTS = ("project-runtime", "project-input", "project-archive")
GENERATED_ROOT_RULE_IDS = {
    "project-runtime": "LINT_PKG_001",
    "project-input": "LINT_PKG_002",
    "project-archive": "LINT_PKG_003",
}
GENERATED_CACHE_PATTERNS = (
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".coverage",
    "htmlcov",
    "*.pyc",
    "*.pyo",
    "*.log",
    ".DS_Store",
)
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
CANONICAL_PACKAGE_RELPATH = "agent-system/tools/aso/agent_system_orchestrator_aso"
CANONICAL_TOOL_RELPATH = f"{CANONICAL_PACKAGE_RELPATH}/aso_tool"
CANONICAL_RESOURCES_RELPATH = f"{CANONICAL_PACKAGE_RELPATH}/resources"
ROOT_PACKAGE_RELPATH = "agent_system_orchestrator_aso"
LEGACY_TOP_LEVEL_TREE_RELPATHS = (
    "agent-system/tools/aso/commands",
    "agent-system/tools/aso/models",
    "agent-system/tools/aso/parsers",
    "agent-system/tools/aso/rules",
)
CONSOLE_ENTRYPOINT = "agent_system_orchestrator_aso.cli:main"
WORKFLOW_DIR_RELPATH = ".github/workflows"
WORKFLOW_TRIGGER_MARKERS = ("upgrade/",)
RESOURCE_SOURCE_SYNC_RELPATHS = (
    "agent-system/00_start/ORCHESTRATOR_START.md",
    "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json",
    "agent-system/tools/aso/aso.py",
    "agent-system/09_validators/rules/governance_rules.json",
)


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    title: str
    details: str
    files: list[str]
    recommendation: str

    def to_json(self, mode: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.details,
            "path": self.files[0] if self.files else "",
            "title": self.title,
            "details": self.details,
            "files": self.files,
            "recommendation": self.recommendation,
        }
        if mode is not None:
            payload["mode"] = mode
        return payload


@dataclass(frozen=True)
class PackageInspection:
    findings: list[Finding]
    files: dict[str, dict[str, object]]
    generated_roots: dict[str, str]
    readmes: dict[str, str]
    git_tracked_generated_files: list[str]
    git_tracked_root_duplicate_files: list[str]


def inspect_package(root: Path) -> PackageInspection:
    findings: list[Finding] = []
    files: dict[str, dict[str, object]] = {}
    generated_roots: dict[str, str] = {}
    readmes: dict[str, str] = {}
    tracked_generated_files: list[str] = []
    tracked_root_duplicate_files: list[str] = []

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
        return PackageInspection(findings, files, generated_roots, readmes, tracked_generated_files, [])

    _check_required_dirs(root, files, findings)
    _check_package_layout(root, files, findings)
    _check_packaged_resources(root, files, findings)
    tracked_generated_files = _tracked_generated_files(root, findings)
    _check_generated_roots(root, tracked_generated_files, generated_roots, findings)
    _check_generated_cache_files(root, findings)
    tracked_root_duplicate_files = _tracked_root_duplicate_files(root, findings)
    _check_tracked_root_duplicate(tracked_root_duplicate_files, findings)
    _check_workflows(root, files, findings)
    _check_readmes(root, files, readmes, findings)
    _check_gitignore(root, files, findings)

    return PackageInspection(
        findings,
        files,
        generated_roots,
        readmes,
        tracked_generated_files,
        tracked_root_duplicate_files,
    )


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


def _check_package_layout(
    root: Path,
    files: dict[str, dict[str, object]],
    findings: list[Finding],
) -> None:
    canonical_package = root / CANONICAL_PACKAGE_RELPATH
    canonical_tool = root / CANONICAL_TOOL_RELPATH
    root_package = root / ROOT_PACKAGE_RELPATH
    direct_wrapper = root / "agent-system" / "tools" / "aso" / "aso.py"
    pyproject = root / "pyproject.toml"

    for relpath, path in (
        (CANONICAL_PACKAGE_RELPATH, canonical_package),
        (CANONICAL_TOOL_RELPATH, canonical_tool),
    ):
        files[relpath] = {"exists": path.exists(), "type": "directory" if path.is_dir() else "missing"}
        if not path.is_dir():
            findings.append(
                Finding(
                    "PACKAGE_LAYOUT_003",
                    "error",
                    "Canonical ASO package directory is missing",
                    f"Required canonical package directory {relpath}/ is not present.",
                    [relpath],
                    "Move the installable ASO package under agent-system/tools/aso/.",
                )
            )

    files[ROOT_PACKAGE_RELPATH] = {
        "exists": root_package.exists(),
        "type": "directory" if root_package.is_dir() else "absent",
    }
    if root_package.exists():
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_004",
                "error",
                "Root duplicate ASO package is present",
                f"{ROOT_PACKAGE_RELPATH}/ must be absent from the package repository root.",
                [ROOT_PACKAGE_RELPATH],
                "Remove the duplicate root package after moving the canonical package under agent-system/tools/aso/.",
            )
        )

    present_legacy_trees: list[str] = []
    for relpath in LEGACY_TOP_LEVEL_TREE_RELPATHS:
        path = root / relpath
        files[relpath] = {
            "exists": path.exists(),
            "type": "directory" if path.is_dir() else "file" if path.exists() else "absent",
        }
        if path.exists():
            present_legacy_trees.append(relpath)

    if present_legacy_trees:
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_009",
                "error",
                "Legacy top-level ASO Python trees are present",
                (
                    "ASO runtime source must live under "
                    f"{CANONICAL_TOOL_RELPATH}/; remove duplicate top-level tree(s): "
                    f"{', '.join(present_legacy_trees)}."
                ),
                present_legacy_trees,
                "Remove legacy top-level commands/, models/, parsers/, and rules/ trees from agent-system/tools/aso/.",
            )
        )

    if not direct_wrapper.is_file():
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_005",
                "error",
                "Direct ASO wrapper is missing",
                "agent-system/tools/aso/aso.py must remain runnable directly.",
                ["agent-system/tools/aso/aso.py"],
                "Restore the direct wrapper and import the canonical package from agent-system/tools/aso/.",
            )
        )
    else:
        try:
            wrapper_text = direct_wrapper.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                Finding(
                    "PACKAGE_LAYOUT_005",
                    "error",
                    "Direct ASO wrapper is unreadable",
                    f"agent-system/tools/aso/aso.py: {exc}",
                    ["agent-system/tools/aso/aso.py"],
                    "Repair the direct wrapper before running package mode lint.",
                )
            )
        else:
            if "agent_system_orchestrator_aso.aso_tool.aso" not in wrapper_text:
                findings.append(
                    Finding(
                        "PACKAGE_LAYOUT_005",
                        "error",
                        "Direct ASO wrapper does not import canonical package",
                        "agent-system/tools/aso/aso.py must delegate to the canonical ASO package.",
                        ["agent-system/tools/aso/aso.py"],
                        "Update the wrapper to import agent_system_orchestrator_aso.aso_tool.aso.",
                    )
                )
            else:
                _check_direct_wrapper_runs(root, direct_wrapper, findings)

    try:
        pyproject_text = pyproject.read_text(encoding="utf-8")
    except OSError as exc:
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_006",
                "error",
                "pyproject.toml is unreadable",
                f"pyproject.toml: {exc}",
                ["pyproject.toml"],
                "Restore pyproject.toml package discovery metadata.",
            )
        )
        return

    try:
        metadata = tomllib.loads(pyproject_text)
    except tomllib.TOMLDecodeError as exc:
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_006",
                "error",
                "pyproject.toml is invalid",
                f"pyproject.toml could not be parsed: {exc}.",
                ["pyproject.toml"],
                "Restore valid pyproject.toml package discovery metadata.",
            )
        )
        return

    project = metadata.get("project", {})
    scripts = project.get("scripts", {}) if isinstance(project, dict) else {}
    aso_entrypoint = scripts.get("aso") if isinstance(scripts, dict) else None
    tool = metadata.get("tool", {})
    setuptools = tool.get("setuptools", {}) if isinstance(tool, dict) else {}
    packages = setuptools.get("packages", {}) if isinstance(setuptools, dict) else {}
    find_config = packages.get("find", {}) if isinstance(packages, dict) else {}
    where = find_config.get("where", []) if isinstance(find_config, dict) else []
    include = find_config.get("include", []) if isinstance(find_config, dict) else []
    package_data = setuptools.get("package-data", {}) if isinstance(setuptools, dict) else {}
    resource_package_data = (
        package_data.get("agent_system_orchestrator_aso.resources")
        if isinstance(package_data, dict)
        else None
    )

    if aso_entrypoint != CONSOLE_ENTRYPOINT:
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_007",
                "error",
                "Console script entrypoint is not canonical",
                f"pyproject.toml project.scripts.aso must be {CONSOLE_ENTRYPOINT!r}.",
                ["pyproject.toml"],
                "Point the aso console script at agent_system_orchestrator_aso.cli:main.",
            )
        )
    if CANONICAL_PACKAGE_RELPATH.rsplit("/", 1)[0] not in where:
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_006",
                "error",
                "pyproject package discovery root is not canonical",
                "pyproject.toml must set tool.setuptools.packages.find.where to agent-system/tools/aso.",
                ["pyproject.toml"],
                "Point setuptools package discovery at agent-system/tools/aso.",
            )
        )
    if "agent_system_orchestrator_aso*" not in include:
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_006",
                "error",
                "pyproject package include pattern is not canonical",
                "pyproject.toml must include agent_system_orchestrator_aso* packages.",
                ["pyproject.toml"],
                "Keep setuptools package discovery limited to agent_system_orchestrator_aso*.",
            )
        )
    if (
        not isinstance(resource_package_data, list)
        or "RESOURCE_MANIFEST.json" not in resource_package_data
        or "agent-system/**/*" not in resource_package_data
    ):
        findings.append(
            Finding(
                "PACKAGE_RESOURCES_003",
                "error",
                "Resource package data is incomplete",
                (
                    "pyproject.toml must include RESOURCE_MANIFEST.json and agent-system/**/* "
                    "for agent_system_orchestrator_aso.resources package data."
                ),
                ["pyproject.toml"],
                "Declare complete ASO resource package data so wheels include vendored Project Factory resources.",
            )
        )


def _check_packaged_resources(
    root: Path,
    files: dict[str, dict[str, object]],
    findings: list[Finding],
) -> None:
    resources_root = root / CANONICAL_RESOURCES_RELPATH
    files[CANONICAL_RESOURCES_RELPATH] = {
        "exists": resources_root.exists(),
        "type": "directory" if resources_root.is_dir() else "missing",
    }
    if not resources_root.is_dir():
        findings.append(
            Finding(
                "PACKAGE_RESOURCES_001",
                "error",
                "Packaged ASO resources are missing",
                f"Required resource package directory {CANONICAL_RESOURCES_RELPATH}/ is not present.",
                [CANONICAL_RESOURCES_RELPATH],
                "Restore packaged ASO resources so installed vendored project creation can run.",
            )
        )
        return

    manifest_in = root / "MANIFEST.in"
    files["MANIFEST.in"] = {
        "exists": manifest_in.exists(),
        "type": "file" if manifest_in.is_file() else "missing",
    }
    try:
        manifest_text = manifest_in.read_text(encoding="utf-8")
    except OSError as exc:
        findings.append(
            Finding(
                "PACKAGE_RESOURCES_004",
                "error",
                "MANIFEST.in is missing resource graft",
                f"MANIFEST.in could not be read: {exc}",
                ["MANIFEST.in"],
                "Restore MANIFEST.in with the packaged ASO resource graft.",
            )
        )
    else:
        required_manifest_markers = (
            "graft agent-system/tools/aso/agent_system_orchestrator_aso/resources",
            (
                "prune agent-system/tools/aso/agent_system_orchestrator_aso/resources/agent-system/tools/aso/"
                "agent_system_orchestrator_aso/resources/agent-system"
            ),
        )
        missing_markers = [marker for marker in required_manifest_markers if marker not in manifest_text]
        if missing_markers:
            findings.append(
                Finding(
                    "PACKAGE_RESOURCES_004",
                    "error",
                    "MANIFEST.in is missing resource graft",
                    f"MANIFEST.in is missing marker(s): {', '.join(missing_markers)}.",
                    ["MANIFEST.in"],
                    "Keep MANIFEST.in graft/prune rules for packaged ASO resources.",
                )
            )

    check = resources.verify_resource_manifest(resources_root)
    if not check.ok:
        findings.append(
            Finding(
                "PACKAGE_RESOURCES_002",
                "error",
                "Packaged ASO resource manifest is invalid",
                "; ".join(check.errors[:10]),
                [CANONICAL_RESOURCES_RELPATH],
                "Regenerate the packaged resource tree and RESOURCE_MANIFEST.json from a clean ASO source tree.",
            )
        )
        return

    _check_root_resource_sync(root, resources_root, findings)


def _check_root_resource_sync(root: Path, resources_root: Path, findings: list[Finding]) -> None:
    if not all(
        (root / relpath).exists()
        for relpath in (
            "agent-system/00_start",
            "agent-system/02_runtime",
            "agent-system/09_validators",
        )
    ):
        return

    manifest_path = resources_root / resources.RESOURCE_MANIFEST
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        findings.append(
            Finding(
                "PACKAGE_RESOURCES_002",
                "error",
                "Packaged ASO resource manifest is unreadable",
                f"{manifest_path.relative_to(root).as_posix()}: {exc}",
                [CANONICAL_RESOURCES_RELPATH],
                "Restore a readable packaged resource manifest.",
            )
        )
        return

    manifest_files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(manifest_files, dict):
        findings.append(
            Finding(
                "PACKAGE_RESOURCES_002",
                "error",
                "Packaged ASO resource manifest is invalid",
                "RESOURCE_MANIFEST.json files entry is missing or invalid.",
                [CANONICAL_RESOURCES_RELPATH],
                "Regenerate RESOURCE_MANIFEST.json from a clean ASO source tree.",
            )
        )
        return

    mismatches: list[str] = []
    for relpath in RESOURCE_SOURCE_SYNC_RELPATHS:
        source_path = root / relpath
        packaged_path = resources_root / relpath
        if not source_path.is_file():
            mismatches.append(f"{relpath} missing from root source")
            continue
        if not packaged_path.is_file():
            mismatches.append(f"{relpath} missing from packaged resources")
            continue
        metadata = manifest_files.get(relpath)
        if not isinstance(metadata, dict):
            mismatches.append(f"{relpath} missing from resource manifest")
            continue
        try:
            source_data = source_path.read_bytes()
            packaged_data = packaged_path.read_bytes()
        except OSError as exc:
            mismatches.append(f"{relpath} could not be read: {exc}")
            continue
        source_hash = hashlib.sha256(source_data).hexdigest()
        packaged_hash = hashlib.sha256(packaged_data).hexdigest()
        manifest_hash = metadata.get("sha256")
        manifest_size = metadata.get("size")
        if source_data != packaged_data or source_hash != packaged_hash:
            mismatches.append(f"{relpath} root sha256={source_hash} packaged sha256={packaged_hash}")
        if manifest_hash != packaged_hash or manifest_size != len(packaged_data):
            mismatches.append(f"{relpath} manifest metadata does not match packaged resource")

    if mismatches:
        findings.append(
            Finding(
                "PACKAGE_RESOURCES_005",
                "error",
                "Packaged ASO resources differ from root source resources",
                "; ".join(mismatches[:10]),
                RESOURCE_SOURCE_SYNC_RELPATHS,
                "Regenerate packaged ASO resources from the root source tree before building wheels or sdists.",
            )
        )


def _check_direct_wrapper_runs(root: Path, direct_wrapper: Path, findings: list[Finding]) -> None:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, str(direct_wrapper.resolve()), "--help"],
            cwd=str(root),
            check=False,
            text=True,
            capture_output=True,
            timeout=10,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_005",
                "error",
                "Direct ASO wrapper is not runnable",
                f"agent-system/tools/aso/aso.py --help failed to run: {exc}.",
                ["agent-system/tools/aso/aso.py"],
                "Repair the direct wrapper so it can run from the repository root.",
            )
        )
        return

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "direct wrapper returned a non-zero exit code").strip()
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_005",
                "error",
                "Direct ASO wrapper is not runnable",
                details,
                ["agent-system/tools/aso/aso.py"],
                "Repair the direct wrapper so it can run from the repository root.",
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
                    GENERATED_ROOT_RULE_IDS[name],
                    "error",
                    f"Root {name} is tracked",
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


def _tracked_cache_files(root: Path, findings: list[Finding]) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
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
                "git executable was not found, so package mode cannot verify generated cache tracking.",
                list(GENERATED_CACHE_PATTERNS),
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
                "Generated cache tracking check failed",
                (result.stderr or result.stdout or "git ls-files failed").strip(),
                list(GENERATED_CACHE_PATTERNS),
                "Repair the Git worktree before running package mode lint.",
            )
        )
        return []

    tracked = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return [relpath for relpath in tracked if _is_generated_cache_file(relpath)]


def _check_generated_cache_files(root: Path, findings: list[Finding]) -> None:
    tracked_cache_files = _tracked_cache_files(root, findings)
    if not tracked_cache_files:
        return

    findings.append(
        Finding(
            "LINT_PKG_006",
            "error",
            "Generated cache files are tracked",
            f"Git tracks generated cache artifact(s): {', '.join(sorted(tracked_cache_files)[:10])}.",
            sorted(tracked_cache_files),
            "Remove generated cache files from package tracking and keep them ignored locally.",
        )
    )


def _tracked_root_duplicate_files(root: Path, findings: list[Finding]) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", ROOT_PACKAGE_RELPATH],
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
                "git executable was not found, so package mode cannot verify root duplicate tracking.",
                [ROOT_PACKAGE_RELPATH],
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
                "Root duplicate tracking check failed",
                (result.stderr or result.stdout or "git ls-files failed").strip(),
                [ROOT_PACKAGE_RELPATH],
                "Repair the Git worktree before running package layout verification.",
            )
        )
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _check_tracked_root_duplicate(tracked_files: list[str], findings: list[Finding]) -> None:
    if not tracked_files:
        return

    findings.append(
        Finding(
            "PACKAGE_LAYOUT_004",
            "error",
            "Root duplicate ASO package is tracked",
            f"Git tracks forbidden root duplicate package files: {', '.join(sorted(tracked_files)[:10])}.",
            sorted(tracked_files),
            "Remove the duplicate root package from Git tracking.",
        )
    )


def _check_workflows(root: Path, files: dict[str, dict[str, object]], findings: list[Finding]) -> None:
    workflows = root / WORKFLOW_DIR_RELPATH
    workflow_files = sorted(workflows.glob("*.yml")) + sorted(workflows.glob("*.yaml")) if workflows.is_dir() else []
    files[WORKFLOW_DIR_RELPATH] = {
        "exists": workflows.exists(),
        "type": "directory" if workflows.is_dir() else "missing",
        "workflow_count": len(workflow_files),
    }
    if not workflow_files:
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_008",
                "error",
                "Governance workflow is missing",
                "No .github/workflows/*.yml or *.yaml file was found.",
                [WORKFLOW_DIR_RELPATH],
                "Restore a governance workflow before package-layout verification.",
            )
        )
        return

    readable_texts: list[str] = []
    unreadable_files: list[str] = []
    for path in workflow_files:
        relpath = path.relative_to(root).as_posix()
        try:
            readable_texts.append(path.read_text(encoding="utf-8"))
        except OSError:
            unreadable_files.append(relpath)

    if unreadable_files:
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_008",
                "error",
                "Governance workflow is unreadable",
                f"Workflow file(s) are unreadable: {', '.join(unreadable_files)}.",
                unreadable_files,
                "Repair workflow file permissions before package-layout verification.",
            )
        )
        return

    combined = "\n".join(readable_texts)
    missing_markers = [marker for marker in WORKFLOW_TRIGGER_MARKERS if marker not in combined]
    if missing_markers:
        findings.append(
            Finding(
                "PACKAGE_LAYOUT_008",
                "error",
                "Governance workflow trigger surface is incomplete",
                f"Workflow files are missing trigger marker(s): {', '.join(missing_markers)}.",
                [path.relative_to(root).as_posix() for path in workflow_files],
                "Keep governance workflow triggers for upgrade/** branches.",
            )
        )


def _is_generated_cache_file(relpath: str) -> bool:
    name = Path(relpath).name
    parts = set(Path(relpath).parts)
    if parts.intersection({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".nox", "htmlcov"}):
        return True
    return name in {".coverage", ".DS_Store"} or name.endswith((".pyc", ".pyo", ".log"))


def _claims_no_cli_wrapper(text: str) -> bool:
    patterns = (
        r"\bno\s+(?:(?:separate|implemented|full|current)\s+){0,4}(?:aso\s+)?(?:cli|command[- ]line)\s+wrapper\b",
        r"\bwithout\s+(?:an?\s+)?(?:(?:separate|implemented|full|current)\s+){0,4}(?:aso\s+)?(?:cli|command[- ]line)\s+wrapper\b",
        r"\bdoes\s+not\s+(?:claim|include|ship|provide|have)\s+(?:an?\s+)?(?:(?:separate|implemented|full|current)\s+){0,4}(?:aso\s+)?(?:cli|command[- ]line)(?:\s+wrapper)?\b",
        r"\bdoesn't\s+(?:claim|include|ship|provide|have)\s+(?:an?\s+)?(?:(?:separate|implemented|full|current)\s+){0,4}(?:aso\s+)?(?:cli|command[- ]line)(?:\s+wrapper)?\b",
    )
    for line in text.splitlines():
        lowered = line.lower()
        if any(re.search(pattern, lowered) for pattern in patterns) and not _is_qualified_historical_cli_line(lowered):
            return True
    return False


def _is_qualified_historical_cli_line(lowered_line: str) -> bool:
    historical_terms = ("earlier", "previous", "historical", "prior", "before", "legacy")
    current_cli_terms = (
        "now includes",
        "currently includes",
        "now provides",
        "currently provides",
        "aso v0 now includes",
        "aso v0 includes",
    )
    return any(term in lowered_line for term in historical_terms) and any(
        term in lowered_line for term in current_cli_terms
    )


def _check_readmes(
    root: Path,
    files: dict[str, dict[str, object]],
    readmes: dict[str, str],
    findings: list[Finding],
) -> None:
    aso_exists = (root / "agent-system" / "tools" / "aso").exists()
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
        if aso_exists and _claims_no_cli_wrapper(text):
            readmes[relpath] = "contradicts-aso-cli"
            findings.append(
                Finding(
                    "LINT_PKG_004",
                    "error",
                    "README claims no CLI wrapper",
                    f"{relpath} claims the package has no CLI wrapper, but agent-system/tools/aso exists.",
                    [relpath, "agent-system/tools/aso"],
                    "Update README wording to describe the read-only ASO helper CLI.",
                )
            )
            continue

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
                "LINT_PKG_005",
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
                "LINT_PKG_005",
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
                "LINT_PKG_005",
                "error",
                ".gitignore lacks generated workspace artifact rules",
                f".gitignore is missing: {', '.join(missing_patterns)}.",
                [".gitignore"],
                "Add root ignore rules for generated workspace artifact directories.",
            )
        )
