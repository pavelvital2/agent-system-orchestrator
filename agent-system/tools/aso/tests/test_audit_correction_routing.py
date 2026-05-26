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
SOURCE_RESULT_REF = f"project-runtime/results/worker/RESULT_{TASK_ID}_ATTEMPT_001.md"
AUDIT_RESULT_REF = f"project-runtime/results/audit/AUDIT_RESULT_{TASK_ID}_ATTEMPT_001.md"


WORKER_RESULT = f"""RESULT:
STATUS: pass
TASK_ID: {TASK_ID}
AGENT_INSTANCE_ID: agent_{TASK_ID}_attempt_001
ROLE: developer
TASK: {TASK_ID}
SUMMARY:
Worker result.
READ_DOCS:
- NONE
READ_INPUTS:
- NONE
CHANGED_FILES:
- app.py
CREATED_FILES:
- NONE
DELETED_FILES:
- NONE
COMMANDS_RUN:
- NONE
TESTS_RUN:
- NONE
EVIDENCE:
- NONE
SCOPE_VERIFICATION:
- NONE
FORBIDDEN_CHANGES_CHECK:
- NONE
RISKS:
- NONE
LIMITATIONS:
- NONE
BLOCKERS:
- NONE
GAPS:
- NONE
NEXT_RECOMMENDED_ACTION:
- NONE
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""


AUDIT_FAIL_RESULT = f"""AUDIT_RESULT:
STATUS: fail
TASK_ID: {TASK_ID}
AGENT_INSTANCE_ID: audit_{TASK_ID}_attempt_001
ROLE: auditor
TASK: {TASK_ID}
SUMMARY:
Audit failed.
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
- CHANGED_FILES_SCOPE_STATUS: failed
SCOPE_VERIFICATION:
- TASK_PACKET_SCHEMA_STATUS: passed
FORBIDDEN_CHANGES_CHECK:
- FORBIDDEN_PATH_STATUS: passed
RISKS:
- NONE
LIMITATIONS:
- NONE
BLOCKERS:
- audit_failed
GAPS:
- NONE
NEXT_RECOMMENDED_ACTION:
- ROUTE_CORRECTION
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""


