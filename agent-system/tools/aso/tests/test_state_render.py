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
P2_VALID_WORKSPACE = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "state" / "p2_valid_workspace"


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
        self.assertIn("--confirm-write", result.stdout)

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
            (root / "project-input").mkdir(exist_ok=True)
            (root / "project-input" / "TZ.md").write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
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
        self.assertIn("Runtime schema: 3.1.1", first_text)

    def test_json_render_reports_schema_health(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            init = run_aso("state", "init", "--root", str(root), "--project-slug", "json-render", "--confirm-write")
            (root / "project-input").mkdir(exist_ok=True)
            (root / "project-input" / "TZ.md").write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
            out = root / "project-runtime" / "rendered" / "state-report.json"

            result = run_aso("state", "render", "--root", str(root), "--format", "json", "--out", str(out))
            report = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["command"], "state render")
        self.assertTrue(report["read_only"])
        self.assertEqual(report["runtime_schema"]["active_version"], "3.1.1")
        self.assertEqual(report["runtime_schema"]["required_sidecars_missing"], [])
        self.assertIn("SCHEMA_MANIFEST", report["sidecars"])

    def test_p2_fixture_render_reports_current_schema_without_mutating_state(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "p2-workspace"
            shutil.copytree(P2_VALID_WORKSPACE, root)
            for sidecar in (root / "project-runtime" / "state").glob("*.json"):
                sidecar_payload = json.loads(sidecar.read_text(encoding="utf-8"))
                sidecar_payload["schema_version"] = "3.1.1"
                sidecar_payload["runtime_schema_version"] = "3.1.1"
                content = sidecar_payload.get("content")
                if isinstance(content, dict) and "runtime_schema_version" in content:
                    content["runtime_schema_version"] = "3.1.1"
                sidecar.write_text(json.dumps(sidecar_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            (root / "project-input").mkdir(exist_ok=True)
            (root / "project-input" / "TZ.md").write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
            project_state = root / "project-runtime" / "state" / "PROJECT_STATE.json"
            payload = json.loads(project_state.read_text(encoding="utf-8"))
            content = payload["content"]
            self.assertIsInstance(content, dict)
            content["tz_path"] = "project-input/TZ.md"
            project_state.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            next_action = root / "project-runtime" / "state" / "NEXT_ACTION.json"
            next_payload = json.loads(next_action.read_text(encoding="utf-8"))
            next_content = next_payload["content"]
            self.assertIsInstance(next_content, dict)
            next_content["action_type"] = "correction"
            next_content["action_semantic"] = "normal"
            next_content["dependency_status"] = "ready"
            next_action.write_text(json.dumps(next_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            tracked = [path for path in root.rglob("*") if path.is_file()]
            mtimes_before = {path: path.stat().st_mtime_ns for path in tracked}
            out = Path(tmp) / "p2-state-report.json"

            result = run_aso(
                "state",
                "render",
                "--root",
                str(root),
                "--format",
                "json",
                "--out",
                str(out),
            )
            report = json.loads(out.read_text(encoding="utf-8"))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(report["runtime_schema"]["current_p2_state"])
            self.assertEqual(report["runtime_schema"]["migration_available_sidecars"], [])
            self.assertEqual(report["runtime_schema"]["unsupported_sidecars"], [])
            self.assertEqual(mtimes_before, {path: path.stat().st_mtime_ns for path in tracked})

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

    def test_confirm_write_materializes_markdown_views_from_json_sidecars(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Materialize Test",
                "--project-slug",
                "materialize-test",
                "--confirm-write",
            )
            (root / "project-input").mkdir(exist_ok=True)
            (root / "project-input" / "TZ.md").write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
            lint_json = Path(tmp) / "lint-before.json"
            before_lint = run_aso(
                "lint",
                "--root",
                str(root),
                "--mode",
                "workspace",
                "--strict",
                "--json-out",
                str(lint_json),
            )
            before_lint_report = json.loads(lint_json.read_text(encoding="utf-8"))
            first = run_aso("state", "render", "--root", str(root), "--confirm-write")
            first_report = json.loads(first.stdout)
            project_state = root / "project-runtime" / "PROJECT_STATE.md"
            first_text = project_state.read_text(encoding="utf-8")
            second = run_aso("state", "render", "--root", str(root), "--confirm-write")
            second_text = project_state.read_text(encoding="utf-8")
            after_status = run_aso("status", "--root", str(root), "--mode", "workspace")
            after_lint = run_aso("lint", "--root", str(root), "--mode", "workspace", "--strict")
            after_doctor = run_aso("doctor", "--root", str(root), "--mode", "workspace", "--strict")

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(before_lint.returncode, 3, before_lint.stdout + before_lint.stderr)
        self.assertIn("LINT_IO_004", before_lint.stdout)
        self.assertIn("aso state render --root WORKSPACE --confirm-write", before_lint.stdout)
        self.assertIn(
            "aso state render --root WORKSPACE --confirm-write",
            before_lint_report["findings"][0]["recommendation"],
        )
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(first_report["status"], "written")
        self.assertEqual(first_report["summary"]["views_written"], 7)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(first_text, second_text)
        self.assertTrue(first_text.startswith("DERIVED VIEW.\n"))
        self.assertIn("Source: project-runtime/state/PROJECT_STATE.json", first_text)
        self.assertIn("Do not edit this file directly.", first_text)
        self.assertIn("Canonical state is JSON sidecar.", first_text)
        self.assertIn("PROJECT_SLUG: materialize-test", first_text)
        self.assertEqual(after_status.returncode, 0, after_status.stdout + after_status.stderr)
        self.assertEqual(after_lint.returncode, 0, after_lint.stdout + after_lint.stderr)
        self.assertEqual(after_doctor.returncode, 0, after_doctor.stdout + after_doctor.stderr)

    def test_confirm_write_rejects_report_out_combination(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            init = run_aso("state", "init", "--root", str(root), "--project-slug", "bad-combo", "--confirm-write")
            result = run_aso(
                "state",
                "render",
                "--root",
                str(root),
                "--confirm-write",
                "--out",
                str(Path(tmp) / "report.md"),
            )

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("--confirm-write cannot be combined with --out", result.stderr)


if __name__ == "__main__":
    unittest.main()
