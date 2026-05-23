from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def write_tz_file(root: Path) -> None:
    tz_file = root / "project-input" / "TZ.md"
    tz_file.parent.mkdir(parents=True, exist_ok=True)
    tz_file.write_text("Europe/Moscow\n", encoding="utf-8")


class StateInitCommandTests(unittest.TestCase):
    def test_dry_run_prints_plan_and_writes_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Dry Run",
                "--project-slug",
                "dry-run",
                "--dry-run",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            plan = json.loads(result.stdout)
            self.assertTrue(plan["dry_run"])
            self.assertEqual(plan["status"], "planned")
            self.assertEqual(len(plan["writes"]), 10)
            self.assertEqual(list(root.iterdir()), [])

    def test_dry_run_json_out_writes_valid_plan_without_target_state_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            json_out = Path(tmp) / "state-init-plan.json"

            result = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Dry Run JSON",
                "--project-slug",
                "dry-run-json",
                "--dry-run",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            plan = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(plan["dry_run"])
            self.assertEqual(plan["status"], "planned")
            self.assertEqual(json.loads(result.stdout), plan)
            self.assertFalse((root / "project-runtime").exists())

    def test_confirm_write_creates_current_sidecars_that_verify_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Init Test",
                "--project-slug",
                "init-test",
                "--confirm-write",
            )
            verify = run_aso("state", "verify", "--root", str(root), "--strict")

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            project_state = json.loads(
                (root / "project-runtime" / "state" / "PROJECT_STATE.json").read_text(encoding="utf-8")
            )
            tz_file = root / "project-input" / "TZ.md"
            next_action = json.loads(
                (root / "project-runtime" / "state" / "NEXT_ACTION.json").read_text(encoding="utf-8")
            )
            self.assertEqual(project_state["content"]["tz_path"], "project-input/TZ.md")
            self.assertEqual(tz_file.read_text(encoding="utf-8"), "# TZ\n\nTIMEZONE: UTC\n")
            self.assertEqual(next_action["content"]["action_semantic"], "normal")
            self.assertNotEqual(next_action["content"]["action_type"], "stop")
            sidecars = sorted((root / "project-runtime" / "state").glob("*.json"))
            self.assertEqual(len(sidecars), 9)
            for path in sidecars:
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["schema_version"], "3.1.0")
                self.assertEqual(payload["runtime_schema_version"], "3.1.0")

    def test_confirmed_current_state_requires_schema_manifest_for_strict_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tz_file(root)

            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Init Test",
                "--project-slug",
                "init-test",
                "--confirm-write",
            )
            ok_verify = run_aso("state", "verify", "--root", str(root), "--strict")
            (root / "project-runtime" / "state" / "SCHEMA_MANIFEST.json").unlink()
            missing_report = root / "missing-schema-manifest-report.json"
            missing_verify = run_aso(
                "state",
                "verify",
                "--root",
                str(root),
                "--strict",
                "--json-out",
                str(missing_report),
            )

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            self.assertEqual(ok_verify.returncode, 0, ok_verify.stdout + ok_verify.stderr)
            self.assertEqual(missing_verify.returncode, 1, missing_verify.stdout + missing_verify.stderr)
            self.assertIn("SIDECAR_REQUIRED_SIDECAR_MISSING", missing_verify.stdout)
            report = json.loads(missing_report.read_text(encoding="utf-8"))
            self.assertIn("SCHEMA_MANIFEST", report["state"]["required_sidecars_missing"])

    def test_confirm_write_json_out_writes_valid_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            json_out = Path(tmp) / "state-init-receipt.json"

            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Receipt Test",
                "--project-slug",
                "receipt-test",
                "--confirm-write",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            receipt = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertFalse(receipt["dry_run"])
            self.assertEqual(receipt["status"], "written")
            self.assertEqual(receipt["write_result"], "wrote default TZ document; wrote state sidecars")
            self.assertEqual(json.loads(init.stdout), receipt)

    def test_confirm_write_preserves_existing_tz_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tz_file(root)

            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Existing TZ",
                "--project-slug",
                "existing-tz",
                "--confirm-write",
            )
            verify = run_aso("state", "verify", "--root", str(root), "--strict")

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            self.assertEqual((root / "project-input" / "TZ.md").read_text(encoding="utf-8"), "Europe/Moscow\n")

    def test_package_root_is_refused(self) -> None:
        result = run_aso("state", "init", "--root", str(REPO_ROOT), "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to initialize the ASO package root", result.stderr)


if __name__ == "__main__":
    unittest.main()
