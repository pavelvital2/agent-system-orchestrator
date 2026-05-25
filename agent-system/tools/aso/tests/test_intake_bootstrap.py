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


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def write_tz(root: Path, relpath: str = "project-input/TZ_REAL.md") -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# TZ\n\nBuild a governed test app.\n", encoding="utf-8")
    return path


def write_placeholder_tz(root: Path, relpath: str = "project-input/TZ.md") -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# TZ Placeholder\n\nSTATUS: placeholder\nMUST_REPLACE_BEFORE_LIFECYCLE: true\n",
        encoding="utf-8",
    )
    return path


def state_init(root: Path, tz_path: str = "project-input/TZ_REAL.md") -> subprocess.CompletedProcess[str]:
    return run_aso(
        "state",
        "init",
        "--root",
        str(root),
        "--tz",
        tz_path,
        "--confirm-write",
        "--deterministic-timestamps",
    )


def assert_bootstrap_views_synced(testcase: unittest.TestCase, root: Path) -> None:
    state_root = root / "project-runtime" / "state"
    next_action = json.loads((state_root / "NEXT_ACTION.json").read_text(encoding="utf-8"))
    current_gate = json.loads((state_root / "CURRENT_GATE.json").read_text(encoding="utf-8"))
    registry = json.loads((state_root / "TASK_REGISTRY.json").read_text(encoding="utf-8"))

    next_content = next_action["content"]
    gate_content = current_gate["content"]
    task = registry["content"]["tasks"][0]
    task_id = next_content["task_id"]
    target_role = next_content["target_role"]

    testcase.assertEqual(gate_content["task_id"], task_id)
    testcase.assertEqual(gate_content["required_next_role"], target_role)
    testcase.assertEqual(task["task_id"], task_id)
    testcase.assertEqual(task["owner_role"], target_role)

    for view_name in ("PROJECT_STATE.md", "NEXT_ACTION.md", "CURRENT_GATE.md", "TASK_REGISTRY.md"):
        view = root / "project-runtime" / view_name
        testcase.assertTrue(view.is_file(), view_name)
        text = view.read_text(encoding="utf-8")
        testcase.assertIn("DERIVED VIEW.", text)
        testcase.assertIn(f"Source: project-runtime/state/{view_name.removesuffix('.md')}.json", text)

    next_view = (root / "project-runtime" / "NEXT_ACTION.md").read_text(encoding="utf-8")
    gate_view = (root / "project-runtime" / "CURRENT_GATE.md").read_text(encoding="utf-8")
    registry_view = (root / "project-runtime" / "TASK_REGISTRY.md").read_text(encoding="utf-8")
    testcase.assertIn(f"TASK_ID: {task_id}", next_view)
    testcase.assertIn(f"TARGET_ROLE: {target_role}", next_view)
    testcase.assertIn(f"TASK_ID: {task_id}", gate_view)
    testcase.assertIn(f"REQUIRED_NEXT_ROLE: {target_role}", gate_view)
    testcase.assertIn(f"TASK_ID: {task_id}", registry_view)
    testcase.assertIn(f"OWNER_ROLE: {target_role}", registry_view)


