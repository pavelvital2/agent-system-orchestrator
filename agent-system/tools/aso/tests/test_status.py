from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
INCIDENT_001_ROOT = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "hotfix_p4_1"
    / "incident_001_workspace_root"
)


RUNTIME_CONTENT = {
    "PROJECT_STATE.md": """# PROJECT_STATE

PROJECT_SLUG:
demo-project

ACTUAL_BRANCH: main
PROJECT_STATUS: active
PROJECT_CHECKPOINT_STATUS: pending
PUSH_ALLOWED: false
""",
    "CURRENT_GATE.md": """# CURRENT_GATE

STATUS:
open
""",
    "NEXT_ACTION.md": """# NEXT_ACTION

ACTION_TYPE: create_agent
TARGET_ROLE: developer
TASK_ID: TASK_DEMO_001
TASK_PACKET: project-runtime/tasks/active/TASK_DEMO_001.md
""",
    "TASK_REGISTRY.md": "# TASK_REGISTRY\n\nNONE\n",
    "ACCEPTED_ARTIFACTS.md": "# ACCEPTED_ARTIFACTS\n\nNONE\n",
    "REPOSITORY_LOCK.md": """# REPOSITORY_LOCK

PUSH_ALLOWED:
false
""",
    "WORKSPACE_IDENTITY.md": """# WORKSPACE_IDENTITY

PROJECT_NAME: Demo Project
ACTUAL_BRANCH:
main
PUSH_ALLOWED: false
""",
}


PACKAGE_README = """# Package

Use the read-only ASO helper at `agent-system/tools/aso/aso.py`.

```text
python3 agent-system/tools/aso/aso.py status --root . --mode package
python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
python3 agent-system/tools/aso/aso.py status --root /path/to/project --mode workspace
python3 agent-system/tools/aso/aso.py lint --root /path/to/project --mode workspace --strict
```

It does not provide mutation, dispatch, or checkpoint commands.
"""


def write_runtime(root: Path, overrides: dict[str, str] | None = None) -> list[Path]:
    runtime = root / "project-runtime"
    runtime.mkdir()
    paths = []
    content = dict(RUNTIME_CONTENT)
    if overrides:
        content.update(overrides)
    for name, text in content.items():
        path = runtime / name
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths


def write_package_fixture(root: Path, *, include_untracked_input: bool = False) -> None:
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
        ),
        encoding="utf-8",
    )
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
    if include_untracked_input:
        (root / "project-input").mkdir()
        (root / "project-input" / "local-task.md").write_text("local\n", encoding="utf-8")


class StatusCommandTests(unittest.TestCase):
    def test_status_outputs_normalized_summary_and_json_without_runtime_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_paths = write_runtime(root)
            mtimes_before = {path: path.stat().st_mtime_ns for path in runtime_paths}
            json_out = root / "status.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "status",
                    "--root",
                    str(root),
                    "--mode",
                    "workspace",
                    "--json-out",
                    str(json_out),
                ],
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Project: demo-project", result.stdout)
            self.assertIn("Branch: main", result.stdout)
            self.assertIn("Project status: active", result.stdout)
            self.assertIn("Current gate: open", result.stdout)
            self.assertIn("Checkpoint status: pending", result.stdout)
            self.assertIn("Next action: create_agent target=developer task=TASK_DEMO_001", result.stdout)
            self.assertIn(
                "Push allowed values: PROJECT_STATE=false, REPOSITORY_LOCK=false, WORKSPACE_IDENTITY=false",
                result.stdout,
            )
            self.assertIn("Runtime consistency: PASS", result.stdout)
            self.assertIn("Findings: 0", result.stdout)

            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["tool"], "aso")
            self.assertEqual(report["command"], "status")
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["summary"]["runtime_consistency"], "PASS")
            self.assertEqual(report["summary"]["finding_count"], 0)
            self.assertEqual(report["findings"], [])

            mtimes_after = {path: path.stat().st_mtime_ns for path in runtime_paths}
            self.assertEqual(mtimes_before, mtimes_after)

    def test_status_reports_conflicting_push_allowed_as_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(
                root,
                {
                    "REPOSITORY_LOCK.md": "# REPOSITORY_LOCK\n\nPUSH_ALLOWED: true\n",
                },
            )

            result = subprocess.run(
                [sys.executable, str(CLI), "status", "--root", str(root)],
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Runtime consistency: FAIL", result.stdout)
            self.assertIn("Findings: 1", result.stdout)

    def test_package_status_passes_without_project_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_package_fixture(root, include_untracked_input=True)
            json_out = root / "package-status.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "status",
                    "--root",
                    str(root),
                    "--mode",
                    "package",
                    "--json-out",
                    str(json_out),
                ],
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ASO package status: PASSED", result.stdout)
            self.assertIn("Package consistency: PASS", result.stdout)
            self.assertIn("project-runtime=absent", result.stdout)
            self.assertIn("project-input=present-untracked", result.stdout)

            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "package")
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["summary"]["generated_roots"]["project-runtime"], "absent")
            self.assertEqual(report["summary"]["generated_roots"]["project-input"], "present-untracked")

    def test_package_status_rejects_workspace_root_with_mode_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "status.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "status",
                    "--root",
                    str(INCIDENT_001_ROOT),
                    "--mode",
                    "package",
                    "--json-out",
                    str(json_out),
                ],
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("MODE_GUARD_001", result.stdout)
            self.assertIn("Use --mode workspace", result.stdout)
            self.assertNotIn("PACKAGE_LAYOUT_006", result.stdout)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["findings"][0]["rule_id"], "MODE_GUARD_001")
            self.assertIn("--mode workspace", report["findings"][0]["recommendation"])


if __name__ == "__main__":
    unittest.main()
