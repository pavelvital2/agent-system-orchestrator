from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import sys


ASO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool.commands import validate_rules  # noqa: E402


FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "rules"


class ValidateRulesTests(unittest.TestCase):
    def _run_validator(self, root: Path, *, strict: bool = True, json_out: str | None = None) -> int:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            return validate_rules.run(SimpleNamespace(root=root, strict=strict, json_out=json_out))

    def test_repository_registry_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "rules-report.json"
            exit_code = self._run_validator(REPO_ROOT, strict=True, json_out=str(report_path))

            self.assertEqual(exit_code, 0)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "passed")
            self.assertGreaterEqual(report["rule_count"], 7)
            self.assertEqual(report["errors"], [])

    def test_valid_fixture_passes(self) -> None:
        exit_code = self._run_validator(FIXTURE_ROOT / "valid_registry", strict=True)

        self.assertEqual(exit_code, 0)

    def test_duplicate_ids_fail(self) -> None:
        exit_code = self._run_validator(FIXTURE_ROOT / "invalid_duplicate", strict=True)

        self.assertNotEqual(exit_code, 0)

    def test_invalid_semantics_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "invalid-report.json"
            exit_code = self._run_validator(
                FIXTURE_ROOT / "invalid_semantics",
                strict=True,
                json_out=str(report_path),
            )

            self.assertNotEqual(exit_code, 0)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            joined_errors = "\n".join(report["errors"])
            self.assertIn("severity", joined_errors)
            self.assertIn("expected_action", joined_errors)
            self.assertIn("rationale", joined_errors)
            self.assertIn("does not exist", joined_errors)


if __name__ == "__main__":
    unittest.main()