BOOTSTRAP_RESULT_WITH_MISSING_PACKET = """RESULT:
STATUS: pass
TASK_ID: TASK_BOOTSTRAP_REQUIREMENTS_001
AGENT_INSTANCE_ID: agent_TASK_BOOTSTRAP_REQUIREMENTS_001_attempt_001
ROLE: requirements_analyst
TASK: TASK_BOOTSTRAP_REQUIREMENTS_001
SUMMARY:
Bootstrap claims a downstream packet.
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
- NONE
SCOPE_VERIFICATION:
- NONE
FORBIDDEN_CHANGES_CHECK:
- NONE
RISKS:
- NONE
LIMITATIONS:
- NONE
BLOCKERS:
- NONE
GAPS:
- NONE
NEXT_RECOMMENDED_ACTION:
- CREATE_AUDITOR
BOOTSTRAP_CONTINUATION_STATUS: downstream_task_packet
BOOTSTRAP_CONTINUATION_REF: project-runtime/tasks/active/TASK_MISSING_DOWNSTREAM.md
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


def run_record_result(path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "record-result",
            "--result",
            str(path),
            "--dry-run",
            "--json",
            *extra,
        ],
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
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{field}: {value}"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
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
        "task_packet": "TASK_PACKET",
        "action_semantic": "ACTION_SEMANTIC",
        "checkpoint_policy": "CHECKPOINT_POLICY",
        "checkpoint_preflight_required": "CHECKPOINT_PREFLIGHT_REQUIRED",
        "checkpoint_receipt_required": "CHECKPOINT_RECEIPT_REQUIRED",
    }
    for key, field in markdown_fields.items():
        if key not in updates:
            continue
        value = updates[key]
        if isinstance(value, bool):
            update_markdown_field(root, "NEXT_ACTION.md", field, "yes" if value else "no")
        elif isinstance(value, str):
            update_markdown_field(root, "NEXT_ACTION.md", field, value)


def set_project_state(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "PROJECT_STATE.json")
    body = content(payload)
    body.update(updates)
    write_sidecar(root, "PROJECT_STATE.json", payload)
    for key, field in {"tz_path": "TZ_PATH", "checkpoint_eligibility": "CHECKPOINT_ELIGIBILITY"}.items():
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


def make_tz_valid(root: Path) -> None:
    tz_path = root / "project-input" / "TZ.md"
    tz_path.parent.mkdir(parents=True, exist_ok=True)
    tz_path.write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
    set_project_state(root, tz_path="project-input/TZ.md")


def write_result_pair(root: Path) -> Path:
    source_path = root / SOURCE_RESULT_REF
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(WORKER_RESULT, encoding="utf-8")
    audit_path = root / AUDIT_RESULT_REF
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(AUDIT_FAIL_RESULT, encoding="utf-8")
    return audit_path


class AuditCorrectionRoutingTests(unittest.TestCase):
    def test_record_result_audit_fail_outputs_correction_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_path = write_result_pair(root)

            result = run_record_result(audit_path, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
        self.assertFalse(report["checkpoint_candidate"])
        correction = report["correction_routing"]
        self.assertEqual(correction["source_audit_result_ref"], AUDIT_RESULT_REF)
        self.assertEqual(correction["source_task_id"], TASK_ID)
        self.assertEqual(correction["target_correction_role"], "developer")
        self.assertIn("CHANGED_FILES_SCOPE_STATUS", correction["failed_checks"])
        self.assertTrue(correction["checkpoint_preflight_blocked"])

    def test_lifecycle_failed_audit_uses_receipt_and_does_not_emit_audit_route_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_path = write_result_pair(root)

            received = run_aso(root, "lifecycle", "receive-result", "--from-result", str(audit_path), "--confirm-write")
            terminated = run_aso(root, "lifecycle", "terminate-agent", "--from-result", str(audit_path), "--confirm-write")

            self.assertEqual(received.returncode, 0, received.stdout + received.stderr)
            self.assertEqual(terminated.returncode, 0, terminated.stdout + terminated.stderr)
            termination_report = json.loads(terminated.stdout)
            self.assertEqual(termination_report["audit_route_ready_event"], {})
            self.assertEqual(termination_report["correction_routing"]["route"], "CORRECTION_REQUIRED")
            events = [
                json.loads(line)
                for line in (root / "project-runtime" / "agents" / "instances.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["event_type"] for event in events], ["AUDIT_RESULT_RECEIVED", "AUDITOR_AGENT_TERMINATED"])
            self.assertEqual(events[0]["status"], "fail")
            self.assertEqual(events[0]["receipt_type"], "AUDIT_RESULT_RECEIPT")
            self.assertEqual(events[1]["next_allowed_action"], "correction_required")
            for event in events:
                receipt = event["result_receipt"]
                self.assertIs(receipt["reuse_allowed"], False)
                self.assertIs(receipt["agent_termination_required"], True)
            self.assertFalse(any(event["event_type"] == "AUDIT_ROUTE_READY" for event in events))

    def test_plan_next_checkpoint_attempt_with_failed_audit_routes_correction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result_pair(root)
            set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            set_task(root, status="audit_passed", audit_refs=[AUDIT_RESULT_REF])
            json_out = Path(tmp) / "plan-next.json"

            result = run_aso(root, "plan-next", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(report["route_status"], "ready")
            self.assertFalse(report["fatal"])
            self.assertNotEqual(report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertFalse(report["dispatchability"]["dispatchable"])
            self.assertEqual(report["dispatchability"]["status"], "correction_required")
            self.assertEqual(report["correction_routing"]["source_audit_result_ref"], AUDIT_RESULT_REF)
            rule_ids = {rule["rule_id"] for rule in report["blocking_rules"]}
            self.assertIn("GOV-AUDIT-FAIL-NO-CHECKPOINT", rule_ids)

    def test_bootstrap_downstream_task_packet_claim_without_dispatchable_packet_routes_correction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "RESULT_TASK_BOOTSTRAP_REQUIREMENTS_001_ATTEMPT_001.md"
            result_path.write_text(BOOTSTRAP_RESULT_WITH_MISSING_PACKET, encoding="utf-8")

            result = run_record_result(result_path, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
        continuation = report["evidence"]["bootstrap_continuation"]
        self.assertTrue(continuation["claimed"])
        self.assertFalse(continuation["dispatchable_downstream_task_packet"])
        rule_ids = {rule["rule_id"] for rule in report["blocking_rules"]}
        self.assertIn("GOV-BOOTSTRAP-CONTINUATION-DOWNSTREAM-PACKET", rule_ids)


if __name__ == "__main__":
    unittest.main()
