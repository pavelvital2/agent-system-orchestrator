"""Root mode detection for package and workspace command surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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

    signal_text = ", ".join(mode.workspace_signals) or "workspace runtime signals"
    files = mode.workspace_signals or [str(root)]
    title = "Package mode was run against a workspace root"
    details = (
        f"{root} looks like an ASO workspace ({signal_text}), not an ASO package "
        "repository root."
    )

    return ModeFinding(
        "MODE_GUARD_001",
        "error",
        title,
        details,
        files,
        "Use --mode workspace for generated ASO projects; use --mode package only from the ASO package repository root.",
    )


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
