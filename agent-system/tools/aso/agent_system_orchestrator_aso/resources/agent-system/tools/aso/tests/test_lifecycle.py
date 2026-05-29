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
        [sys.executable, str(CLI), "lifecycle", *extra, "--root", str(root)],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def run_aso(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *extra, "--root", str(root)],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


class LifecycleCommandTests(unittest.TestCase):
    def test_lifecycle_records_result_acceptance_termination_and_audit_ready_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_path = root / "project-runtime" / "results" / "worker" / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.parent.mkdir(parents=True)
            result_path.write_text(RESULT, encoding="utf-8")
            package_result_path = (
                root
                / "project-runtime"
                / "artifacts"
                / "candidates"
                / "TASK_DEMO_001"
                / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            )
            package_result_path.parent.mkdir(parents=True)
            package_result_path.write_text(RESULT, encoding="utf-8")
            candidate = package_result_path.parent / "manifest.json"
            candidate.write_text(
                json.dumps(
                    {
                        "artifact_package_schema_version": "1.1.0",
                        "artifact_type": "RESULT",
                        "artifact_id": "RESULT_TASK_DEMO_001_ATTEMPT_001",
                        "task_id": "TASK_DEMO_001",
                        "role": "developer",
                        "attempt_no": 1,
                        "status": "pass",
                        "main_document": "RESULT_TASK_DEMO_001_ATTEMPT_001.md",
                        "structured_artifacts": "NONE",
                        "evidence_refs": "NONE",
                        "created_at": "2026-05-22T00:00:00Z",
                        "producer": {
                            "agent_instance_id": "agent_TASK_DEMO_001_attempt_001",
                            "role": "developer",
                        },
                    }
                ),
                encoding="utf-8",
            )

            received = run_lifecycle(
                root,
                "receive-result",
                "--from-result",
                str(result_path),
                "--confirm-write",
            )
            accepted = run_aso(
                root,
                "artifact",
                "accept",
                "--package",
                "project-runtime/artifacts/candidates/TASK_DEMO_001/manifest.json",
                "--confirm-write",
                "--format",
                "json",
            )

            result = run_lifecycle(root, "terminate-agent", "--from-result", str(result_path), "--confirm-write")

            self.assertEqual(received.returncode, 0, received.stdout + received.stderr)
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "written")
            self.assertTrue(report["mutations_performed"])
            event_path = root / "project-runtime" / "agents" / "instances.jsonl"
            events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([event["event_type"] for event in events], ["RESULT_RECEIVED", "ARTIFACT_ACCEPTED", "AGENT_TERMINATED", "AUDIT_ROUTE_READY"])
            event = events[2]
            self.assertEqual(event["event_type"], "AGENT_TERMINATED")
            self.assertEqual(event["task_id"], "TASK_DEMO_001")
            self.assertEqual(event["agent_role"], "developer")
            self.assertEqual(event["agent_instance_id"], "agent_TASK_DEMO_001_attempt_001")
            self.assertEqual(event["result_ref"], "project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md")
            self.assertEqual(event["artifact_ids"], ["RESULT_TASK_DEMO_001_ATTEMPT_001"])
            self.assertEqual(event["artifact_receipt_refs"], ["project-runtime/receipts/artifacts/TASK_DEMO_001/RESULT_TASK_DEMO_001_ATTEMPT_001.acceptance.json"])
            self.assertEqual(event["termination_reason"], "result_submitted")
            self.assertEqual(event["created_by"], "orchestrator")
            self.assertEqual(event["next_allowed_action"], "audit_route")
            self.assertEqual(events[3]["previous_event_type"], "AGENT_TERMINATED")

    def test_terminate_agent_requires_existing_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = run_lifecycle(
                root,
                "terminate-agent",
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

    def test_terminate_agent_requires_artifact_accepted_receipt_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_path = root / "project-runtime" / "results" / "worker" / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.parent.mkdir(parents=True)
            result_path.write_text(RESULT, encoding="utf-8")

            received = run_lifecycle(
                root,
                "receive-result",
                "--from-result",
                str(result_path),
                "--confirm-write",
            )
            result = run_lifecycle(
                root,
                "terminate-agent",
                "--from-result",
                str(result_path),
                "--confirm-write",
            )

            self.assertEqual(received.returncode, 0, received.stdout + received.stderr)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            rule_ids = {finding["rule_id"] for finding in report["findings"]}
            self.assertIn("LIFECYCLE_SEQUENCE_002", rule_ids)
            events = [
                json.loads(line)
                for line in (root / "project-runtime/agents/instances.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["event_type"] for event in events], ["RESULT_RECEIVED"])


if __name__ == "__main__":
    unittest.main()
