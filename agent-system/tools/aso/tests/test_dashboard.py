from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "state"
VALID_WORKSPACE = FIXTURE_ROOT / "valid_workspace"
P2_VALID_WORKSPACE = FIXTURE_ROOT / "p2_valid_workspace"
DAG_AUDIT_ONLY_DEP = FIXTURE_ROOT / "dag_invalid_audit_passed_dependency_ready"


def run_dashboard(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "dashboard", "--root", str(root), *extra],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def copy_valid_workspace(tmp: str) -> Path:
    root = Path(tmp) / "workspace"
    shutil.copytree(VALID_WORKSPACE, root)
    return root


def unused_home_output_path() -> Path:
    for suffix in range(1000):
        candidate = Path.home() / f"aso-audit-outside-dashboard-test-{suffix}.txt"
        if not candidate.exists():
            return candidate
    raise AssertionError("could not find an unused outside-root output path")


def load_sidecar(root: Path, name: str) -> dict[str, object]:
    return json.loads((root / "project-runtime" / "state" / name).read_text(encoding="utf-8"))


def write_sidecar(root: Path, name: str, payload: dict[str, object]) -> None:
    (root / "project-runtime" / "state" / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class DashboardCommandTests(unittest.TestCase):
    def test_stdout_mode_prints_html_without_writing_state(self) -> None:
        tracked = [path for path in VALID_WORKSPACE.rglob("*") if path.is_file()]
        mtimes_before = {path: path.stat().st_mtime_ns for path in tracked}

        result = run_dashboard(VALID_WORKSPACE)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("<!doctype html>"))
        self.assertIn("ASO Static Dashboard", result.stdout)
        self.assertIn("Current Gate", result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertEqual(mtimes_before, {path: path.stat().st_mtime_ns for path in tracked})

    def test_tmp_output_writes_static_html(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            out = Path(tmp) / "dashboard.html"

            result = run_dashboard(VALID_WORKSPACE, "--out", str(out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(out.is_file())
            html = out.read_text(encoding="utf-8")
            self.assertTrue(html.startswith("<!doctype html>"))
            self.assertIn("Task packet", html)
            self.assertIn("ASO dashboard written:", result.stdout)

    def test_workspace_dashboard_output_writes_static_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            out = root / "project-runtime" / "dashboard" / "dashboard.html"

            result = run_dashboard(root, "--out", str(out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(out.is_file())
            self.assertTrue(out.read_text(encoding="utf-8").startswith("<!doctype html>"))

    def test_forbidden_output_path_is_rejected(self) -> None:
        forbidden = REPO_ROOT / "agent-system" / "dashboard.html"

        result = run_dashboard(VALID_WORKSPACE, "--out", str(forbidden))

        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("forbidden", result.stderr)
        self.assertFalse(forbidden.exists())

    def test_outside_root_absolute_output_path_is_rejected(self) -> None:
        forbidden = unused_home_output_path()

        result = run_dashboard(VALID_WORKSPACE, "--out", str(forbidden))

        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("ASO_OUTPUT_PATH_FORBIDDEN", result.stderr)
        self.assertFalse(forbidden.exists())

    def test_untrusted_state_text_is_html_escaped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            project_state = load_sidecar(root, "PROJECT_STATE.json")
            project_content = project_state["content"]
            self.assertIsInstance(project_content, dict)
            project_content["project_slug"] = "<script>alert(1)</script>"
            write_sidecar(root, "PROJECT_STATE.json", project_state)

            next_action = load_sidecar(root, "NEXT_ACTION.json")
            next_content = next_action["content"]
            self.assertIsInstance(next_content, dict)
            next_content["summary"] = "A & B < C"
            write_sidecar(root, "NEXT_ACTION.json", next_action)

            result = run_dashboard(root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", result.stdout)
            self.assertIn("A &amp; B &lt; C", result.stdout)
            self.assertNotIn("<script>alert(1)</script>", result.stdout)

    def test_stage_3_observability_sections_render_missing_optional_as_not_available(self) -> None:
        result = run_dashboard(VALID_WORKSPACE)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Package Sync Status", result.stdout)
        self.assertIn("DAG Summary", result.stdout)
        self.assertIn("Runtime Schema Health", result.stdout)
        self.assertIn("Result Routing Summary", result.stdout)
        self.assertIn("Incident Health", result.stdout)
        self.assertIn("Checkpoint-Preflight Readiness", result.stdout)
        self.assertIn("<span>Package Sync</span><strong>not_available</strong>", result.stdout)
        self.assertIn("<th scope=\"row\">Status</th><td>not_available</td>", result.stdout)
        self.assertNotIn("<span>Package Sync</span><strong>passed</strong>", result.stdout)

    def test_dashboard_reports_runtime_schema_health_for_current_state(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            (root / "project-input").mkdir()
            (root / "project-input" / "TZ.md").write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
            init = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "state",
                    "init",
                    "--root",
                    str(root),
                    "--project-slug",
                    "dashboard-schema",
                    "--confirm-write",
                ],
                check=False,
                text=True,
                capture_output=True,
                cwd=REPO_ROOT,
            )

            result = run_dashboard(root)

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("<span>Runtime Schema</span><strong>3.1.1</strong>", result.stdout)
        self.assertIn("<th scope=\"row\">Current P2 state</th><td>true</td>", result.stdout)
        self.assertIn("<th scope=\"row\">Verify status</th><td>passed</td>", result.stdout)

    def test_dashboard_reports_packaged_p2_fixture_as_current_state(self) -> None:
        result = run_dashboard(P2_VALID_WORKSPACE)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("<span>Runtime Schema</span><strong>3.1.1</strong>", result.stdout)
        self.assertIn("<th scope=\"row\">Current P2 state</th><td>true</td>", result.stdout)
        self.assertIn("<th scope=\"row\">Verify status</th><td>passed</td>", result.stdout)
        self.assertIn("<th scope=\"row\">Migration available</th><td>0</td>", result.stdout)

    def test_uncheckpointed_audit_dependency_blocks_dashboard_readiness(self) -> None:
        result = run_dashboard(DAG_AUDIT_ONLY_DEP)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("<span>Dashboard Status</span><strong>blocked</strong>", result.stdout)
        self.assertIn("<th scope=\"row\">Audit passed not checkpointed</th><td>1</td>", result.stdout)
        self.assertIn("<th scope=\"row\">Checkpoint done</th><td>0</td>", result.stdout)
        self.assertIn("<th scope=\"row\">Ready blocked by uncheckpointed dependency</th><td>1</td>", result.stdout)
        self.assertIn("<th scope=\"row\">Uncheckpointed dependency findings</th><td>1</td>", result.stdout)
        self.assertIn("dag.verify.DAG_DEPENDENCY_AUDIT_PASSED_WITHOUT_CHECKPOINT", result.stdout)

    def test_stage_3_dynamic_diagnostic_labels_are_html_escaped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            task_registry = load_sidecar(root, "TASK_REGISTRY.json")
            registry_content = task_registry["content"]
            self.assertIsInstance(registry_content, dict)
            tasks = registry_content["tasks"]
            self.assertIsInstance(tasks, list)
            self.assertIsInstance(tasks[0], dict)
            tasks[0]["task_id"] = "<img src=x onerror=alert(1)>"
            tasks[0]["return_to_requester_after_audit_pass"] = True
            tasks[0]["return_to_role_after_audit_pass"] = "developer & <lead>"
            tasks[0]["return_task_after_audit_pass"] = "TASK_REQUESTER_<1>"
            write_sidecar(root, "TASK_REGISTRY.json", task_registry)

            project_state = load_sidecar(root, "PROJECT_STATE.json")
            project_content = project_state["content"]
            self.assertIsInstance(project_content, dict)
            project_content["active_blockers"] = ["incident <script>alert(2)</script>"]
            write_sidecar(root, "PROJECT_STATE.json", project_state)

            result = run_dashboard(root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("&lt;img src=x onerror=alert(1)&gt;", result.stdout)
            self.assertIn("developer &amp; &lt;lead&gt;", result.stdout)
            self.assertIn("incident &lt;script&gt;alert(2)&lt;/script&gt;", result.stdout)
            self.assertNotIn("<img src=x onerror=alert(1)>", result.stdout)
            self.assertNotIn("<script>alert(2)</script>", result.stdout)

    def test_dashboard_remains_static_without_interactive_write_controls(self) -> None:
        result = run_dashboard(VALID_WORKSPACE)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lowered = result.stdout.lower()
        self.assertNotIn("<form", lowered)
        self.assertNotIn("<button", lowered)
        self.assertNotIn("type=\"submit\"", lowered)


if __name__ == "__main__":
    unittest.main()
