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
P1_FIXTURES = ASO_TOOL_ROOT / "tests" / "fixtures" / "project_factory_p1"

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


def _write_fake_github_tools(bin_dir: Path) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    git = bin_dir / "git"
    gh = bin_dir / "gh"
    git.write_text(
        """#!/usr/bin/env bash
set -eu
if [ "${1:-}" != "-C" ]; then
  exit 2
fi
target="$2"
shift 2
cmd="${1:-}"
case "$cmd" in
  rev-parse)
    if [ "${2:-}" = "--show-toplevel" ]; then
      if [ -d "$target/.git" ]; then
        cd "$target"
        pwd -P
        exit 0
      fi
      exit 1
    fi
    if [ "${2:-}" = "HEAD" ]; then
      echo "fakecommit123"
      exit 0
    fi
    ;;
  init)
    mkdir -p "$target/.git"
    exit 0
    ;;
  add)
    exit 0
    ;;
  commit)
    if [ "${FAKE_GIT_COMMIT_FAIL:-0}" = "1" ]; then
      echo "fake git commit failure" >&2
      exit 42
    fi
    exit 0
    ;;
  ls-files)
    if [ "${FAKE_GIT_FORBIDDEN_TRACKED:-0}" = "1" ]; then
      printf '%s\\n' .gitignore README.md aso.lock project-input/secret.md
    else
      printf '%s\\n' .gitignore README.md aso.lock
    fi
    exit 0
    ;;
  branch)
    if [ "${2:-}" = "--show-current" ]; then
      echo "main"
      exit 0
    fi
    ;;
  remote)
    exit 1
    ;;
esac
exit 2
""",
        encoding="utf-8",
    )
    gh.write_text(
        """#!/usr/bin/env bash
set -eu
if [ "${1:-}" = "auth" ] && [ "${2:-}" = "status" ]; then
  if [ "${FAKE_GH_AUTH_FAIL:-0}" = "1" ]; then
    echo "fake gh auth failure" >&2
    exit 43
  fi
  exit 0
fi
if [ "${1:-}" = "repo" ] && [ "${2:-}" = "create" ]; then
  if [ "${FAKE_GH_CREATE_FAIL:-0}" = "1" ]; then
    echo "fake gh repo create failure" >&2
    exit 44
  fi
  exit 0
fi
exit 2
""",
        encoding="utf-8",
    )
    git.chmod(0o755)
    gh.chmod(0o755)


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
            readme = (target / "README.md").read_text(encoding="utf-8")
            self.assertTrue((target / "agent-system" / "tools" / "aso" / "aso.py").is_file())
            self.assertTrue((target / "project-input").is_dir())
            self.assertFalse((target / "project-input" / "TZ.md").exists())
            self.assertTrue((target / "project-input" / "README.md").is_file())
            self.assertTrue((target / "project-runtime").is_dir())
            self.assertFalse((target / "project-runtime" / "state").exists())
            self.assertFalse((target / "project-runtime" / "PROJECT_STATE.md").exists())
            self.assertTrue((target / "project-archive").is_dir())
            self.assertFalse((target / "agent-system" / ".git").exists())
            verify_result = _run_cli(["project", "verify-clean", "--root", str(target), "--strict"])

        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        self.assertEqual(verify_result.returncode, 0, verify_result.stdout + verify_result.stderr)
        self.assertIn("Engine mode: vendored", create_result.stdout)
        self.assertIn("Runtime schema: 3.1.1", create_result.stdout)
        self.assertIn("Runtime state: not initialized", create_result.stdout)
        self.assertIn("Runtime markdown views: not materialized (0)", create_result.stdout)
        self.assertIn("state init --root", create_result.stdout)
        self.assertIn("--tz project-input/TZ_REAL.md --confirm-write", create_result.stdout)
        self.assertNotIn("--mode package", create_result.stdout)
        self.assertIn("--mode workspace", readme)
        self.assertIn("state init --root . --tz project-input/TZ_REAL.md --confirm-write", readme)
        self.assertIn("intake bootstrap --root . --tz project-input/TZ_REAL.md", readme)
        self.assertIn("plan-next --root . --strict", readme)
        self.assertIn("lint --root . --mode workspace --strict", readme)
        self.assertIn("doctor --root . --mode workspace --strict", readme)
        self.assertIn("lifecycle terminate-agent", readme)
        self.assertNotIn("--mode package", readme)
        self.assertEqual(lock["aso_engine"]["version"], lockfile.PACKAGE_VERSION)
        self.assertEqual(lock["aso_engine"]["runtime_schema"], lockfile.RUNTIME_SCHEMA_VERSION)
        self.assertEqual(lock["project"]["repo_url"], "https://github.com/example/demo-project.git")

    def test_create_defaults_to_local_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "demo-project"

            result = _run_cli(
                [
                    "project",
                    "create",
                    "--target",
                    str(target),
                    "--name",
                    "Demo Project",
                    "--slug",
                    "demo-project",
                    "--engine-mode",
                    "vendored",
                ]
            )
            wrapper_exists = (target / "agent-system" / "tools" / "aso" / "aso.py").is_file()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Engine mode: vendored", result.stdout)
        self.assertTrue(wrapper_exists)

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
            state_verify_result = _run_cli(["state", "verify", "--root", str(target), "--strict"])
            lock = json.loads((target / lockfile.LOCKFILE_NAME).read_text(encoding="utf-8"))

            self.assertTrue((target / ".gitignore").is_file())
            self.assertTrue((target / "README.md").is_file())
            self.assertTrue((target / "project-input").is_dir())
            self.assertFalse((target / "project-input" / "TZ.md").exists())
            self.assertTrue((target / "project-input" / "README.md").is_file())
            self.assertTrue((target / "project-runtime").is_dir())
            self.assertFalse((target / "project-runtime" / "state").exists())
            self.assertFalse((target / "project-runtime" / "PROJECT_STATE.md").exists())
            self.assertTrue((target / "project-archive").is_dir())
            self.assertFalse((target / "agent-system").exists())
            readme = (target / "README.md").read_text(encoding="utf-8")

        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        self.assertEqual(verify_result.returncode, 0, verify_result.stderr)
        self.assertNotEqual(state_verify_result.returncode, 0, state_verify_result.stdout + state_verify_result.stderr)
        self.assertIn("Engine mode: reference", create_result.stdout)
        self.assertIn("Runtime state: not initialized", create_result.stdout)
        self.assertIn("Runtime markdown views: not materialized (0)", create_result.stdout)
        self.assertNotIn("- agent-system/", create_result.stdout)
        self.assertIn("ASO project verify-clean: PASS", verify_result.stdout)
        self.assertIn("ASO state verify: FAILED", state_verify_result.stdout)
        self.assertIn("aso state init --root . --tz project-input/TZ_REAL.md --confirm-write", readme)
        self.assertIn("aso intake bootstrap --root . --tz project-input/TZ_REAL.md", readme)
        self.assertIn("aso plan-next --root . --strict", readme)
        self.assertIn("aso lint --root . --mode workspace --strict", readme)
        self.assertIn("aso doctor --root . --mode workspace --strict", readme)
        self.assertIn("aso lifecycle terminate-agent", readme)
        self.assertEqual(lock["aso_engine"]["version"], lockfile.PACKAGE_VERSION)
        self.assertEqual(lock["aso_engine"]["runtime_schema"], lockfile.RUNTIME_SCHEMA_VERSION)
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
        self.assertFalse(plan["planned_state_init"]["enabled_for_local_create"])
        self.assertTrue(plan["planned_state_init"]["dry_run"])
        self.assertFalse(plan["planned_state_init"]["writes_performed"])
        self.assertTrue(plan["planned_state_init"]["requires_explicit_tz"])
        self.assertEqual(plan["planned_state_init"]["planned_writes"], [])
        self.assertFalse(plan["planned_state_init"]["publication_boundary"]["tracked"])
        self.assertFalse(plan["planned_state_init"]["publication_boundary"]["pushed"])
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
        self.assertFalse(target.exists())

    def test_create_github_dry_run_fixture_and_argument_validation(self) -> None:
        fixture = json.loads((P1_FIXTURES / "github_dry_run_answers.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "github-demo"
            report_path = Path(tmp) / "plan.json"
            args = [
                "project",
                "create",
                "--github",
                "--dry-run",
                "--target",
                str(target),
                "--name",
                str(fixture["project_name"]),
                "--slug",
                str(fixture["project_slug"]),
                "--profile",
                str(fixture["profile"]),
                "--owner",
                str(fixture["github_owner"]),
                "--repo",
                str(fixture["github_repo"]),
                "--private",
                "--branch",
                str(fixture["branch"]),
                "--engine-mode",
                str(fixture["engine_mode"]),
                "--json-out",
                str(report_path),
            ]
            result = _run_cli(args, env_overrides={"PATH": str(Path(tmp) / "empty-bin")})
            unsafe_owner_args = list(args)
            unsafe_owner_args[unsafe_owner_args.index("--owner") + 1] = "../bad"
            unsafe_repo_args = list(args)
            unsafe_repo_args[unsafe_repo_args.index("--repo") + 1] = "bad.git"
            unsafe_owner = _run_cli(unsafe_owner_args)
            unsafe_repo = _run_cli(unsafe_repo_args)
            plan = json.loads(report_path.read_text(encoding="utf-8"))

            self.assertFalse(target.exists())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(plan["repo_owner"], "example")
        self.assertEqual(plan["repo_name"], "demo")
        self.assertEqual(plan["engine_mode"], "reference")
        self.assertIn("planned_state_init", plan)
        self.assertEqual(plan["planned_state_init"]["runtime_schema_version"], "3.1.1")
        self.assertEqual(unsafe_owner.returncode, 1)
        self.assertIn("repo owner contains unsafe characters", unsafe_owner.stderr)
        self.assertEqual(unsafe_repo.returncode, 1)
        self.assertIn("repo name contains unsafe characters", unsafe_repo.stderr)

    def test_create_github_real_publish_requires_confirm_publish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "github-demo"
            result = _run_cli(
                [
                    "project",
                    "create",
                    "--github",
                    "--target",
                    str(target),
                    "--name",
                    "Demo",
                    "--slug",
                    "demo",
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
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("--confirm-publish", result.stderr)
        self.assertFalse(target.exists())

    def test_create_github_real_publish_with_fake_tools_success_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target = tmp_root / "github-demo"
            receipt_path = tmp_root / "receipt.json"
            fake_bin = tmp_root / "bin"
            _write_fake_github_tools(fake_bin)

            result = _run_cli(
                [
                    "project",
                    "create",
                    "--github",
                    "--confirm-publish",
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
                    "--json-out",
                    str(receipt_path),
                ],
                env_overrides={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(receipt["repository"], "example/demo")
        self.assertEqual(receipt["commit"], "fakecommit123")
        self.assertEqual(receipt["tracked_paths"], [".gitignore", "README.md", "aso.lock"])
        self.assertFalse(receipt["runtime_state_initialized"])
        self.assertEqual(receipt["runtime_state_files"], 0)
        self.assertFalse((target / "agent-system").exists())

    def test_create_github_real_publish_with_fake_tools_failure_paths(self) -> None:
        cases = (
            ("FAKE_GH_AUTH_FAIL", "gh auth status returned non-zero exit status 43"),
            ("FAKE_GIT_COMMIT_FAIL", "git commit returned non-zero exit status 42"),
            ("FAKE_GH_CREATE_FAIL", "gh repo create returned non-zero exit status 44"),
            ("FAKE_GIT_FORBIDDEN_TRACKED", "tracked publication-boundary validation failed during pre-push"),
        )

        for env_name, message in cases:
            with self.subTest(env_name=env_name), tempfile.TemporaryDirectory() as tmp:
                tmp_root = Path(tmp)
                target = tmp_root / "github-demo"
                fake_bin = tmp_root / "bin"
                _write_fake_github_tools(fake_bin)

                result = _run_cli(
                    [
                        "project",
                        "create",
                        "--github",
                        "--confirm-publish",
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
                    ],
                    env_overrides={"PATH": f"{fake_bin}:{os.environ['PATH']}", env_name: "1"},
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)

    def test_create_github_real_publish_requires_explicit_branch_before_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "github-demo"
            result = _run_cli(
                [
                    "project",
                    "create",
                    "--github",
                    "--confirm-publish",
                    "--target",
                    str(target),
                    "--name",
                    "Demo",
                    "--slug",
                    "demo",
                    "--owner",
                    "example",
                    "--repo",
                    "demo",
                    "--private",
                    "--engine-mode",
                    "reference",
                ]
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("explicit --branch", result.stderr)
        self.assertFalse(target.exists())

    def test_create_github_real_publish_requires_explicit_visibility_before_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "github-demo"
            args = argparse.Namespace(
                github=True,
                dry_run=False,
                confirm_publish=True,
                target=str(target),
                name="Demo",
                slug="demo",
                profile="generic",
                owner="example",
                repo="demo",
                public=False,
                private=False,
                internal=False,
                branch="main",
                branch_explicit=True,
                engine_mode="reference",
                json_out=None,
            )

            with (
                mock.patch.object(project.shutil, "which", side_effect=AssertionError("tools must not be checked")),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                result = project.run_create(args)

        self.assertEqual(result, 1)
        self.assertFalse(target.exists())

    def test_create_github_real_publish_fails_when_git_or_gh_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "github-demo"
            args = argparse.Namespace(
                github=True,
                dry_run=False,
                confirm_publish=True,
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
                branch_explicit=True,
                engine_mode="reference",
                json_out=None,
            )

            stderr = io.StringIO()
            with (
                mock.patch.object(project.shutil, "which", return_value=None),
                contextlib.redirect_stderr(stderr),
            ):
                result = project.run_create(args)

        self.assertEqual(result, 1)
        self.assertIn("git executable is unavailable", stderr.getvalue())
        self.assertFalse(target.exists())

    def test_create_github_real_publish_rejects_unsafe_owner_before_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "github-demo"
            args = argparse.Namespace(
                github=True,
                dry_run=False,
                confirm_publish=True,
                target=str(target),
                name="Demo",
                slug="demo",
                profile="generic",
                owner="../example",
                repo="demo",
                public=False,
                private=True,
                internal=False,
                branch="main",
                branch_explicit=True,
                engine_mode="reference",
                json_out=None,
            )

            with (
                mock.patch.object(project.shutil, "which", side_effect=AssertionError("tools must not be checked")),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                result = project.run_create(args)

        self.assertEqual(result, 1)
        self.assertFalse(target.exists())

    def test_create_github_real_publish_rejects_engine_repo_target(self) -> None:
        with (
            mock.patch.object(project.shutil, "which", side_effect=lambda name: f"/fake/bin/{name}"),
            mock.patch.object(project, "_run_checked", return_value=subprocess.CompletedProcess([], 0, "", "")),
        ):
            with self.assertRaisesRegex(project.PublishError, "ASO engine repository"):
                project.publish_github_project(
                    target=REPO_ROOT,
                    project_name="Demo",
                    project_slug="demo",
                    profile="generic",
                    owner="example",
                    repo="demo",
                    visibility="private",
                    default_branch="main",
                    engine_mode="reference",
                )

    def test_create_github_real_publish_rejects_parent_git_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target = tmp_root / "nested" / "github-demo"

            def fake_git_toplevel(path: Path) -> Path | None:
                return tmp_root if path == tmp_root else None

            with (
                mock.patch.object(project.shutil, "which", side_effect=lambda name: f"/fake/bin/{name}"),
                mock.patch.object(project, "_run_checked", return_value=subprocess.CompletedProcess([], 0, "", "")),
                mock.patch.object(project, "_git_toplevel", side_effect=fake_git_toplevel),
            ):
                with self.assertRaisesRegex(project.PublishError, "parent Git worktree"):
                    project.publish_github_project(
                        target=target,
                        project_name="Demo",
                        project_slug="demo",
                        profile="generic",
                        owner="example",
                        repo="demo",
                        visibility="private",
                        default_branch="main",
                        engine_mode="reference",
                    )

            self.assertFalse(target.exists())

    def test_create_github_real_publish_uses_target_scoped_git_and_gh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "github-demo"
            receipt_path = Path(tmp) / "receipt.json"
            calls: list[list[str]] = []
            git_initialized = False

            def fake_which(name: str) -> str | None:
                if name in {"git", "gh"}:
                    return f"/fake/bin/{name}"
                return None

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                nonlocal git_initialized
                calls.append(command)
                if command[:3] == ["/fake/bin/gh", "auth", "status"]:
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[:4] == ["/fake/bin/git", "-C", str(target), "init"]:
                    git_initialized = True
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[:4] == ["/fake/bin/git", "-C", str(target), "add"]:
                    self.assertEqual(command[4:], [".gitignore", "README.md", "aso.lock"])
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[:4] == ["/fake/bin/git", "-C", str(target), "commit"]:
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[:5] == ["/fake/bin/git", "-C", str(target), "rev-parse", "HEAD"]:
                    return subprocess.CompletedProcess(command, 0, "abc123\n", "")
                if command[:4] == ["/fake/bin/gh", "repo", "create", "example/demo"]:
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[0] in {"git", "/fake/bin/git"} and command[3:] == ["rev-parse", "--show-toplevel"]:
                    if git_initialized and command[2] == str(target):
                        return subprocess.CompletedProcess(command, 0, f"{target}\n", "")
                    return subprocess.CompletedProcess(command, 1, "", "not a git repository")
                if command[0] in {"git", "/fake/bin/git"} and command[3:] == ["ls-files"]:
                    return subprocess.CompletedProcess(command, 0, ".gitignore\nREADME.md\naso.lock\n", "")
                if command[0] in {"git", "/fake/bin/git"} and command[3:] == ["branch", "--show-current"]:
                    return subprocess.CompletedProcess(command, 0, "main\n", "")
                if command[0] in {"git", "/fake/bin/git"} and command[3:] == ["remote", "get-url", "origin"]:
                    return subprocess.CompletedProcess(command, 1, "", "no remote")
                raise AssertionError(f"unexpected command: {command}")

            args = argparse.Namespace(
                github=True,
                dry_run=False,
                confirm_publish=True,
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
                branch_explicit=True,
                engine_mode="reference",
                json_out=str(receipt_path),
            )

            stdout = io.StringIO()
            with (
                mock.patch.object(project.shutil, "which", side_effect=fake_which),
                mock.patch.object(project.subprocess, "run", side_effect=fake_run),
                contextlib.redirect_stdout(stdout),
            ):
                result = project.run_create(args)

            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertIn("ASO project GitHub publish: PASS", stdout.getvalue())
        self.assertEqual(receipt["repository"], "example/demo")
        self.assertEqual(receipt["commit"], "abc123")
        self.assertEqual(receipt["tracked_paths"], [".gitignore", "README.md", "aso.lock"])
        self.assertEqual(receipt["pre_publish_verify_clean"], "pass")
        self.assertEqual(receipt["post_publish_verify_clean"], "pass")
        self.assertIn(
            ["/fake/bin/gh", "repo", "create", "example/demo", "--private", "--source", str(target), "--remote", "origin", "--push"],
            calls,
        )
        self.assertTrue(all(command[:3] != ["/fake/bin/git", "-C", str(REPO_ROOT)] for command in calls))
        self.assertFalse((target / "project-input" / "aso_upgrade_project_factory_p0").exists())

    def test_create_github_vendored_real_publish_checks_tracked_boundary_before_push(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "github-demo"
            calls: list[list[str]] = []
            git_initialized = False
            git_committed = False

            def fake_which(name: str) -> str | None:
                if name in {"git", "gh"}:
                    return f"/fake/bin/{name}"
                return None

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                nonlocal git_initialized, git_committed
                calls.append(command)
                if command[:3] == ["/fake/bin/gh", "auth", "status"]:
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[:4] == ["/fake/bin/git", "-C", str(target), "init"]:
                    git_initialized = True
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[:4] == ["/fake/bin/git", "-C", str(target), "add"]:
                    self.assertIn("agent-system", command[4:])
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[:4] == ["/fake/bin/git", "-C", str(target), "commit"]:
                    git_committed = True
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[:5] == ["/fake/bin/git", "-C", str(target), "rev-parse", "HEAD"]:
                    raise AssertionError("rev-parse HEAD must not run before boundary passes")
                if command[:4] == ["/fake/bin/gh", "repo", "create", "example/demo"]:
                    raise AssertionError("gh repo create must not run before boundary passes")
                if command[0] in {"git", "/fake/bin/git"} and command[3:] == ["rev-parse", "--show-toplevel"]:
                    if git_initialized and command[2] == str(target):
                        return subprocess.CompletedProcess(command, 0, f"{target}\n", "")
                    return subprocess.CompletedProcess(command, 1, "", "not a git repository")
                if command[0] in {"git", "/fake/bin/git"} and command[3:] == ["ls-files"]:
                    if git_committed and command[2] == str(target):
                        return subprocess.CompletedProcess(
                            command,
                            0,
                            ".gitignore\nREADME.md\naso.lock\nagent-system/project-runtime/state.json\n",
                            "",
                        )
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[0] in {"git", "/fake/bin/git"} and command[3:] == ["branch", "--show-current"]:
                    return subprocess.CompletedProcess(command, 0, "main\n", "")
                if command[0] in {"git", "/fake/bin/git"} and command[3:] == ["remote", "get-url", "origin"]:
                    return subprocess.CompletedProcess(command, 1, "", "no remote")
                raise AssertionError(f"unexpected command: {command}")

            args = argparse.Namespace(
                github=True,
                dry_run=False,
                confirm_publish=True,
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
                branch_explicit=True,
                engine_mode="vendored",
                json_out=None,
            )

            stderr = io.StringIO()
            with (
                mock.patch.object(project.shutil, "which", side_effect=fake_which),
                mock.patch.object(project.subprocess, "run", side_effect=fake_run),
                contextlib.redirect_stderr(stderr),
            ):
                result = project.run_create(args)

        self.assertEqual(result, 1)
        self.assertIn("tracked publication-boundary validation failed during pre-push", stderr.getvalue())
        self.assertIn("agent-system/project-runtime/state.json", stderr.getvalue())
        self.assertTrue(any(command[:4] == ["/fake/bin/git", "-C", str(target), "commit"] for command in calls))
        self.assertFalse(any(command[:4] == ["/fake/bin/gh", "repo", "create", "example/demo"] for command in calls))

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
        self.assertIn(f"Package drift: 3.2.0 is compatible with current package {lockfile.PACKAGE_VERSION}", result.stdout)

    def test_verify_clean_accepts_p1_reference_and_p0_lock_compatibility_fixtures(self) -> None:
        cases = (
            (
                "reference_valid",
                "Engine mode: reference",
                f"Package drift: 3.3.0 is compatible with current package {lockfile.PACKAGE_VERSION}",
            ),
            (
                "p0_lock_compatible",
                "Engine mode: vendored",
                f"Package drift: 3.2.0 is compatible with current package {lockfile.PACKAGE_VERSION}",
            ),
        )

        for fixture_name, engine_text, package_text in cases:
            with self.subTest(fixture_name=fixture_name):
                result = _run_cli(["project", "verify-clean", "--root", str(P1_FIXTURES / fixture_name), "--strict"])

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("ASO project verify-clean: PASS", result.stdout)
                self.assertIn(engine_text, result.stdout)
                self.assertIn(package_text, result.stdout)

    def test_publication_boundary_negative_fixture_fails_when_forbidden_path_is_tracked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "boundary-negative"
            shutil.copytree(P1_FIXTURES / "publication_boundary_negative" / "tracked_project_input", root)
            forbidden_path = root / "project-input" / "aso_upgrade_project_factory_p1_github_wizard" / "TASK.md"
            _write(forbidden_path, "# Should Not Be Published\n")
            _init_git(root)
            subprocess.run(
                ["git", "-C", str(root), "add", ".gitignore", "README.md", "aso.lock"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "add",
                    "-f",
                    "project-input/aso_upgrade_project_factory_p1_github_wizard/TASK.md",
                ],
                check=True,
                capture_output=True,
            )

            result = _run_cli(["project", "verify-clean", "--root", str(root), "--strict"])

        self.assertEqual(result.returncode, 1)
        self.assertIn("PROJECT_VERIFY_CLEAN_007", result.stdout)
        self.assertIn("project-input/aso_upgrade_project_factory_p1_github_wizard/TASK.md", result.stdout)

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
            _write(source / "00_start" / "ORCHESTRATOR_START.md", "# Start\n")
            _write(source / "02_runtime" / "ORCHESTRATOR_RUNTIME_CONTRACT.json", "{}\n")
            _write(source / "09_validators" / "VALIDATOR_SPEC.md", "# Validators\n")
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
            self.assertEqual(summary.copied_files, 6)
            self.assertFalse(summary.runtime_state_initialized)
            self.assertEqual(summary.runtime_state_files, 0)
            self.assertTrue((generated_agent_system / "README.md").is_file())
            self.assertTrue((generated_agent_system / "00_start" / "ORCHESTRATOR_START.md").is_file())
            self.assertTrue((generated_agent_system / "ORCHESTRATOR_RUNTIME_CONTRACT.json").is_file())
            self.assertTrue((generated_agent_system / "02_runtime" / "ORCHESTRATOR_RUNTIME_CONTRACT.json").is_file())
            self.assertTrue((generated_agent_system / "09_validators").is_dir())
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

    def test_vendored_create_refuses_incomplete_agent_system_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            source = tmp_root / "source-agent-system"
            target = tmp_root / "generated"
            _write(source / "README.md", "# Fixture\n")
            _write(source / "tools" / "aso" / "aso.py", "print('ok')\n")

            with self.assertRaisesRegex(ValueError, "agent-system source is incomplete"):
                project.create_project(
                    target=target,
                    project_name="Demo Project",
                    project_slug="demo-project",
                    repo_url=None,
                    source_agent_system=source,
                )

    def test_vendored_copy_excludes_nested_packaged_resource_tree_and_library_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            source = tmp_root / "source-agent-system"
            target = tmp_root / "generated"
            _write(source / "00_start" / "ORCHESTRATOR_START.md", "# Start\n")
            _write(source / "02_runtime" / "ORCHESTRATOR_RUNTIME_CONTRACT.json", "{}\n")
            _write(source / "09_validators" / "VALIDATOR_SPEC.md", "# Validators\n")
            _write(source / "tools" / "aso" / "aso.py", "print('ok')\n")
            _write(source / "tools" / "aso" / "agent_system_orchestrator_aso" / "resources" / "agent-system" / "README.md")
            _write(source / "tools" / "aso" / ".tox" / "py" / "lib" / "python3.12" / "site-packages" / "bad.py")
            _write(source / "tools" / "aso" / "dist" / "package.whl")

            project.create_project(
                target=target,
                project_name="Demo Project",
                project_slug="demo-project",
                repo_url=None,
                source_agent_system=source,
            )

            generated_agent_system = target / "agent-system"
            self.assertFalse(
                (
                    generated_agent_system
                    / "tools"
                    / "aso"
                    / "agent_system_orchestrator_aso"
                    / "resources"
                    / "agent-system"
                ).exists()
            )
            self.assertFalse((generated_agent_system / "tools" / "aso" / ".tox").exists())
            self.assertFalse((generated_agent_system / "tools" / "aso" / "dist").exists())


if __name__ == "__main__":
    unittest.main()
