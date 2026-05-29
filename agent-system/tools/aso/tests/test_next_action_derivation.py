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
P2_VALID_WORKSPACE = FIXTURE_ROOT / "p2_valid_workspace"
TASK_ID = "TASK_NEXT_ACTION_DERIVED_001"
TASK_PACKET = f"project-runtime/tasks/active/{TASK_ID}.md"
RESULT_REF = f"project-runtime/results/worker/RESULT_{TASK_ID}_ATTEMPT_001.md"
AUDIT_RESULT_REF = f"project-runtime/results/audit/AUDIT_RESULT_{TASK_ID}_ATTEMPT_001.md"


def run_aso(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *extra, "--root", str(root)],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def copy_workspace(tmp: str) -> Path:
    root = Path(tmp) / "workspace"
    shutil.copytree(P2_VALID_WORKSPACE, root)
    return root


def load_sidecar(root: Path, name: str) -> dict[str, object]:
    return json.loads((root / "project-runtime" / "state" / name).read_text(encoding="utf-8"))


def write_sidecar(root: Path, name: str, payload: dict[str, object]) -> None:
    (root / "project-runtime" / "state" / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def fixture_task(status: str = "ready") -> dict[str, object]:
    return {
        "accepted_files": [],
        "audit_refs": [],
        "branch": "NONE",
        "checkpoint_ref": "NONE",
        "commit_hash": "NONE",
        "correction_links": [],
        "created_at": "2026-05-21T00:00:00Z",
        "dependencies": [],
        "owner_role": "developer",
        "push_status": "not_required",
        "requested_by_role": "NONE",
        "requested_by_task": "NONE",
        "research_question_id": "NONE",
        "result_refs": [],
        "return_task_after_audit_pass": "NONE",
        "return_to_requester_after_audit_pass": False,
        "return_to_role_after_audit_pass": "none",
        "status": status,
        "task_id": TASK_ID,
        "task_kind": "normal",
        "task_packet": TASK_PACKET,
        "task_title": "Next action derivation fixture task",
        "task_type": "developer",
        "updated_at": "2026-05-21T00:00:00Z",
    }


def fixture_task_for(task_id: str, task_packet: str, status: str) -> dict[str, object]:
    task = fixture_task(status)
    task.update(
        {
            "task_id": task_id,
            "task_packet": task_packet,
            "task_title": f"Next action derivation fixture task {task_id}",
        }
    )
    return task


def write_task_packet(root: Path) -> None:
    path = root / TASK_PACKET
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# TASK PACKET",
                "",
                f"TASK_ID: {TASK_ID}",
                "TASK_KIND: normal",
                "TASK_TYPE: developer",
                "TARGET_ROLE: developer",
                "TASK_COMPLEXITY: high",
                "REASONING_LEVEL_REQUIRED: high",
                "AGENT_LIFECYCLE_POLICY: one_agent_one_task_delete_after_result",
                "RESULT_CONTRACT: Write RESULT.",
                "EVIDENCE_REQUIREMENTS: State derivation fixture.",
                "EXPECTED_ARTIFACT_PACKAGE: manifest.json",
                "",
            ]
        ),
        encoding="utf-8",
    )


