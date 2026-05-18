"""Console-script bridge for the existing ASO helper script.

The implementation intentionally delegates to agent-system/tools/aso/aso.py so
direct script execution and installed ``aso`` use the same command parser.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


_SCRIPT_MODULE_NAME = "_agent_system_orchestrator_aso_script"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _aso_tool_dir() -> Path:
    return _repo_root() / "agent-system" / "tools" / "aso"


def _load_script_module() -> ModuleType:
    tool_dir = _aso_tool_dir()
    script_path = tool_dir / "aso.py"
    if not script_path.is_file():
        raise RuntimeError(f"ASO script is unavailable at expected path: {script_path}")

    tool_dir_text = str(tool_dir)
    if tool_dir_text not in sys.path:
        sys.path.insert(0, tool_dir_text)

    spec = importlib.util.spec_from_file_location(_SCRIPT_MODULE_NAME, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load ASO script module from: {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[_SCRIPT_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    module = _load_script_module()
    script_main = getattr(module, "main", None)
    if script_main is None:
        raise RuntimeError("ASO script does not expose main(argv).")
    return int(script_main(argv))
