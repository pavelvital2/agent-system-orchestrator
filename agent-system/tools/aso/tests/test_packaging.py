from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


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
        self.assertIn("archive", result.stdout)

    def test_console_script_entrypoint_is_registered_in_project_metadata(self) -> None:
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("[project.scripts]", pyproject)
        self.assertIn('aso = "agent_system_orchestrator_aso.cli:main"', pyproject)


if __name__ == "__main__":
    unittest.main()
