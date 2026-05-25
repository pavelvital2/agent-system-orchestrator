from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
ASO_TOOL_ROOT = REPO_ROOT / "agent-system" / "tools" / "aso"

sys.path.insert(0, str(ASO_TOOL_ROOT))

from agent_system_orchestrator_aso.aso_tool import dispatch_receipts  # noqa: E402


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


class DispatchReceiptTests(unittest.TestCase):
    def test_dispatch_receipt_command_writes_external_runner_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()

            result = run_aso(
                "dispatch",
                "receipt",
                "--root",
                str(root),
                "--agent-instance-id",
                "agent_TASK_DEMO_001_attempt_001",
                "--task-id",
                "TASK_DEMO_001",
                "--role",
                "developer",
                "--reasoning-effort",
                "high",
                "--prompt-ref",
                "project-runtime/handoffs/TASK_DEMO_001.prompt.md",
                "--handoff-ref",
                "project-runtime/handoffs/TASK_DEMO_001.json",
                "--runner",
                "external_codex_cli",
                "--model",
                "gpt-5-codex",
                "--started-at",
                "2026-05-25T00:00:00Z",
                "--confirm-write",
                "--format",
                "json",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "written")
            self.assertTrue(report["mutations_performed"])
            self.assertFalse(report["live_dispatch_performed_by_aso"])
            receipt_path = root / "project-runtime/agents/dispatches/agent_TASK_DEMO_001_attempt_001.json"
            self.assertTrue(receipt_path.is_file())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["runner"], "external_codex_cli")
            self.assertEqual(receipt["model"], "gpt-5-codex")
            self.assertEqual(receipt["reasoning_effort"], "high")
            self.assertEqual(receipt["prompt_ref"], "project-runtime/handoffs/TASK_DEMO_001.prompt.md")
            self.assertEqual(receipt["task_id"], "TASK_DEMO_001")
            self.assertEqual(receipt["role"], "developer")
            self.assertEqual(receipt["started_at"], "2026-05-25T00:00:00Z")
            self.assertEqual(receipt["handoff_ref"], "project-runtime/handoffs/TASK_DEMO_001.json")
            self.assertEqual(
                receipt["receipt_ref"],
                "project-runtime/agents/dispatches/agent_TASK_DEMO_001_attempt_001.json",
            )
            self.assertIn("model_reasoning_effort", receipt["external_runner_command_template"])
            self.assertTrue(dispatch_receipts.validate_dispatch_receipt(receipt).passed)

    def test_reasoning_compliance_uses_receipt_not_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = dispatch_receipts.build_dispatch_receipt(
                agent_instance_id="agent_TASK_DEMO_001_attempt_001",
                task_id="TASK_DEMO_001",
                role="developer",
                runner="external_codex_cli",
                model="UNKNOWN",
                reasoning_effort="medium",
                prompt_ref="project-runtime/handoffs/TASK_DEMO_001.prompt.md",
                handoff_ref="project-runtime/handoffs/TASK_DEMO_001.json",
                started_at="2026-05-25T00:00:00Z",
            )
            path = dispatch_receipts.receipt_path(root, "agent_TASK_DEMO_001_attempt_001")
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(receipt), encoding="utf-8")

            compliance = dispatch_receipts.reasoning_compliance_from_receipt(
                root,
                "agent_TASK_DEMO_001_attempt_001",
                "high",
            )

            self.assertEqual(compliance["status"], "failed")
            self.assertIn("below required_level=high", "; ".join(compliance["errors"]))


if __name__ == "__main__":
    unittest.main()
