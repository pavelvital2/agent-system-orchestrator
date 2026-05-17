from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"


RUNTIME_CONTENT = {
    "PROJECT_STATE.md": """# PROJECT_STATE

PROJECT_SLUG:
demo-project

ACTUAL_BRANCH: main
PROJECT_STATUS: active
PROJECT_CHECKPOINT_STATUS: pending
PUSH_ALLOWED: false
""",
    "CURRENT_GATE.md": """# CURRENT_GATE

STATUS:
open
""",
    "NEXT_ACTION.md": """# NEXT_ACTION

ACTION_TYPE: create_agent
TARGET_ROLE: developer
TASK_ID: TASK_DEMO_001
TASK_PACKET: project-runtime/tasks/active/TASK_DEMO_001.md
""",
    "TASK_REGISTRY.md": "# TASK_REGISTRY\n\nNONE\n",
    "ACCEPTED_ARTIFACTS.md": "# ACCEPTED_ARTIFACTS\n\nNONE\n",
    "REPOSITORY_LOCK.md": """# REPOSITORY_LOCK

PUSH_ALLOWED:
false
""",
    "WORKSPACE_IDENTITY.md": """# WORKSPACE_IDENTITY

PROJECT_NAME: Demo Project
ACTUAL_BRANCH:
main
PUSH_ALLOWED: false
""",
}


def write_runtime(root: Path, overrides: dict[str, str] | None = None) -> list[Path]:
    runtime = root / "project-runtime"
    runtime.mkdir()
    paths = []
    content = dict(RUNTIME_CONTENT)
    if overrides:
        content.update(overrides)
    for name, text in content.items():
        path = runtime / name
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths


class StatusCommandTests(unittest.TestCase):
    def test_status_outputs_normalized_summary_and_json_without_runtime_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_paths = write_runtime(root)
            mtimes_before = {path: path.stat().st_mtime_ns for path in runtime_paths}
            json_out = root / "status.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "status",
                    "--root",
                    str(root),
                    "--json-out",
                    str(json_out),
                ],
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Project: demo-project", result.stdout)
            self.assertIn("Branch: main", result.stdout)
            self.assertIn("Project status: active", result.stdout)
            self.assertIn("Current gate: open", result.stdout)
            self.assertIn("Checkpoint status: pending", result.stdout)
            self.assertIn("Next action: create_agent target=developer task=TASK_DEMO_001", result.stdout)
            self.assertIn(
                "Push allowed values: PROJECT_STATE=false, REPOSITORY_LOCK=false, WORKSPACE_IDENTITY=false",
                result.stdout,
            )
            self.assertIn("Runtime consistency: PASS", result.stdout)
            self.assertIn("Findings: 0", result.stdout)

            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["tool"], "aso")
            self.assertEqual(report["command"], "status")
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["summary"]["runtime_consistency"], "PASS")
            self.assertEqual(report["summary"]["finding_count"], 0)
            self.assertEqual(report["findings"], [])

            mtimes_after = {path: path.stat().st_mtime_ns for path in runtime_paths}
            self.assertEqual(mtimes_before, mtimes_after)

    def test_status_reports_conflicting_push_allowed_as_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(
                root,
                {
                    "REPOSITORY_LOCK.md": "# REPOSITORY_LOCK\n\nPUSH_ALLOWED: true\n",
                },
            )

            result = subprocess.run(
                [sys.executable, str(CLI), "status", "--root", str(root)],
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Runtime consistency: FAIL", result.stdout)
            self.assertIn("Findings: 1", result.stdout)


if __name__ == "__main__":
    unittest.main()
