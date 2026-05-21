from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
ASO_TOOL_ROOT = REPO_ROOT / "agent-system" / "tools" / "aso"
CLI = ASO_TOOL_ROOT / "aso.py"
FIXTURES = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "project_verify_clean"

sys.path.insert(0, str(ASO_TOOL_ROOT))

from agent_system_orchestrator_aso.aso_tool import lockfile  # noqa: E402
from agent_system_orchestrator_aso.aso_tool.commands import project  # noqa: E402


def _run_cli(args: list[str], *, env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env_overrides:
        env.update(env_overrides)
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
        self.assertEqual(lock["aso_engine"]["version"], "3.3.0")
        self.assertEqual(lock["aso_engine"]["runtime_schema"], "3.0.0")
        self.assertEqual(lock["project"]["repo_url"], "https://github.com/example/demo-project.git")

    def test_create_local_reference_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "ref-demo"

            create_result = _run_cli(
                [
                    "project",
                    "create",
                    "--local",
                    "--engine-mode",
                    "reference",
                    "--target",
                    str(target),
                    "--name",
                    "Reference Demo",
                    "--slug",
                    "ref-demo",
                    "--profile",
                    "generic",
                    "--repo-url",
                    "none",
                    "--branch",
                    "main",
                ]
            )
            verify_result = _run_cli(["project", "verify-clean", "--root", str(target), "--strict"])
            lock = json.loads((target / lockfile.LOCKFILE_NAME).read_text(encoding="utf-8"))

            self.assertTrue((target / ".gitignore").is_file())
            self.assertTrue((target / "README.md").is_file())
            self.assertTrue((target / "project-input").is_dir())
            self.assertTrue((target / "project-runtime").is_dir())
            self.assertTrue((target / "project-archive").is_dir())
            self.assertFalse((target / "agent-system").exists())

        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        self.assertEqual(verify_result.returncode, 0, verify_result.stderr)
        self.assertIn("Engine mode: reference", create_result.stdout)
        self.assertNotIn("- agent-system/", create_result.stdout)
        self.assertIn("ASO project verify-clean: PASS", verify_result.stdout)
        self.assertEqual(lock["aso_engine"]["version"], "3.3.0")
        self.assertEqual(lock["aso_engine"]["runtime_schema"], "3.0.0")
        self.assertEqual(lock["aso_engine"]["engine_mode"], "reference")
        self.assertIsNone(lock["project"]["repo_url"])

    def test_create_github_dry_run_writes_deterministic_plan_without_target_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target = tmp_root / "github-demo"
            report_path = tmp_root / "github-plan.json"
            second_report_path = tmp_root / "github-plan-2.json"

            args = [
                "project",
                "create",
                "--github",
                "--dry-run",
                "--target",
                str(target),
                "--name",
                "Demo",
                "--slug",
                "demo",
                "--profile",
                "generic",
                "--owner",
                "example",
                "--repo",
                "demo",
                "--private",
                "--branch",
                "main",
                "--engine-mode",
                "reference",
            ]
            result = _run_cli([*args, "--json-out", str(report_path)], env_overrides={"PATH": str(tmp_root / "empty-bin")})
            second_result = _run_cli([*args, "--json-out", str(second_report_path)])
            plan = json.loads(report_path.read_text(encoding="utf-8"))
            second_plan = json.loads(second_report_path.read_text(encoding="utf-8"))

            self.assertFalse(target.exists())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(second_result.returncode, 0, second_result.stderr)
        self.assertEqual(plan, second_plan)
        self.assertEqual(plan["target"], str(target))
        self.assertEqual(plan["project_name"], "Demo")
        self.assertEqual(plan["slug"], "demo")
        self.assertEqual(plan["profile"], "generic")
        self.assertEqual(plan["engine_mode"], "reference")
        self.assertEqual(plan["repo_owner"], "example")
        self.assertEqual(plan["repo_name"], "demo")
        self.assertEqual(plan["visibility"], "private")
        self.assertEqual(plan["branch"], "main")
        self.assertEqual(
            plan["planned_local_files"],
            [".gitignore", "README.md", "aso.lock", "project-archive/", "project-input/", "project-runtime/"],
        )
        self.assertEqual(
            plan["planned_git_commands"],
            [
                f"git -C {target} init -b main",
                f"git -C {target} add .gitignore README.md aso.lock",
                f'git -C {target} commit -m "Initial ASO project"',
            ],
        )
        self.assertEqual(
            plan["planned_gh_command"],
            f"gh repo create example/demo --private --source {target} --remote origin --push",
        )
        self.assertTrue(plan["confirmation_required_for_real_publish"])

    def test_create_github_dry_run_uses_no_subprocesses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "github-demo"
            args = argparse.Namespace(
                github=True,
                dry_run=True,
                confirm_publish=False,
                target=str(target),
                name="Demo",
                slug="demo",
                profile="generic",
                owner="example",
                repo="demo",
                public=False,
                private=True,
                internal=False,
                branch="main",
                engine_mode="reference",
                json_out=None,
            )

            stdout = io.StringIO()
            with (
                mock.patch.object(project.subprocess, "run", side_effect=AssertionError("subprocess must not run")),
                contextlib.redirect_stdout(stdout),
            ):
                result = project.run_create(args)

        self.assertEqual(result, 0)
        self.assertEqual(
            json.loads(stdout.getvalue())["planned_gh_command"],
            f"gh repo create example/demo --private --source {target} --remote origin --push",
        )

    def test_create_github_requires_owner_and_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_args = [
                "project",
                "create",
                "--github",
                "--dry-run",
                "--target",
                str(Path(tmp) / "github-demo"),
                "--name",
                "Demo",
                "--slug",
                "demo",
                "--profile",
                "generic",
                "--private",
                "--branch",
                "main",
                "--engine-mode",
                "reference",
            ]

            missing_owner = _run_cli([*base_args, "--repo", "demo"])
            missing_repo = _run_cli([*base_args, "--owner", "example"])

        self.assertEqual(missing_owner.returncode, 1)
        self.assertIn("owner is required for --github", missing_owner.stderr)
        self.assertEqual(missing_repo.returncode, 1)
        self.assertIn("repo is required for --github", missing_repo.stderr)

    def test_create_mode_and_visibility_flags_are_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "github-demo")
            local_and_github = _run_cli(
                [
                    "project",
                    "create",
                    "--local",
                    "--github",
                    "--target",
                    target,
                    "--name",
                    "Demo",
                    "--slug",
                    "demo",
                ]
            )
            public_and_private = _run_cli(
                [
                    "project",
                    "create",
                    "--github",
                    "--dry-run",
                    "--target",
                    target,
                    "--name",
                    "Demo",
                    "--slug",
                    "demo",
                    "--owner",
                    "example",
                    "--repo",
                    "demo",
                    "--public",
                    "--private",
                ]
            )

        self.assertEqual(local_and_github.returncode, 2)
        self.assertIn("not allowed with argument", local_and_github.stderr)
        self.assertEqual(public_and_private.returncode, 2)
        self.assertIn("not allowed with argument", public_and_private.stderr)

    def test_verify_clean_accepts_valid_fixture(self) -> None:
        result = _run_cli(["project", "verify-clean", "--root", str(FIXTURES / "valid_minimal"), "--strict"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ASO project verify-clean: PASS", result.stdout)
        self.assertIn("Violations: 0", result.stdout)
        self.assertIn("Package drift: 3.2.0 is compatible with current package 3.3.0", result.stdout)

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

    def test_verify_clean_strict_fails_when_reference_git_tracks_agent_system(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "reference-tracked-agent-system"
            project.create_project(
                target=root,
                project_name="Reference Project",
                project_slug="reference-project",
                repo_url=None,
                engine_mode="reference",
            )
            _init_git(root)
            _write(root / "agent-system" / "README.md", "# Should not be tracked\n")
            subprocess.run(
                ["git", "-C", str(root), "add", "-f", "agent-system/README.md"],
                check=True,
                capture_output=True,
            )

            result = _run_cli(["project", "verify-clean", "--root", str(root), "--strict"])

        self.assertEqual(result.returncode, 1)
        self.assertIn("PROJECT_VERIFY_CLEAN_007", result.stdout)
        self.assertIn("agent-system/README.md", result.stdout)

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

    def test_create_rejects_invalid_engine_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_cli(
                [
                    "project",
                    "create",
                    "--local",
                    "--target",
                    str(Path(tmp) / "demo-project"),
                    "--name",
                    "Demo Project",
                    "--slug",
                    "demo-project",
                    "--engine-mode",
                    "linked",
                ]
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

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
