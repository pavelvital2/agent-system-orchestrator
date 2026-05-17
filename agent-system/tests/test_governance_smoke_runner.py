from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SMOKE_RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "run_governance_smoke_tests.py"


def write_fake_runner(path: Path) -> None:
    path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail

            case "${1:-}" in
              --list-fixtures)
                printf '%s\\n' pass_fixture fail_fixture slow_fixture
                ;;
              --run-fixture)
                case "${2:-}" in
                  pass_fixture)
                    printf 'PASS: fake fixture\\n'
                    ;;
                  fail_fixture)
                    printf 'FAIL: fake fixture\\n'
                    exit 9
                    ;;
                  slow_fixture)
                    printf 'sleeping\\n'
                    sleep 10
                    ;;
                  *)
                    printf 'unknown fixture\\n' >&2
                    exit 64
                    ;;
                esac
                ;;
              *)
                printf 'unknown command\\n' >&2
                exit 64
                ;;
            esac
            """
        ),
        encoding="utf-8",
    )
    path.chmod(0o755)


class GovernanceSmokeRunnerTests(unittest.TestCase):
    def test_json_summary_includes_passed_and_skipped_fixtures_with_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_runner = root / "fake_smoke.sh"
            json_out = root / "smoke.json"
            log_dir = root / "logs"
            write_fake_runner(fake_runner)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SMOKE_RUNNER),
                    "--runner",
                    str(fake_runner),
                    "--fixture",
                    "pass_fixture",
                    "--json-out",
                    str(json_out),
                    "--log-dir",
                    str(log_dir),
                    "--timeout-per-fixture",
                    "5",
                ],
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "passed")
            self.assertEqual(summary["status_values"], ["passed", "failed", "timeout", "skipped"])
            self.assertEqual(summary["counts"], {"passed": 1, "failed": 0, "timeout": 0, "skipped": 2})
            fixtures = {fixture["name"]: fixture for fixture in summary["fixtures"]}
            statuses = {name: fixture["status"] for name, fixture in fixtures.items()}
            self.assertEqual(statuses["pass_fixture"], "passed")
            self.assertEqual(statuses["fail_fixture"], "skipped")
            self.assertIn("duration_ms", fixtures["pass_fixture"])
            self.assertIsInstance(fixtures["pass_fixture"]["duration_ms"], int)
            self.assertEqual(fixtures["fail_fixture"]["duration_ms"], 0)
            self.assertIn("PASS: fake fixture", (log_dir / "pass_fixture.log").read_text(encoding="utf-8"))

    def test_timeout_kills_fixture_process_group_and_records_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_runner = root / "fake_smoke.sh"
            json_out = root / "smoke.json"
            write_fake_runner(fake_runner)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SMOKE_RUNNER),
                    "--runner",
                    str(fake_runner),
                    "--fixture",
                    "slow_fixture",
                    "--json-out",
                    str(json_out),
                    "--timeout-per-fixture",
                    "0.2",
                ],
                check=False,
                text=True,
                capture_output=True,
                timeout=5,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            summary = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["counts"]["timeout"], 1)
            slow_fixture = next(fixture for fixture in summary["fixtures"] if fixture["name"] == "slow_fixture")
            self.assertEqual(slow_fixture["status"], "timeout")
            self.assertIn("duration_ms", slow_fixture)

    def test_failed_fixture_is_recorded_without_stopping_summary_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_runner = root / "fake_smoke.sh"
            json_out = root / "smoke.json"
            write_fake_runner(fake_runner)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SMOKE_RUNNER),
                    "--runner",
                    str(fake_runner),
                    "--fixture",
                    "fail_fixture",
                    "--json-out",
                    str(json_out),
                    "--timeout-per-fixture",
                    "5",
                ],
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            summary = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["counts"]["failed"], 1)
            fail_fixture = next(fixture for fixture in summary["fixtures"] if fixture["name"] == "fail_fixture")
            self.assertEqual(fail_fixture["status"], "failed")
            self.assertIn("duration_ms", fail_fixture)
            self.assertEqual(fail_fixture["returncode"], 9)


if __name__ == "__main__":
    unittest.main()
