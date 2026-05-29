from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from test_audit_correction_routing import (  # noqa: E402
    FAIL_001_AUDIT_REF,
    SOURCE_RESULT_REF,
    TASK_ID,
    audit_fail_result,
    clone_task_packet,
    configure_checkpoint_attempt,
    content,
    copy_valid_workspace,
    load_sidecar,
    make_tz_valid,
    run_aso,
    set_current_gate,
    set_next_action,
    set_project_state,
    set_task,
    write_audit_ref,
    write_sidecar,
)


CORRECTION_TASK_1 = "TASK_CORRECTION_FIXTURE_001"
CORRECTION_TASK_2 = "TASK_CORRECTION_FIXTURE_002"
CORRECTION_FAIL_REF = f"project-runtime/results/audit/AUDIT_RESULT_{CORRECTION_TASK_1}_ATTEMPT_001.md"
CORRECTION_PASS_REF = f"project-runtime/results/audit/AUDIT_RESULT_{CORRECTION_TASK_2}_ATTEMPT_001.md"


def append_task(root: Path, *, task_id: str, status: str, audit_refs: list[str], **updates: object) -> None:
    payload = load_sidecar(root, "TASK_REGISTRY.json")
    tasks = content(payload)["tasks"]
    if not isinstance(tasks, list) or not tasks or not isinstance(tasks[0], dict):
        raise AssertionError("fixture task registry must contain one task")
    task = dict(tasks[0])
    for field in (
        "correction_of",
        "resolved_by",
        "superseded_by",
        "effective_audit_ref",
        "raw_status",
        "resolution_status",
        "effective_status",
    ):
        task.pop(field, None)
    task.update(
        {
            "task_id": task_id,
            "task_title": f"Correction fixture {task_id}",
            "task_kind": "correction",
            "status": status,
            "task_packet": f"project-runtime/tasks/active/{task_id}.md",
            "audit_refs": audit_refs,
            "result_refs": [],
            "correction_links": [],
        }
    )
    task.update(updates)
    tasks.append(task)
    write_sidecar(root, "TASK_REGISTRY.json", payload)
    clone_task_packet(root, task_id)


