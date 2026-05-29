from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
ASO_TOOL_ROOT = REPO_ROOT / "agent-system" / "tools" / "aso"

sys.path.insert(0, str(ASO_TOOL_ROOT))

from agent_system_orchestrator_aso.aso_tool import transition_engine  # noqa: E402


def _sidecars(next_action_updates: dict[str, object] | None = None) -> dict[str, dict[str, object]]:
    next_action = {
        "action_type": "create_agent",
        "target_role": "developer",
        "task_id": "TASK_001",
        "task_packet": "project-runtime/tasks/active/TASK_001.md",
        "checkpoint_policy": "no_checkpoint",
        "checkpoint_preflight_required": False,
    }
    if next_action_updates:
        next_action.update(next_action_updates)
    return {
        "PROJECT_STATE": {
            "content": {
                "current_phase": "implementation",
                "project_status": "active",
                "active_branches": [
                    {
                        "current_task": "TASK_001",
                        "current_agent_role": "developer",
                    }
                ],
            }
        },
        "CURRENT_GATE": {
            "content": {
                "status": "open",
                "task_id": "TASK_001",
                "task_packet": "project-runtime/tasks/active/TASK_001.md",
                "required_next_role": "developer",
            }
        },
        "TASK_REGISTRY": {
            "content": {
                "tasks": [
                    {
                        "task_id": "TASK_001",
                        "status": "ready",
                        "task_type": "developer",
                        "owner_role": "developer",
                        "task_packet": "project-runtime/tasks/active/TASK_001.md",
                        "audit_refs": [],
                        "result_refs": [],
                    }
                ]
            }
        },
        "NEXT_ACTION": {
            "content": next_action
        },
    }


class TransitionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = transition_engine.load_runtime_contract()

    def test_allowed_transition_selects_next_state_and_action(self) -> None:
        decision = transition_engine.derive_transition(
            self.contract,
            "TASK_READY",
            "CREATE_AGENT_DISPATCHED",
            target_role="developer",
            task_id="TASK_001",
            task_packet="project-runtime/tasks/active/TASK_001.md",
        )

        self.assertTrue(decision.allowed, decision.to_json())
        self.assertEqual(decision.next_state, "AGENT_RUNNING")
        self.assertEqual(decision.next_action["recommended_next_action"], "WAIT_FOR_RESULT")
        self.assertEqual(decision.transition_selected["from_state"], "TASK_READY")
        self.assertIn("agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json", decision.reference_docs_used)

    def test_duplicate_same_task_dispatch_is_forbidden_after_progress(self) -> None:
        decision = transition_engine.derive_transition(
            self.contract,
            "AGENT_RUNNING",
            "CREATE_AGENT_DISPATCHED",
            same_task=True,
            target_role="developer",
            task_id="TASK_001",
        )

        self.assertFalse(decision.allowed)
        rule_ids = {finding.rule_id for finding in decision.findings}
        self.assertIn("RUNTIME_TRANSITION_FORBIDDEN", rule_ids)
        self.assertIn("RUNTIME_TRANSITION_NOT_ALLOWED", rule_ids)

    def test_forbidden_dispatch_role_is_rejected(self) -> None:
        decision = transition_engine.derive_transition(
            self.contract,
            "TASK_READY",
            "CREATE_AGENT_DISPATCHED",
            target_role="orchestrator",
            task_id="TASK_001",
        )

        self.assertFalse(decision.allowed)
        self.assertIn("RUNTIME_FORBIDDEN_DISPATCH_ROLE", {finding.rule_id for finding in decision.findings})

    def test_audit_pass_and_fail_route_to_distinct_contract_states(self) -> None:
        passed = transition_engine.derive_transition(
            self.contract,
            "AUDIT_PENDING",
            {"event_type": "AUDIT_RESULT_RECEIVED", "status": "pass"},
            task_id="TASK_001",
        )
        failed = transition_engine.derive_transition(
            self.contract,
            "AUDIT_PENDING",
            {"event_type": "AUDIT_RESULT_RECEIVED", "status": "fail"},
            task_id="TASK_001",
        )

        self.assertTrue(passed.allowed, passed.to_json())
        self.assertEqual(passed.next_state, "CHECKPOINT_ELIGIBLE")
        self.assertEqual(passed.next_action["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
        self.assertTrue(failed.allowed, failed.to_json())
        self.assertEqual(failed.next_state, "CORRECTION_REQUIRED")
        self.assertEqual(failed.next_action["recommended_next_action"], "CORRECTION_REQUIRED")

    def test_checkpoint_eligible_is_intermediate_and_completion_is_explicit(self) -> None:
        self.assertNotIn("CHECKPOINT_ELIGIBLE", self.contract["terminal_states"])
        self.assertIn("PROJECT_COMPLETED", self.contract["terminal_states"])
        self.assertIn("NO_NEXT_ACTION", self.contract["terminal_states"])

        checkpoint_pass = transition_engine.derive_transition(
            self.contract,
            "CHECKPOINT_ELIGIBLE",
            "CHECKPOINT_PREFLIGHT_PASS",
            task_id="TASK_001",
        )
        checkpoint_complete = transition_engine.derive_transition(
            self.contract,
            "FINAL_AUDIT_PASS",
            "CHECKPOINT_COMMITTED_OR_ARCHIVED",
            task_id="TASK_001",
        )
        finalized = transition_engine.derive_transition(
            self.contract,
            "FINAL_CHECKPOINT_COMPLETE",
            "FINALIZE",
            task_id="TASK_001",
        )
        terminal = transition_engine.derive_transition(
            self.contract,
            "PROJECT_COMPLETED",
            "NO_NEXT_ACTION",
            task_id="TASK_001",
        )

        self.assertTrue(checkpoint_pass.allowed, checkpoint_pass.to_json())
        self.assertEqual(checkpoint_pass.next_state, "FINAL_AUDIT_PASS")
        self.assertEqual(checkpoint_pass.next_action["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
        self.assertTrue(checkpoint_complete.allowed, checkpoint_complete.to_json())
        self.assertEqual(checkpoint_complete.next_state, "FINAL_CHECKPOINT_COMPLETE")
        self.assertEqual(checkpoint_complete.next_action["recommended_next_action"], "FINALIZE")
        self.assertTrue(finalized.allowed, finalized.to_json())
        self.assertEqual(finalized.next_state, "PROJECT_COMPLETED")
        self.assertEqual(finalized.next_action["recommended_next_action"], "NO_NEXT_ACTION")
        self.assertTrue(terminal.allowed, terminal.to_json())
        self.assertEqual(terminal.next_state, "NO_NEXT_ACTION")
        self.assertEqual(terminal.next_action["recommended_next_action"], "NO_NEXT_ACTION")

    def test_record_result_route_uses_contract_next_actions(self) -> None:
        profile_pass = transition_engine.derive_result_route(
            self.contract,
            "profile_result",
            "pass",
            task_id="TASK_001",
        )
        audit_fail = transition_engine.derive_result_route(
            self.contract,
            "audit_result",
            "fail",
            task_id="TASK_001",
        )

        self.assertTrue(profile_pass.allowed, profile_pass.to_json())
        self.assertEqual(profile_pass.current_state, "AGENT_TERMINATED")
        self.assertEqual(profile_pass.next_action["recommended_next_action"], "CREATE_AUDITOR")
        self.assertTrue(audit_fail.allowed, audit_fail.to_json())
        self.assertEqual(audit_fail.next_state, "CORRECTION_REQUIRED")
        self.assertEqual(audit_fail.next_action["recommended_next_action"], "CORRECTION_REQUIRED")

    def test_record_result_route_rejects_audit_status_missing_from_contract(self) -> None:
        decision = transition_engine.derive_result_route(
            self.contract,
            "audit_result",
            "blocked",
            task_id="TASK_001",
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.current_state, "AUDIT_PENDING")
        self.assertEqual(decision.event, "AUDIT_RESULT_RECEIVED")
        rule_ids = {finding.rule_id for finding in decision.findings}
        self.assertIn("RUNTIME_EVENT_NOT_ALLOWED", rule_ids)
        self.assertIn("RUNTIME_TRANSITION_NOT_ALLOWED", rule_ids)

    def test_sidecar_next_action_consistency_passes_for_task_ready_dispatch(self) -> None:
        decision = transition_engine.explain_next_action_from_sidecars(self.contract, _sidecars())

        self.assertTrue(decision.allowed, decision.to_json())
        self.assertEqual(decision.current_state, "TASK_READY")
        self.assertEqual(decision.next_action["recommended_next_action"], "CREATE_AGENT")
        self.assertEqual(decision.inputs["stored_recommended_next_action"], "CREATE_AGENT")

    def test_routing_authority_report_exposes_validate_route_apply_layers(self) -> None:
        report = transition_engine.routing_authority_report(self.contract, _sidecars())

        self.assertTrue(report["contract_authoritative"])
        self.assertEqual(report["current_state"], "TASK_READY")
        self.assertEqual(report["canonical_recommended_next_action"], "CREATE_AGENT")
        self.assertEqual(
            set(report["routing_layers"]),
            {"validate", "route_next", "apply_transition"},
        )
        self.assertEqual(report["routing_layers"]["validate"]["status"], "passed")
        self.assertEqual(report["routing_layers"]["route_next"]["recommended_next_action"], "CREATE_AGENT")
        self.assertTrue(report["routing_layers"]["apply_transition"]["mutating_authority"])
        self.assertFalse(report["routing_layers"]["apply_transition"]["mutations_performed"])
        self.assertIn("developer", report["roles"]["dispatchable_roles"])
        self.assertIn("PROJECT_COMPLETED", report["lifecycle_statuses"]["terminal_states"])

    def test_sidecar_next_action_consistency_detects_stale_stop(self) -> None:
        decision = transition_engine.explain_next_action_from_sidecars(
            self.contract,
            _sidecars(
                {
                    "action_type": "stop",
                    "target_role": "none",
                    "checkpoint_policy": "no_checkpoint",
                    "checkpoint_preflight_required": False,
                }
            ),
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.current_state, "TASK_READY")
        self.assertIn("RUNTIME_NEXT_ACTION_STALE", {finding.rule_id for finding in decision.findings})


if __name__ == "__main__":
    unittest.main()
