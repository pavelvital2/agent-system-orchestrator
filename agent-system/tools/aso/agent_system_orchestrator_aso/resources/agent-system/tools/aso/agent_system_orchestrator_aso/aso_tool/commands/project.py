"""Project Factory project creation and verification commands."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .. import lockfile, resources
from . import state_init, state_render


EXIT_OK = 0
EXIT_FAIL = 1
EXIT_IO_ERROR = 3

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
FORBIDDEN_TRACKED_ROOTS = (
    "project-input",
    "project-runtime",
    "project-archive",
    ".venv",
    ".tmp",
    "tmp",
    "secrets",
    "private",
)
REFERENCE_ENGINE_MODE = "reference"
VENDORED_DIR_NAMES_EXCLUDED = {
    ".git",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".tmp",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "logs",
    "node_modules",
    "private",
    "project-archive",
    "project-input",
    "project-runtime",
    "secrets",
    "site-packages",
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
GITHUB_OWNER_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
GITHUB_REPO_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}\Z")
SECRET_LIKE_FILENAMES = {
    ".coverage",
    ".DS_Store",
    ".env",
    ".token",
    "cookies.json",
    "token",
    "token.json",
}
CACHE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
}
CACHE_SUFFIXES = (".pyc", ".pyo", ".pyd")
SECRET_LIKE_SUFFIXES = (".cookie", ".crt", ".key", ".p12", ".pem", ".pfx", ".token")
RUNTIME_CONTRACT_RELPATH = Path("02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json")
RUNTIME_CONTRACT_ROOT_RELPATH = Path("ORCHESTRATOR_RUNTIME_CONTRACT.json")
SOURCE_AGENT_SYSTEM_FILE_SENTINELS = (
    Path("00_start/ORCHESTRATOR_START.md"),
    RUNTIME_CONTRACT_RELPATH,
    Path("tools/aso/aso.py"),
)
SOURCE_AGENT_SYSTEM_DIR_SENTINELS = (Path("09_validators"),)
GENERATED_AGENT_SYSTEM_FILE_SENTINELS = (
    *SOURCE_AGENT_SYSTEM_FILE_SENTINELS,
    RUNTIME_CONTRACT_ROOT_RELPATH,
)
VENDORED_RELPATHS_EXCLUDED = (
    Path("tools/aso/agent_system_orchestrator_aso/resources/RESOURCE_MANIFEST.json"),
    Path("tools/aso/agent_system_orchestrator_aso/resources/agent-system"),
)
PYTHON_VERSION_DIR_RE = re.compile(r"python\d+(?:\.\d+)?\Z")


@dataclass(frozen=True)
class CreateSummary:
    target: Path
    created_entries: tuple[str, ...]
    copied_files: int
    skipped_paths: tuple[str, ...]
    runtime_state_initialized: bool
    runtime_state_files: int
    runtime_markdown_views: int


def run_verify_clean(args: argparse.Namespace) -> int:
    """Run `aso project verify-clean`."""

    root = Path(str(args.root)).expanduser()
    report = verify_clean(root)
    _print_verify_clean_text(report)
    if args.json_out and not _write_json(args.json_out, report):
        return EXIT_IO_ERROR
    if args.strict and report["violations"]:
        return EXIT_FAIL
    return EXIT_OK


def run_create(args: object) -> int:
    """Run `aso project create`."""

    if getattr(args, "github", False):
        return run_create_github(args)

    if getattr(args, "dry_run", False) or getattr(args, "confirm_publish", False):
        print("error: --dry-run and --confirm-publish are only supported with --github", file=sys.stderr)
        return EXIT_FAIL

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
    print(f"Runtime state: {'initialized' if summary.runtime_state_initialized else 'not initialized'}")
    print(f"Runtime markdown views: materialized ({summary.runtime_markdown_views})")
    print("Created entries:")
    for entry in summary.created_entries:
        print(f"- {entry}")
    print(f"Vendored files: {summary.copied_files}")
    print("Next step:")
    if args.engine_mode == lockfile.DEFAULT_ENGINE_MODE:
        print(
            "PYTHONDONTWRITEBYTECODE=1 python3 "
            f"{summary.target / 'agent-system/tools/aso/aso.py'} status --root {summary.target} --mode workspace"
        )
    else:
        print(f"PYTHONDONTWRITEBYTECODE=1 aso status --root {summary.target} --mode workspace")
    return EXIT_OK


def run_create_github(args: object) -> int:
    """Run `aso project create --github`."""

    if getattr(args, "dry_run", False):
        return run_create_github_dry_run(args)
    if not getattr(args, "confirm_publish", False):
        print("error: --github requires --dry-run for planning or --confirm-publish for real publish", file=sys.stderr)
        return EXIT_FAIL
    if not getattr(args, "branch_explicit", False):
        print("error: real GitHub publish requires explicit --branch", file=sys.stderr)
        return EXIT_FAIL

    try:
        receipt = publish_github_project(
            target=Path(str(args.target)).expanduser(),
            project_name=str(args.name),
            project_slug=str(args.slug),
            profile=str(args.profile),
            owner=getattr(args, "owner", None),
            repo=getattr(args, "repo", None),
            visibility=_required_visibility_from_args(args),
            default_branch=str(args.branch),
            engine_mode=str(args.engine_mode),
        )
    except PublishError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAIL

    if getattr(args, "json_out", None):
        if not _write_json(str(args.json_out), receipt):
            return EXIT_IO_ERROR
    print("ASO project GitHub publish: PASS")
    print(f"Target: {receipt['target']}")
    print(f"Repository: {receipt['repository']}")
    print(f"Visibility: {receipt['visibility']}")
    print(f"Branch: {receipt['branch']}")
    print(f"Commit: {receipt['commit']}")
    return EXIT_OK


def run_create_github_dry_run(args: object) -> int:
    """Run `aso project create --github --dry-run`."""

    try:
        plan = build_github_dry_run_plan(
            target=Path(str(args.target)).expanduser(),
            project_name=str(args.name),
            project_slug=str(args.slug),
            profile=str(args.profile),
            owner=getattr(args, "owner", None),
            repo=getattr(args, "repo", None),
            visibility=_visibility_from_args(args),
            default_branch=str(args.branch),
            engine_mode=str(args.engine_mode),
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAIL

    if getattr(args, "json_out", None):
        if not _write_json(str(args.json_out), plan):
            return EXIT_IO_ERROR
    else:
        print(json.dumps(plan, indent=2, sort_keys=True))
    return EXIT_OK


class PublishError(ValueError):
    """Raised for guarded GitHub publication failures."""


def publish_github_project(
    *,
    target: Path,
    project_name: str,
    project_slug: str,
    profile: str,
    owner: object,
    repo: object,
    visibility: str,
    default_branch: str,
    engine_mode: str,
) -> dict[str, object]:
    """Create, verify, commit, and publish a generated project with GitHub CLI."""

    target = target.expanduser()
    _validate_create_inputs(
        target=target,
        project_name=project_name,
        project_slug=project_slug,
        profile=profile,
        default_branch=default_branch,
        engine_mode=engine_mode,
    )
    owner_text = _validate_github_owner(owner)
    repo_text = _validate_github_repo(repo)
    if visibility not in {"public", "private", "internal"}:
        raise PublishError("visibility must be one of public, private, or internal")

    git_exe = _required_executable("git")
    gh_exe = _required_executable("gh")
    _run_checked([gh_exe, "auth", "status"], label="gh auth status")
    _verify_publish_target_safety(target)

    summary = create_project(
        target=target,
        project_name=project_name,
        project_slug=project_slug,
        profile=profile,
        repo_url=None,
        default_branch=default_branch,
        engine_mode=engine_mode,
    )
    pre_report = verify_clean(target)
    _raise_for_verify_clean_failure(pre_report, phase="pre-publish")

    trackable_paths = _trackable_generated_paths(engine_mode=engine_mode)
    _run_git_checked(git_exe, target, ["init", "-b", default_branch], label="git init")
    _run_git_checked(git_exe, target, ["add", *trackable_paths], label="git add")
    _run_git_checked(git_exe, target, ["commit", "-m", "Initial ASO project"], label="git commit")
    _verify_tracked_publication_boundary(target, engine_mode=engine_mode, phase="pre-push")
    commit = _run_git_checked(git_exe, target, ["rev-parse", "HEAD"], label="git rev-parse").stdout.strip()
    _run_checked(
        [
            gh_exe,
            "repo",
            "create",
            f"{owner_text}/{repo_text}",
            f"--{visibility}",
            "--source",
            str(target),
            "--remote",
            "origin",
            "--push",
        ],
        label="gh repo create",
    )

    post_report = verify_clean(target)
    _raise_for_verify_clean_failure(post_report, phase="post-publish")

    return {
        "status": "published",
        "target": str(summary.target),
        "project_name": project_name,
        "slug": project_slug,
        "profile": profile,
        "engine_mode": engine_mode,
        "repository": f"{owner_text}/{repo_text}",
        "repo_owner": owner_text,
        "repo_name": repo_text,
        "visibility": visibility,
        "branch": default_branch,
        "commit": commit,
        "tracked_paths": trackable_paths,
        "runtime_state_initialized": summary.runtime_state_initialized,
        "runtime_state_files": summary.runtime_state_files,
        "pre_publish_verify_clean": pre_report["status"],
        "post_publish_verify_clean": post_report["status"],
    }


def verify_clean(root: Path) -> dict[str, object]:
    """Build a read-only clean generated project verification report."""

    root = root.expanduser()
    violations: list[dict[str, object]] = []

    if not root.is_dir():
        violations.append(
            _violation(
                "PROJECT_VERIFY_CLEAN_001",
                "Project root is not a readable directory",
                str(root),
                "Run verify-clean with --root pointing at a generated project directory.",
            )
        )

    lock_report = _verify_lockfile(root, violations)
    gitignore_status, missing_gitignore_entries = _verify_gitignore(root, violations)
    repo_report = _verify_git_repository_metadata(root, lock_report["lockfile"], violations)
    nested_git_paths = _nested_agent_system_git_paths(root)
    if nested_git_paths:
        violations.append(
            _violation(
                "PROJECT_VERIFY_CLEAN_008",
                "Vendored agent-system contains nested Git metadata",
                ", ".join(nested_git_paths[:10]),
                "Remove copied .git metadata from vendored agent-system content.",
                paths=nested_git_paths,
            )
        )

    tracked_forbidden_paths = repo_report["tracked_forbidden_paths"]
    if tracked_forbidden_paths:
        violations.append(
            _violation(
                "PROJECT_VERIFY_CLEAN_007",
                "Git tracks forbidden generated-project artifacts",
                ", ".join(tracked_forbidden_paths[:10]),
                "Remove local roots, caches, upgrade packages, and secret-like files from Git tracking.",
                paths=tracked_forbidden_paths,
            )
        )

    status = "pass" if not violations else "fail"
    return {
        "tool": "aso",
        "command": "project verify-clean",
        "status": status,
        "root": str(root),
        "lockfile_status": lock_report["status"],
        "gitignore_status": gitignore_status,
        "tracked_forbidden_paths": tracked_forbidden_paths,
        "nested_git_paths": nested_git_paths,
        "repo_metadata_status": repo_report["repo_metadata_status"],
        "package_version": lock_report["package_version"],
        "package_version_status": lock_report["package_version_status"],
        "package_version_drift": lock_report["package_version_drift"],
        "runtime_schema": lock_report["runtime_schema"],
        "engine_mode": lock_report["engine_mode"],
        "missing_gitignore_entries": missing_gitignore_entries,
        "git": repo_report["git"],
        "violations": violations,
    }


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
    """Create a clean local Project Factory workspace."""

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
        _readme_text(project_name=project_name, project_slug=project_slug, engine_mode=engine_mode),
        encoding="utf-8",
    )
    for root_name in LOCAL_ROOTS:
        (target / root_name).mkdir()
    _write_bootstrap_inputs(target)

    copied_files = 0
    skipped_paths: tuple[str, ...] = ()
    runtime_state_files, runtime_markdown_views = _initialize_runtime_state(
        root=target,
        project_name=project_name,
        project_slug=project_slug,
        profile=profile,
        repo_url=repo_url,
        default_branch=default_branch,
    )
    created_entries = [
        ".gitignore",
        "README.md",
        "aso.lock",
        "project-archive/",
        "project-input/",
        "project-runtime/",
    ]
    if engine_mode == lockfile.DEFAULT_ENGINE_MODE:
        source = _resolve_vendored_agent_system(source_agent_system)
        copied_files, skipped_paths = _copy_vendored_agent_system(source, target / "agent-system")
        created_entries.insert(2, "agent-system/")

    return CreateSummary(
        target=target,
        created_entries=tuple(created_entries),
        copied_files=copied_files,
        skipped_paths=skipped_paths,
        runtime_state_initialized=True,
        runtime_state_files=runtime_state_files,
        runtime_markdown_views=runtime_markdown_views,
    )


def _write_bootstrap_inputs(root: Path) -> None:
    (root / "project-input" / "TZ.md").write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")


def build_github_dry_run_plan(
    *,
    target: Path,
    project_name: str,
    project_slug: str,
    profile: str,
    owner: object,
    repo: object,
    visibility: str,
    default_branch: str,
    engine_mode: str,
) -> dict[str, object]:
    """Build a deterministic GitHub publication plan without touching git, gh, or disk."""

    target = target.expanduser()
    _validate_create_inputs(
        target=target,
        project_name=project_name,
        project_slug=project_slug,
        profile=profile,
        default_branch=default_branch,
        engine_mode=engine_mode,
    )

    owner_text = _validate_github_owner(owner)
    repo_text = _validate_github_repo(repo)
    if visibility not in {"public", "private", "internal"}:
        raise ValueError("visibility must be one of public, private, or internal")

    local_files = list(_planned_local_files(engine_mode=engine_mode))
    trackable_paths = [path.rstrip("/") for path in local_files if path not in {"project-archive/", "project-input/", "project-runtime/"}]
    visibility_flag = f"--{visibility}"
    target_text = str(target)

    return {
        "target": target_text,
        "project_name": project_name,
        "slug": project_slug,
        "profile": profile,
        "engine_mode": engine_mode,
        "repo_owner": owner_text,
        "repo_name": repo_text,
        "visibility": visibility,
        "branch": default_branch,
        "planned_local_files": local_files,
        "planned_state_init": _planned_state_init(
            target=target,
            project_name=project_name,
            project_slug=project_slug,
            profile=profile,
            repo_url=None,
            default_branch=default_branch,
        ),
        "planned_git_commands": [
            f"git -C {target_text} init -b {default_branch}",
            f"git -C {target_text} add {' '.join(trackable_paths)}",
            f'git -C {target_text} commit -m "Initial ASO project"',
        ],
        "planned_gh_command": f"gh repo create {owner_text}/{repo_text} {visibility_flag} --source {target_text} --remote origin --push",
        "confirmation_required_for_real_publish": True,
    }


def _required_executable(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise PublishError(f"{name} executable is unavailable")
    return executable


def _run_checked(command: list[str], *, label: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise PublishError(f"{label} failed because executable is unavailable") from exc
    except subprocess.TimeoutExpired as exc:
        raise PublishError(f"{label} timed out") from exc
    except OSError as exc:
        raise PublishError(f"{label} failed: {exc}") from exc
    if result.returncode != 0:
        raise PublishError(f"{label} returned non-zero exit status {result.returncode}")
    return result


def _run_git_checked(
    git_exe: str,
    target: Path,
    args: list[str],
    *,
    label: str,
) -> subprocess.CompletedProcess[str]:
    return _run_checked([git_exe, "-C", str(target), *args], label=label)


def _validate_github_owner(value: object) -> str:
    owner = _required_text(value, "owner")
    if not GITHUB_OWNER_RE.fullmatch(owner):
        raise PublishError("repo owner contains unsafe characters")
    return owner


def _validate_github_repo(value: object) -> str:
    repo = _required_text(value, "repo")
    if repo in {".", ".."} or repo.endswith(".git") or not GITHUB_REPO_RE.fullmatch(repo):
        raise PublishError("repo name contains unsafe characters")
    return repo


def _verify_publish_target_safety(target: Path) -> None:
    resolved_target = target.resolve(strict=False)
    if _is_aso_engine_repo_target(resolved_target):
        raise PublishError("target must not be the ASO engine repository")

    existing_parent = _nearest_existing_parent(resolved_target)
    parent_worktree = _git_toplevel(existing_parent)
    if parent_worktree is not None and parent_worktree != resolved_target:
        raise PublishError("target must not be nested inside an existing parent Git worktree")


def _nearest_existing_parent(path: Path) -> Path:
    current = path
    while not current.exists() and current.parent != current:
        current = current.parent
    return current


def _is_aso_engine_repo_target(target: Path) -> bool:
    source_agent_system = _find_source_agent_system(Path(__file__))
    if source_agent_system is None:
        return False
    tool_repo = source_agent_system.parent.resolve(strict=False)
    agent_system_root = source_agent_system.resolve(strict=False)
    return target in {tool_repo, agent_system_root}


def _trackable_generated_paths(*, engine_mode: str) -> list[str]:
    return [
        path.rstrip("/")
        for path in _planned_local_files(engine_mode=engine_mode)
        if path not in {"project-archive/", "project-input/", "project-runtime/"}
    ]


def _raise_for_verify_clean_failure(report: dict[str, object], *, phase: str) -> None:
    if report.get("violations"):
        raise PublishError(f"verify-clean --strict failed during {phase}")


def _verify_tracked_publication_boundary(root: Path, *, engine_mode: str, phase: str) -> None:
    violations: list[dict[str, object]] = []
    tracked_paths = _git_ls_files(root, violations)
    if violations:
        raise PublishError(f"tracked publication-boundary validation failed during {phase}")

    forbidden_paths = sorted(
        path for path in tracked_paths if _is_forbidden_tracked_path(path, engine_mode=engine_mode)
    )
    if forbidden_paths:
        sample = ", ".join(forbidden_paths[:10])
        raise PublishError(f"tracked publication-boundary validation failed during {phase}: {sample}")


def _verify_lockfile(root: Path, violations: list[dict[str, object]]) -> dict[str, object]:
    lock_path = root / lockfile.LOCKFILE_NAME
    validation = lockfile.validate_lockfile_path(lock_path)
    decoded: object | None = None
    if lock_path.is_file():
        try:
            decoded = lockfile.read_lockfile(lock_path)
        except (OSError, json.JSONDecodeError):
            decoded = None

    for finding in validation.findings:
        violations.append(
            _violation(
                finding.rule_id,
                finding.message,
                finding.evidence,
                "Restore a valid Project Factory P0 aso.lock.",
                path=finding.path,
            )
        )

    aso_engine = decoded.get("aso_engine") if isinstance(decoded, dict) else None
    if not isinstance(aso_engine, dict):
        aso_engine = {}

    package_version = aso_engine.get("version")
    package_version_drift: str | None = None
    package_version_status = "unknown"
    if isinstance(package_version, str):
        if package_version == lockfile.PACKAGE_VERSION:
            package_version_status = "current"
        elif package_version in lockfile.COMPATIBLE_PACKAGE_VERSIONS:
            package_version_status = "compatible_drift"
            package_version_drift = f"{package_version} is compatible with current package {lockfile.PACKAGE_VERSION}"
        else:
            package_version_status = "unsupported"

    return {
        "status": "pass" if validation.ok else "fail",
        "lockfile": decoded if isinstance(decoded, dict) else None,
        "package_version": package_version,
        "package_version_status": package_version_status,
        "package_version_drift": package_version_drift,
        "runtime_schema": aso_engine.get("runtime_schema"),
        "engine_mode": aso_engine.get("engine_mode"),
    }


def _verify_gitignore(root: Path, violations: list[dict[str, object]]) -> tuple[str, list[str]]:
    gitignore_path = root / ".gitignore"
    if not gitignore_path.is_file():
        violations.append(
            _violation(
                "PROJECT_VERIFY_CLEAN_002",
                ".gitignore is missing",
                ".gitignore",
                "Restore .gitignore with all required Project Factory local boundary entries.",
                path=".gitignore",
            )
        )
        return "fail", list(REQUIRED_GITIGNORE_ENTRIES)

    try:
        text = gitignore_path.read_text(encoding="utf-8")
    except OSError as exc:
        violations.append(
            _violation(
                "PROJECT_VERIFY_CLEAN_003",
                ".gitignore is unreadable",
                str(exc),
                "Repair .gitignore permissions or encoding.",
                path=".gitignore",
            )
        )
        return "fail", list(REQUIRED_GITIGNORE_ENTRIES)

    entries = {line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")}
    missing = [entry for entry in REQUIRED_GITIGNORE_ENTRIES if entry not in entries]
    if missing:
        violations.append(
            _violation(
                "PROJECT_VERIFY_CLEAN_004",
                ".gitignore lacks required publication boundary entries",
                ", ".join(missing),
                "Restore the generated Project Factory .gitignore minimum entries.",
                path=".gitignore",
                paths=missing,
            )
        )
        return "fail", missing
    return "pass", []


def _verify_git_repository_metadata(
    root: Path,
    lock: dict[str, object] | None,
    violations: list[dict[str, object]],
) -> dict[str, object]:
    git: dict[str, object] = {
        "is_root_git_repo": False,
        "toplevel": None,
        "branch": None,
        "origin": None,
        "error": None,
    }
    tracked_forbidden_paths: list[str] = []

    git_root = _git_toplevel(root)
    if git_root is None:
        return {
            "repo_metadata_status": "skipped_not_git_repo",
            "tracked_forbidden_paths": tracked_forbidden_paths,
            "git": git,
        }

    git["toplevel"] = str(git_root)
    if git_root != root.resolve(strict=False):
        return {
            "repo_metadata_status": "skipped_parent_git_repo",
            "tracked_forbidden_paths": tracked_forbidden_paths,
            "git": git,
        }

    git["is_root_git_repo"] = True
    tracked_paths = _git_ls_files(root, violations)
    engine_mode = None
    aso_engine = lock.get("aso_engine") if isinstance(lock, dict) else None
    if isinstance(aso_engine, dict):
        mode = aso_engine.get("engine_mode")
        if isinstance(mode, str):
            engine_mode = mode

    tracked_forbidden_paths = sorted(
        path for path in tracked_paths if _is_forbidden_tracked_path(path, engine_mode=engine_mode)
    )
    branch = _git_value(root, ["branch", "--show-current"])
    origin = _git_value(root, ["remote", "get-url", "origin"])
    git["branch"] = branch or None
    git["origin"] = origin or None

    metadata_status = "pass"
    project_metadata = lock.get("project") if isinstance(lock, dict) else None
    if isinstance(project_metadata, dict):
        expected_branch = project_metadata.get("default_branch")
        if isinstance(expected_branch, str) and expected_branch.strip() and branch and branch != expected_branch:
            metadata_status = "fail"
            violations.append(
                _violation(
                    "PROJECT_VERIFY_CLEAN_009",
                    "Git branch conflicts with aso.lock project.default_branch",
                    f"expected {expected_branch}, actual {branch}",
                    "Check out the expected branch or update the generated project metadata intentionally.",
                    path="aso.lock",
                )
            )

        expected_origin = project_metadata.get("repo_url")
        if isinstance(expected_origin, str) and expected_origin.strip() and origin and origin != expected_origin:
            metadata_status = "fail"
            violations.append(
                _violation(
                    "PROJECT_VERIFY_CLEAN_010",
                    "Git origin conflicts with aso.lock project.repo_url",
                    f"expected {expected_origin}, actual {origin}",
                    "Point origin at the generated project repository or update the lock metadata intentionally.",
                    path="aso.lock",
                )
            )

    return {
        "repo_metadata_status": metadata_status,
        "tracked_forbidden_paths": tracked_forbidden_paths,
        "git": git,
    }


def _git_toplevel(root: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=False,
            text=True,
            capture_output=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    if not text:
        return None
    return Path(text).resolve(strict=False)


def _git_ls_files(root: Path, violations: list[dict[str, object]]) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            check=False,
            text=True,
            capture_output=True,
            timeout=10,
        )
    except FileNotFoundError:
        violations.append(
            _violation(
                "PROJECT_VERIFY_CLEAN_005",
                "Git is unavailable",
                "git executable was not found",
                "Run verify-clean in an environment with git available.",
            )
        )
        return []
    except (subprocess.TimeoutExpired, OSError) as exc:
        violations.append(
            _violation(
                "PROJECT_VERIFY_CLEAN_006",
                "Git tracked-file check failed",
                str(exc),
                "Repair the Git worktree and rerun verify-clean.",
            )
        )
        return []

    if result.returncode != 0:
        violations.append(
            _violation(
                "PROJECT_VERIFY_CLEAN_006",
                "Git tracked-file check failed",
                (result.stderr or result.stdout or "git ls-files failed").strip(),
                "Repair the Git worktree and rerun verify-clean.",
            )
        )
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _git_value(root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            text=True,
            capture_output=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _is_forbidden_tracked_path(relpath: str, *, engine_mode: str | None = None) -> bool:
    parts = tuple(part for part in relpath.split("/") if part)
    if not parts:
        return False
    if engine_mode == REFERENCE_ENGINE_MODE and parts[0] == "agent-system":
        return True
    if parts[0] in FORBIDDEN_TRACKED_ROOTS:
        return True
    if any(part in LOCAL_ROOTS for part in parts[1:]):
        return True
    if parts[0] == ".git":
        return True
    if parts[0] == "agent-system" and ".git" in parts[1:]:
        return True
    if any(part.startswith("aso_upgrade_") for part in parts):
        return True
    if any(part in CACHE_DIR_NAMES for part in parts):
        return True

    name = parts[-1]
    lower_name = name.lower()
    if lower_name in SECRET_LIKE_FILENAMES:
        return True
    if lower_name.startswith(".env."):
        return True
    if lower_name.endswith(CACHE_SUFFIXES):
        return True
    if lower_name.endswith(SECRET_LIKE_SUFFIXES):
        return True
    if lower_name.endswith(".log"):
        return True
    return False


def _nested_agent_system_git_paths(root: Path) -> list[str]:
    agent_system = root / "agent-system"
    if not agent_system.is_dir():
        return []

    nested: list[str] = []
    for path in sorted(agent_system.rglob(".git"), key=lambda item: item.as_posix()):
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = path.as_posix()
        nested.append(relative)
    return nested


def _violation(
    rule_id: str,
    message: str,
    evidence: str,
    recommendation: str,
    *,
    path: str = "",
    paths: list[str] | None = None,
) -> dict[str, object]:
    return {
        "rule_id": rule_id,
        "severity": "error",
        "message": message,
        "path": path,
        "paths": paths or ([path] if path else []),
        "evidence": evidence,
        "recommendation": recommendation,
    }


def _print_verify_clean_text(report: dict[str, object]) -> None:
    violations = report["violations"]
    print(f"ASO project verify-clean: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    print(f"Lockfile: {report['lockfile_status']}")
    print(f"Gitignore: {report['gitignore_status']}")
    print(f"Repository metadata: {report['repo_metadata_status']}")
    print(f"Package version: {report['package_version']}")
    if report.get("package_version_drift"):
        print(f"Package drift: {report['package_version_drift']}")
    print(f"Runtime schema: {report['runtime_schema']}")
    print(f"Engine mode: {report['engine_mode']}")
    print(f"Tracked forbidden paths: {len(report['tracked_forbidden_paths'])}")
    print(f"Nested Git paths: {len(report['nested_git_paths'])}")
    print(f"Violations: {len(violations)}")
    for violation in violations:
        if not isinstance(violation, dict):
            continue
        print(f"- {violation['severity']} {violation['rule_id']}: {violation['message']} ({violation['evidence']})")


def _write_json(path_text: str, report: dict[str, object]) -> bool:
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso project: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso project: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def _visibility_from_args(args: object) -> str:
    if getattr(args, "public", False):
        return "public"
    if getattr(args, "internal", False):
        return "internal"
    return "private"


def _required_visibility_from_args(args: object) -> str:
    selected = [name for name in ("public", "private", "internal") if getattr(args, name, False)]
    if len(selected) != 1:
        raise PublishError("real GitHub publish requires exactly one of --private, --public, or --internal")
    return selected[0]


def _required_text(value: object, name: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"{name} is required for --github")
    return text


def _planned_local_files(*, engine_mode: str) -> tuple[str, ...]:
    entries = [
        ".gitignore",
        "README.md",
        "aso.lock",
        "project-archive/",
        "project-input/",
        "project-runtime/",
    ]
    if engine_mode == lockfile.DEFAULT_ENGINE_MODE:
        entries.insert(2, "agent-system/")
    return tuple(entries)


def _initialize_runtime_state(
    *,
    root: Path,
    project_name: str,
    project_slug: str,
    profile: str,
    repo_url: str | None,
    default_branch: str,
) -> tuple[int, int]:
    sidecars = state_init._initial_sidecars(
        root=root,
        project_name=project_name,
        project_slug=project_slug,
        tz_path=state_init.CANONICAL_TZ_PATH,
        profile=profile,
        repo_url=repo_url or state_init.NONE,
        branch=default_branch,
        package_version=lockfile.PACKAGE_VERSION,
        runtime_schema_version=lockfile.RUNTIME_SCHEMA_VERSION,
        probe_git=False,
    )
    state_root = root / "project-runtime" / "state"
    ok, detail = state_init._validate_existing_state(state_root, sidecars)
    if not ok:
        raise ValueError(f"runtime state init refused: {detail}")
    wrote, write_detail = state_init._write_sidecars(state_root, sidecars)
    if not wrote:
        raise ValueError(f"runtime state init failed: {write_detail}")
    materialize_report, materialize_exit = state_render.materialize_compatibility_views(root)
    if materialize_exit != state_render.EXIT_OK:
        raise ValueError(f"runtime markdown materialization failed: {materialize_report.get('findings', [])}")
    materialize_summary = materialize_report.get("summary")
    views_written = (
        materialize_summary.get("views_written")
        if isinstance(materialize_summary, dict)
        else None
    )
    return len(sidecars), int(views_written) if isinstance(views_written, int) else 0


def _planned_state_init(
    *,
    target: Path,
    project_name: str,
    project_slug: str,
    profile: str,
    repo_url: str | None,
    default_branch: str,
) -> dict[str, object]:
    state_root = target / "project-runtime" / "state"
    return {
        "enabled_for_local_create": True,
        "dry_run": True,
        "writes_performed": False,
        "project_name": project_name,
        "project_slug": project_slug,
        "profile": profile,
        "repo_url": repo_url,
        "branch": default_branch,
        "package_version": lockfile.PACKAGE_VERSION,
        "runtime_schema_version": lockfile.RUNTIME_SCHEMA_VERSION,
        "state_root": str(state_root),
        "planned_writes": [
            str(state_root / filename)
            for filename in state_init.SIDECAR_FILENAMES
        ],
        "publication_boundary": {
            "ignored_root": "project-runtime/",
            "tracked": False,
            "pushed": False,
        },
    }


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
    if engine_mode not in lockfile.SUPPORTED_ENGINE_MODES:
        raise ValueError(f"engine-mode must be one of {', '.join(lockfile.SUPPORTED_ENGINE_MODES)}")


def _normalize_repo_url(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    return text


@dataclass(frozen=True)
class VendoredAgentSystemSource:
    root: object
    origin: str


def _default_source_agent_system() -> Path:
    source = _find_source_agent_system(Path(__file__))
    if source is None:
        raise ValueError(
            "agent-system source checkout could not be found from ASO package path; "
            "installed packages must use packaged vendored resources"
        )
    return source


def _resolve_vendored_agent_system(source_agent_system: Path | None = None) -> VendoredAgentSystemSource:
    if source_agent_system is not None:
        source = source_agent_system.expanduser()
        _assert_agent_system_source(source, origin=str(source))
        return VendoredAgentSystemSource(source, str(source))

    source = _find_source_agent_system(Path(__file__))
    if source is not None:
        _assert_agent_system_source(source, origin=str(source))
        return VendoredAgentSystemSource(source, str(source))

    try:
        resource_root = resources.packaged_resource_root("agent-system")
    except FileNotFoundError as exc:
        raise ValueError(str(exc)) from exc
    _assert_agent_system_source(resource_root, origin=f"{resources.RESOURCE_PACKAGE}:agent-system")
    return VendoredAgentSystemSource(resource_root, f"{resources.RESOURCE_PACKAGE}:agent-system")


def _find_source_agent_system(anchor_file: Path) -> Path | None:
    anchor = anchor_file.resolve()
    candidates: list[Path] = []
    for parent in anchor.parents:
        if parent.name == "agent-system":
            candidates.append(parent)
        candidates.append(parent / "agent-system")

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        if not _agent_system_source_errors(resolved):
            return resolved
    return None


def _assert_agent_system_source(source: object, *, origin: str) -> None:
    errors = _agent_system_source_errors(source)
    if errors:
        raise ValueError(f"agent-system source is incomplete at {origin}: {', '.join(errors)}")


def _agent_system_source_errors(source: object) -> list[str]:
    errors: list[str] = []
    if not _resource_is_dir(source):
        return ["agent-system root is not a readable directory"]

    for relpath in SOURCE_AGENT_SYSTEM_FILE_SENTINELS:
        if not _resource_child(source, relpath).is_file():
            errors.append(f"missing file {relpath.as_posix()}")
    for relpath in SOURCE_AGENT_SYSTEM_DIR_SENTINELS:
        if not _resource_child(source, relpath).is_dir():
            errors.append(f"missing directory {relpath.as_posix()}")
    return errors


def _gitignore_text() -> str:
    lines = [
        "# ASO Project Factory local workspace boundary",
        *REQUIRED_GITIGNORE_ENTRIES,
        "",
    ]
    return "\n".join(lines)


def _readme_text(*, project_name: str, project_slug: str, engine_mode: str) -> str:
    commands = (
        (
            "PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py state render --root . --confirm-write",
            "PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py status --root . --mode workspace",
            "PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lint --root . --mode workspace --strict",
            "PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py doctor --root . --mode workspace --strict",
            "PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lifecycle terminate-agent --root . --from-result project-runtime/results/worker/RESULT_TASK_ID_ATTEMPT_001.md --confirm-write",
        )
        if engine_mode == lockfile.DEFAULT_ENGINE_MODE
        else (
            "PYTHONDONTWRITEBYTECODE=1 aso project verify-clean --root . --strict",
            "PYTHONDONTWRITEBYTECODE=1 aso state render --root . --confirm-write",
            "PYTHONDONTWRITEBYTECODE=1 aso status --root . --mode workspace",
            "PYTHONDONTWRITEBYTECODE=1 aso lint --root . --mode workspace --strict",
            "PYTHONDONTWRITEBYTECODE=1 aso doctor --root . --mode workspace --strict",
            "PYTHONDONTWRITEBYTECODE=1 aso lifecycle terminate-agent --root . --from-result project-runtime/results/worker/RESULT_TASK_ID_ATTEMPT_001.md --confirm-write",
        )
    )
    engine_note = (
        "This project vendors ASO engine files under `agent-system/`."
        if engine_mode == lockfile.DEFAULT_ENGINE_MODE
        else "This project references an external ASO engine recorded in `aso.lock`."
    )
    return (
        f"# {project_name}\n\n"
        "Generated by ASO Project Factory.\n\n"
        f"{engine_note}\n\n"
        "## Local ASO commands\n\n"
        "```bash\n"
        + "\n".join(commands)
        + "\n"
        "```\n\n"
        "Before routing a profile-agent RESULT to audit, record the lifecycle "
        "termination event with `aso lifecycle terminate-agent --confirm-write`.\n\n"
        "## Publication boundary\n\n"
        "The local ASO working roots `project-input/`, `project-runtime/`, and "
        "`project-archive/` are intentionally ignored and should not be tracked.\n\n"
        f"Project slug: `{project_slug}`\n"
    )


def _copy_vendored_agent_system(source: VendoredAgentSystemSource, destination: Path) -> tuple[int, tuple[str, ...]]:
    _assert_agent_system_source(source.root, origin=source.origin)
    destination.mkdir(parents=True, exist_ok=True)
    skipped: list[str] = []
    copied_files = _copy_vendored_resource_tree(source.root, destination, Path(), skipped)
    copied_files += _materialize_runtime_contract_root_sentinel(destination)

    _assert_generated_agent_system(destination)

    return copied_files, tuple(skipped)


def _copy_vendored_resource_tree(source: object, destination: Path, relative: Path, skipped: list[str]) -> int:
    source_node = _resource_child(source, relative)
    copied_files = 0
    for child in sorted(source_node.iterdir(), key=lambda item: item.name):
        child_relative = relative / child.name
        if _exclude_vendored_path(child_relative, is_dir=child.is_dir()):
            skipped.append(child_relative.as_posix())
            continue
        if isinstance(child, Path) and child.is_symlink():
            skipped.append(child_relative.as_posix())
            continue

        destination_path = destination / child_relative
        if child.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            copied_files += _copy_vendored_resource_tree(source, destination, child_relative, skipped)
            continue
        if not child.is_file():
            skipped.append(child_relative.as_posix())
            continue

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(child, Path):
            shutil.copy2(child, destination_path)
        else:
            destination_path.write_bytes(child.read_bytes())
        copied_files += 1
    return copied_files


def _resource_child(root: object, relative: Path):
    node = root
    for part in relative.parts:
        node = node.joinpath(part)
    return node


def _resource_is_dir(resource: object) -> bool:
    try:
        return bool(resource.is_dir())
    except (AttributeError, FileNotFoundError, OSError):
        return False


def _materialize_runtime_contract_root_sentinel(destination: Path) -> int:
    source = destination / RUNTIME_CONTRACT_RELPATH
    target = destination / RUNTIME_CONTRACT_ROOT_RELPATH
    if not source.is_file():
        return 0
    previous = target.read_bytes() if target.is_file() else None
    shutil.copy2(source, target)
    return 0 if previous == target.read_bytes() else 1


def _assert_generated_agent_system(destination: Path) -> None:
    errors: list[str] = []
    for relpath in GENERATED_AGENT_SYSTEM_FILE_SENTINELS:
        if not (destination / relpath).is_file():
            errors.append(f"missing file {relpath.as_posix()}")
    for relpath in SOURCE_AGENT_SYSTEM_DIR_SENTINELS:
        if not (destination / relpath).is_dir():
            errors.append(f"missing directory {relpath.as_posix()}")

    library_roots = _vendored_library_root_paths(destination)
    if library_roots:
        errors.append(f"forbidden library roots copied: {', '.join(library_roots[:10])}")

    if errors:
        raise ValueError(f"generated agent-system validation failed: {', '.join(errors)}")


def _vendored_library_root_paths(root: Path) -> list[str]:
    forbidden: list[str] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = path.as_posix()
        if path.is_dir():
            name = path.name
            if name in {"site-packages", "node_modules"} or PYTHON_VERSION_DIR_RE.fullmatch(name):
                forbidden.append(relative)
        elif path.name == "pyvenv.cfg":
            forbidden.append(Path(relative).parent.as_posix())
    return sorted(set(forbidden))


def _exclude_vendored_path(relative: Path, *, is_dir: bool) -> bool:
    parts = relative.parts
    if any(_relative_is_or_is_inside(relative, excluded) for excluded in VENDORED_RELPATHS_EXCLUDED):
        return True
    if any(part in VENDORED_DIR_NAMES_EXCLUDED for part in parts):
        return True
    if any(PYTHON_VERSION_DIR_RE.fullmatch(part) for part in parts):
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


def _relative_is_or_is_inside(relative: Path, parent: Path) -> bool:
    return relative == parent or parent in relative.parents
