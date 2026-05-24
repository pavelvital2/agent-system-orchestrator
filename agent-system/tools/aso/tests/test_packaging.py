from __future__ import annotations

import subprocess
import sys
import unittest
import tomllib
from importlib import import_module
from importlib import metadata
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
ASO_TOOL_ROOT = REPO_ROOT / "agent-system" / "tools" / "aso"

sys.path.insert(0, str(ASO_TOOL_ROOT))

import agent_system_orchestrator_aso.cli as wrapper_cli  # noqa: E402


class PackagingCommandTests(unittest.TestCase):
    def test_module_entrypoint_exposes_existing_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agent_system_orchestrator_aso", "--help"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
            env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ASO_TOOL_ROOT)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Read-only Agent System Orchestrator control-plane helper.", result.stdout)
        self.assertIn("status", result.stdout)
        self.assertIn("lint", result.stdout)
        self.assertIn("doctor", result.stdout)
        self.assertIn("validate-rules", result.stdout)
        self.assertIn("plan-next", result.stdout)
        self.assertIn("record-result", result.stdout)
        self.assertIn("checkpoint-preflight", result.stdout)
        self.assertIn("dashboard", result.stdout)
        self.assertIn("dag", result.stdout)
        self.assertIn("state", result.stdout)
        self.assertIn("archive", result.stdout)
        self.assertIn("package-layout", result.stdout)
        self.assertIn("package-sync", result.stdout)
        self.assertIn("orchestrator", result.stdout)

    def test_console_script_entrypoint_is_registered_in_project_metadata(self) -> None:
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("[project.scripts]", pyproject)
        self.assertIn('aso = "agent_system_orchestrator_aso.cli:main"', pyproject)
        self.assertTrue(callable(wrapper_cli.main))

    def test_test_extra_installs_schema_test_dependency(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        test_extra = pyproject["project"]["optional-dependencies"]["test"]

        self.assertIn("jsonschema>=4.22", test_extra)

    def test_schema_test_environment_has_jsonschema_available(self) -> None:
        try:
            import_module("jsonschema")
        except ImportError as exc:
            raise AssertionError(
                "jsonschema must be importable for schema tests; install the supported test extra with "
                'python3 -m pip install -e ".[test]"'
            ) from exc

        self.assertIsInstance(metadata.version("jsonschema"), str)

    def test_canonical_package_contains_aso_implementation(self) -> None:
        bundled_tool_dir = ASO_TOOL_ROOT / "agent_system_orchestrator_aso" / "aso_tool"

        self.assertTrue((bundled_tool_dir / "aso.py").is_file())
        self.assertTrue((bundled_tool_dir / "commands" / "status.py").is_file())
        self.assertTrue((bundled_tool_dir / "commands" / "dag.py").is_file())
        self.assertTrue((bundled_tool_dir / "commands" / "package_checks.py").is_file())
        self.assertTrue((bundled_tool_dir / "commands" / "package_sync.py").is_file())
        self.assertTrue((bundled_tool_dir / "commands" / "record_result.py").is_file())
        self.assertFalse((bundled_tool_dir / "tests").exists())

    def test_setuptools_discovers_canonical_package_only(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        package_find = pyproject["tool"]["setuptools"]["packages"]["find"]

        self.assertEqual(package_find["where"], ["agent-system/tools/aso"])
        self.assertEqual(package_find["include"], ["agent_system_orchestrator_aso*"])
        self.assertFalse((REPO_ROOT / "agent_system_orchestrator_aso").exists())

    def test_runtime_resource_package_data_is_declared(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        package_data = pyproject["tool"]["setuptools"]["package-data"]

        self.assertEqual(
            package_data["agent_system_orchestrator_aso.resources"],
            ["agent-system/**/*.json", "agent-system/**/*.md"],
        )
        resources_root = ASO_TOOL_ROOT / "agent_system_orchestrator_aso" / "resources"
        self.assertTrue((resources_root / "agent-system/09_validators/rules/governance_rules.json").is_file())
        self.assertTrue(
            (
                resources_root
                / "agent-system/02_runtime/PLANNER_DISPATCHABILITY_GATE_P5_4_CONTRACT.md"
            ).is_file()
        )

    def test_package_version_is_coherent(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        init_file = (ASO_TOOL_ROOT / "agent_system_orchestrator_aso" / "__init__.py").read_text(encoding="utf-8")
        package_version = pyproject["project"]["version"]

        self.assertEqual(package_version, "3.7.6")
        self.assertIn(f'__version__ = "{package_version}"', init_file)

    def test_package_layout_verify_accepts_package_mode(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ASO_TOOL_ROOT / "aso.py"),
                "package-layout",
                "verify",
                "--root",
                ".",
                "--mode",
                "package",
            ],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
            env={"PYTHONDONTWRITEBYTECODE": "1"},
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ASO package-layout verify: PASSED", result.stdout)

    def test_install_smoke_target_covers_clean_console_import_path(self) -> None:
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertIn("install-smoke:", makefile)
        self.assertIn("install-test:", makefile)
        self.assertIn('-m pip install -e ".[test]"', makefile)
        self.assertIn("agent-system/scripts/install_aso_clean.sh --source .", makefile)
        self.assertIn("bin/aso\" --help >/dev/null", makefile)
        self.assertIn("bin/aso\" status --root . --mode package", makefile)
        self.assertIn("bin/aso\" package-layout verify --root . --mode package --strict", makefile)
        self.assertIn("agent_system_orchestrator_aso.cli", makefile)
        self.assertIn("/site-packages/agent_system_orchestrator_aso/__init__.py", makefile)
        self.assertIn("ci: test smoke doctor lint install-smoke", makefile)


if __name__ == "__main__":
    unittest.main()
