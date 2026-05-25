from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[4]
ASO_TOOL_ROOT = REPO_ROOT / "agent-system" / "tools" / "aso"
CLI = ASO_TOOL_ROOT / "aso.py"
P1_FIXTURES = ASO_TOOL_ROOT / "tests" / "fixtures" / "project_factory_p1"

sys.path.insert(0, str(ASO_TOOL_ROOT))

from agent_system_orchestrator_aso.aso_tool.commands import project, wizard  # noqa: E402


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


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


class WizardCommandTests(unittest.TestCase):
    def test_wizard_help_is_available(self) -> None:
        result = _run_cli(["wizard", "--help"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
        self.assertIn("--answers", result.stdout)

    def test_github_answers_dry_run_writes_deterministic_plan_without_target_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target = tmp_root / "demo-project"
            answers_path = tmp_root / "answers.json"
            plan_path = tmp_root / "wizard-plan.json"
            second_plan_path = tmp_root / "wizard-plan-2.json"
            answers = {
                "project_name": "Demo Project",
                "project_slug": "demo-project",
                "profile": "generic",
                "target": str(target),
                "engine_mode": "reference",
                "publish_mode": "github",
                "github_owner": "example",
                "github_repo": "demo-project",
                "visibility": "private",
                "branch": "main",
                "confirm_publish": False,
            }
            _write_json(answers_path, answers)

            args = ["wizard", "--answers", str(answers_path), "--dry-run"]
            result = _run_cli(
                [*args, "--json-out", str(plan_path)],
                env_overrides={"PATH": str(tmp_root / "empty-bin")},
            )
            second_result = _run_cli([*args, "--json-out", str(second_plan_path)])
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            second_plan = json.loads(second_plan_path.read_text(encoding="utf-8"))

            self.assertFalse(target.exists())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(second_result.returncode, 0, second_result.stderr)
        self.assertEqual(plan, second_plan)
        self.assertEqual(plan["target"], str(target))
        self.assertEqual(plan["repo_owner"], "example")
        self.assertEqual(plan["repo_name"], "demo-project")
        self.assertEqual(
            plan["planned_gh_command"],
            f"gh repo create example/demo-project --private --source {target} --remote origin --push",
        )
        self.assertTrue(plan["confirmation_required_for_real_publish"])

    def test_reference_github_answers_fixture_parses_and_builds_dry_run_plan(self) -> None:
        answers_path = P1_FIXTURES / "wizard_answers_reference_github.json"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            plan_path = tmp_root / "wizard-plan.json"
            result = _run_cli(
                ["wizard", "--answers", str(answers_path), "--dry-run", "--json-out", str(plan_path)],
                env_overrides={"PATH": str(tmp_root / "empty-bin")},
            )
            answers = wizard._load_answers(str(answers_path))
            plan = json.loads(plan_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(answers["publish_mode"], "github")
        self.assertEqual(answers["engine_mode"], "reference")
        self.assertFalse(answers["confirm_publish"])
        self.assertEqual(plan["target"], "/tmp/aso-pf1-demo")
        self.assertEqual(plan["repo_owner"], "example")
        self.assertEqual(plan["repo_name"], "demo")
        self.assertEqual(plan["engine_mode"], "reference")
        self.assertEqual(
            plan["planned_gh_command"],
            "gh repo create example/demo --private --source /tmp/aso-pf1-demo --remote origin --push",
        )

    def test_local_answers_dry_run_writes_plan_without_creating_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target = tmp_root / "local-demo"
            answers_path = tmp_root / "answers.json"
            plan_path = tmp_root / "wizard-local-plan.json"
            _write_json(
                answers_path,
                {
                    "project_name": "Local Demo",
                    "project_slug": "local-demo",
                    "profile": "generic",
                    "target": str(target),
                    "engine_mode": "vendored",
                    "publish_mode": "local",
                    "branch": "main",
                    "confirm_publish": False,
                },
            )

            result = _run_cli(["wizard", "--answers", str(answers_path), "--dry-run", "--json-out", str(plan_path)])
            plan = json.loads(plan_path.read_text(encoding="utf-8"))

            self.assertFalse(target.exists())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(plan["publish_mode"], "local")
        self.assertEqual(plan["planned_operations"], ["create local Project Factory workspace"])
        self.assertIn("agent-system/", plan["planned_local_files"])
        self.assertTrue(plan["confirmation_required_for_real_create"])

    def test_local_create_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target = tmp_root / "local-demo"
            answers_path = tmp_root / "answers.json"
            _write_json(
                answers_path,
                {
                    "project_name": "Local Demo",
                    "project_slug": "local-demo",
                    "profile": "generic",
                    "target": str(target),
                    "engine_mode": "reference",
                    "publish_mode": "local",
                    "branch": "main",
                    "confirm_publish": False,
                },
            )

            result = _run_cli(["wizard", "--answers", str(answers_path)])

            self.assertFalse(target.exists())

        self.assertEqual(result.returncode, 1)
        self.assertIn("explicit confirmation", result.stderr)

    def test_local_create_runs_project_factory_after_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target = tmp_root / "local-demo"
            answers_path = tmp_root / "answers.json"
            _write_json(
                answers_path,
                {
                    "project_name": "Local Demo",
                    "project_slug": "local-demo",
                    "profile": "generic",
                    "target": str(target),
                    "engine_mode": "reference",
                    "publish_mode": "local",
                    "branch": "main",
                    "confirm_publish": True,
                },
            )

            result = _run_cli(["wizard", "--answers", str(answers_path)])

            self.assertTrue((target / ".gitignore").is_file())
            self.assertTrue((target / "README.md").is_file())
            self.assertTrue((target / "aso.lock").is_file())
            self.assertFalse((target / "agent-system").exists())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ASO project create", result.stdout)

    def test_github_publish_requires_confirmation_before_project_delegation(self) -> None:
        args = argparse.Namespace(answers=None, dry_run=False, json_out=None)
        answers = {
            "project_name": "Demo",
            "project_slug": "demo",
            "profile": "generic",
            "target": "/tmp/demo",
            "engine_mode": "reference",
            "publish_mode": "github",
            "github_owner": "example",
            "github_repo": "demo",
            "visibility": "private",
            "branch": "main",
            "confirm_publish": False,
        }

        stderr = io.StringIO()
        with (
            mock.patch.object(wizard, "_load_answers", return_value=answers),
            mock.patch.object(project, "run_create", side_effect=AssertionError("must not publish")),
            contextlib.redirect_stderr(stderr),
        ):
            result = wizard.run(args)

        self.assertEqual(result, 1)
        self.assertIn("explicit confirmation", stderr.getvalue())

    def test_interactive_collection_prompts_plain_fields_and_confirmation(self) -> None:
        prompts: list[str] = []
        responses = iter(
            [
                "Demo Project",
                "demo-project",
                "generic",
                "/tmp/demo-project",
                "reference",
                "github",
                "main",
                "example",
                "demo-project",
                "private",
                "no",
            ]
        )

        def fake_input(prompt: str) -> str:
            prompts.append(prompt)
            return next(responses)

        with mock.patch("builtins.input", side_effect=fake_input):
            answers = wizard._collect_answers({}, interactive=True)

        self.assertEqual(answers["project_name"], "Demo Project")
        self.assertEqual(answers["publish_mode"], "github")
        self.assertEqual(answers["github_owner"], "example")
        self.assertFalse(answers["confirm_publish"])
        self.assertTrue(
            all("token" not in prompt.lower() and "password" not in prompt.lower() for prompt in prompts)
        )
