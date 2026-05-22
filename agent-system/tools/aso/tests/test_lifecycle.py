from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]


RESULT = """# RESULT

STATUS: pass
TASK_ID: TASK_DEMO_001
AGENT_INSTANCE_ID: agent_TASK_DEMO_001_attempt_001
ROLE: developer
TASK: TASK_DEMO_001
SUMMARY:
Done.
READ_DOCS:
- NONE
READ_INPUTS:
- NONE
CHANGED_FILES:
- NONE
CREATED_FILES:
- NONE
DELETED_FILES:
- NONE
COMMANDS_RUN:
- NONE
TESTS_RUN:
- NONE
EVIDENCE:
- NONE
SCOPE_VERIFICATION:
- NONE
FORBIDDEN_CHANGES_CHECK:
- NONE
RISKS:
- NONE
LIMITATIONS:
- NONE
BLOCKERS:
- NONE
GAPS:
- NONE
NEXT_RECOMMENDED_ACTION:
- NONE
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""


def run_lifecycle(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "lifecycle", "terminate-agent", "--root", str(root), *extra],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


class LifecycleCommandTests(unittest.TestCase):
    def test_terminate_agent_writes_agent_terminated_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_path = root / "project-runtime" / "results" / "worker" / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.parent.mkdir(parents=True)
            result_path.write_text(RESULT, encoding="utf-8")

            result = run_lifecycle(root, "--from-result", str(result_path), "--confirm-write")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "written")
            self.assertTrue(report["mutations_performed"])
            event_path = root / "project-runtime" / "agents" / "instances.jsonl"
            events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(events), 1)
            event = events[0]
            self.assertEqual(event["event_type"], "AGENT_TERMINATED")
            self.assertEqual(event["task_id"], "TASK_DEMO_001")
            self.assertEqual(event["agent_role"], "developer")
            self.assertEqual(event["agent_instance_id"], "agent_TASK_DEMO_001_attempt_001")
            self.assertEqual(event["result_ref"], "project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md")
            self.assertEqual(event["termination_reason"], "result_submitted")
            self.assertEqual(event["created_by"], "orchestrator")
            self.assertEqual(event["next_allowed_action"], "audit_route")

    def test_terminate_agent_requires_existing_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = run_lifecycle(
                root,
                "--from-result",
                "project-runtime/results/worker/MISSING.md",
                "--confirm-write",
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "blocked")
            rule_ids = {finding["rule_id"] for finding in report["findings"]}
            self.assertIn("LIFECYCLE_RESULT_IO_001", rule_ids)
            self.assertFalse((root / "project-runtime" / "agents" / "instances.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
