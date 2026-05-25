from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "design"


NEGATIVE_FIXTURES = {
    "bad_design_missing_sources.md": "DRF-001",
    "bad_design_assumption_as_fact.md": "DRF-002",
    "bad_design_no_acceptance_criteria.md": "DRF-003",
    "bad_design_giant_task.md": "DRF-004",
    "bad_design_missing_testing_strategy.md": "DRF-005",
    "bad_design_unresolved_dependency.md": "DRF-006",
}


def run_validate_design(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "validate-design", *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


class ValidateDesignCommandTests(unittest.TestCase):
    def test_valid_design_fixture_passes_strict(self) -> None:
        fixture = FIXTURE_ROOT / "valid_design.md"
        mtime_before = fixture.stat().st_mtime_ns

        result = run_validate_design(str(fixture), "--root", str(REPO_ROOT), "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ASO validate-design: PASSED", result.stdout)
        self.assertEqual(fixture.stat().st_mtime_ns, mtime_before)

    def test_negative_design_fixtures_fail_with_expected_rule_ids(self) -> None:
        for filename, rule_id in NEGATIVE_FIXTURES.items():
            with self.subTest(filename=filename):
                fixture = FIXTURE_ROOT / filename
                result = run_validate_design(str(fixture), "--root", str(REPO_ROOT), "--strict")

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("ASO validate-design: FAILED", result.stdout)
                self.assertIn(rule_id, result.stdout)

    def test_json_output_is_parseable_and_deterministic(self) -> None:
        fixture = FIXTURE_ROOT / "bad_design_missing_sources.md"
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "validate-design.json"

            first = run_validate_design(
                str(fixture),
                "--root",
                str(REPO_ROOT),
                "--strict",
                "--json-out",
                str(json_out),
            )
            self.assertEqual(first.returncode, 1, first.stdout + first.stderr)
            payload = json.loads(json_out.read_text(encoding="utf-8"))

            second_json = Path(tmp) / "validate-design-second.json"
            second = run_validate_design(
                str(fixture),
                "--root",
                str(REPO_ROOT),
                "--strict",
                "--json-out",
                str(second_json),
            )
            self.assertEqual(second.returncode, 1, second.stdout + second.stderr)

            self.assertEqual(payload, json.loads(second_json.read_text(encoding="utf-8")))
            self.assertEqual(payload["command"], "validate-design")
            self.assertEqual(payload["status"], "failed")
            self.assertEqual(payload["summary"]["errors"], 1)
            self.assertEqual(payload["findings"][0]["rule_id"], "DRF-001")


if __name__ == "__main__":
    unittest.main()
