from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "incidents"


def fixture(name: str) -> Path:
    return FIXTURE_ROOT / name


def run_incident_fixture(path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "incident",
            "fixture",
            "--incident",
            str(path),
            "--dry-run",
            "--strict",
            *extra,
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        env=env,
    )


class IncidentFixtureCommandTests(unittest.TestCase):
    def test_help_declares_dry_run_and_explicit_outputs(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "incident", "fixture", "--help"],
            check=False,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("without mutating runtime state", result.stdout)
        self.assertIn("--dry-run", result.stdout)
        self.assertIn("--json-out", result.stdout)
        self.assertIn("--out", result.stdout)

    def test_dry_run_flag_is_required(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "incident",
                "fixture",
                "--incident",
                str(fixture("valid_fixture_proposal.md")),
                "--strict",
            ],
            check=False,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--dry-run", result.stderr)

    def test_valid_incident_produces_deterministic_non_mutating_proposal(self) -> None:
        path = fixture("valid_fixture_proposal.md")
        before = path.stat().st_mtime_ns

        result = run_incident_fixture(path)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(report["report_status"], "ready")
        self.assertEqual(report["incident_id"], "INC_FIXTURE_VALID_001")
        self.assertEqual(report["triggering_rule_ids"], ["GOV-FORBIDDEN-FILES", "GOV-CHECKPOINT-AUDIT-GATE"])
        self.assertEqual(report["expected_failure_status"], "failed")
        self.assertTrue(report["dry_run"])
        self.assertTrue(report["read_only"])
        self.assertFalse(report["mutations_performed"])
        self.assertFalse(report["safety_controls"]["validator_weakened"])
        self.assertFalse(report["safety_controls"]["owner_decision_approved"])
        self.assertEqual(report["validation_errors"], [])
        paths = {item["path"] for item in report["proposed_fixture_paths"]}
        self.assertIn("agent-system/tests/fixtures/incidents/inc_fixture_valid_001.md", paths)
        self.assertIn("agent-system/tests/fixtures/incidents/inc_fixture_valid_001.proposal.json", paths)
        self.assertIn("agent-system/tools/aso/tests/test_inc_fixture_valid_001_incident_fixture.py", paths)
        self.assertEqual(path.stat().st_mtime_ns, before)

    def test_json_out_and_out_write_only_explicit_proposal_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "proposal.json"
            text_out = Path(tmp) / "proposal.md"

            result = run_incident_fixture(
                fixture("valid_fixture_proposal.md"),
                "--json-out",
                str(json_out),
                "--out",
                str(text_out),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["incident_id"], "INC_FIXTURE_VALID_001")
            self.assertIn("INC_FIXTURE_VALID_001", text_out.read_text(encoding="utf-8"))

    def test_json_out_traversal_into_forbidden_repo_root_is_rejected(self) -> None:
        forbidden = REPO_ROOT / "project-runtime" / "proposal.json"
        self.assertFalse(forbidden.exists())

        result = run_incident_fixture(
            fixture("valid_fixture_proposal.md"),
            "--root",
            "agent-system",
            "--json-out",
            "../project-runtime/proposal.json",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse(forbidden.exists())

    def test_out_traversal_into_forbidden_repo_root_is_rejected(self) -> None:
        forbidden = REPO_ROOT / "project-runtime" / "proposal.md"
        self.assertFalse(forbidden.exists())

        result = run_incident_fixture(
            fixture("valid_fixture_proposal.md"),
            "--root",
            "agent-system",
            "--out",
            "../project-runtime/proposal.md",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse(forbidden.exists())

    def test_missing_rule_id_fails_under_strict(self) -> None:
        result = run_incident_fixture(fixture("missing_rule_id.md"))

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["report_status"], "rejected")
        rule_ids = {item["rule_id"] for item in report["validation_errors"]}
        self.assertIn("INCIDENT_FORMAT_002", rule_ids)
        self.assertIn("INCIDENT_RULE_001", rule_ids)

    def test_attempted_auto_approval_is_rejected(self) -> None:
        result = run_incident_fixture(fixture("attempted_auto_approval.md"))

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["report_status"], "rejected")
        self.assertFalse(report["safety_controls"]["owner_decision_approved"])
        self.assertFalse(report["safety_controls"]["validator_weakened"])
        rule_ids = {item["rule_id"] for item in report["validation_errors"]}
        self.assertIn("INCIDENT_SAFETY_001", rule_ids)


if __name__ == "__main__":
    unittest.main()
