"""Project Factory P0 project creation commands."""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .. import lockfile


EXIT_OK = 0
EXIT_FAIL = 1

REQUIRED_GITIGNORE_ENTRIES = (
    "/project-input/",
    "/project-runtime/",
    "/project-archive/",
    "/.tmp/",
    "/tmp/",
    "/.venv/",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.crt",
    "*.p12",
    "*.pfx",
    "*.cookie",
    "cookies.json",
    "secrets/",
    "private/",
    "**/__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".coverage",
    "htmlcov/",
    ".DS_Store",
)

LOCAL_ROOTS = ("project-input", "project-runtime", "project-archive")
VENDORED_DIR_NAMES_EXCLUDED = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp",
    ".venv",
    "__pycache__",
    "htmlcov",
    "logs",
    "private",
    "project-archive",
    "project-input",
    "project-runtime",
    "secrets",
    "tmp",
}
VENDORED_FILE_NAMES_EXCLUDED = {
    ".coverage",
    ".DS_Store",
    ".env",
    "cookies.json",
}
VENDORED_SUFFIXES_EXCLUDED = (
    ".cookie",
    ".crt",
    ".key",
    ".log",
    ".p12",
    ".pem",
    ".pfx",
    ".pyc",
    ".pyo",
)
SLUG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


@dataclass(frozen=True)
class CreateSummary:
    target: Path
    created_entries: tuple[str, ...]
    copied_files: int
    skipped_paths: tuple[str, ...]


def run_create(args: object) -> int:
    """Run `aso project create --local`."""

    try:
        target = Path(str(args.target)).expanduser()
        repo_url = _normalize_repo_url(getattr(args, "repo_url", None))
        summary = create_project(
            target=target,
            project_name=str(args.name),
            project_slug=str(args.slug),
            profile=str(args.profile),
            repo_url=repo_url,
            default_branch=str(args.branch),
            engine_mode=str(args.engine_mode),
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAIL

    print("ASO project create")
    print(f"Target: {summary.target}")
    print(f"Project: {args.name} ({args.slug})")
    print(f"Engine mode: {args.engine_mode}")
    print(f"Package version: {lockfile.PACKAGE_VERSION}")
    print(f"Runtime schema: {lockfile.RUNTIME_SCHEMA_VERSION}")
    print("Created entries:")
    for entry in summary.created_entries:
        print(f"- {entry}")
    print(f"Vendored files: {summary.copied_files}")
    print("Next step:")
    print(f"PYTHONDONTWRITEBYTECODE=1 python3 {summary.target / 'agent-system/tools/aso/aso.py'} status --root {summary.target} --mode package")
    return EXIT_OK


def create_project(
    *,
    target: Path,
    project_name: str,
    project_slug: str,
    profile: str = lockfile.DEFAULT_PROFILE,
    repo_url: str | None = None,
    default_branch: str = lockfile.DEFAULT_BRANCH,
    engine_mode: str = lockfile.DEFAULT_ENGINE_MODE,
    source_agent_system: Path | None = None,
) -> CreateSummary:
    """Create a clean local Project Factory P0 workspace."""

    target = target.expanduser()
    _validate_create_inputs(
        target=target,
        project_name=project_name,
        project_slug=project_slug,
        profile=profile,
        default_branch=default_branch,
        engine_mode=engine_mode,
    )

    if target.exists() and not target.is_dir():
        raise ValueError(f"target exists and is not a directory: {target}")
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"target must be empty: {target}")

    target.mkdir(parents=True, exist_ok=True)
    lock = lockfile.generate_lockfile(
        project_name=project_name,
        project_slug=project_slug,
        profile=profile,
        repo_url=repo_url,
        default_branch=default_branch,
        engine_mode=engine_mode,
    )
    lockfile.write_lockfile(target / lockfile.LOCKFILE_NAME, lock)
    (target / ".gitignore").write_text(_gitignore_text(), encoding="utf-8")
    (target / "README.md").write_text(
        _readme_text(project_name=project_name, project_slug=project_slug),
        encoding="utf-8",
    )
    for root_name in LOCAL_ROOTS:
        (target / root_name).mkdir()

    copied_files = 0
    skipped_paths: tuple[str, ...] = ()
    if engine_mode == lockfile.DEFAULT_ENGINE_MODE:
        source = source_agent_system or _default_source_agent_system()
        copied_files, skipped_paths = _copy_vendored_agent_system(source, target / "agent-system")

    return CreateSummary(
        target=target,
        created_entries=(
            ".gitignore",
            "README.md",
            "agent-system/",
            "aso.lock",
            "project-archive/",
            "project-input/",
            "project-runtime/",
        ),
        copied_files=copied_files,
        skipped_paths=skipped_paths,
    )


def _validate_create_inputs(
    *,
    target: Path,
    project_name: str,
    project_slug: str,
    profile: str,
    default_branch: str,
    engine_mode: str,
) -> None:
    if not str(target):
        raise ValueError("target is required")
    if not project_name.strip():
        raise ValueError("name is required")
    if not project_slug.strip() or not SLUG_RE.fullmatch(project_slug):
        raise ValueError("slug must start with an alphanumeric character and contain only letters, numbers, dots, dashes, or underscores")
    if not profile.strip():
        raise ValueError("profile is required")
    if not default_branch.strip():
        raise ValueError("branch is required")
    if engine_mode != lockfile.DEFAULT_ENGINE_MODE:
        raise ValueError("engine-mode must be vendored")


def _normalize_repo_url(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    return text


def _default_source_agent_system() -> Path:
    return Path(__file__).resolve().parents[5]


def _gitignore_text() -> str:
    lines = [
        "# ASO Project Factory local workspace boundary",
        *REQUIRED_GITIGNORE_ENTRIES,
        "",
    ]
    return "\n".join(lines)


def _readme_text(*, project_name: str, project_slug: str) -> str:
    return (
        f"# {project_name}\n\n"
        "Generated by ASO Project Factory P0.\n\n"
        "## Local ASO commands\n\n"
        "```bash\n"
        "PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py status --root . --mode package\n"
        "```\n\n"
        "## Publication boundary\n\n"
        "The local ASO working roots `project-input/`, `project-runtime/`, and "
        "`project-archive/` are intentionally ignored and should not be tracked.\n\n"
        f"Project slug: `{project_slug}`\n"
    )


def _copy_vendored_agent_system(source: Path, destination: Path) -> tuple[int, tuple[str, ...]]:
    if not source.is_dir():
        raise ValueError(f"agent-system source is not a readable directory: {source}")

    destination.mkdir(parents=True, exist_ok=True)
    copied_files = 0
    skipped: list[str] = []

    for source_path in sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()):
        relative = source_path.relative_to(source)
        if _exclude_vendored_path(relative, is_dir=source_path.is_dir() or source_path.is_symlink()):
            skipped.append(relative.as_posix())
            continue
        if source_path.is_symlink():
            skipped.append(relative.as_posix())
            continue
        destination_path = destination / relative
        if source_path.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            continue
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        copied_files += 1

    return copied_files, tuple(skipped)


def _exclude_vendored_path(relative: Path, *, is_dir: bool) -> bool:
    parts = relative.parts
    if any(part in VENDORED_DIR_NAMES_EXCLUDED for part in parts):
        return True
    if any(part.startswith("aso_upgrade_") for part in parts):
        return True
    name = relative.name
    if name in VENDORED_FILE_NAMES_EXCLUDED:
        return True
    if name.startswith(".env."):
        return True
    if name.endswith(VENDORED_SUFFIXES_EXCLUDED):
        return True
    if is_dir and name.endswith(".egg-info"):
        return True
    return False
