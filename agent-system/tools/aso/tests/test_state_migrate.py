from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "state"
VALID_WORKSPACE = FIXTURE_ROOT / "valid_workspace"
LEGACY_MIGRATION_SOURCE = VALID_WORKSPACE


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def copy_fixture(tmp: str, fixture_name: str) -> Path:
    root = Path(tmp) / fixture_name
    shutil.copytree(FIXTURE_ROOT / fixture_name, root)
    return root


class StateMigrateCommandTests(unittest.TestCase):
    def test_dry_run_prints_deterministic_plan_and_writes_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "legacy-migration-source"
            shutil.copytree(LEGACY_MIGRATION_SOURCE, root)
            tracked = [path for path in root.rglob("*") if path.is_file()]
            mtimes_before = {path: path.stat().st_mtime_ns for path in tracked}

            first = run_aso("state", "migrate", "--root", str(root), "--dry-run")
            second = run_aso("state", "migrate", "--root", str(root), "--dry-run")

            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(first.stdout, second.stdout)
            plan = json.loads(first.stdout)
            self.assertTrue(plan["dry_run"])
            self.assertEqual(plan["status"], "planned")
            self.assertEqual(plan["from_schema_version"], "2.0.0")
            self.assertEqual(plan["to_schema_version"], "3.1.0")
            self.assertEqual(len(plan["writes"]), 9)
            self.assertFalse((root / "project-runtime" / "reports").exists())
            self.assertEqual(mtimes_before, {path: path.stat().st_mtime_ns for path in tracked})

    def test_confirm_write_migrates_and_strict_verify_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture(tmp, "valid_workspace")

            migrate = run_aso("state", "migrate", "--root", str(root), "--confirm-write")
            verify = run_aso("state", "verify", "--root", str(root), "--strict")

            self.assertEqual(migrate.returncode, 0, migrate.stdout + migrate.stderr)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            receipt = root / "project-runtime" / "reports" / "state-migration-2_0_0-to-3_1_0.json"
            self.assertTrue(receipt.is_file())
            for filename in (
                "PROJECT_STATE.json",
                "TASK_REGISTRY.json",
                "NEXT_ACTION.json",
                "CURRENT_GATE.json",
                "WORKSPACE_IDENTITY.json",
                "ACCEPTED_ARTIFACTS.json",
                "SCHEMA_MANIFEST.json",
            ):
                payload = json.loads((root / "project-runtime" / "state" / filename).read_text(encoding="utf-8"))
                self.assertEqual(payload["schema_version"], "3.1.0")
                self.assertEqual(payload["runtime_schema_version"], "3.1.0")
                self.assertEqual(payload["migration_source_schema"], "2.0.0")

    def test_negative_fixture_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture(tmp, "valid_workspace")
            path = root / "project-runtime" / "state" / "CURRENT_GATE.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            content = payload["content"]
            self.assertIsInstance(content, dict)
            content["status"] = "active"
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            result = run_aso("state", "migrate", "--root", str(root), "--dry-run")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "failed")
            rule_ids = {finding["rule_id"] for finding in report["findings"]}
            self.assertIn("SIDECAR_ENUM_VALUE_INVALID", rule_ids)

    def test_writes_require_confirm_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture(tmp, "valid_workspace")

            result = run_aso("state", "migrate", "--root", str(root))

            self.assertEqual(result.returncode, 2)
            self.assertIn("writes require --confirm-write", result.stderr)


if __name__ == "__main__":
    unittest.main()
