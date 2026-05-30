from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ASO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "state"
if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool.aso import main  # noqa: E402


class OrchestratorConveyorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="aso-orchestrator-"))
        self.root = self.tmpdir / "workspace"
        state = self.root / "project-runtime" / "state"
        state.mkdir(parents=True)
        (state / "PROJECT_STATE.json").write_text(
            json.dumps({"content": {"current_phase": "implementation", "project_status": "active"}}),
            encoding="utf-8",
        )
        (state / "CURRENT_GATE.json").write_text(
            json.dumps({"content": {"gate_type": "implementation", "gate_status": "open"}}),
            encoding="utf-8",
        )
        (state / "NEXT_ACTION.json").write_text(
            json.dumps({"content": {"action_type": "create_agent", "target_role": "developer", "task_id": "TASK_001"}}),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_orchestrator_status_reads_json_sidecars(self) -> None:
        code, stdout, stderr = self._run(
            ["orchestrator", "status", "--root", str(self.root), "--format", "json"]
        )

        self.assertEqual(code, 0, stderr)
        report = json.loads(stdout)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["mutations_performed"])
        self.assertEqual(report["summary"]["current_phase"], "implementation")
        self.assertIn("agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json", report["context_budget"]["normal_flow_docs"])

    def test_orchestrator_next_can_write_guarded_report(self) -> None:
        out = self.root / "project-runtime" / "reports" / "next.json"

        code, stdout, stderr = self._run(
            ["orchestrator", "next", "--root", str(self.root), "--json-out", str(out)]
        )

        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, "")
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["target_role"], "developer")
        self.assertFalse(report["dispatchable"])
        self.assertFalse(report["dispatchability"]["dispatchable"])
        self.assertFalse(report["dispatchability"]["live_dispatch_performed"])

    def test_orchestrator_next_surfaces_blocked_dispatchability_reasons(self) -> None:
        root = self.tmpdir / "blocked-workspace"
        shutil.copytree(FIXTURE_ROOT / "p2_valid_workspace", root)
        out = root / "project-runtime" / "reports" / "next.json"

        code, stdout, stderr = self._run(
            ["orchestrator", "next", "--root", str(root), "--json-out", str(out)]
        )

        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, "")
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(report["read_only"])
        self.assertFalse(report["mutations_performed"])
        self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
        self.assertNotEqual(report["recommended_next_action"], "CREATE_AGENT")
        self.assertFalse(report["dispatchable"])
        self.assertFalse(report["dispatchability"]["dispatchable"])
        self.assertFalse(report["dispatchability"]["live_dispatch_performed"])
        reason_codes = {reason["reason_code"] for reason in report["dispatchability"]["reasons"]}
        self.assertTrue(
            {
                "action_type_not_dispatch_capable",
                "target_role_not_profile_execution",
                "target_role_control_or_pseudo",
                "task_id_none",
                "task_packet_none",
            }.issubset(reason_codes)
        )
        self.assertEqual(set(report["summary"]["dispatchability_reason_codes"]), reason_codes)

    def test_orchestrator_status_summarizes_blocked_next_route(self) -> None:
        root = self.tmpdir / "blocked-status-workspace"
        shutil.copytree(FIXTURE_ROOT / "p2_valid_workspace", root)

        code, stdout, stderr = self._run(
            ["orchestrator", "status", "--root", str(root), "--format", "json"]
        )

        self.assertEqual(code, 0, stderr)
        report = json.loads(stdout)
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["read_only"])
        self.assertFalse(report["mutations_performed"])
        self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
        self.assertFalse(report["dispatchable"])
        self.assertFalse(report["next_route"]["dispatchable"])
        self.assertFalse(report["next_route"]["live_dispatch_performed"])
        self.assertIn("task_packet_none", report["summary"]["next_dispatchability_reason_codes"])

    def test_orchestrator_next_preserves_valid_dispatchable_plan_next_verdict(self) -> None:
        root = self.tmpdir / "valid-workspace"
        shutil.copytree(FIXTURE_ROOT / "valid_workspace", root)

        code, stdout, stderr = self._run(
            ["orchestrator", "next", "--root", str(root), "--format", "json"]
        )

        self.assertEqual(code, 0, stderr)
        report = json.loads(stdout)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["mutations_performed"])
        self.assertEqual(report["recommended_next_action"], "CREATE_AGENT")
        self.assertTrue(report["dispatchable"])
        self.assertTrue(report["dispatchability"]["dispatchable"])
        self.assertEqual(report["dispatchability"]["verdict"], "dispatchable")
        self.assertEqual(report["dispatchability"]["reasons"], [])
        self.assertFalse(report["dispatchability"]["live_dispatch_performed"])


if __name__ == "__main__":
    unittest.main()
