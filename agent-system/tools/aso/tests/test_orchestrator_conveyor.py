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
        self.assertIn("agent-system/02_runtime/ORCHESTRATOR_CONVEYOR_PROTOCOL.md", report["context_budget"]["normal_flow_docs"])

    def test_orchestrator_next_can_write_guarded_report(self) -> None:
        out = self.root / "project-runtime" / "reports" / "next.json"

        code, stdout, stderr = self._run(
            ["orchestrator", "next", "--root", str(self.root), "--json-out", str(out)]
        )

        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, "")
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["target_role"], "developer")


if __name__ == "__main__":
    unittest.main()