def configure_active_task(root: Path, *, task_status: str = "ready") -> None:
    write_task_packet(root)

    registry = load_sidecar(root, "TASK_REGISTRY.json")
    registry_content = registry["content"]
    assert isinstance(registry_content, dict)
    registry_content["tasks"] = [fixture_task(task_status)]
    write_sidecar(root, "TASK_REGISTRY.json", registry)

    project_state = load_sidecar(root, "PROJECT_STATE.json")
    project_content = project_state["content"]
    assert isinstance(project_content, dict)
    project_content.update(
        {
            "current_phase": "implementation",
            "project_status": "active",
            "identity_validation_status": "passed",
            "repository_lock_status": "accepted",
            "baseline_tracking_status": "passed",
            "checkpoint_eligibility": "not_applicable",
            "checkpoint_eligibility_status": "not_checked",
            "audit_status": "pending",
            "project_checkpoint_status": "not_required",
            "checkpoint_blocked_by": [],
            "active_blockers": [],
            "active_gaps": [],
            "active_branches": [
                {
                    "branch_id": "BRANCH-next-action-derived",
                    "status": "active",
                    "current_task": TASK_ID,
                    "current_agent_role": "developer",
                    "dependencies": [],
                    "blocked_by": "",
                }
            ],
        }
    )
    write_sidecar(root, "PROJECT_STATE.json", project_state)

    current_gate = load_sidecar(root, "CURRENT_GATE.json")
    gate_content = current_gate["content"]
    assert isinstance(gate_content, dict)
    gate_content.update(
        {
            "gate_id": "GATE-NEXT-ACTION-DERIVED",
            "gate_name": "Next action derivation fixture",
            "gate_type": "implementation",
            "status": "open",
            "owner_role": "orchestrator",
            "task_id": TASK_ID,
            "task_packet": TASK_PACKET,
            "action_semantic": "normal",
            "workspace_identity_status": "passed",
            "repository_lock_status": "accepted",
            "baseline_tracking_status": "passed",
            "checkpoint_eligibility": "not_applicable",
            "checkpoint_eligibility_status": "not_checked",
            "project_checkpoint_status": "not_required",
            "required_next_role": "developer",
            "gate_evidence": [],
            "blocking_status": "NONE",
        }
    )
    write_sidecar(root, "CURRENT_GATE.json", current_gate)

    set_next_action(
        root,
        action_id="ACTION-CREATE-AGENT-NEXT-ACTION-DERIVED",
        action_type="create_agent",
        target_role="developer",
        task_id=TASK_ID,
        task_packet=TASK_PACKET,
        dependency_status="ready",
        action_semantic="normal",
        workspace_identity_required=True,
        repository_lock_required=True,
        checkpoint_policy="no_checkpoint",
        checkpoint_preflight_required=False,
        checkpoint_receipt_required=False,
        checkpoint_receipt_ref="NONE",
        instruction_for_orchestrator="Create the developer fixture agent.",
    )


def set_next_action(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "NEXT_ACTION.json")
    content = payload["content"]
    assert isinstance(content, dict)
    content.update(updates)
    write_sidecar(root, "NEXT_ACTION.json", payload)


