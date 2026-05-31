from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]

SIDECAR_VIEWS = (
    "PROJECT_STATE.md",
    "TASK_REGISTRY.md",
    "NEXT_ACTION.md",
    "CURRENT_GATE.md",
    "WORKSPACE_IDENTITY.md",
    "REPOSITORY_LOCK.md",
    "ACCEPTED_ARTIFACTS.md",
    "CHECKPOINT_STATE.md",
    "SCHEMA_MANIFEST.md",
)
LEGACY_COMPATIBILITY_VIEWS = (
    "GAP_REGISTER.md",
    "AGENT_RESULTS_LOG.md",
    "ORCHESTRATOR_EVENTS_LOG.md",
    "STATUS_SUMMARY.md",
)


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def write_tz(root: Path, name: str = "TZ_REAL.md") -> None:
    path = root / "project-input" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# TZ\n\nBuild a governed bootstrap fixture.\n", encoding="utf-8")


def state_init(root: Path) -> subprocess.CompletedProcess[str]:
    return run_aso(
        "state",
        "init",
        "--root",
        str(root),
        "--project-name",
        "Bootstrap Materialization",
        "--project-slug",
        "bootstrap-materialization",
        "--tz",
        "project-input/TZ_REAL.md",
        "--confirm-write",
        "--deterministic-timestamps",
    )


def assert_materialized_views(testcase: unittest.TestCase, root: Path) -> None:
    for name in SIDECAR_VIEWS:
        path = root / "project-runtime" / name
        testcase.assertTrue(path.is_file(), name)
        text = path.read_text(encoding="utf-8")
        testcase.assertTrue(text.startswith("DERIVED VIEW.\n"), name)
        testcase.assertIn(f"Source: project-runtime/state/{name.removesuffix('.md')}.json", text)

    for name in LEGACY_COMPATIBILITY_VIEWS:
        path = root / "project-runtime" / name
        testcase.assertTrue(path.is_file(), name)
        text = path.read_text(encoding="utf-8")
        testcase.assertTrue(text.startswith("DERIVED COMPATIBILITY VIEW.\n"), name)
        testcase.assertIn("Canonical state is JSON sidecar", text)


class BootstrapMaterializationTests(unittest.TestCase):
    def test_state_init_materializes_required_bootstrap_views_and_validators_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz(root)

            init = state_init(root)
            verify = run_aso("state", "verify", "--root", str(root), "--strict")
            lint = run_aso("lint", "--root", str(root), "--mode", "workspace", "--strict")
            status = run_aso("status", "--root", str(root), "--mode", "workspace")
            doctor = run_aso("doctor", "--root", str(root), "--mode", "workspace", "--strict")

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            receipt = json.loads(init.stdout)
            self.assertEqual(receipt["materialization"]["sidecar_views_written"], 9)
            self.assertEqual(receipt["materialization"]["legacy_views_written"], 4)
            assert_materialized_views(self, root)
            self.assertIn(
                "NEXT_ACTION: correction",
                (root / "project-runtime" / "STATUS_SUMMARY.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)
            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)

    def test_intake_bootstrap_rematerializes_views_and_keeps_dispatchable_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz(root)
            init = state_init(root)
            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            for path in (root / "project-runtime").glob("*.md"):
                path.unlink()
            plan_path = Path(tmp) / "plan-next.json"

            intake = run_aso(
                "intake",
                "bootstrap",
                "--root",
                str(root),
                "--tz",
                "project-input/TZ_REAL.md",
                "--target-role",
                "requirements_analyst",
                "--confirm-write",
                "--deterministic-timestamps",
            )
            verify = run_aso("state", "verify", "--root", str(root), "--strict")
            plan = run_aso("plan-next", "--root", str(root), "--strict", "--json-out", str(plan_path))

            self.assertEqual(intake.returncode, 0, intake.stdout + intake.stderr)
            self.assertEqual(json.loads(intake.stdout)["status"], "created")
            assert_materialized_views(self, root)
            self.assertTrue((root / "project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md").is_file())
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CREATE_AGENT")
            self.assertTrue(plan_report["dispatchable"])

    def test_legacy_compatibility_views_are_not_strict_startup_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz(root)
            init = state_init(root)
            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            for name in LEGACY_COMPATIBILITY_VIEWS:
                (root / "project-runtime" / name).unlink()

            verify = run_aso("state", "verify", "--root", str(root), "--strict")
            lint = run_aso("lint", "--root", str(root), "--mode", "workspace", "--strict")
            status = run_aso("status", "--root", str(root), "--mode", "workspace")

            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)
            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)

    def test_generated_project_has_no_fake_tz_runtime_state_or_package_root_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "generated"

            create = run_aso(
                "project",
                "create",
                "--local",
                "--engine-mode",
                "vendored",
                "--target",
                str(target),
                "--name",
                "Generated Clean",
                "--slug",
                "generated-clean",
                "--repo-url",
                "none",
            )
            verify_clean = run_aso("project", "verify-clean", "--root", str(target), "--strict")

            self.assertEqual(create.returncode, 0, create.stdout + create.stderr)
            self.assertEqual(verify_clean.returncode, 0, verify_clean.stdout + verify_clean.stderr)
            self.assertTrue((target / "project-input" / "README.md").is_file())
            self.assertFalse((target / "project-input" / "TZ.md").exists())
            self.assertFalse((target / "project-runtime" / "state").exists())
            self.assertFalse((target / "project-runtime" / "PROJECT_STATE.md").exists())
            self.assertFalse((target / "agent_system_orchestrator_aso").exists())
            self.assertFalse((target / "agent-system" / "project-runtime").exists())
            self.assertFalse((target / "agent-system" / "tools" / "aso" / "agent_system_orchestrator_aso" / "resources" / "agent-system").exists())
            for forbidden in ("site-packages", ".venv", "__pycache__", ".pytest_cache", ".tox", "dist", "build"):
                self.assertFalse(any(target.rglob(forbidden)), forbidden)


if __name__ == "__main__":
    unittest.main()
