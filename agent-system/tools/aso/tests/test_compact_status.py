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

PROJECT_SLUG: demo-project
ACTUAL_BRANCH: main
PROJECT_STATUS: active
PROJECT_CHECKPOINT_STATUS: pending
PUSH_ALLOWED: false
""",
    "CURRENT_GATE.md": """# CURRENT_GATE

STATUS: open
""",
    "NEXT_ACTION.md": """# NEXT_ACTION

ACTION_TYPE: create_agent
TARGET_ROLE: developer
TASK_ID: TASK_DEMO_001
TASK_PACKET: project-runtime/tasks/active/TASK_DEMO_001.md
""",
    "TASK_REGISTRY.md": "# TASK_REGISTRY\n\nNONE\n",
    "ACCEPTED_ARTIFACTS.md": "# ACCEPTED_ARTIFACTS\n\nNONE\n",
    "REPOSITORY_LOCK.md": "# REPOSITORY_LOCK\n\nPUSH_ALLOWED: false\n",
    "WORKSPACE_IDENTITY.md": "# WORKSPACE_IDENTITY\n\nPROJECT_NAME: Demo Project\nACTUAL_BRANCH: main\nPUSH_ALLOWED: false\n",
}


def write_runtime(root: Path, overrides: dict[str, str] | None = None) -> None:
    runtime = root / "project-runtime"
    runtime.mkdir()
    content = dict(RUNTIME_CONTENT)
    if overrides:
        content.update(overrides)
    for name, text in content.items():
        (runtime / name).write_text(text, encoding="utf-8")


def run_status(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "status", "--root", str(root), *extra],
        check=False,
        text=True,
        capture_output=True,
    )


class CompactStatusTests(unittest.TestCase):
    def test_status_compact_outputs_short_operator_summary_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            out = root / "status.json"

            result = run_status(root, "--compact", "--json-out", str(out))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Project: demo-project", result.stdout)
            self.assertIn("Current gate: open", result.stdout)
            self.assertIn("Next action: create_agent target=developer task=TASK_DEMO_001", result.stdout)
            self.assertIn("Runtime consistency: PASS", result.stdout)
            self.assertNotIn("Recommendation:", result.stdout)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["command"], "status")
            self.assertEqual(report["summary"]["runtime_consistency"], "PASS")

    def test_status_full_keeps_finding_recommendations_for_deep_debug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root, {"REPOSITORY_LOCK.md": "# REPOSITORY_LOCK\n\nPUSH_ALLOWED: true\n"})

            result = run_status(root, "--full")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Runtime consistency: FAIL", result.stdout)
            self.assertIn("STATUS_003", result.stdout)
            self.assertIn("Recommendation:", result.stdout)


if __name__ == "__main__":
    unittest.main()
