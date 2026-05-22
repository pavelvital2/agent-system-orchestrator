"""Stable hotfix diagnostics and repair hints for ASO validators."""

from __future__ import annotations

import json
from pathlib import Path

from .. import runtime_schema_contracts


MODE_GUARD_001_TITLE = "Invalid mode: package checks were requested for workspace root."
MODE_GUARD_001_RECOMMENDATION = "Use --mode workspace."

MISSING_RUNTIME_VIEWS_TITLE = "Runtime markdown views are missing but JSON sidecars are valid."
MISSING_RUNTIME_VIEWS_RECOMMENDATION = (
    "Run aso state render --root WORKSPACE --confirm-write "
    "(or aso state materialize --root WORKSPACE --views runtime-markdown --confirm-write)."
)

LINT_AGENT_003_TITLE = "Agent termination event is missing after RESULT."
LINT_AGENT_003_RECOMMENDATION = (
    "Run aso lifecycle terminate-agent --root WORKSPACE --from-result RESULT_PATH --confirm-write "
    "before audit route."
)


def required_runtime_view_names() -> tuple[str, ...]:
    return tuple(f"{sidecar_type}.md" for sidecar_type in runtime_schema_contracts.REQUIRED_SIDECARS)


def missing_runtime_views_with_valid_sidecars(root: Path, missing_names: list[str]) -> bool:
    """Return true when missing Markdown views can be repaired from valid JSON sidecars."""
    if not missing_names:
        return False
    state_root = root / runtime_schema_contracts.STATE_ROOT
    missing_sidecars = {Path(name).stem for name in missing_names}
    if not missing_sidecars:
        return False
    for sidecar_type in missing_sidecars:
        path = state_root / f"{sidecar_type}.json"
        if not path.is_file():
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        if payload.get("sidecar_type") != sidecar_type:
            return False
        content = payload.get("content")
        if not isinstance(content, dict):
            return False
    return True