def write_result(root: Path, ref: str, *, status: str, role: str) -> None:
    path = root / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    heading = "AUDIT_RESULT:" if role == "auditor" else "RESULT:"
    next_action = "CHECKPOINT_PREFLIGHT" if role == "auditor" and status == "pass" else "ROUTE_CORRECTION"
    path.write_text(
        "\n".join(
            [
                heading,
                "",
                f"STATUS: {status}",
                f"TASK_ID: {TASK_ID}",
                f"AGENT_INSTANCE_ID: {'audit' if role == 'auditor' else 'agent'}_{TASK_ID}_attempt_001",
                f"ROLE: {role}",
                f"TASK: {TASK_ID}",
                "SUMMARY:",
                "Next action derivation fixture.",
                "READ_DOCS:",
                "- NONE",
                "READ_INPUTS:",
                "- NONE",
                "CHANGED_FILES:",
                "- NONE",
                "CREATED_FILES:",
                "- NONE",
                "DELETED_FILES:",
                "- NONE",
                "COMMANDS_RUN:",
                "- NONE",
                "TESTS_RUN:",
                "- NONE",
                "EVIDENCE:",
                f"- SOURCE_RESULT_REF: {RESULT_REF}",
                "SCOPE_VERIFICATION:",
                "- TASK_PACKET_SCHEMA_STATUS: passed",
                "FORBIDDEN_CHANGES_CHECK:",
                "- FORBIDDEN_PATH_STATUS: passed",
                "RISKS:",
                "- NONE",
                "LIMITATIONS:",
                "- NONE",
                "BLOCKERS:",
                "- NONE",
                "GAPS:",
                "- NONE",
                "NEXT_RECOMMENDED_ACTION:",
                f"- {next_action}",
                "REUSE_ALLOWED: false",
                "AGENT_TERMINATION_REQUIRED: true",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_lifecycle_events(root: Path, events: list[dict[str, object]]) -> None:
    path = root / "project-runtime" / "agents" / "instances.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8")


def dispatch_event() -> dict[str, object]:
    return {
        "event": "agent_task_dispatched",
        "event_type": "CREATE_AGENT_DISPATCHED",
        "task_id": TASK_ID,
        "agent_role": "developer",
        "role": "developer",
        "agent_instance_id": f"agent_{TASK_ID}_attempt_001",
        "timestamp_utc": "2026-05-25T10:00:00Z",
        "created_by": "orchestrator",
    }


def result_received_event() -> dict[str, object]:
    return {
        "event": "agent_result_received",
        "event_type": "RESULT_RECEIVED",
        "task_id": TASK_ID,
        "agent_role": "developer",
        "role": "developer",
        "agent_instance_id": f"agent_{TASK_ID}_attempt_001",
        "result_ref": RESULT_REF,
        "timestamp_utc": "2026-05-25T10:01:00Z",
        "created_by": "orchestrator",
    }


def audit_result_event(status: str) -> dict[str, object]:
    return {
        "event": "audit_result_received",
        "event_type": "AUDIT_RESULT_RECEIVED",
        "status": status,
        "task_id": TASK_ID,
        "agent_role": "auditor",
        "role": "auditor",
        "agent_instance_id": f"audit_{TASK_ID}_attempt_001",
        "result_ref": AUDIT_RESULT_REF,
        "timestamp_utc": "2026-05-25T10:02:00Z",
        "created_by": "orchestrator",
    }


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class NextActionDerivationTests(unittest.TestCase):
    def test_active_running_task_overwrites_stale_checkpoint_cache_without_lifecycle_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_workspace(tmp)
            active_task_id = "TASK_ACTIVE_RUNNING"
            old_task_id = "TASK_OLD_CHECKPOINT_DONE"
            active_packet = f"project-runtime/tasks/active/{active_task_id}.md"
            old_packet = f"project-runtime/tasks/active/{old_task_id}.md"

            registry = load_sidecar(root, "TASK_REGISTRY.json")
            registry_content = registry["content"]
            assert isinstance(registry_content, dict)
            old_task = fixture_task_for(old_task_id, old_packet, "checkpoint_done")
            old_task["audit_refs"] = ["project-runtime/results/audit/AUDIT_RESULT_OLD_ATTEMPT_001.md"]
            registry_content["tasks"] = [
                old_task,
                fixture_task_for(active_task_id, active_packet, "running"),
            ]
            write_sidecar(root, "TASK_REGISTRY.json", registry)

            project_state = load_sidecar(root, "PROJECT_STATE.json")
            project_content = project_state["content"]
            assert isinstance(project_content, dict)
            project_content.update(
                {
                    "current_phase": "implementation",
                    "project_status": "active",
                    "identity_validation_status": "passed",
                    "repository_lock_status": "accepted",
                    "baseline_tracking_status": "passed",
                    "checkpoint_eligibility": "not_applicable",
                    "checkpoint_eligibility_status": "not_checked",
                    "audit_status": "pending",
                    "project_checkpoint_status": "not_required",
                    "checkpoint_blocked_by": [],
                    "active_blockers": [],
                    "active_gaps": [],
                    "active_branches": [],
                }
            )
            write_sidecar(root, "PROJECT_STATE.json", project_state)

            current_gate = load_sidecar(root, "CURRENT_GATE.json")
            gate_content = current_gate["content"]
            assert isinstance(gate_content, dict)
            gate_content.update(
                {
                    "status": "open",
                    "task_id": "NONE",
                    "task_packet": "NONE",
                    "required_next_role": "none",
                    "checkpoint_eligibility": "not_applicable",
                    "checkpoint_eligibility_status": "not_checked",
                    "project_checkpoint_status": "not_required",
                }
            )
            write_sidecar(root, "CURRENT_GATE.json", current_gate)

            set_next_action(
                root,
                action_type="update_state",
                target_role="orchestrator",
                task_id=old_task_id,
                task_packet=old_packet,
                dependency_status="ready",
                action_semantic="normal",
                workspace_identity_required=False,
                repository_lock_required=False,
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
                instruction_for_orchestrator="Run checkpoint preflight.",
            )
            verify_json = Path(tmp) / "verify.json"
            plan_json = Path(tmp) / "plan.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))
            render = run_aso(root, "state", "render", "--confirm-write")
            refreshed = load_sidecar(root, "NEXT_ACTION.json")["content"]
            verify_after = run_aso(root, "state", "verify", "--strict")

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = load_json(verify_json)
            rule_ids = {finding["rule_id"] for finding in verify_report["findings"]}
            self.assertIn("RUNTIME_NEXT_ACTION_STALE", rule_ids)
            self.assertIn("STALE_NEXT_ACTION_TASK_ID", rule_ids)
            self.assertEqual(verify_report["reconciliation"]["canonical_recommended_next_action"], "WAIT_FOR_RESULT")
            self.assertEqual(plan.returncode, 1, plan.stdout + plan.stderr)
            plan_report = load_json(plan_json)
            self.assertEqual(plan_report["recommended_next_action"], "WAIT_FOR_RESULT")
            self.assertEqual(plan_report["task_id"], active_task_id)
            self.assertNotEqual(plan_report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            self.assertIsInstance(refreshed, dict)
            self.assertEqual(refreshed["task_id"], active_task_id)
            self.assertEqual(refreshed["action_type"], "route_result")
            self.assertEqual(refreshed["checkpoint_policy"], "no_checkpoint")
            self.assertFalse(refreshed["checkpoint_preflight_required"])
            self.assertFalse(refreshed["checkpoint_receipt_required"])
            self.assertEqual(verify_after.returncode, 0, verify_after.stdout + verify_after.stderr)

    def test_repeated_create_agent_cache_is_replaced_by_wait_for_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_workspace(tmp)
            configure_active_task(root)
            write_lifecycle_events(root, [dispatch_event()])
            verify_json = Path(tmp) / "verify.json"
            plan_json = Path(tmp) / "plan.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))
            render = run_aso(root, "state", "render", "--confirm-write")
            refreshed = load_sidecar(root, "NEXT_ACTION.json")["content"]

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = load_json(verify_json)
            self.assertIn("RUNTIME_NEXT_ACTION_STALE", {finding["rule_id"] for finding in verify_report["findings"]})
            self.assertEqual(verify_report["reconciliation"]["canonical_recommended_next_action"], "WAIT_FOR_RESULT")
            self.assertEqual(plan.returncode, 1, plan.stdout + plan.stderr)
            plan_report = load_json(plan_json)
            self.assertEqual(plan_report["recommended_next_action"], "WAIT_FOR_RESULT")
            self.assertNotEqual(plan_report["recommended_next_action"], "CREATE_AGENT")
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            self.assertIsInstance(refreshed, dict)
            self.assertEqual(refreshed["action_type"], "route_result")
            self.assertEqual(refreshed["target_role"], "orchestrator")

    def test_stale_checkpoint_preflight_cache_routes_correction_after_audit_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_workspace(tmp)
            configure_active_task(root)
            write_result(root, RESULT_REF, status="pass", role="developer")
            write_result(root, AUDIT_RESULT_REF, status="fail", role="auditor")
            write_lifecycle_events(root, [result_received_event(), audit_result_event("fail")])
            set_next_action(
                root,
                action_type="update_state",
                target_role="orchestrator",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
                instruction_for_orchestrator="Run checkpoint preflight.",
            )
            verify_json = Path(tmp) / "verify.json"
            plan_json = Path(tmp) / "plan.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))
            render = run_aso(root, "state", "render", "--confirm-write")
            refreshed = load_sidecar(root, "NEXT_ACTION.json")["content"]

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = load_json(verify_json)
            self.assertEqual(verify_report["reconciliation"]["canonical_recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertIn("RUNTIME_NEXT_ACTION_STALE", {finding["rule_id"] for finding in verify_report["findings"]})
            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = load_json(plan_json)
            self.assertEqual(plan_report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertNotEqual(plan_report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            self.assertIsInstance(refreshed, dict)
            self.assertEqual(refreshed["action_type"], "correction")
            self.assertFalse(refreshed["checkpoint_preflight_required"])

    def test_stale_correction_cache_routes_checkpoint_after_audit_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_workspace(tmp)
            configure_active_task(root)
            write_result(root, RESULT_REF, status="pass", role="developer")
            write_result(root, AUDIT_RESULT_REF, status="pass", role="auditor")
            write_lifecycle_events(root, [result_received_event(), audit_result_event("pass")])
            set_next_action(
                root,
                action_type="correction",
                target_role="orchestrator",
                checkpoint_policy="no_checkpoint",
                checkpoint_preflight_required=False,
                checkpoint_receipt_required=False,
                instruction_for_orchestrator="Route correction.",
            )
            verify_json = Path(tmp) / "verify.json"
            plan_json = Path(tmp) / "plan.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))
            render = run_aso(root, "state", "render", "--confirm-write")
            refreshed = load_sidecar(root, "NEXT_ACTION.json")["content"]

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = load_json(verify_json)
            self.assertEqual(verify_report["reconciliation"]["canonical_recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertIn("RUNTIME_NEXT_ACTION_STALE", {finding["rule_id"] for finding in verify_report["findings"]})
            self.assertEqual(plan.returncode, 1, plan.stdout + plan.stderr)
            plan_report = load_json(plan_json)
            self.assertEqual(plan_report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertNotEqual(plan_report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            self.assertIsInstance(refreshed, dict)
            self.assertEqual(refreshed["action_type"], "update_state")
            self.assertTrue(refreshed["checkpoint_preflight_required"])

    def test_terminal_project_derives_no_next_action_and_render_refreshes_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_workspace(tmp)
            configure_active_task(root, task_status="completed")

            project_state = load_sidecar(root, "PROJECT_STATE.json")
            project_content = project_state["content"]
            assert isinstance(project_content, dict)
            project_content.update(
                {
                    "current_phase": "completed",
                    "project_status": "completed",
                    "audit_status": "passed",
                    "project_checkpoint_status": "passed",
                    "checkpoint_eligibility": "not_applicable",
                    "checkpoint_eligibility_status": "eligible",
                    "active_blockers": [],
                    "active_gaps": [],
                    "checkpoint_blocked_by": [],
                    "active_branches": [],
                }
            )
            write_sidecar(root, "PROJECT_STATE.json", project_state)

            current_gate = load_sidecar(root, "CURRENT_GATE.json")
            gate_content = current_gate["content"]
            assert isinstance(gate_content, dict)
            gate_content.update(
                {
                    "gate_id": "GATE-PROJECT-COMPLETED",
                    "gate_name": "Project completed",
                    "gate_type": "terminal",
                    "status": "passed",
                    "task_id": "NONE",
                    "task_packet": "NONE",
                    "action_semantic": "stop_terminal",
                    "required_next_role": "none",
                    "blocking_status": "NONE",
                    "project_checkpoint_status": "passed",
                }
            )
            write_sidecar(root, "CURRENT_GATE.json", current_gate)

            set_next_action(
                root,
                action_type="create_agent",
                target_role="developer",
                task_id=TASK_ID,
                task_packet=TASK_PACKET,
                dependency_status="ready",
                action_semantic="normal",
                workspace_identity_required=True,
                repository_lock_required=True,
                checkpoint_policy="no_checkpoint",
                checkpoint_preflight_required=False,
                checkpoint_receipt_required=False,
                instruction_for_orchestrator="Stale dispatch after completion.",
            )
            verify_json = Path(tmp) / "verify.json"
            plan_json = Path(tmp) / "plan.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))
            render = run_aso(root, "state", "render", "--confirm-write")
            refreshed = load_sidecar(root, "NEXT_ACTION.json")["content"]
            verify_after = run_aso(root, "state", "verify", "--strict")

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = load_json(verify_json)
            self.assertEqual(verify_report["reconciliation"]["canonical_recommended_next_action"], "NO_NEXT_ACTION")
            self.assertIn("RUNTIME_NEXT_ACTION_STALE", {finding["rule_id"] for finding in verify_report["findings"]})
            self.assertEqual(plan.returncode, 1, plan.stdout + plan.stderr)
            plan_report = load_json(plan_json)
            self.assertEqual(plan_report["recommended_next_action"], "NO_NEXT_ACTION")
            self.assertNotEqual(plan_report["recommended_next_action"], "CREATE_AGENT")
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            self.assertIsInstance(refreshed, dict)
            self.assertEqual(refreshed["action_type"], "stop")
            self.assertEqual(refreshed["target_role"], "none")
            self.assertEqual(refreshed["task_id"], "NONE")
            self.assertEqual(refreshed["action_semantic"], "stop_terminal")
            self.assertEqual(verify_after.returncode, 0, verify_after.stdout + verify_after.stderr)


if __name__ == "__main__":
    unittest.main()
