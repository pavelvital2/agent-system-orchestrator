"""Runtime access to ASO governance resources."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources as importlib_resources
from pathlib import Path


RESOURCE_PACKAGE = "agent_system_orchestrator_aso.resources"


@dataclass(frozen=True)
class ResourceText:
    relative_path: str
    text: str
    origin: str
    attempted_paths: tuple[str, ...]


def _normal_parts(relative_path: str | Path) -> tuple[str, ...]:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"resource path must be repository-relative without parent traversal: {relative_path}")
    return path.as_posix().split("/")


def source_tree_root(anchor_file: str | Path) -> Path | None:
    """Return the source repository root when running from a checkout."""

    anchor = Path(anchor_file).resolve()
    for parent in anchor.parents:
        if (parent / "agent-system" / "tools" / "aso" / "aso.py").is_file() and (
            parent / "agent-system" / "09_validators"
        ).is_dir():
            return parent
    return None


def _packaged_resource(relative_path: str | Path):
    resource = importlib_resources.files(RESOURCE_PACKAGE)
    for part in _normal_parts(relative_path):
        resource = resource.joinpath(part)
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
