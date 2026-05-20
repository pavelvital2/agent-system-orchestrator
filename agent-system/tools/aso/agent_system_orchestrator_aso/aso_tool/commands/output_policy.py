"""Shared generated-output path policy for read-only ASO commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


RULE_ID_OUTPUT_PATH_FORBIDDEN = "ASO_OUTPUT_PATH_FORBIDDEN"
SAFE_TMP_ROOT = Path("/tmp")
WORKSPACE_FORBIDDEN_ROOTS = ("project-input", "project-archive", ".tmp", "tmp")


@dataclass(frozen=True)
class OutputPathError:
    rule_id: str
    message: str
    evidence: str


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_output_path(value: str, *, base: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() and base is not None:
        path = base / path
    return path.resolve(strict=False)


def _workspace_allowed_targets(root: Path, allowed_workspace_subdirs: tuple[str, ...]) -> list[Path]:
    workspace = root.expanduser().resolve(strict=False)
    return [(workspace / relpath).resolve(strict=False) for relpath in allowed_workspace_subdirs]


def _workspace_runtime_root(root: Path) -> Path:
    workspace = root.expanduser().resolve(strict=False)
    return (workspace / "project-runtime").resolve(strict=False)


def _workspace_forbidden_roots(root: Path) -> list[Path]:
    workspace = root.expanduser().resolve(strict=False)
    return [(workspace / relpath).resolve(strict=False) for relpath in WORKSPACE_FORBIDDEN_ROOTS]


def validate_generated_output_path(
    root: Path,
    path: Path,
    *,
    allowed_workspace_subdirs: tuple[str, ...] = (),
    policy_roots: tuple[Path, ...] | None = None,
) -> OutputPathError | None:
    """Allow stdout-equivalent explicit writes only to temp or approved runtime dirs."""

    resolved = path.expanduser().resolve(strict=False)
    for target in _workspace_allowed_targets(root, allowed_workspace_subdirs):
        if is_relative_to(resolved, target) and resolved != target:
            return None

    for forbidden_root in _workspace_forbidden_roots(root):
        if is_relative_to(resolved, forbidden_root):
            return OutputPathError(
                RULE_ID_OUTPUT_PATH_FORBIDDEN,
                (
                    "Generated output path is forbidden inside workspace generated roots; "
                    "use stdout, /tmp outside the workspace, or an explicitly allowed "
                    "project-runtime report/proposal/dashboard subdirectory."
                ),
                resolved.as_posix(),
            )

    runtime_root = _workspace_runtime_root(root)
    if is_relative_to(resolved, runtime_root):
        return OutputPathError(
            RULE_ID_OUTPUT_PATH_FORBIDDEN,
            (
                "Generated output path is forbidden inside workspace project-runtime; "
                "use stdout or an explicitly allowed project-runtime report/proposal/dashboard subdirectory."
            ),
            resolved.as_posix(),
        )

    tmp_root = SAFE_TMP_ROOT.resolve(strict=True)
    if is_relative_to(resolved, tmp_root) and resolved != tmp_root:
        return None

    _ = policy_roots
    return OutputPathError(
        RULE_ID_OUTPUT_PATH_FORBIDDEN,
        (
            "Generated output path is forbidden; use stdout, /tmp/..., "
            "or an explicitly allowed workspace project-runtime report/proposal/dashboard path."
        ),
        resolved.as_posix(),
    )
