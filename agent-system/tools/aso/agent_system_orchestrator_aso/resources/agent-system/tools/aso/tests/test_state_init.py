from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
DETERMINISTIC_TIMESTAMP = "2026-05-21T00:00:00Z"
RFC3339_UTC_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"


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


def write_placeholder_tz_file(root: Path) -> None:
    tz_file = root / "project-input" / "TZ.md"
    tz_file.parent.mkdir(parents=True, exist_ok=True)
    tz_file.write_text(
        "# TZ Placeholder\n\nSTATUS: placeholder\nMUST_REPLACE_BEFORE_LIFECYCLE: true\n",
        encoding="utf-8",
    )


class StateInitCommandTests(unittest.TestCase):
    def test_dry_run_prints_plan_and_writes_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tz_file(root)

            result = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Dry Run",
                "--project-slug",
                "dry-run",
                "--tz",
                "project-input/TZ.md",
                "--dry-run",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            plan = json.loads(result.stdout)
            self.assertTrue(plan["dry_run"])
            self.assertEqual(plan["status"], "planned")
            self.assertEqual(len(plan["writes"]), 22)
            self.assertFalse((root / "project-runtime").exists())

    def test_confirm_write_without_real_tz_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Missing TZ",
                "--project-slug",
                "missing-tz",
                "--confirm-write",
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("--tz is required when project-input/TZ.md is absent", result.stderr)
            self.assertFalse((root / "project-runtime").exists())

    def test_placeholder_tz_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_placeholder_tz_file(root)

            result = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Placeholder TZ",
                "--project-slug",
                "placeholder-tz",
                "--tz",
                "project-input/TZ.md",
                "--confirm-write",
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("placeholder TZ document", result.stderr)
            self.assertFalse((root / "project-runtime").exists())

    def test_dry_run_json_out_writes_valid_plan_without_target_state_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz_file(root)
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
                "--tz",
                "project-input/TZ.md",
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
                "--tz",
                "project-input/TZ.md",
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
            self.assertEqual(tz_file.read_text(encoding="utf-8"), "Europe/Moscow\n")
            self.assertEqual(next_action["content"]["action_semantic"], "normal")
            self.assertNotEqual(next_action["content"]["action_type"], "stop")
            sidecars = sorted((root / "project-runtime" / "state").glob("*.json"))
            self.assertEqual(len(sidecars), 9)
            for name in (
                "PROJECT_STATE.md",
                "TASK_REGISTRY.md",
                "NEXT_ACTION.md",
                "CURRENT_GATE.md",
                "WORKSPACE_IDENTITY.md",
                "REPOSITORY_LOCK.md",
                "ACCEPTED_ARTIFACTS.md",
                "CHECKPOINT_STATE.md",
                "SCHEMA_MANIFEST.md",
                "GAP_REGISTER.md",
                "AGENT_RESULTS_LOG.md",
                "ORCHESTRATOR_EVENTS_LOG.md",
                "STATUS_SUMMARY.md",
            ):
                self.assertTrue((root / "project-runtime" / name).is_file(), name)
            for path in sidecars:
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["schema_version"], "3.2.0")
                self.assertEqual(payload["runtime_schema_version"], "3.2.0")
                self.assertRegex(payload["updated_at"], RFC3339_UTC_PATTERN)

    def test_deterministic_timestamps_flag_uses_regression_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tz_file(root)

            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Deterministic Init",
                "--project-slug",
                "deterministic-init",
                "--tz",
                "project-input/TZ.md",
                "--confirm-write",
                "--deterministic-timestamps",
            )

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            state_root = root / "project-runtime" / "state"
            for path in state_root.glob("*.json"):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["updated_at"], DETERMINISTIC_TIMESTAMP)
            workspace_identity = json.loads((state_root / "WORKSPACE_IDENTITY.json").read_text(encoding="utf-8"))
            repository_lock = json.loads((state_root / "REPOSITORY_LOCK.json").read_text(encoding="utf-8"))
            self.assertEqual(workspace_identity["content"]["validated_at"], DETERMINISTIC_TIMESTAMP)
            self.assertEqual(repository_lock["content"]["created_at"], DETERMINISTIC_TIMESTAMP)

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
            write_tz_file(root)
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
                "--tz",
                "project-input/TZ.md",
                "--confirm-write",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            receipt = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertFalse(receipt["dry_run"])
            self.assertEqual(receipt["status"], "written")
            self.assertEqual(
                receipt["write_result"],
                "existing TZ document preserved; wrote state sidecars; materialized compatibility views",
            )
            self.assertEqual(receipt["materialization"]["sidecar_views_written"], 9)
            self.assertEqual(receipt["materialization"]["legacy_views_written"], 4)
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

    def test_confirm_write_with_explicit_canonical_tz_preserves_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_tz_file(root)

            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Canonical TZ",
                "--project-slug",
                "canonical-tz",
                "--tz",
                "project-input/TZ.md",
                "--confirm-write",
            )
            render = run_aso("state", "render", "--root", str(root), "--confirm-write")
            verify = run_aso("state", "verify", "--root", str(root), "--strict")

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            project_state = json.loads(
                (root / "project-runtime" / "state" / "PROJECT_STATE.json").read_text(encoding="utf-8")
            )
            self.assertEqual(project_state["content"]["tz_path"], "project-input/TZ.md")
            self.assertIn(
                "TZ_PATH: project-input/TZ.md",
                (root / "project-runtime" / "PROJECT_STATE.md").read_text(encoding="utf-8"),
            )
            self.assertEqual((root / "project-input" / "TZ.md").read_text(encoding="utf-8"), "Europe/Moscow\n")

    def test_confirm_write_with_owner_noncanonical_tz_copies_to_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owner_tz = root / "project-input" / "TZ_REAL_E2E_TELEGRAM_BOT.md"
            owner_tz.parent.mkdir(parents=True, exist_ok=True)
            owner_tz.write_text("# TZ\n\nBuild a Telegram bot.\n", encoding="utf-8")

            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Owner TZ",
                "--project-slug",
                "owner-tz",
                "--tz",
                "project-input/TZ_REAL_E2E_TELEGRAM_BOT.md",
                "--confirm-write",
            )
            render = run_aso("state", "render", "--root", str(root), "--confirm-write")
            verify = run_aso("state", "verify", "--root", str(root), "--strict")

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            receipt = json.loads(init.stdout)
            self.assertIn("copied project-input/TZ_REAL_E2E_TELEGRAM_BOT.md to project-input/TZ.md", receipt["write_result"])
            self.assertEqual(
                (root / "project-input" / "TZ.md").read_text(encoding="utf-8"),
                "# TZ\n\nBuild a Telegram bot.\n",
            )
            project_state = json.loads(
                (root / "project-runtime" / "state" / "PROJECT_STATE.json").read_text(encoding="utf-8")
            )
            self.assertEqual(project_state["content"]["tz_path"], "project-input/TZ.md")
            self.assertIn(
                "TZ_PATH: project-input/TZ.md",
                (root / "project-runtime" / "PROJECT_STATE.md").read_text(encoding="utf-8"),
            )

    def test_package_root_is_refused(self) -> None:
        result = run_aso("state", "init", "--root", str(REPO_ROOT), "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to initialize the ASO package root", result.stderr)


if __name__ == "__main__":
    unittest.main()
