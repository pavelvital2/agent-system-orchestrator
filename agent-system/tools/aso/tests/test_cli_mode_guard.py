from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from package_fixture_helpers import PYPROJECT_RESOURCE_DATA, write_minimal_package_resources, write_resource_manifest_in


CLI = Path(__file__).resolve().parents[1] / "aso.py"


PACKAGE_README = """# Package

Use the ASO helper at `agent-system/tools/aso/aso.py` for read-only diagnostics plus explicit confirmed writes.

```text
python3 agent-system/tools/aso/aso.py status --root . --mode package
python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
python3 agent-system/tools/aso/aso.py status --root /path/to/project --mode workspace
python3 agent-system/tools/aso/aso.py lint --root /path/to/project --mode workspace --strict
```

It does not dispatch live agents, execute checkpoints, or run daemons.
"""


RUNTIME_CONTENT = {
    "PROJECT_STATE.md": """# PROJECT_STATE

PROJECT_SLUG: demo-project
ACTUAL_BRANCH: main
PROJECT_STATUS: active
PROJECT_CHECKPOINT_STATUS: pending
PUSH_ALLOWED: false
""",
    "CURRENT_GATE.md": """# CURRENT_GATE

STATUS: open
""",
    "NEXT_ACTION.md": """# NEXT_ACTION

ACTION_TYPE: create_agent
TARGET_ROLE: developer
TASK_ID: TASK_DEMO_001
TASK_PACKET: project-runtime/tasks/active/TASK_DEMO_001.md
""",
    "TASK_REGISTRY.md": "# TASK_REGISTRY\n\nNONE\n",
    "ACCEPTED_ARTIFACTS.md": "# ACCEPTED_ARTIFACTS\n\nNONE\n",
    "REPOSITORY_LOCK.md": "# REPOSITORY_LOCK\n\nPUSH_ALLOWED: false\n",
    "WORKSPACE_IDENTITY.md": "# WORKSPACE_IDENTITY\n\nPROJECT_NAME: Demo Project\nPUSH_ALLOWED: false\n",
}


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )


def _write_runtime(root: Path) -> None:
    runtime = root / "project-runtime"
    runtime.mkdir()
    for name, text in RUNTIME_CONTENT.items():
        (runtime / name).write_text(text, encoding="utf-8")
    state = runtime / "state"
    state.mkdir()
    (state / "PROJECT_STATE.json").write_text(
        json.dumps(
            {
                "project_slug": "demo-project",
                "package_version": "3.7.9",
                "governance_ruleset_version": "3.7.9",
                "runtime_schema_version": "3.1.1",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_package_fixture(root: Path) -> None:
    aso_root = root / "agent-system" / "tools" / "aso"
    package = aso_root / "agent_system_orchestrator_aso"
    (package / "aso_tool" / "commands").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "README.md").write_text(PACKAGE_README, encoding="utf-8")
    (root / "agent-system" / "README.md").write_text(PACKAGE_README, encoding="utf-8")
    (aso_root / "aso.py").write_text(
        (
            "import sys\n"
            "from agent_system_orchestrator_aso.aso_tool.aso import build_parser, main\n"
            'if __name__ == "__main__":\n'
            "    sys.exit(main())\n"
        ),
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("\n", encoding="utf-8")
    (package / "cli.py").write_text("from .aso_tool.aso import main\n", encoding="utf-8")
    (package / "aso_tool" / "__init__.py").write_text("\n", encoding="utf-8")
    (package / "aso_tool" / "commands" / "__init__.py").write_text("\n", encoding="utf-8")
    (package / "aso_tool" / "aso.py").write_text(
        (
            "import argparse\n"
            "def build_parser():\n"
            "    return argparse.ArgumentParser(prog='aso')\n"
            "def main(argv=None):\n"
            "    build_parser().parse_args(argv)\n"
            "    return 0\n"
        ),
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        (
            "[project]\n"
            'name = "aso-fixture"\n'
            'version = "0.0.0"\n'
            "\n"
            "[project.scripts]\n"
            'aso = "agent_system_orchestrator_aso.cli:main"\n'
            "\n"
            "[tool.setuptools.packages.find]\n"
            'where = ["agent-system/tools/aso"]\n'
            'include = ["agent_system_orchestrator_aso*"]\n'
        )
        + PYPROJECT_RESOURCE_DATA,
        encoding="utf-8",
    )
    write_minimal_package_resources(package)
    write_resource_manifest_in(root)
    (root / ".gitignore").write_text(
        "/project-runtime/\n/project-input/\n/project-archive/\n",
        encoding="utf-8",
    )
    (root / ".github" / "workflows" / "governance.yml").write_text(
        (
            "name: governance\n"
            "on:\n"
            "  push:\n"
            "    branches:\n"
            "      - main\n"
            "      - upgrade/**\n"
        ),
        encoding="utf-8",
    )


class CliModeGuardTests(unittest.TestCase):
    def test_package_root_omitted_mode_auto_detects_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_package_fixture(root)
            json_out = root / "status.json"

            result = _run_cli("status", "--root", str(root), "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO package status:", result.stdout)
            self.assertEqual(json.loads(json_out.read_text(encoding="utf-8"))["mode"], "package")

    def test_workspace_root_omitted_mode_auto_detects_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_runtime(root)
            json_out = root / "status.json"

            result = _run_cli("status", "--root", str(root), "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Project: demo-project", result.stdout)
            self.assertEqual(json.loads(json_out.read_text(encoding="utf-8"))["mode"], "workspace")

    def test_explicit_package_mode_bypasses_ambiguous_auto_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_package_fixture(root)
            _write_runtime(root)
            json_out = root / "status.json"

            result = _run_cli(
                "status",
                "--root",
                str(root),
                "--mode",
                "package",
                "--json-out",
                str(json_out),
            )

            self.assertNotIn("ASO_MODE_AMBIGUOUS", result.stderr)
            self.assertEqual(json.loads(json_out.read_text(encoding="utf-8"))["mode"], "package")

    def test_explicit_workspace_mode_bypasses_ambiguous_auto_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_package_fixture(root)
            _write_runtime(root)
            json_out = root / "status.json"

            result = _run_cli(
                "status",
                "--root",
                str(root),
                "--mode",
                "workspace",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("ASO_MODE_AMBIGUOUS", result.stderr)
            self.assertEqual(json.loads(json_out.read_text(encoding="utf-8"))["mode"], "workspace")

    def test_ambiguous_root_omitted_mode_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_package_fixture(root)
            _write_runtime(root)

            result = _run_cli("status", "--root", str(root))

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("ASO_MODE_AMBIGUOUS", result.stderr)
            self.assertIn("Pass --mode package or --mode workspace explicitly", result.stderr)


if __name__ == "__main__":
    unittest.main()
