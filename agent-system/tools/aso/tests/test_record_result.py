from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "results"


def fixture(name: str) -> Path:
    return FIXTURE_ROOT / name


def run_record_result(path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "record-result",
            "--result",
            str(path),
            "--dry-run",
            "--json",
            *extra,
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def report_from(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    return json.loads(result.stdout)


class RecordResultCommandTests(unittest.TestCase):
    def test_help_declares_dry_run_read_only(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "record-result", "--help"],
            check=False,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Dry-run/read-only", result.stdout)
        self.assertIn("without mutating state", result.stdout)
        self.assertIn("--json", result.stdout)
        self.assertNotIn("--json-out", result.stdout)

    def test_dry_run_flag_is_required(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "record-result",
                "--result",
                str(fixture("RESULT_TASK_DEMO_001_PASS.md")),
            ],
            check=False,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--dry-run", result.stderr)

    def test_profile_pass_routes_to_auditor_and_does_not_mutate_fixture(self) -> None:
        path = fixture("RESULT_TASK_DEMO_001_PASS.md")
        before = path.stat().st_mtime_ns

        result = run_record_result(path, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["report_status"], "ready")
        self.assertEqual(report["result_type"], "profile_result")
        self.assertEqual(report["task_id"], "TASK_DEMO_001")
        self.assertEqual(report["role"], "developer")
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["audit_required"])
        self.assertFalse(report["checkpoint_candidate"])
        self.assertEqual(report["recommended_next_action"], "CREATE_AUDITOR")
        self.assertTrue(report["dry_run"])
        self.assertTrue(report["read_only"])
        self.assertFalse(report["mutations_performed"])
        self.assertEqual(path.stat().st_mtime_ns, before)
        rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
        self.assertIn("GOV-CHECKPOINT-AUDIT-GATE", rule_ids)

    def test_audit_pass_routes_to_checkpoint_preflight_candidate(self) -> None:
        result = run_record_result(fixture("AUDIT_RESULT_TASK_DEMO_001_PASS.md"), "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["report_status"], "ready")
        self.assertEqual(report["result_type"], "audit_result")
        self.assertEqual(report["role"], "auditor")
        self.assertEqual(report["status"], "pass")
        self.assertFalse(report["audit_required"])
        self.assertTrue(report["checkpoint_candidate"])
        self.assertEqual(report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
        evidence = report["evidence"]
        self.assertIsInstance(evidence, dict)
        self.assertEqual(
            evidence["source_result_refs"],
            ["agent-system/tests/fixtures/results/RESULT_TASK_DEMO_001_PASS.md"],
        )
        self.assertEqual(report["blocking_rules"], [])

    def test_profile_failed_result_never_becomes_checkpoint_ready(self) -> None:
        result = run_record_result(fixture("RESULT_TASK_DEMO_001_FAIL.md"), "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["result_type"], "profile_result")
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["checkpoint_candidate"])
        self.assertEqual(report["recommended_next_action"], "ROUTE_CORRECTION")
        rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
        self.assertIn("GOV-PROFILE-FAIL-NO-CHECKPOINT", rule_ids)

    def test_audit_non_pass_statuses_never_become_checkpoint_ready(self) -> None:
        cases = {
            "AUDIT_RESULT_TASK_DEMO_001_FAIL.md": ("fail", "ROUTE_CORRECTION"),
            "AUDIT_RESULT_TASK_DEMO_001_BLOCKED.md": ("blocked", "ORCHESTRATOR_BLOCKED_ROUTING"),
            "AUDIT_RESULT_TASK_DEMO_001_GAP.md": ("gap", "REGISTER_GAP"),
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                result = run_record_result(fixture(filename), "--strict")

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                report = report_from(result)
                self.assertEqual(report["result_type"], "audit_result")
                self.assertEqual(report["status"], expected[0])
                self.assertFalse(report["checkpoint_candidate"])
                self.assertEqual(report["recommended_next_action"], expected[1])

    def test_strict_rejects_profile_audit_bypass_attempt(self) -> None:
        result = run_record_result(fixture("RESULT_TASK_DEMO_001_BYPASS.md"), "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["report_status"], "rejected")
        self.assertFalse(report["checkpoint_candidate"])
        self.assertEqual(report["recommended_next_action"], "CREATE_AUDITOR")
        rule_ids = {item["rule_id"] for item in report["validation_errors"]}
        self.assertIn("RESULT_BYPASS_001", rule_ids)

    def test_strict_rejects_malformed_result(self) -> None:
        result = run_record_result(fixture("RESULT_TASK_DEMO_001_MALFORMED.md"), "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["report_status"], "rejected")
        self.assertFalse(report["checkpoint_candidate"])
        rule_ids = {item["rule_id"] for item in report["validation_errors"]}
        self.assertIn("RESULT_FORMAT_003", rule_ids)
        self.assertIn("RESULT_FORMAT_004", rule_ids)


if __name__ == "__main__":
    unittest.main()
