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


def run_plan_next(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "plan-next", "--root", str(root), *extra],
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
    value = payload["content"]
    if not isinstance(value, dict):
        raise AssertionError("sidecar content must be a dictionary")
    return value


def update_markdown_field(root: Path, filename: str, field: str, value: str) -> None:
    path = root / "project-runtime" / filename
    lines = path.read_text(encoding="utf-8").splitlines()
    prefix = f"{field}:"
    updated = False
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{field}: {value}"
            updated = True
            break
    if not updated:
        lines.append(f"{field}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_next_action(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "NEXT_ACTION.json")
    body = content(payload)
    body.update(updates)
    write_sidecar(root, "NEXT_ACTION.json", payload)
    markdown_fields = {
        "action_type": "ACTION_TYPE",
        "target_role": "TARGET_ROLE",
        "task_id": "TASK_ID",
        "dependency_status": "DEPENDENCY_STATUS",
        "action_semantic": "ACTION_SEMANTIC",
        "checkpoint_policy": "CHECKPOINT_POLICY",
    }
    for key, field in markdown_fields.items():
        if key in updates and isinstance(updates[key], str):
            update_markdown_field(root, "NEXT_ACTION.md", field, str(updates[key]))


def set_project_state(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "PROJECT_STATE.json")
    body = content(payload)
    body.update(updates)
    write_sidecar(root, "PROJECT_STATE.json", payload)
    markdown_fields = {
        "current_phase": "CURRENT_PHASE",
        "project_status": "PROJECT_STATUS",
        "identity_validation_status": "IDENTITY_VALIDATION_STATUS",
        "repository_lock_status": "REPOSITORY_LOCK_STATUS",
        "checkpoint_eligibility": "CHECKPOINT_ELIGIBILITY",
    }
    for key, field in markdown_fields.items():
        if key in updates and isinstance(updates[key], str):
            update_markdown_field(root, "PROJECT_STATE.md", field, str(updates[key]))


def set_task(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "TASK_REGISTRY.json")
    body = content(payload)
    tasks = body["tasks"]
    if not isinstance(tasks, list) or not tasks or not isinstance(tasks[0], dict):
        raise AssertionError("fixture task registry must contain one task")
    tasks[0].update(updates)
    write_sidecar(root, "TASK_REGISTRY.json", payload)
    if "status" in updates and isinstance(updates["status"], str):
        update_markdown_field(root, "TASK_REGISTRY.md", "STATUS", str(updates["status"]))
    if "checkpoint_required" in updates and isinstance(updates["checkpoint_required"], bool):
        update_markdown_field(
            root,
            "TASK_REGISTRY.md",
            "CHECKPOINT_REQUIRED",
            "true" if updates["checkpoint_required"] else "false",
        )


class PlanNextCommandTests(unittest.TestCase):
    def test_help_declares_dry_run_read_only(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "plan-next", "--help"],
            check=False,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Dry-run/read-only", result.stdout)
        self.assertIn("mutating state", result.stdout)

    def test_valid_workspace_recommends_create_agent_and_does_not_edit_state(self) -> None:
        tracked = [path for path in VALID_WORKSPACE.rglob("*") if path.is_file()]
        mtimes_before = {path: path.stat().st_mtime_ns for path in tracked}
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(VALID_WORKSPACE, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO plan-next: READY", result.stdout)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(report["dry_run"])
            self.assertTrue(report["read_only"])
            self.assertFalse(report["mutations_performed"])
            self.assertEqual(report["recommended_next_action"], "CREATE_AGENT")
            self.assertEqual(report["target_role"], "runtime_architect")
            self.assertEqual(report["task_packet"], "project-runtime/tasks/active/TASK_FIXTURE_STATE_001.md")
            self.assertEqual(report["blocking_rules"], [])
        self.assertEqual(mtimes_before, {path: path.stat().st_mtime_ns for path in tracked})

    def test_checkpoint_with_audit_pass_evidence_recommends_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            set_next_action(
                root,
                action_type="checkpoint",
                action_semantic="checkpoint",
                checkpoint_policy="after_audit_pass",
            )
            set_task(
                root,
                status="audit_passed",
                checkpoint_required=True,
                audit_refs=["project-runtime/audits/AUDIT_TASK_FIXTURE_STATE_001_PASS.md"],
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertEqual(report["blocking_rules"], [])
            self.assertTrue(report["evidence"]["audit_pass_evidence"]["present"])

    def test_checkpoint_without_audit_pass_evidence_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            set_next_action(
                root,
                action_type="checkpoint",
                action_semantic="checkpoint",
                checkpoint_policy="after_audit_pass",
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["recommended_next_action"], "CREATE_AUDITOR")
            self.assertEqual(report["target_role"], "auditor")
            rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
            self.assertIn("GOV-CHECKPOINT-AUDIT-GATE", rule_ids)
            self.assertFalse(report["evidence"]["audit_pass_evidence"]["present"])

    def test_checkpoint_completed_without_audit_refs_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            set_next_action(
                root,
                action_type="checkpoint",
                action_semantic="checkpoint",
                checkpoint_policy="after_audit_pass",
            )
            set_task(root, status="completed", checkpoint_required=True, audit_refs=[])
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["recommended_next_action"], "CREATE_AUDITOR")
            rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
            self.assertIn("GOV-CHECKPOINT-AUDIT-GATE", rule_ids)
            audit_evidence = report["evidence"]["audit_pass_evidence"]
            self.assertFalse(audit_evidence["present"])
            self.assertEqual(audit_evidence["task_status"], "completed")
            self.assertEqual(audit_evidence["task_audit_refs"], [])

    def test_none_action_recommends_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            set_next_action(
                root,
                action_type="none",
                target_role="none",
                dependency_status="not_required",
                action_semantic="none",
                checkpoint_policy="not_required",
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "NONE")
            self.assertEqual(report["blocking_rules"], [])

    def test_blocked_gap_owner_decision_recommends_ask_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            set_project_state(
                root,
                project_status="blocked",
                active_blockers=["GAP-001 owner_decision_required"],
            )
            set_next_action(
                root,
                action_type="manual",
                dependency_status="blocked",
                blocked_by=["GAP-001 owner_decision_required"],
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "ASK_OWNER")
            rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
            self.assertIn("GOV-ACTION-SEMANTICS", rule_ids)

    def test_incident_state_recommends_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            set_project_state(
                root,
                current_phase="incident_recovery",
                project_status="blocked",
                active_blockers=["incident_recovery: wrong_branch_push"],
            )
            set_next_action(
                root,
                action_type="manual",
                dependency_status="blocked",
                blocked_by=["incident_recovery: wrong_branch_push"],
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "FREEZE")
            rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
            self.assertIn("GOV-ACTION-SEMANTICS", rule_ids)


if __name__ == "__main__":
    unittest.main()
