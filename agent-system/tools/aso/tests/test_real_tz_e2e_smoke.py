from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
INSTALL_SCRIPT = REPO_ROOT / "agent-system" / "scripts" / "install_aso_clean.sh"
REAL_TZ_FIXTURE = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "real_tz_e2e" / "TZ_REAL_E2E_TELEGRAM_BOT.md"
MISSING_TZ_FIXTURE = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "real_tz_e2e" / "MISSING_TZ_PATH.txt"


def run_cmd(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(args, cwd=cwd or REPO_ROOT, env=env, text=True, capture_output=True, check=False)


def require_success(result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode != 0:
        raise AssertionError(
            "command failed with exit code "
            f"{result.returncode}: {' '.join(result.args)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def file_fingerprints(root: Path) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relpath = path.relative_to(root).as_posix()
        fingerprints[relpath] = hashlib.sha256(path.read_bytes()).hexdigest()
    return fingerprints


class RealTzE2ESmokeTests(unittest.TestCase):
    def test_installed_cli_real_tz_bootstrap_planning_smoke(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aso-real-tz-e2e-") as tmp_text:
            tmp = Path(tmp_text)
            venv = tmp / "venv"
            source_copy = tmp / "source-copy"
            workspace = tmp / "workspace"
            workspace_input = workspace / "project-input"
            workspace_input.mkdir(parents=True)
            shutil.copyfile(REAL_TZ_FIXTURE, workspace_input / "TZ_REAL_E2E_TELEGRAM_BOT.md")

            source_status_before = run_cmd(["git", "status", "--short", "--branch"]).stdout
            install = run_cmd(
                [
                    "bash",
                    str(INSTALL_SCRIPT),
                    "--source",
                    str(REPO_ROOT),
                    "--venv",
                    str(venv),
                    "--source-copy",
                    str(source_copy),
                    "--with-test",
                ]
            )
            require_success(install)
            source_status_after_install = run_cmd(["git", "status", "--short", "--branch"]).stdout
            self.assertEqual(source_status_before, source_status_after_install)

            aso = venv / "bin" / "aso"
            python = venv / "bin" / "python"
            self.assertTrue(aso.is_file())
            require_success(
                run_cmd(
                    [
                        str(python),
                        "-c",
                        (
                            "import importlib.metadata as md, jsonschema, pathlib, "
                            "agent_system_orchestrator_aso; "
                            "dist = md.distribution('agent-system-orchestrator'); "
                            "source = pathlib.Path(agent_system_orchestrator_aso.__file__).resolve(); "
                            "assert source.is_relative_to(pathlib.Path(r'"
                            + str(venv)
                            + "').resolve()), source; "
                            "assert md.version('jsonschema'); "
                            "print(jsonschema.__version__)"
                        ),
                    ]
                )
            )

            init_json = tmp / "state-init.json"
            intake_json = tmp / "intake.json"
            plan_json = tmp / "plan-next.json"
            require_success(
                run_cmd(
                    [
                        str(aso),
                        "state",
                        "init",
                        "--root",
                        str(workspace),
                        "--tz",
                        "project-input/TZ_REAL_E2E_TELEGRAM_BOT.md",
                        "--confirm-write",
                        "--json-out",
                        str(init_json),
                    ]
                )
            )
            require_success(run_cmd([str(aso), "state", "verify", "--root", str(workspace), "--strict"]))
            require_success(
                run_cmd(
                    [
                        str(aso),
                        "intake",
                        "bootstrap",
                        "--root",
                        str(workspace),
                        "--tz",
                        "project-input/TZ_REAL_E2E_TELEGRAM_BOT.md",
                        "--target-role",
                        "requirements_analyst",
                        "--confirm-write",
                        "--json-out",
                        str(intake_json),
                    ]
                )
            )
            before_plan = file_fingerprints(workspace)
            require_success(run_cmd([str(aso), "plan-next", "--root", str(workspace), "--strict", "--json-out", str(plan_json)]))
            after_plan = file_fingerprints(workspace)
            source_status_after_plan = run_cmd(["git", "status", "--short", "--branch"]).stdout

            self.assertEqual(before_plan, after_plan)
            self.assertEqual(source_status_before, source_status_after_plan)

            init_report = json.loads(init_json.read_text(encoding="utf-8"))
            intake_report = json.loads(intake_json.read_text(encoding="utf-8"))
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            project_state = json.loads((workspace / "project-runtime/state/PROJECT_STATE.json").read_text(encoding="utf-8"))
            workspace_identity = json.loads(
                (workspace / "project-runtime/state/WORKSPACE_IDENTITY.json").read_text(encoding="utf-8")
            )
            registry = json.loads((workspace / "project-runtime/state/TASK_REGISTRY.json").read_text(encoding="utf-8"))
            current_gate = json.loads((workspace / "project-runtime/state/CURRENT_GATE.json").read_text(encoding="utf-8"))
            task = registry["content"]["tasks"][0]

            self.assertIn("jsonschema", run_cmd([str(python), "-m", "pip", "show", "jsonschema"]).stdout)
            self.assertEqual(init_report["status"], "written")
            self.assertEqual(intake_report["status"], "created")
            self.assertEqual(intake_report["target_role"], "requirements_analyst")
            self.assertEqual(plan_report["recommended_next_action"], "CREATE_AGENT")
            self.assertTrue(plan_report["dispatchable"])
            self.assertFalse(plan_report["mutations_performed"])
            self.assertEqual(plan_report["target_role"], "requirements_analyst")
            self.assertEqual(project_state["content"]["identity_validation_status"], "not_checked")
            self.assertEqual(project_state["content"]["repository_lock_status"], "draft")
            self.assertEqual(workspace_identity["content"]["identity_validation_status"], "not_required")
            self.assertEqual(workspace_identity["content"]["repository_lock_status"], "pending")
            self.assertNotIn(plan_report["task_id"], ("", "NONE"))
            self.assertNotIn(plan_report["task_packet"], ("", "NONE"))
            self.assertEqual(task["task_id"], plan_report["task_id"])
            self.assertEqual(task["task_packet"], plan_report["task_packet"])
            self.assertEqual(task["owner_role"], "requirements_analyst")
            self.assertEqual(current_gate["content"]["task_id"], plan_report["task_id"])
            self.assertEqual(current_gate["content"]["task_packet"], plan_report["task_packet"])
            self.assertTrue((workspace / plan_report["task_packet"]).is_file())
            self.assertEqual(sorted(path.name for path in workspace.iterdir()), ["project-input", "project-runtime"])
            self.assertFalse((workspace / "Dockerfile").exists())
            self.assertFalse((workspace / ".env.example").exists())

    def test_installed_cli_missing_tz_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aso-real-tz-negative-") as tmp_text:
            tmp = Path(tmp_text)
            venv = tmp / "venv"
            source_copy = tmp / "source-copy"
            workspace = tmp / "workspace"
            workspace.mkdir()
            missing_tz = MISSING_TZ_FIXTURE.read_text(encoding="utf-8").strip()

            install = run_cmd(
                [
                    "bash",
                    str(INSTALL_SCRIPT),
                    "--source",
                    str(REPO_ROOT),
                    "--venv",
                    str(venv),
                    "--source-copy",
                    str(source_copy),
                    "--with-test",
                ]
            )
            require_success(install)

            result = run_cmd(
                [
                    str(venv / "bin" / "aso"),
                    "state",
                    "init",
                    "--root",
                    str(workspace),
                    "--tz",
                    missing_tz,
                    "--confirm-write",
                ]
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("--tz file is missing or unreadable", result.stderr)
            self.assertFalse((workspace / "project-runtime").exists())
            self.assertFalse((workspace / "project-input" / "TZ.md").exists())


if __name__ == "__main__":
    unittest.main()
