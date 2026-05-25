from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


FORBIDDEN_ROOTS = ("project-input/", "project-runtime/", "project-archive/", ".venv/")
ALLOWED_UNTRACKED_PATHS = ("MANIFEST.in",)
ALLOWED_UNTRACKED_PREFIXES = (
    "agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/",
    "agent-system/tools/aso/agent_system_orchestrator_aso/resources/",
    "agent-system/tools/aso/tests/",
)


def _git_paths(repo_root: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def _is_forbidden_root(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(normalized == root.rstrip("/") or normalized.startswith(root) for root in FORBIDDEN_ROOTS)


def _copy_file(repo_root: Path, destination: Path, relpath: str) -> None:
    if _is_forbidden_root(relpath):
        return
    source = repo_root / relpath
    if not source.is_file():
        return
    target = destination / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def create_current_source_snapshot(repo_root: Path, destination: Path) -> Path:
    """Create a committed temp source tree with current allowed worktree edits."""

    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    for relpath in _git_paths(repo_root, "ls-files", "-z"):
        _copy_file(repo_root, destination, relpath)

    for relpath in _git_paths(repo_root, "ls-files", "--others", "--exclude-standard", "-z"):
        normalized = relpath.replace("\\", "/")
        if normalized in ALLOWED_UNTRACKED_PATHS or any(
            normalized.startswith(prefix) for prefix in ALLOWED_UNTRACKED_PREFIXES
        ):
            _copy_file(repo_root, destination, relpath)

    subprocess.run(["git", "init", "-q"], cwd=destination, check=True)
    subprocess.run(["git", "config", "user.email", "aso-test@example.invalid"], cwd=destination, check=True)
    subprocess.run(["git", "config", "user.name", "ASO Test"], cwd=destination, check=True)
    subprocess.run(["git", "add", "."], cwd=destination, check=True)
    subprocess.run(["git", "commit", "-m", "current source snapshot"], cwd=destination, check=True, stdout=subprocess.DEVNULL)
    return destination
