from __future__ import annotations

import subprocess
import sys
import unittest
import tomllib
from pathlib import Path

import agent_system_orchestrator_aso.cli as wrapper_cli


REPO_ROOT = Path(__file__).resolve().parents[4]


class PackagingCommandTests(unittest.TestCase):
    def test_module_entrypoint_exposes_existing_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent_system_orchestrator_aso", "--help"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Read-only Agent System Orchestrator control-plane helper.", result.stdout)
        self.assertIn("status", result.stdout)
        self.assertIn("lint", result.stdout)
        self.assertIn("doctor", result.stdout)
        self.assertIn("validate-rules", result.stdout)
        self.assertIn("plan-next", result.stdout)
        self.assertIn("checkpoint-preflight", result.stdout)
        self.assertIn("dashboard", result.stdout)
        self.assertIn("dag", result.stdout)
        self.assertIn("state", result.stdout)
        self.assertIn("archive", result.stdout)
        self.assertIn("package-sync", result.stdout)

    def test_console_script_entrypoint_is_registered_in_project_metadata(self) -> None:
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("[project.scripts]", pyproject)
        self.assertIn('aso = "agent_system_orchestrator_aso.cli:main"', pyproject)

    def test_non_editable_install_has_bundled_script_fallback(self) -> None:
        bundled_tool_dir = wrapper_cli._bundled_aso_tool_dir()

        self.assertTrue((bundled_tool_dir / "aso.py").is_file())
        self.assertTrue((bundled_tool_dir / "commands" / "status.py").is_file())
        self.assertTrue((bundled_tool_dir / "commands" / "dag.py").is_file())
        self.assertTrue((bundled_tool_dir / "commands" / "package_checks.py").is_file())
        self.assertTrue((bundled_tool_dir / "commands" / "package_sync.py").is_file())
        self.assertFalse((bundled_tool_dir / "tests").exists())

    def test_stage2_package_version_is_coherent(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        init_file = (REPO_ROOT / "agent_system_orchestrator_aso" / "__init__.py").read_text(
            encoding="utf-8"
        )

        self.assertEqual(pyproject["project"]["version"], "3.0.2")
        self.assertIn('__version__ = "3.0.2"', init_file)


if __name__ == "__main__":
    unittest.main()
