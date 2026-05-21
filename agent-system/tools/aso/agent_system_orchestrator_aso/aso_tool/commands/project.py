"""Project Factory P0 project creation and verification commands."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .. import lockfile


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


@dataclass(frozen=True)
class CreateSummary:
    target: Path
    created_entries: tuple[str, ...]
    copied_files: int
    skipped_paths: tuple[str, ...]


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

    return {
        "status": "pass" if validation.ok else "fail",
        "lockfile": decoded if isinstance(decoded, dict) else None,
        "package_version": aso_engine.get("version"),
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
    tracked_forbidden_paths = sorted(path for path in tracked_paths if _is_forbidden_tracked_path(path))
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


def _is_forbidden_tracked_path(relpath: str) -> bool:
    parts = tuple(part for part in relpath.split("/") if part)
    if not parts:
        return False
    if parts[0] in FORBIDDEN_TRACKED_ROOTS:
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
        print(f"aso project verify-clean: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso project verify-clean: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


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
