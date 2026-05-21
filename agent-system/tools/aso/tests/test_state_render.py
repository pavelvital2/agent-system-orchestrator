from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


class StateRenderCommandTests(unittest.TestCase):
    def test_help_declares_state_render(self) -> None:
        result = run_aso("state", "render", "--help")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("--format", result.stdout)
        self.assertIn("--out", result.stdout)

    def test_initialized_workspace_renders_deterministic_markdown_to_tmp(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Render Test",
                "--project-slug",
                "render-test",
                "--confirm-write",
            )
            out = Path(tmp) / "state-report.md"

            first = run_aso("state", "render", "--root", str(root), "--format", "markdown", "--out", str(out))
            first_text = out.read_text(encoding="utf-8")
            second = run_aso("state", "render", "--root", str(root), "--format", "markdown", "--out", str(out))
            second_text = out.read_text(encoding="utf-8")

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(first_text, second_text)
        self.assertTrue(first_text.startswith("# ASO Runtime State Report\n"))
        self.assertIn("Runtime schema: 3.1.0", first_text)

    def test_json_render_reports_schema_health(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            init = run_aso("state", "init", "--root", str(root), "--project-slug", "json-render", "--confirm-write")
            out = root / "project-runtime" / "rendered" / "state-report.json"

            result = run_aso("state", "render", "--root", str(root), "--format", "json", "--out", str(out))
            report = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["command"], "state render")
        self.assertTrue(report["read_only"])
        self.assertEqual(report["runtime_schema"]["active_version"], "3.1.0")
        self.assertEqual(report["runtime_schema"]["required_sidecars_missing"], [])
        self.assertIn("SCHEMA_MANIFEST", report["sidecars"])

    def test_forbidden_output_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            init = run_aso("state", "init", "--root", str(root), "--project-slug", "bad-out", "--confirm-write")
            out = root / "project-runtime" / "state-report.md"

            result = run_aso("state", "render", "--root", str(root), "--out", str(out))

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("ASO_OUTPUT_PATH_FORBIDDEN", result.stderr)


if __name__ == "__main__":
    unittest.main()
