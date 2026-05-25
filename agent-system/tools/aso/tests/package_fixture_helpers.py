from __future__ import annotations

import hashlib
import json
from pathlib import Path


PYPROJECT_RESOURCE_DATA = """
[tool.setuptools.package-data]
"agent_system_orchestrator_aso.resources" = [
    "RESOURCE_MANIFEST.json",
    "agent-system/**/*",
]
"""

MANIFEST_IN_TEXT = (
    "graft agent-system/tools/aso/agent_system_orchestrator_aso/resources\n"
    "prune agent-system/tools/aso/agent_system_orchestrator_aso/resources/agent-system/tools/aso/"
    "agent_system_orchestrator_aso/resources/agent-system\n"
)

MINIMAL_RESOURCE_FILES = {
    "agent-system/00_start/ORCHESTRATOR_START.md": b"# Start\n",
    "agent-system/ORCHESTRATOR_RUNTIME_CONTRACT.json": b"{}\n",
    "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json": b"{}\n",
    "agent-system/09_validators/VALIDATOR_SPEC.md": b"# Validators\n",
    "agent-system/tools/aso/aso.py": b"print('ok')\n",
}


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_bytes(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _resource_manifest(files: dict[str, bytes]) -> str:
    return json.dumps(
        {
            "schema": "aso_resource_manifest_v1",
            "resource_root": "agent-system",
            "required_file_sentinels": [
                "agent-system/00_start/ORCHESTRATOR_START.md",
                "agent-system/ORCHESTRATOR_RUNTIME_CONTRACT.json",
                "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json",
                "agent-system/tools/aso/aso.py",
            ],
            "required_directory_sentinels": ["agent-system/09_validators"],
            "files": {
                relpath: {
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size": len(data),
                }
                for relpath, data in sorted(files.items())
            },
        },
        indent=2,
        sort_keys=True,
    ) + "\n"


def write_minimal_package_resources(package_root: Path) -> list[Path]:
    resources_root = package_root / "resources"
    paths = [_write(resources_root / "__init__.py", "\n")]
    for relpath, data in MINIMAL_RESOURCE_FILES.items():
        paths.append(_write_bytes(resources_root / relpath, data))
    paths.append(_write(resources_root / "RESOURCE_MANIFEST.json", _resource_manifest(MINIMAL_RESOURCE_FILES)))
    return paths


def write_resource_manifest_in(root: Path) -> Path:
    return _write(root / "MANIFEST.in", MANIFEST_IN_TEXT)
