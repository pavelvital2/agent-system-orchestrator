from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "context_pack"


NEGATIVE_FIXTURES = {
    "bad_context_pack_archive_doc.json": "CPP-002",
    "bad_context_pack_deprecated_doc.json": "CPP-003",
    "bad_context_pack_forbidden_doc.json": "CPP-004",
    "bad_context_pack_missing_required_fields.json": "CPS-002",
    "bad_context_pack_budget_overflow.json": "CPB-001",
    "bad_context_pack_path_escape.json": "CPP-001",
}


def run_validate_context_pack(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "validate-context-pack", *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


class ValidateContextPackCommandTests(unittest.TestCase):
    def test_valid_context_pack_fixture_passes_strict(self) -> None:
        fixture = FIXTURE_ROOT / "valid_context_pack.json"
        mtime_before = fixture.stat().st_mtime_ns

        result = run_validate_context_pack(str(fixture), "--root", str(REPO_ROOT), "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ASO validate-context-pack: PASSED", result.stdout)
        self.assertEqual(fixture.stat().st_mtime_ns, mtime_before)

    def test_negative_context_pack_fixtures_fail_with_expected_rule_ids(self) -> None:
        for filename, rule_id in NEGATIVE_FIXTURES.items():
            with self.subTest(filename=filename):
                fixture = FIXTURE_ROOT / filename
                result = run_validate_context_pack(str(fixture), "--root", str(REPO_ROOT), "--strict")

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("ASO validate-context-pack: FAILED", result.stdout)
                self.assertIn(rule_id, result.stdout)

    def test_json_output_is_parseable_and_deterministic(self) -> None:
        fixture = FIXTURE_ROOT / "bad_context_pack_forbidden_doc.json"
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "validate-context-pack.json"

            first = run_validate_context_pack(
                str(fixture),
                "--root",
                str(REPO_ROOT),
                "--strict",
                "--json-out",
                str(json_out),
            )
            self.assertEqual(first.returncode, 1, first.stdout + first.stderr)
            payload = json.loads(json_out.read_text(encoding="utf-8"))

            second_json = Path(tmp) / "validate-context-pack-second.json"
            second = run_validate_context_pack(
                str(fixture),
                "--root",
                str(REPO_ROOT),
                "--strict",
                "--json-out",
                str(second_json),
            )
            self.assertEqual(second.returncode, 1, second.stdout + second.stderr)

            self.assertEqual(payload, json.loads(second_json.read_text(encoding="utf-8")))
            self.assertEqual(payload["command"], "validate-context-pack")
            self.assertEqual(payload["status"], "failed")
            self.assertEqual(payload["summary"]["errors"], 2)
            self.assertEqual(payload["findings"][0]["rule_id"], "CPP-004")
            self.assertTrue(payload["read_only"])


if __name__ == "__main__":
    unittest.main()
