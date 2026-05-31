from __future__ import annotations

import subprocess
import sys
import unittest
from importlib import import_module
from importlib import metadata
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib


REPO_ROOT = Path(__file__).resolve().parents[4]
ASO_TOOL_ROOT = REPO_ROOT / "agent-system" / "tools" / "aso"

sys.path.insert(0, str(ASO_TOOL_ROOT))

import agent_system_orchestrator_aso.cli as wrapper_cli  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import runtime_schema_contracts  # noqa: E402


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
        self.assertIn("Filesystem-governed ASO control-plane CLI with read-only diagnostics", result.stdout)
        self.assertIn("explicit confirmed writes.", result.stdout)
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

    def test_python_310_toml_parser_runtime_dependency_is_conditional(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        dependencies = pyproject["project"]["dependencies"]

        self.assertIn('tomli>=2; python_version < "3.11"', dependencies)

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
            ["RESOURCE_MANIFEST.json", "agent-system/**/*"],
        )
        resources_root = ASO_TOOL_ROOT / "agent_system_orchestrator_aso" / "resources"
        self.assertTrue((resources_root / "RESOURCE_MANIFEST.json").is_file())
        self.assertTrue((resources_root / "agent-system/00_start/ORCHESTRATOR_START.md").is_file())
        self.assertTrue((resources_root / "agent-system/ORCHESTRATOR_RUNTIME_CONTRACT.json").is_file())
        self.assertTrue((resources_root / "agent-system/tools/aso/aso.py").is_file())
        self.assertTrue((resources_root / "agent-system/09_validators/rules/governance_rules.json").is_file())
        self.assertTrue(
            (
                resources_root
                / "agent-system/02_runtime/PLANNER_DISPATCHABILITY_GATE_P5_4_CONTRACT.md"
            ).is_file()
        )
        self.assertFalse(
            (
                resources_root
                / "agent-system/tools/aso/agent_system_orchestrator_aso/resources/agent-system"
            ).exists()
        )

    def test_package_version_is_coherent(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        agent_readme = (REPO_ROOT / "agent-system" / "README.md").read_text(encoding="utf-8")
        authority_map = (
            REPO_ROOT / "agent-system" / "02_runtime" / "CONTRACT_AUTHORITY_MAP.md"
        ).read_text(encoding="utf-8")
        package_version = pyproject["project"]["version"]

        self.assertEqual(package_version, runtime_schema_contracts.ACTIVE_PACKAGE_VERSION)
        self.assertIn(f"governed `{package_version}` package/governance tuple", root_readme)
        self.assertIn(f"governed `{package_version}` package/governance tuple", agent_readme)
        self.assertIn(f"package_version: {package_version}", authority_map)
        self.assertIn(
            f"governance_ruleset_version: {runtime_schema_contracts.ACTIVE_GOVERNANCE_RULESET_VERSION}",
            authority_map,
        )

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
        self.assertIn("install-test-smoke:", makefile)
        self.assertIn("install-test:", makefile)
        self.assertIn('-m pip install -e ".[test]"', makefile)
        self.assertIn("agent-system/scripts/install_aso_clean.sh --source .", makefile)
        self.assertIn("agent-system/scripts/installed_cli_smoke.sh", makefile)
        self.assertIn('python" -m pip install "$$dist_dir"/*.whl', makefile)
        self.assertIn('python" -m pip install "$$dist_dir"/*.tar.gz', makefile)
        self.assertIn('build-venv/bin/python" -m pip install -U pip setuptools wheel build', makefile)
        self.assertIn('build-venv/bin/python" -m build "$$build_src" --outdir "$$dist_dir"', makefile)
        self.assertIn("--with-test", makefile)
        self.assertIn("import jsonschema", makefile)
        self.assertIn("md.version('jsonschema')", makefile)
        self.assertIn("clean-console", makefile)
        self.assertIn("wheel-console", makefile)
        self.assertIn("sdist-console", makefile)
        self.assertIn("project create --local --target", makefile)
        self.assertIn("project verify-clean --root", makefile)
        self.assertIn("agent_system_orchestrator_aso.cli", makefile)
        self.assertIn("/site-packages/agent_system_orchestrator_aso/__init__.py", makefile)
        self.assertIn("e2e-real-tz-smoke:", makefile)
        self.assertIn("source-contamination-guard:", makefile)
        self.assertIn("ci: test smoke doctor lint install-smoke", makefile)
        self.assertIn("$(MAKE) install-test-smoke", makefile)
        self.assertIn("$(MAKE) e2e-real-tz-smoke", makefile)
        self.assertIn("$(MAKE) source-contamination-guard", makefile)

    def test_editable_installers_use_isolated_dependency_install(self) -> None:
        for relpath in ("install.sh", "install.ps1"):
            with self.subTest(relpath=relpath):
                installer = (REPO_ROOT / relpath).read_text(encoding="utf-8")

                self.assertNotIn("--system-site-packages", installer)
                self.assertNotIn("--no-deps", installer)
                self.assertNotIn("--no-build-isolation", installer)
                self.assertIn("pip install --upgrade pip setuptools wheel", installer)
                self.assertIn("install -e .", installer)
                self.assertIn("project create --local --target", installer)
                self.assertIn("project verify-clean --root", installer)


if __name__ == "__main__":
    unittest.main()
