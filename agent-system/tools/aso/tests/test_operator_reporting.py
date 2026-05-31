from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from test_lifecycle_finalization import prepare_finalizable_workspace  # noqa: E402


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "state"
VALID_WORKSPACE = FIXTURE_ROOT / "valid_workspace"
FINAL_WORKER_RESULT_REF = "project-runtime/results/worker/RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md"
FINAL_WORKER_RESULT_WITH_TESTS = """RESULT:
STATUS: pass
TASK_ID: TASK_FIXTURE_STATE_001
AGENT_INSTANCE_ID: implementation_fixture_attempt_001
ROLE: developer
TASK: TASK_FIXTURE_STATE_001
SUMMARY:
Fixture implementation passed.
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
- PYTHONDONTWRITEBYTECODE=1 python3 -m unittest agent-system/tools/aso/tests/test_operator_reporting.py -v
TESTS_RUN:
- PYTHONDONTWRITEBYTECODE=1 python3 -m unittest agent-system/tools/aso/tests/test_operator_reporting.py -v
EVIDENCE:
- RESULT_STATUS: pass
- VALIDATION_STATUS: passed
- RESULT_SCHEMA_STATUS: passed
SCOPE_VERIFICATION:
- NONE
FORBIDDEN_CHANGES_CHECK:
- NONE
RISKS:
- NONE
LIMITATIONS:
- fixture limitation carried into final receipt
BLOCKERS:
- NONE
GAPS:
- NONE
NEXT_RECOMMENDED_ACTION:
- CHECKPOINT_PREFLIGHT
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""


def run_aso(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *extra, "--root", str(root)],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def copy_valid_workspace(tmp: str) -> Path:
    root = Path(tmp) / "workspace"
    shutil.copytree(VALID_WORKSPACE, root)
    return root


class OperatorReportingTests(unittest.TestCase):
    def test_monitor_summary_json_surfaces_operator_status_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)

            result = run_aso(root, "monitor-summary", "--json")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["command"], "monitor-summary")
            self.assertEqual(report["current_phase"], "implementation")
            self.assertEqual(report["active_blocker"], "NONE")
            self.assertEqual(report["waiting_for"], "developer")
            self.assertEqual(report["audit_status"], "pending")
            self.assertIn("final_receipt", report)
            self.assertFalse(report["mutations_performed"])

    def test_operator_report_generation_writes_full_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            json_out = root / "project-runtime" / "reports" / "operator.json"
            md_out = root / "project-runtime" / "reports" / "operator.md"

            result = run_aso(root, "report", "operator", "--json-out", str(json_out), "--out", str(md_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["command"], "report operator")
            self.assertEqual(report["monitor_summary"]["current_phase"], "implementation")
            self.assertEqual(report["stdout_policy"]["default"], "compact")
            self.assertEqual(len(report["tasks"]), 1)
            self.assertIn("ASO Operator Report", md_out.read_text(encoding="utf-8"))

    def test_operator_event_log_append_records_required_event_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            reports = root / "project-runtime" / "reports"
            receipts = root / "project-runtime" / "receipts" / "state-reconciliation"
            results = root / "project-runtime" / "results" / "worker"
            audits = root / "project-runtime" / "results" / "audit"
            for path in (reports, receipts, results, audits):
                path.mkdir(parents=True, exist_ok=True)
            (reports / "stdout.txt").write_text("ok\n", encoding="utf-8")
            (reports / "stderr.txt").write_text("", encoding="utf-8")
            (reports / "handoff.json").write_text("{}\n", encoding="utf-8")
            (receipts / "receipt.json").write_text("{}\n", encoding="utf-8")
            result_ref = "project-runtime/results/worker/RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md"
            audit_ref = "project-runtime/results/audit/AUDIT_RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md"
            (root / result_ref).write_text("# RESULT\nSTATUS: pass\n", encoding="utf-8")
            (root / audit_ref).write_text("# AUDIT_RESULT\nSTATUS: pass\n", encoding="utf-8")

            result = run_aso(
                root,
                "report",
                "operator",
                "--record-event",
                "--confirm-write",
                "--json",
                "--event-command",
                "make test",
                "--event-exit-code",
                "0",
                "--stdout-ref",
                "project-runtime/reports/stdout.txt",
                "--stderr-ref",
                "project-runtime/reports/stderr.txt",
                "--file-changed",
                "README.md",
                "--agent",
                "implementation_demo_001",
                "--handoff",
                "project-runtime/reports/handoff.json",
                "--result",
                result_ref,
                "--audit",
                audit_ref,
                "--blocker",
                "NONE",
                "--manual-nudge",
                "owner-reminded",
                "--mutation-receipt",
                "project-runtime/receipts/state-reconciliation/receipt.json",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            compact = json.loads(result.stdout)
            self.assertIn("event_record_ref", compact)
            event_log = root / "project-runtime" / "events" / "operator_events.jsonl"
            records = [json.loads(line) for line in event_log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record["command"], "make test")
            self.assertEqual(record["exit_code"], 0)
            for field in (
                "stdout_refs",
                "stderr_refs",
                "files_changed",
                "agents",
                "handoffs",
                "results",
                "audits",
                "blockers",
                "manual_nudge_markers",
                "mutation_receipts",
            ):
                self.assertIn(field, record)
            self.assertEqual(record["manual_nudge_markers"], ["owner-reminded"])

    def test_final_run_receipt_writes_json_and_markdown_equivalent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = prepare_finalizable_workspace(tmp)
            worker_result = root / FINAL_WORKER_RESULT_REF
            worker_result.parent.mkdir(parents=True, exist_ok=True)
            worker_result.write_text(FINAL_WORKER_RESULT_WITH_TESTS, encoding="utf-8")
            event_log = root / "project-runtime" / "events" / "operator_events.jsonl"
            event_log.parent.mkdir(parents=True, exist_ok=True)
            event_log.write_text(
                json.dumps(
                    {
                        "event_type": "OPERATOR_EVENT_RECORDED",
                        "agent_instance_id": "implementation_fixture_attempt_001",
                        "role": "developer",
                        "task_id": "TASK_FIXTURE_STATE_001",
                        "status": "pass",
                        "result_ref": FINAL_WORKER_RESULT_REF,
                        "manual_nudge_markers": ["owner-confirmed-final-run"],
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            finalize = run_aso(root, "lifecycle", "finalize", "--confirm-write")
            self.assertEqual(finalize.returncode, 0, finalize.stdout + finalize.stderr)

            result = run_aso(root, "report", "final-run", "--confirm-write", "--json")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            compact = json.loads(result.stdout)
            self.assertEqual(compact["final_status"], "completed")
            self.assertEqual(compact["audit_status"], "passed")
            self.assertEqual(compact["terminal_state"], "PROJECT_COMPLETED")
            json_path = root / "project-runtime" / "reports" / "FINAL_RUN_RECEIPT.json"
            md_path = root / "project-runtime" / "reports" / "FINAL_RUN_RECEIPT.md"
            self.assertTrue(json_path.is_file())
            self.assertTrue(md_path.is_file())
            receipt = json.loads(json_path.read_text(encoding="utf-8"))
            for field in (
                "final_status",
                "audit_status",
                "product_tests",
                "commits",
                "agents",
                "tasks",
                "artifacts",
                "manual_nudges",
                "known_limitations",
                "terminal_state",
            ):
                self.assertIn(field, receipt)
            self.assertEqual(receipt["terminal_state"], "PROJECT_COMPLETED")
            self.assertTrue(any("test_operator_reporting.py -v" in item for item in receipt["product_tests"]))
            self.assertIn("owner-confirmed-final-run", receipt["manual_nudges"])
            self.assertTrue(any("fixture limitation carried into final receipt" in item for item in receipt["known_limitations"]))
            markdown = md_path.read_text(encoding="utf-8")
            self.assertIn("ASO Final Run Receipt", markdown)
            for field in (
                "product_tests",
                "commits",
                "agents",
                "tasks",
                "artifacts",
                "manual_nudges",
                "known_limitations",
            ):
                self.assertIn(f"## {field}", markdown)
            self.assertIn("test_operator_reporting.py -v", markdown)
            self.assertIn("owner-confirmed-final-run", markdown)
            self.assertIn("fixture limitation carried into final receipt", markdown)
            self.assertIn('"artifact_id": "ARTIFACT-FIXTURE-001"', markdown)

    def test_operator_report_default_stdout_is_compact_even_with_large_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            event_log = root / "project-runtime" / "events" / "operator_events.jsonl"
            event_log.parent.mkdir(parents=True, exist_ok=True)
            large_marker = "X" * 50_000
            event_log.write_text(
                json.dumps(
                    {
                        "event_type": "OPERATOR_EVENT_RECORDED",
                        "manual_nudge_markers": [large_marker],
                        "command": "external command",
                        "exit_code": 0,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_aso(root, "report", "operator")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertLess(len(result.stdout.encode("utf-8")), 12_000)
            self.assertNotIn(large_marker, result.stdout)
            self.assertIn("Report hash:", result.stdout)

            full = run_aso(root, "report", "operator", "--json", "--diff-mode", "full")

            self.assertEqual(full.returncode, 0, full.stdout + full.stderr)
            self.assertIn(large_marker, full.stdout)


if __name__ == "__main__":
    unittest.main()
