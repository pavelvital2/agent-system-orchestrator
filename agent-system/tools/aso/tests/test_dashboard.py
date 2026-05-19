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

    def test_forbidden_output_path_is_rejected(self) -> None:
        forbidden = REPO_ROOT / "agent-system" / "dashboard.html"

        result = run_dashboard(VALID_WORKSPACE, "--out", str(forbidden))

        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("forbidden", result.stderr)
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


if __name__ == "__main__":
    unittest.main()
