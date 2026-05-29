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
    PASS_003_AUDIT_REF,
    TASK_ID,
    audit_fail_result,
    audit_pass_result,
    configure_checkpoint_attempt,
    content,
    copy_valid_workspace,
    load_sidecar,
    run_aso,
    set_current_gate,
    set_next_action,
    set_project_state,
    set_task,
    write_audit_ref,
    write_sidecar,
)


def set_original_task_checkpoint_attempt(root: Path, audit_refs: list[str]) -> None:
    configure_checkpoint_attempt(root, audit_refs)
    set_task(
        root,
        status="audit_passed",
        raw_status="failed",
        resolved_by=[PASS_003_AUDIT_REF],
        resolution_status="resolved",
        effective_status="audit_passed",
        effective_audit_ref=PASS_003_AUDIT_REF,
    )


def write_valid_cross_task_resolution(root: Path) -> None:
    write_audit_ref(root, FAIL_001_AUDIT_REF, audit_fail_result("SCOPE_A", "fail_original"))
    write_audit_ref(root, PASS_003_AUDIT_REF, audit_pass_result([FAIL_001_AUDIT_REF]))
    payload = load_sidecar(root, "TASK_REGISTRY.json")
    tasks = content(payload)["tasks"]
    if not isinstance(tasks, list) or not tasks or not isinstance(tasks[0], dict):
        raise AssertionError("fixture task registry must contain one task")
    correction_task = dict(tasks[0])
    for field in (
        "correction_of",
        "resolved_by",
        "superseded_by",
        "effective_audit_ref",
        "raw_status",
        "resolution_status",
        "effective_status",
    ):
        correction_task.pop(field, None)
    correction_task.update(
        {
            "task_id": "TASK_CORRECTION_CHECKPOINT_001",
            "task_title": "Checkpoint correction",
            "task_kind": "correction",
            "status": "audit_passed",
            "task_packet": "project-runtime/tasks/active/TASK_CORRECTION_CHECKPOINT_001.md",
            "audit_refs": [PASS_003_AUDIT_REF],
            "result_refs": [],
            "correction_of": [TASK_ID, FAIL_001_AUDIT_REF],
            "correction_links": [TASK_ID, FAIL_001_AUDIT_REF],
            "resolution_status": "not_required",
            "effective_status": "audit_passed",
            "effective_audit_ref": PASS_003_AUDIT_REF,
        }
    )
    tasks.append(correction_task)
    write_sidecar(root, "TASK_REGISTRY.json", payload)


def append_unlinked_correction_pass(root: Path) -> None:
    payload = load_sidecar(root, "TASK_REGISTRY.json")
    tasks = content(payload)["tasks"]
    if not isinstance(tasks, list) or not tasks or not isinstance(tasks[0], dict):
        raise AssertionError("fixture task registry must contain one task")
    correction_task = dict(tasks[0])
    for field in (
        "correction_of",
        "resolved_by",
        "superseded_by",
        "effective_audit_ref",
        "raw_status",
        "resolution_status",
        "effective_status",
    ):
        correction_task.pop(field, None)
    correction_task.update(
        {
            "task_id": "TASK_UNLINKED_CORRECTION_001",
            "task_title": "Unlinked checkpoint correction",
            "task_kind": "correction",
            "status": "audit_passed",
            "task_packet": "project-runtime/tasks/active/TASK_UNLINKED_CORRECTION_001.md",
            "audit_refs": [PASS_003_AUDIT_REF],
            "result_refs": [],
            "correction_links": [],
        }
    )
    tasks.append(correction_task)
    write_sidecar(root, "TASK_REGISTRY.json", payload)


class CheckpointEvidenceSelectionTests(unittest.TestCase):
    def test_checkpoint_uses_latest_effective_pass_in_resolution_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            write_valid_cross_task_resolution(root)
            set_original_task_checkpoint_attempt(root, [FAIL_001_AUDIT_REF])
            checkpoint_json = Path(tmp) / "checkpoint-effective-pass.json"

            result = run_aso(
                root,
                "checkpoint-preflight",
                "--mode",
                "workspace",
                "--strict",
                "--json-out",
                str(checkpoint_json),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(checkpoint_json.read_text(encoding="utf-8"))
            self.assertTrue(report["eligible"])
            evidence = report["evidence"]["audit_pass_evidence"]
            self.assertTrue(evidence["present"])
            self.assertEqual(evidence["effective_audit_ref"], PASS_003_AUDIT_REF)
            self.assertEqual(evidence["invalid_audit_results"], [])
            self.assertEqual(evidence["unresolved_audit_failures"], [])
            self.assertEqual(evidence["resolved_audit_failures"][0]["ref"], FAIL_001_AUDIT_REF)
            self.assertEqual(evidence["resolved_audit_failures"][0]["resolved_by_audit_ref"], PASS_003_AUDIT_REF)

    def test_stale_failed_audit_is_not_suppressed_without_valid_resolution_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            write_audit_ref(root, FAIL_001_AUDIT_REF, audit_fail_result("SCOPE_A", "fail_original"))
            write_audit_ref(root, PASS_003_AUDIT_REF, audit_pass_result([FAIL_001_AUDIT_REF]))
            set_original_task_checkpoint_attempt(root, [FAIL_001_AUDIT_REF])
            append_unlinked_correction_pass(root)
            set_task(
                root,
                status="audit_passed",
                raw_status="failed",
                audit_refs=[FAIL_001_AUDIT_REF],
                resolved_by=[],
                resolution_status="resolved",
                effective_status="audit_passed",
                effective_audit_ref=PASS_003_AUDIT_REF,
            )
            checkpoint_json = Path(tmp) / "checkpoint-invalid-resolution.json"
            plan_json = Path(tmp) / "plan-invalid-resolution.json"

            checkpoint = run_aso(
                root,
                "checkpoint-preflight",
                "--mode",
                "workspace",
                "--strict",
                "--json-out",
                str(checkpoint_json),
            )
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))

            self.assertEqual(checkpoint.returncode, 1, checkpoint.stdout + checkpoint.stderr)
            checkpoint_report = json.loads(checkpoint_json.read_text(encoding="utf-8"))
            evidence = checkpoint_report["evidence"]["audit_pass_evidence"]
            self.assertFalse(evidence["present"])
            self.assertEqual(evidence["unresolved_audit_failures"][0]["ref"], FAIL_001_AUDIT_REF)
            diagnostics = evidence["unresolved_audit_failures"][0]["resolution_diagnostics"]
            self.assertEqual(diagnostics[0]["rule_id"], "AUDIT_PASS_RESOLUTION_LINK_INVALID")
            self.assertEqual(checkpoint_report["correction_routing"]["source_audit_result_ref"], FAIL_001_AUDIT_REF)

            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CORRECTION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
