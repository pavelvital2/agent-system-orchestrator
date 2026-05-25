"""Root mode detection for package and workspace command surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import repair_hints

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    tomllib = None


PACKAGE_ROOT = "agent-system/tools/aso"
PACKAGE_PYPROJECT_MARKERS = (
    'aso = "agent_system_orchestrator_aso.cli:main"',
    'where = ["agent-system/tools/aso"]',
    'include = ["agent_system_orchestrator_aso*"]',
)
WORKSPACE_STATE_GLOBS = (
    "project-runtime/state/*.json",
    "project-runtime/PROJECT_STATE.md",
    "project-runtime/WORKSPACE_IDENTITY.md",
    "project-runtime/REPOSITORY_LOCK.md",
)
INITIALIZED_WORKSPACE_STATE_GLOB = "project-runtime/state/*.json"


@dataclass(frozen=True)
class ModeFinding:
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
class RootMode:
    kind: str
    package_signals: list[str]
    workspace_signals: list[str]


def classify_root(root: Path) -> RootMode:
    """Classify an ASO command root without mutating it."""
    if not root.exists() or not root.is_dir():
        return RootMode("invalid", [], [])

    package_signals = _package_signals(root)
    workspace_signals = _workspace_signals(root)
    has_package = bool(package_signals)
    has_workspace = bool(workspace_signals)

    if has_package and has_workspace:
        return RootMode("ambiguous", package_signals, workspace_signals)
    if has_package:
        return RootMode("package_repo", package_signals, workspace_signals)
    if has_workspace:
        return RootMode("workspace", package_signals, workspace_signals)
    return RootMode("invalid", package_signals, workspace_signals)


def package_mode_guard(root: Path) -> ModeFinding | None:
    """Return a clear mode mismatch before package layout diagnostics."""
    mode = classify_root(root)
    if mode.kind != "workspace":
        return None

    files = mode.workspace_signals or [str(root)]

    return ModeFinding(
        "MODE_GUARD_001",
        "error",
        repair_hints.MODE_GUARD_001_TITLE,
        repair_hints.MODE_GUARD_001_TITLE,
        files,
        repair_hints.MODE_GUARD_001_RECOMMENDATION,
    )


def resolve_omitted_mode(root: Path) -> tuple[str, ModeFinding | None]:
    """Resolve an omitted CLI --mode value without mutating the root.

    Explicit --mode values bypass this helper. Package repository roots are
    detected by the package pyproject plus the packaged agent-system tree.
    Initialized workspaces are detected by JSON state sidecars. Roots that show
    both signals fail closed because silently choosing either mode can mask a
    package/workspace boundary mistake.
    """
    package_signals = _package_signals(root)
    workspace_signals = _initialized_workspace_signals(root)

    if package_signals and workspace_signals:
        return "workspace", ModeFinding(
            "ASO_MODE_AMBIGUOUS",
            "error",
            "Ambiguous ASO command mode",
            (
                "Root contains both ASO package repository signals and "
                "initialized workspace state signals."
            ),
            package_signals + workspace_signals,
            "Pass --mode package or --mode workspace explicitly.",
        )

    if package_signals:
        return "package", None
    if workspace_signals:
        return "workspace", None

    return "workspace", None


def _package_signals(root: Path) -> list[str]:
    signals: list[str] = []
    if (root / PACKAGE_ROOT).is_dir():
        signals.append(PACKAGE_ROOT)
    if _is_aso_pyproject(root / "pyproject.toml"):
        signals.append("pyproject.toml")
    if (root / ".github" / "workflows").is_dir():
        signals.append(".github/workflows")
    if "pyproject.toml" in signals and PACKAGE_ROOT in signals:
        return signals
    return []


def _workspace_signals(root: Path) -> list[str]:
    signals: list[str] = []
    if (root / "aso.lock").is_file():
        signals.append("aso.lock")
    for pattern in WORKSPACE_STATE_GLOBS:
        if any(root.glob(pattern)):
            base = pattern.replace("*.json", "")
            signals.append(base.rstrip("/"))
    return signals


def _initialized_workspace_signals(root: Path) -> list[str]:
    if any(root.glob(INITIALIZED_WORKSPACE_STATE_GLOB)):
        return ["project-runtime/state"]
    return []


def _is_aso_pyproject(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False

    if tomllib is not None:
        try:
            metadata = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return False
        project = metadata.get("project", {})
        scripts = project.get("scripts", {}) if isinstance(project, dict) else {}
        aso_entrypoint = scripts.get("aso") if isinstance(scripts, dict) else None
        tool = metadata.get("tool", {})
        setuptools = tool.get("setuptools", {}) if isinstance(tool, dict) else {}
        packages = setuptools.get("packages", {}) if isinstance(setuptools, dict) else {}
        find_config = packages.get("find", {}) if isinstance(packages, dict) else {}
        where = find_config.get("where", []) if isinstance(find_config, dict) else []
        include = find_config.get("include", []) if isinstance(find_config, dict) else []
        return (
            aso_entrypoint == "agent_system_orchestrator_aso.cli:main"
            and "agent-system/tools/aso" in where
            and "agent_system_orchestrator_aso*" in include
        )

    return all(marker in text for marker in PACKAGE_PYPROJECT_MARKERS)
