"""Runtime access to ASO governance resources."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib import resources as importlib_resources
from pathlib import Path
import re


RESOURCE_PACKAGE = "agent_system_orchestrator_aso.resources"
RESOURCE_MANIFEST = "RESOURCE_MANIFEST.json"
RESOURCE_AGENT_SYSTEM_ROOT = "agent-system"
RESOURCE_REQUIRED_FILE_SENTINELS = (
    "agent-system/00_start/ORCHESTRATOR_START.md",
    "agent-system/ORCHESTRATOR_RUNTIME_CONTRACT.json",
    "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json",
    "agent-system/tools/aso/aso.py",
)
RESOURCE_REQUIRED_DIR_SENTINELS = ("agent-system/09_validators",)
RESOURCE_FORBIDDEN_DIR_NAMES = {
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
    "node_modules",
    "project-archive",
    "project-input",
    "project-runtime",
    "site-packages",
    "tmp",
}
RESOURCE_FORBIDDEN_RELPATHS = (
    "agent-system/tools/aso/agent_system_orchestrator_aso/resources/agent-system",
)
PYTHON_VERSION_DIR_RE = re.compile(r"python\d+(?:\.\d+)?\Z")


@dataclass(frozen=True)
class ResourceText:
    relative_path: str
    text: str
    origin: str
    attempted_paths: tuple[str, ...]


@dataclass(frozen=True)
class ResourceManifestCheck:
    ok: bool
    errors: tuple[str, ...]
    manifest_origin: str
    files_checked: int


def _normal_parts(relative_path: str | Path) -> tuple[str, ...]:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"resource path must be repository-relative without parent traversal: {relative_path}")
    return path.as_posix().split("/")


def source_tree_root(anchor_file: str | Path) -> Path | None:
    """Return the source repository root when running from a checkout."""

    anchor = Path(anchor_file).resolve()
    for parent in anchor.parents:
        agent_system = parent / "agent-system"
        if (
            (agent_system / "00_start" / "ORCHESTRATOR_START.md").is_file()
            and (agent_system / "02_runtime" / "ORCHESTRATOR_RUNTIME_CONTRACT.json").is_file()
            and (agent_system / "tools" / "aso" / "aso.py").is_file()
            and (agent_system / "09_validators").is_dir()
        ):
            return parent
    return None


def _packaged_resource(relative_path: str | Path):
    resource = importlib_resources.files(RESOURCE_PACKAGE)
    for part in _normal_parts(relative_path):
        resource = resource.joinpath(part)
    return resource


def packaged_resource_root(relative_path: str | Path):
    try:
        resource = _packaged_resource(relative_path)
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise FileNotFoundError(
            f"Packaged ASO resource root could not be loaded: {relative_path}. "
            "Reinstall agent-system-orchestrator from a complete wheel or sdist."
        ) from exc
    if not resource.is_dir():
        raise FileNotFoundError(
            f"Packaged ASO resource root is missing or not a directory: {RESOURCE_PACKAGE}:{relative_path}"
        )
    return resource


def resource_exists(relative_path: str | Path, *, anchor_file: str | Path) -> bool:
    source_root = source_tree_root(anchor_file)
    if source_root is not None and (source_root / relative_path).is_file():
        return True
    try:
        return _packaged_resource(relative_path).is_file()
    except (FileNotFoundError, ModuleNotFoundError):
        return False


def read_resource_text(relative_path: str | Path, *, anchor_file: str | Path) -> ResourceText:
    rel = Path(relative_path).as_posix()
    attempted: list[str] = []
    source_root = source_tree_root(anchor_file)
    if source_root is not None:
        source_path = source_root / rel
        attempted.append(str(source_path))
        if source_path.is_file():
            return ResourceText(rel, source_path.read_text(encoding="utf-8"), str(source_path), tuple(attempted))

    package_path = f"{RESOURCE_PACKAGE}:{rel}"
    attempted.append(package_path)
    try:
        packaged = _packaged_resource(rel)
        if packaged.is_file():
            return ResourceText(rel, packaged.read_text(encoding="utf-8"), package_path, tuple(attempted))
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        attempted.append(f"{package_path} ({exc})")

    message = (
        f"Packaged ASO resource could not be loaded: {rel}. "
        f"Attempted: {', '.join(attempted)}. "
        "Reinstall agent-system-orchestrator from a complete source archive, or run the direct script from an ASO "
        "source checkout."
    )
    raise FileNotFoundError(message)


def verify_resource_manifest(resource_root: object | None = None) -> ResourceManifestCheck:
    """Verify packaged resource hashes and required vendored source sentinels."""

    errors: list[str] = []
    root = resource_root
    manifest_origin = f"{RESOURCE_PACKAGE}:{RESOURCE_MANIFEST}"
    if root is None:
        try:
            root = importlib_resources.files(RESOURCE_PACKAGE)
        except (FileNotFoundError, ModuleNotFoundError) as exc:
            return ResourceManifestCheck(False, (f"resource package unavailable: {exc}",), manifest_origin, 0)
    else:
        manifest_origin = str(root)

    manifest_resource = _resource_joinpath(root, Path(RESOURCE_MANIFEST))
    if not manifest_resource.is_file():
        return ResourceManifestCheck(False, ("resource manifest is missing",), manifest_origin, 0)

    try:
        manifest = json.loads(manifest_resource.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return ResourceManifestCheck(False, (f"resource manifest is unreadable: {exc}",), manifest_origin, 0)

    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        return ResourceManifestCheck(False, ("resource manifest files map is missing or empty",), manifest_origin, 0)

    for relpath in RESOURCE_REQUIRED_FILE_SENTINELS:
        entry = _resource_joinpath(root, Path(relpath))
        if not entry.is_file():
            errors.append(f"missing required resource file {relpath}")
    for relpath in RESOURCE_REQUIRED_DIR_SENTINELS:
        entry = _resource_joinpath(root, Path(relpath))
        if not entry.is_dir():
            errors.append(f"missing required resource directory {relpath}")

    actual_files = set(_iter_resource_file_relpaths(_resource_joinpath(root, Path(RESOURCE_AGENT_SYSTEM_ROOT)), Path(RESOURCE_AGENT_SYSTEM_ROOT)))
    manifest_files = set(files)
    missing_from_manifest = sorted(actual_files - manifest_files)
    missing_from_resources = sorted(manifest_files - actual_files)
    if missing_from_manifest:
        errors.append(f"resource manifest omits packaged file(s): {', '.join(missing_from_manifest[:10])}")
    if missing_from_resources:
        errors.append(f"resource manifest lists missing file(s): {', '.join(missing_from_resources[:10])}")

    for relpath, metadata in sorted(files.items()):
        if not isinstance(relpath, str):
            errors.append("resource manifest contains non-string path")
            continue
        try:
            _normal_parts(relpath)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if _is_forbidden_resource_relpath(relpath):
            errors.append(f"resource manifest includes forbidden path {relpath}")
            continue
        if not isinstance(metadata, dict):
            errors.append(f"resource manifest metadata is not an object for {relpath}")
            continue
        expected_sha = metadata.get("sha256")
        expected_size = metadata.get("size")
        if not isinstance(expected_sha, str) or not isinstance(expected_size, int):
            errors.append(f"resource manifest metadata is incomplete for {relpath}")
            continue
        resource = _resource_joinpath(root, Path(relpath))
        if not resource.is_file():
            continue
        data = resource.read_bytes()
        actual_sha = hashlib.sha256(data).hexdigest()
        if actual_sha != expected_sha:
            errors.append(f"resource hash mismatch for {relpath}")
        if len(data) != expected_size:
            errors.append(f"resource size mismatch for {relpath}")

    return ResourceManifestCheck(not errors, tuple(errors), manifest_origin, len(files))


def _resource_joinpath(root: object, relative: Path):
    node = root
    for part in relative.parts:
        node = node.joinpath(part)
    return node


def _iter_resource_file_relpaths(resource: object, relative: Path):
    if not resource.is_dir():
        return
    for child in sorted(resource.iterdir(), key=lambda item: item.name):
        child_relative = relative / child.name
        if child.is_dir():
            yield from _iter_resource_file_relpaths(child, child_relative)
        elif child.is_file():
            yield child_relative.as_posix()


def _is_forbidden_resource_relpath(relpath: str) -> bool:
    relative = Path(relpath)
    if any(_relative_is_or_is_inside(relative, Path(forbidden)) for forbidden in RESOURCE_FORBIDDEN_RELPATHS):
        return True
    if any(part in RESOURCE_FORBIDDEN_DIR_NAMES for part in relative.parts):
        return True
    return any(PYTHON_VERSION_DIR_RE.fullmatch(part) for part in relative.parts)


def _relative_is_or_is_inside(relative: Path, parent: Path) -> bool:
    return relative == parent or parent in relative.parents
