from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
ASO_TOOL_ROOT = REPO_ROOT / "agent-system" / "tools" / "aso"
CLI = ASO_TOOL_ROOT / "aso.py"
FIXTURES = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "project_verify_clean"

sys.path.insert(0, str(ASO_TOOL_ROOT))

from agent_system_orchestrator_aso.aso_tool import lockfile  # noqa: E402
from agent_system_orchestrator_aso.aso_tool.commands import project  # noqa: E402


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )


def _write(path: Path, text: str = "fixture\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _copy_fixture(name: str, target: Path) -> None:
    shutil.copytree(FIXTURES / name, target)


def _init_git(root: Path) -> None:
    result = subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=False, capture_output=True)
    if result.returncode != 0:
        subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "checkout", "-b", "main"], check=True, capture_output=True)


class ProjectCommandTests(unittest.TestCase):
    def test_project_help_surfaces_are_available(self) -> None:
        cases = (
            ["project", "--help"],
            ["project", "create", "--help"],
            ["project", "verify-clean", "--help"],
        )

        for args in cases:
            with self.subTest(args=args):
                result = _run_cli(args)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)

    def test_create_local_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "demo-project"

            create_result = _run_cli(
                [
                    "project",
                    "create",
                    "--local",
                    "--target",
                    str(target),
                    "--name",
                    "Demo Project",
                    "--slug",
                    "demo-project",
                    "--profile",
                    "generic",
                    "--repo-url",
                    "https://github.com/example/demo-project.git",
                    "--branch",
                    "main",
                ]
            )

            lock = json.loads((target / lockfile.LOCKFILE_NAME).read_text(encoding="utf-8"))
            self.assertTrue((target / ".gitignore").is_file())
            self.assertTrue((target / "README.md").is_file())
            self.assertTrue((target / "agent-system" / "tools" / "aso" / "aso.py").is_file())
            self.assertTrue((target / "project-input").is_dir())
            self.assertTrue((target / "project-runtime").is_dir())
            self.assertTrue((target / "project-archive").is_dir())
            self.assertFalse((target / "agent-system" / ".git").exists())

        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        self.assertIn("Engine mode: vendored", create_result.stdout)
        self.assertIn("Runtime schema: 3.0.0", create_result.stdout)
        self.assertEqual(lock["aso_engine"]["version"], "3.2.0")
        self.assertEqual(lock["aso_engine"]["runtime_schema"], "3.0.0")
        self.assertEqual(lock["project"]["repo_url"], "https://github.com/example/demo-project.git")

    def test_verify_clean_accepts_valid_fixture(self) -> None:
        result = _run_cli(["project", "verify-clean", "--root", str(FIXTURES / "valid_minimal"), "--strict"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ASO project verify-clean: PASS", result.stdout)
        self.assertIn("Violations: 0", result.stdout)

    def test_verify_clean_accepts_generated_project_and_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target = tmp_root / "demo-project"
            report_path = tmp_root / "verify-clean.json"

            create_result = _run_cli(
                [
                    "project",
                    "create",
                    "--local",
                    "--target",
                    str(target),
                    "--name",
                    "Demo Project",
                    "--slug",
                    "demo-project",
                    "--profile",
                    "generic",
                    "--repo-url",
                    "https://github.com/example/demo-project.git",
                    "--branch",
                    "main",
                ]
            )
            verify_result = _run_cli(
                [
                    "project",
                    "verify-clean",
                    "--root",
                    str(target),
                    "--strict",
                    "--json-out",
                    str(report_path),
                ]
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        self.assertEqual(verify_result.returncode, 0, verify_result.stderr)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["lockfile_status"], "pass")
        self.assertEqual(report["gitignore_status"], "pass")
        self.assertEqual(report["tracked_forbidden_paths"], [])
        self.assertEqual(report["nested_git_paths"], [])

    def test_verify_clean_non_strict_reports_violations_without_failing(self) -> None:
        result = _run_cli(["project", "verify-clean", "--root", str(FIXTURES / "invalid_missing_gitignore")])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ASO project verify-clean: FAIL", result.stdout)
        self.assertIn("PROJECT_VERIFY_CLEAN_002", result.stdout)

    def test_verify_clean_strict_fails_for_missing_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "missing-gitignore.json"
            result = _run_cli(
                [
                    "project",
                    "verify-clean",
                    "--root",
                    str(FIXTURES / "invalid_missing_gitignore"),
                    "--strict",
                    "--json-out",
                    str(report_path),
                ]
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["status"], "fail")
        self.assertIn("PROJECT_VERIFY_CLEAN_002", {item["rule_id"] for item in report["violations"]})

    def test_verify_clean_strict_fails_for_tracked_forbidden_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "tracked-forbidden"
            _copy_fixture("valid_minimal", root)
            _init_git(root)
            _write(root / "project-input" / "aso_upgrade_project_factory_p0" / "TASK.md", "local upgrade\n")
            _write(root / ".env", "TOKEN=local\n")
            _write(root / "agent-system" / "tools" / "aso" / "__pycache__" / "aso.pyc", "cache\n")
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "add",
                    "-f",
                    "project-input/aso_upgrade_project_factory_p0/TASK.md",
                    ".env",
                    "agent-system/tools/aso/__pycache__/aso.pyc",
                ],
                check=True,
                capture_output=True,
            )

            result = _run_cli(["project", "verify-clean", "--root", str(root), "--strict"])

        self.assertEqual(result.returncode, 1)
        self.assertIn("PROJECT_VERIFY_CLEAN_007", result.stdout)
        self.assertIn("project-input/aso_upgrade_project_factory_p0/TASK.md", result.stdout)

    def test_verify_clean_strict_fails_for_nested_agent_system_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "nested-git"
            _copy_fixture("valid_minimal", root)
            _write(root / "agent-system" / "package" / ".git" / "config", "[core]\n")

            result = _run_cli(["project", "verify-clean", "--root", str(root), "--strict"])

        self.assertEqual(result.returncode, 1)
        self.assertIn("PROJECT_VERIFY_CLEAN_008", result.stdout)
        self.assertIn("agent-system/package/.git", result.stdout)

    def test_create_refuses_non_empty_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "demo-project"
            _write(target / "existing.txt")

            result = _run_cli(
                [
                    "project",
                    "create",
                    "--local",
                    "--target",
                    str(target),
                    "--name",
                    "Demo Project",
                    "--slug",
                    "demo-project",
                ]
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("target must be empty", result.stderr)

    def test_vendored_copy_excludes_forbidden_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            source = tmp_root / "source-agent-system"
            target = tmp_root / "generated"
            _write(source / "README.md", "# Fixture\n")
            _write(source / "tools" / "aso" / "aso.py", "print('ok')\n")
            _write(source / ".git" / "config")
            _write(source / "project-runtime" / "state.json")
            _write(source / "logs" / "run.log")
            _write(source / ".venv" / "bin" / "python")
            _write(source / "tmp" / "scratch.txt")
            _write(source / "private" / "key.pem")
            _write(source / "project-input" / "aso_upgrade_project_factory_p0" / "TASK.md")
            _write(source / "tools" / "aso" / "__pycache__" / "aso.pyc")
            _write(source / ".env.local")

            summary = project.create_project(
                target=target,
                project_name="Demo Project",
                project_slug="demo-project",
                repo_url=None,
                source_agent_system=source,
            )

            generated_agent_system = target / "agent-system"
            self.assertEqual(summary.copied_files, 2)
            self.assertTrue((generated_agent_system / "README.md").is_file())
            self.assertTrue((generated_agent_system / "tools" / "aso" / "aso.py").is_file())
            self.assertFalse((generated_agent_system / ".git").exists())
            self.assertFalse((generated_agent_system / "project-runtime").exists())
            self.assertFalse((generated_agent_system / "logs").exists())
            self.assertFalse((generated_agent_system / ".venv").exists())
            self.assertFalse((generated_agent_system / "tmp").exists())
            self.assertFalse((generated_agent_system / "private").exists())
            self.assertFalse((generated_agent_system / "project-input").exists())
            self.assertFalse((generated_agent_system / "tools" / "aso" / "__pycache__").exists())
            self.assertFalse((generated_agent_system / ".env.local").exists())


if __name__ == "__main__":
    unittest.main()