class IntakeBootstrapCommandTests(unittest.TestCase):
    def test_bootstrap_creates_dispatchable_requirements_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz(root)
            receipt_path = Path(tmp) / "intake.json"
            plan_path = Path(tmp) / "plan-next.json"

            init = state_init(root)
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
                "--json-out",
                str(receipt_path),
            )
            verify = run_aso("state", "verify", "--root", str(root), "--strict")
            plan = run_aso("plan-next", "--root", str(root), "--strict", "--json-out", str(plan_path))

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            self.assertEqual(intake.returncode, 0, intake.stdout + intake.stderr)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "created")
            self.assertTrue(receipt["mutations_performed"])
            self.assertEqual(receipt["target_role"], "requirements_analyst")
            self.assertEqual(receipt["tz_path"], "project-input/TZ.md")
            packet = root / "project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md"
            self.assertTrue(packet.is_file())
            packet_text = packet.read_text(encoding="utf-8")
            self.assertIn("Do not implement product logic", packet_text)
            self.assertIn("project-input/TZ.md", packet_text)
            self.assertIn("TASK_COMPLEXITY: xhigh", packet_text)
            self.assertIn("REASONING_LEVEL_REQUIRED: xhigh", packet_text)
            self.assertIn("AGENT_LIFECYCLE_POLICY: one_agent_one_task_delete_after_result", packet_text)
            self.assertIn("RESULT_CONTRACT: agent-system/03_templates/AGENT_RESULT_TEMPLATE.md", packet_text)
            self.assertIn("EVIDENCE_REQUIREMENTS: dispatch receipt", packet_text)
            self.assertIn("EXPECTED_ARTIFACT_PACKAGE: project-runtime/artifacts/candidates/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001/manifest.json", packet_text)
            self.assertIn(
                "project-runtime/artifacts/candidates/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001/manifest.json",
                packet_text,
            )
            self.assertIn(
                "project-runtime/artifacts/candidates/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001/**",
                packet_text,
            )
            self.assertIn("project-runtime/results/** only as secondary/compatibility evidence", packet_text)
            self.assertIn("Do not write accepted artifacts directly", packet_text)
            self.assertIn("Audit and acceptance happen after candidate artifact creation", packet_text)
            registry = json.loads((root / "project-runtime/state/TASK_REGISTRY.json").read_text(encoding="utf-8"))
            self.assertEqual(len(registry["content"]["tasks"]), 1)
            self.assertEqual(registry["content"]["tasks"][0]["created_at"], DETERMINISTIC_TIMESTAMP)
            self.assertEqual(registry["content"]["tasks"][0]["updated_at"], DETERMINISTIC_TIMESTAMP)
            assert_bootstrap_views_synced(self, root)
            plan_report = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CREATE_AGENT")
            self.assertTrue(plan_report["dispatchable"])
            self.assertEqual(plan_report["target_role"], "requirements_analyst")
            self.assertEqual(plan_report["resolved_reasoning_level"], "xhigh")
            self.assertEqual(plan_report["reasoning_source"], "task_packet.REASONING_LEVEL_REQUIRED")
            self.assertTrue(plan_report["dispatch_receipt"]["required"])

    def test_bootstrap_is_idempotent_for_same_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz(root)
            self.assertEqual(state_init(root).returncode, 0)

            first = run_aso(
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
            second = run_aso(
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

            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(json.loads(second.stdout)["status"], "already_exists")
            registry = json.loads((root / "project-runtime/state/TASK_REGISTRY.json").read_text(encoding="utf-8"))
            self.assertEqual(len(registry["content"]["tasks"]), 1)

    def test_without_confirm_write_preserves_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz(root)
            self.assertEqual(state_init(root).returncode, 0)
            state_root = root / "project-runtime/state"
            before = {path.name: path.read_text(encoding="utf-8") for path in state_root.glob("*.json")}

            result = run_aso(
                "intake",
                "bootstrap",
                "--root",
                str(root),
                "--tz",
                "project-input/TZ_REAL.md",
                "--target-role",
                "requirements_analyst",
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "blocked")
            self.assertFalse((root / "project-runtime/bootstrap").exists())
            after = {path.name: path.read_text(encoding="utf-8") for path in state_root.glob("*.json")}
            self.assertEqual(before, after)

    def test_bootstrap_preserves_existing_canonical_tz_and_materialized_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            canonical = write_tz(root, "project-input/TZ.md")
            canonical.write_text("# TZ\n\nCanonical request.\n", encoding="utf-8")
            owner_tz = write_tz(root, "project-input/TZ_REAL.md")
            self.assertEqual(state_init(root, "project-input/TZ.md").returncode, 0)
            render = run_aso("state", "render", "--root", str(root), "--confirm-write")
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)

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

            self.assertEqual(intake.returncode, 0, intake.stdout + intake.stderr)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            receipt = json.loads(intake.stdout)
            self.assertEqual(receipt["tz_path"], "project-input/TZ.md")
            self.assertEqual(canonical.read_text(encoding="utf-8"), "# TZ\n\nCanonical request.\n")
            self.assertEqual(owner_tz.read_text(encoding="utf-8"), "# TZ\n\nBuild a governed test app.\n")
            project_state = json.loads(
                (root / "project-runtime" / "state" / "PROJECT_STATE.json").read_text(encoding="utf-8")
            )
            self.assertEqual(project_state["content"]["tz_path"], "project-input/TZ.md")
            self.assertIn(
                "TZ_PATH: project-input/TZ.md",
                (root / "project-runtime" / "PROJECT_STATE.md").read_text(encoding="utf-8"),
            )

    def test_tz_outside_workspace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            tz_path = Path(tmp) / "outside.md"
            tz_path.write_text("# TZ\n", encoding="utf-8")
            write_tz(root)
            self.assertEqual(state_init(root).returncode, 0)

            result = run_aso(
                "intake",
                "bootstrap",
                "--root",
                str(root),
                "--tz",
                str(tz_path),
                "--target-role",
                "requirements_analyst",
                "--confirm-write",
                "--deterministic-timestamps",
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("workspace-local", result.stderr)

    def test_placeholder_tz_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz(root)
            self.assertEqual(state_init(root).returncode, 0)
            write_placeholder_tz(root)

            result = run_aso(
                "intake",
                "bootstrap",
                "--root",
                str(root),
                "--tz",
                "project-input/TZ.md",
                "--target-role",
                "requirements_analyst",
                "--confirm-write",
                "--deterministic-timestamps",
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("placeholder TZ document", result.stderr)
            self.assertFalse((root / "project-runtime/bootstrap").exists())


if __name__ == "__main__":
    unittest.main()