def audit_pass_for(task_id: str, correction_refs: list[str]) -> str:
    correction_lines = "\n".join(f"- CORRECTION_REF: {ref}" for ref in correction_refs)
    return f"""AUDIT_RESULT:
STATUS: pass
TASK_ID: {task_id}
AGENT_INSTANCE_ID: audit_{task_id}_attempt_001
ROLE: auditor
TASK: {task_id}
SUMMARY:
Correction audit passed.
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
- SOURCE_RESULT_REF: {SOURCE_RESULT_REF}
{correction_lines}
- CHANGED_FILES_SCOPE_STATUS: passed
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


def prepare_multi_attempt_chain(root: Path) -> None:
    make_tz_valid(root)
    write_audit_ref(root, FAIL_001_AUDIT_REF, audit_fail_result("SCOPE_A", "fail_original"))
    write_audit_ref(root, CORRECTION_FAIL_REF, audit_fail_result("SCOPE_B", "fail_correction").replace(TASK_ID, CORRECTION_TASK_1))
    write_audit_ref(root, CORRECTION_PASS_REF, audit_pass_for(CORRECTION_TASK_2, [FAIL_001_AUDIT_REF, CORRECTION_FAIL_REF]))
    set_task(
        root,
        status="completed",
        raw_status="failed",
        audit_refs=[FAIL_001_AUDIT_REF],
        resolved_by=[CORRECTION_TASK_2, CORRECTION_PASS_REF],
        superseded_by=[CORRECTION_TASK_2],
        resolution_status="superseded",
        effective_status="superseded",
        effective_audit_ref=CORRECTION_PASS_REF,
    )
    append_task(
        root,
        task_id=CORRECTION_TASK_1,
        status="completed",
        raw_status="failed",
        audit_refs=[CORRECTION_FAIL_REF],
        correction_of=[TASK_ID, FAIL_001_AUDIT_REF],
        resolved_by=[CORRECTION_TASK_2, CORRECTION_PASS_REF],
        superseded_by=[CORRECTION_TASK_2],
        resolution_status="superseded",
        effective_status="superseded",
        effective_audit_ref=CORRECTION_PASS_REF,
    )
    append_task(
        root,
        task_id=CORRECTION_TASK_2,
        status="completed",
        audit_refs=[CORRECTION_PASS_REF],
        correction_of=[TASK_ID, CORRECTION_TASK_1, FAIL_001_AUDIT_REF, CORRECTION_FAIL_REF],
        resolution_status="not_required",
        effective_status="completed",
        effective_audit_ref=CORRECTION_PASS_REF,
    )


class CorrectionResolutionGraphTests(unittest.TestCase):
    def test_multi_attempt_chain_rolls_historical_failures_into_resolved_effective_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            prepare_multi_attempt_chain(root)
            set_project_state(
                root,
                current_phase="completed",
                project_status="completed",
                audit_status="passed",
                checkpoint_eligibility="not_applicable",
                checkpoint_eligibility_status="eligible",
                checkpoint_preflight_status="passed",
                project_checkpoint_status="passed",
                active_branches=[],
                active_blockers=[],
                active_gaps=[],
                checkpoint_blocked_by=[],
                action_semantic="completed_state_transition",
            )
            set_current_gate(
                root,
                gate_type="terminal",
                status="passed",
                task_id="NONE",
                task_packet="NONE",
                action_semantic="stop_terminal",
                checkpoint_eligibility="not_applicable",
                checkpoint_eligibility_status="eligible",
                project_checkpoint_status="passed",
                required_next_role="none",
                blocking_status="NONE",
            )
            set_next_action(
                root,
                action_type="stop",
                target_role="none",
                task_id="NONE",
                task_packet="NONE",
                action_semantic="stop_terminal",
                checkpoint_policy="no_checkpoint",
                checkpoint_preflight_required=False,
                checkpoint_receipt_required=False,
            )
            verify_json = Path(tmp) / "verify-resolution-graph.json"
            plan_json = Path(tmp) / "plan-resolution-graph.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))

            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            verify_report = json.loads(verify_json.read_text(encoding="utf-8"))
            rollup = verify_report["state"]["task_effective_status_rollup"]
            self.assertEqual(rollup["counts"]["unresolved_effective_tasks"], 0)
            self.assertEqual(rollup["counts"]["historical_resolved_tasks"], 2)
            self.assertEqual(
                {task["task_id"]: task["effective_status"] for task in rollup["tasks"]},
                {
                    TASK_ID: "superseded",
                    CORRECTION_TASK_1: "superseded",
                    CORRECTION_TASK_2: "completed",
                },
            )

            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            evidence = plan_report["evidence"]["transition_engine"]["audit_failure_evidence"]
            self.assertEqual(evidence["unresolved_effective_failure_count"], 0)
            self.assertEqual(
                {item["ref"] for item in evidence["resolved_audit_failures"]},
                {FAIL_001_AUDIT_REF, CORRECTION_FAIL_REF},
            )
            self.assertEqual(plan_report["recommended_next_action"], "NO_NEXT_ACTION")

    def test_declared_resolution_without_valid_receipt_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            configure_checkpoint_attempt(root, [FAIL_001_AUDIT_REF])
            write_audit_ref(root, FAIL_001_AUDIT_REF, audit_fail_result("SCOPE_A", "fail_original"))
            set_task(
                root,
                status="completed",
                raw_status="failed",
                audit_refs=[FAIL_001_AUDIT_REF],
                resolved_by=["TASK_DOES_NOT_EXIST"],
                resolution_status="resolved",
                effective_status="completed",
                effective_audit_ref="project-runtime/results/audit/AUDIT_RESULT_UNKNOWN_ATTEMPT_001.md",
            )
            verify_json = Path(tmp) / "verify-malicious-resolution.json"
            plan_json = Path(tmp) / "plan-malicious-resolution.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = json.loads(verify_json.read_text(encoding="utf-8"))
            rule_ids = {finding["rule_id"] for finding in verify_report["findings"]}
            self.assertIn("TASK_RESOLUTION_STATUS_MISMATCH", rule_ids)
            self.assertIn("TASK_EFFECTIVE_STATUS_MISMATCH", rule_ids)
            self.assertIn("SIDECAR_AUDIT_FAIL_UNRESOLVED", rule_ids)

            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(plan_report["correction_routing"]["source_audit_result_ref"], FAIL_001_AUDIT_REF)


if __name__ == "__main__":
    unittest.main()
