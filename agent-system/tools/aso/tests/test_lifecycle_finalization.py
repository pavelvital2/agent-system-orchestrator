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
TASK_ID = "TASK_FIXTURE_STATE_001"
TASK_PACKET = "project-runtime/tasks/active/TASK_FIXTURE_STATE_001.md"
AUDIT_REF = f"project-runtime/results/audit/AUDIT_RESULT_{TASK_ID}_ATTEMPT_001.md"

AUDIT_PASS_RESULT = f"""AUDIT_RESULT:
STATUS: pass
TASK_ID: {TASK_ID}
AGENT_INSTANCE_ID: audit_{TASK_ID}_attempt_001
ROLE: auditor
TASK: {TASK_ID}
SUMMARY:
Audit passed.
READ_DOCS:
- NONE
READ_INPUTS:
- NONE
CHANGED_FILES:
- NONE
CREATED_FILES:
- NONE
DELETED_FILES:
- NONE
COMMANDS_RUN:
- NONE
TESTS_RUN:
- NONE
EVIDENCE:
- SOURCE_RESULT_REF: project-runtime/results/worker/RESULT_{TASK_ID}_ATTEMPT_001.md
SCOPE_VERIFICATION:
- TASK_PACKET_SCHEMA_STATUS: passed
FORBIDDEN_CHANGES_CHECK:
- FORBIDDEN_PATH_STATUS: passed
RISKS:
- NONE
LIMITATIONS:
- NONE
BLOCKERS:
- NONE
GAPS:
- NONE
NEXT_RECOMMENDED_ACTION:
- CHECKPOINT_PREFLIGHT
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""


def run_aso(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *extra, "--root", str(root)],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def copy_valid_workspace(tmp: str) -> Path:
    root = Path(tmp) / "workspace"
    shutil.copytree(VALID_WORKSPACE, root)
    return root


def load_sidecar(root: Path, name: str) -> dict[str, object]:
    return json.loads((root / "project-runtime" / "state" / name).read_text(encoding="utf-8"))


def write_sidecar(root: Path, name: str, payload: dict[str, object]) -> None:
    (root / "project-runtime" / "state" / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def content(payload: dict[str, object]) -> dict[str, object]:
    body = payload["content"]
    if not isinstance(body, dict):
        raise AssertionError("sidecar content must be a dictionary")
    return body


def update_markdown_field(root: Path, filename: str, field: str, value: object) -> None:
    path = root / "project-runtime" / filename
    lines = path.read_text(encoding="utf-8").splitlines()
    rendered = "yes" if value is True else "no" if value is False else str(value)
    prefix = f"{field}:"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{field}: {rendered}"
            break
    else:
        lines.append(f"{field}: {rendered}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_project_state(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "PROJECT_STATE.json")
    content(payload).update(updates)
    write_sidecar(root, "PROJECT_STATE.json", payload)
    fields = {
        "tz_path": "TZ_PATH",
        "audit_status": "AUDIT_STATUS",
        "checkpoint_eligibility": "CHECKPOINT_ELIGIBILITY",
        "checkpoint_eligibility_status": "CHECKPOINT_ELIGIBILITY_STATUS",
        "checkpoint_preflight_status": "CHECKPOINT_PREFLIGHT_STATUS",
        "checkpoint_receipt_ref": "CHECKPOINT_RECEIPT_REF",
        "project_checkpoint_status": "PROJECT_CHECKPOINT_STATUS",
        "current_phase": "CURRENT_PHASE",
        "project_status": "PROJECT_STATUS",
        "action_semantic": "ACTION_SEMANTIC",
    }
    for key, field in fields.items():
        if key in updates:
            update_markdown_field(root, "PROJECT_STATE.md", field, updates[key])


def set_current_gate(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "CURRENT_GATE.json")
    content(payload).update(updates)
    write_sidecar(root, "CURRENT_GATE.json", payload)
    fields = {
        "gate_type": "GATE_TYPE",
        "status": "STATUS",
        "task_id": "TASK_ID",
        "task_packet": "TASK_PACKET",
        "action_semantic": "ACTION_SEMANTIC",
        "checkpoint_eligibility": "CHECKPOINT_ELIGIBILITY",
        "checkpoint_eligibility_status": "CHECKPOINT_ELIGIBILITY_STATUS",
        "project_checkpoint_status": "PROJECT_CHECKPOINT_STATUS",
        "required_next_role": "REQUIRED_NEXT_ROLE",
    }
    for key, field in fields.items():
        if key in updates:
            update_markdown_field(root, "CURRENT_GATE.md", field, updates[key])


def set_next_action(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "NEXT_ACTION.json")
    content(payload).update(updates)
    write_sidecar(root, "NEXT_ACTION.json", payload)
    fields = {
        "action_type": "ACTION_TYPE",
        "target_role": "TARGET_ROLE",
        "task_id": "TASK_ID",
        "task_packet": "TASK_PACKET",
        "dependency_status": "DEPENDENCY_STATUS",
        "action_semantic": "ACTION_SEMANTIC",
        "workspace_identity_required": "WORKSPACE_IDENTITY_REQUIRED",
        "repository_lock_required": "REPOSITORY_LOCK_REQUIRED",
        "checkpoint_policy": "CHECKPOINT_POLICY",
        "checkpoint_preflight_required": "CHECKPOINT_PREFLIGHT_REQUIRED",
        "checkpoint_receipt_required": "CHECKPOINT_RECEIPT_REQUIRED",
        "checkpoint_receipt_ref": "CHECKPOINT_RECEIPT_REF",
    }
    for key, field in fields.items():
        if key in updates:
            update_markdown_field(root, "NEXT_ACTION.md", field, updates[key])


def set_task(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "TASK_REGISTRY.json")
    tasks = content(payload)["tasks"]
    if not isinstance(tasks, list) or not tasks or not isinstance(tasks[0], dict):
        raise AssertionError("fixture task registry must contain one task")
    tasks[0].update(updates)
    write_sidecar(root, "TASK_REGISTRY.json", payload)


def prepare_finalizable_workspace(tmp: str) -> Path:
    root = copy_valid_workspace(tmp)
    (root / "project-input" / "TZ.md").write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
    audit_path = root / AUDIT_REF
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(AUDIT_PASS_RESULT, encoding="utf-8")
    checkpoint_ref = "project-runtime/receipts/checkpoints/CHECKPOINT_TASK_FIXTURE_STATE_001.json"
    set_project_state(
        root,
        tz_path="project-input/TZ.md",
        audit_status="passed",
        checkpoint_eligibility="local_only",
        checkpoint_eligibility_status="eligible",
        checkpoint_preflight_status="passed",
        checkpoint_receipt_ref=checkpoint_ref,
        project_checkpoint_status="passed",
        checkpoint_blocked_by=[],
        current_phase="finalization",
        project_status="active",
        action_semantic="normal",
    )
    set_current_gate(
        root,
        gate_type="finalization",
        status="passed",
        task_id=TASK_ID,
        task_packet=TASK_PACKET,
        action_semantic="normal",
        checkpoint_eligibility="local_only",
        checkpoint_eligibility_status="eligible",
        project_checkpoint_status="passed",
        required_next_role="orchestrator",
        blocking_status="NONE",
    )
    set_next_action(
        root,
        action_type="finalize",
        target_role="orchestrator",
        task_id=TASK_ID,
        task_packet=TASK_PACKET,
        dependency_status="ready",
        blocked_by=[],
        action_semantic="normal",
        workspace_identity_required=False,
        repository_lock_required=False,
        checkpoint_policy="no_checkpoint",
        checkpoint_preflight_required=False,
        checkpoint_receipt_required=False,
        checkpoint_receipt_ref=checkpoint_ref,
    )
    set_task(root, status="checkpoint_done", audit_refs=[AUDIT_REF])
    return root


class LifecycleFinalizationTests(unittest.TestCase):
    def test_finalize_confirm_write_creates_completed_state_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = prepare_finalizable_workspace(tmp)
            out = Path(tmp) / "finalize.json"

            result = run_aso(root, "lifecycle", "finalize", "--confirm-write", "--json-out", str(out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "written")
            self.assertTrue(report["mutations_performed"])
            self.assertEqual(report["terminal_state"], "PROJECT_COMPLETED")
            self.assertEqual(report["recommended_next_action"], "NO_NEXT_ACTION")
            self.assertTrue((root / report["receipt_ref"]).is_file())
            self.assertEqual(report["state_verify_after"]["status"], "passed")

            project_state = content(load_sidecar(root, "PROJECT_STATE.json"))
            current_gate = content(load_sidecar(root, "CURRENT_GATE.json"))
            next_action = content(load_sidecar(root, "NEXT_ACTION.json"))
            task = content(load_sidecar(root, "TASK_REGISTRY.json"))["tasks"][0]
            self.assertEqual(project_state["current_phase"], "completed")
            self.assertEqual(project_state["project_status"], "completed")
            self.assertEqual(current_gate["gate_type"], "terminal")
            self.assertEqual(current_gate["status"], "passed")
            self.assertEqual(next_action["action_type"], "stop")
            self.assertEqual(next_action["target_role"], "none")
            self.assertEqual(next_action["action_semantic"], "stop_terminal")
            self.assertEqual(task["status"], "completed")

    def test_finalize_is_idempotent_after_project_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = prepare_finalizable_workspace(tmp)
            first = run_aso(root, "lifecycle", "finalize", "--confirm-write")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            receipt_path = root / "project-runtime/receipts/lifecycle/PROJECT_FINALIZATION_RECEIPT.json"
            state_path = root / "project-runtime/state/PROJECT_STATE.json"
            first_receipt = receipt_path.read_text(encoding="utf-8")
            first_state = state_path.read_text(encoding="utf-8")

            second = run_aso(root, "lifecycle", "finalize", "--confirm-write")

            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            report = json.loads(second.stdout)
            self.assertEqual(report["status"], "already_finalized")
            self.assertFalse(report["mutations_performed"])
            self.assertEqual(receipt_path.read_text(encoding="utf-8"), first_receipt)
            self.assertEqual(state_path.read_text(encoding="utf-8"), first_state)

    def test_finalize_and_state_verify_reject_unresolved_completion_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = prepare_finalizable_workspace(tmp)
            set_project_state(root, checkpoint_blocked_by=["CHECKPOINT-BLOCKER-001"])
            set_task(root, status="blocked")

            result = run_aso(root, "lifecycle", "finalize", "--confirm-write")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            rule_ids = {finding["rule_id"] for finding in report["findings"]}
            self.assertIn("LIFECYCLE_FINALIZE_UNRESOLVED_TASKS", rule_ids)
            self.assertIn("LIFECYCLE_FINALIZE_STALE_BLOCKERS", rule_ids)
            self.assertFalse((root / "project-runtime/receipts/lifecycle/PROJECT_FINALIZATION_RECEIPT.json").exists())

            set_project_state(root, current_phase="completed", project_status="completed", audit_status="passed")
            set_current_gate(root, gate_type="terminal", status="passed", action_semantic="stop_terminal", required_next_role="none")
            set_next_action(root, action_type="stop", target_role="none", action_semantic="stop_terminal", dependency_status="completed")
            verify = run_aso(root, "state", "verify", "--strict")

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            self.assertIn("PROJECT_COMPLETED_UNRESOLVED_TASKS", verify.stdout)
            self.assertIn("PROJECT_COMPLETED_STALE_BLOCKERS", verify.stdout)

    def test_plan_next_after_finalize_returns_no_next_action_terminal_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = prepare_finalizable_workspace(tmp)
            finalize = run_aso(root, "lifecycle", "finalize", "--confirm-write")
            self.assertEqual(finalize.returncode, 0, finalize.stdout + finalize.stderr)
            out = Path(tmp) / "plan-next.json"

            result = run_aso(root, "plan-next", "--strict", "--json-out", str(out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "NO_NEXT_ACTION")
            self.assertEqual(report["route_status"], "ready")
            self.assertFalse(report["dispatchable"])
            self.assertEqual(report["target_role"], "none")
            self.assertEqual(report["task_id"], "NONE")
            self.assertNotIn(report["recommended_next_action"], {"CHECKPOINT_PREFLIGHT", "CREATE_AGENT", "CREATE_AUDITOR", "CORRECTION_REQUIRED", "ACCEPT_ARTIFACT"})
            self.assertEqual(report["evidence"]["transition_engine"]["current_state"], "PROJECT_COMPLETED")


if __name__ == "__main__":
    unittest.main()
