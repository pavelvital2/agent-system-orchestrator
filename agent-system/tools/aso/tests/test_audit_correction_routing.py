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
AUDIT_PASS_RESULT_REF = f"project-runtime/results/audit/AUDIT_RESULT_{TASK_ID}_ATTEMPT_002.md"
FAIL_001_AUDIT_REF = f"project-runtime/results/audit/AUDIT_RESULT_{TASK_ID}_ATTEMPT_101.md"
FAIL_002_AUDIT_REF = f"project-runtime/results/audit/AUDIT_RESULT_{TASK_ID}_ATTEMPT_102.md"
PASS_003_AUDIT_REF = f"project-runtime/results/audit/AUDIT_RESULT_{TASK_ID}_ATTEMPT_103.md"
SECOND_TASK_ID = "TASK_FIXTURE_STATE_002"
SECOND_AUDIT_PASS_RESULT_REF = f"project-runtime/results/audit/AUDIT_RESULT_{SECOND_TASK_ID}_ATTEMPT_001.md"
UNROUTABLE_AUDIT_FAIL_REF = "project-runtime/results/audit/AUDIT_RESULT_UNROUTABLE_ATTEMPT_001.md"


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


AUDIT_PASS_RESULT = f"""AUDIT_RESULT:
STATUS: pass
TASK_ID: {TASK_ID}
AGENT_INSTANCE_ID: audit_{TASK_ID}_attempt_002
ROLE: auditor
TASK: {TASK_ID}
SUMMARY:
Audit passed after correction.
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
- CORRECTION_REF: {AUDIT_RESULT_REF}
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


AUDIT_PASS_RESULT_NO_CORRECTION = AUDIT_PASS_RESULT.replace(f"- CORRECTION_REF: {AUDIT_RESULT_REF}\n", "")


SECOND_AUDIT_PASS_RESULT = f"""AUDIT_RESULT:
STATUS: pass
TASK_ID: {SECOND_TASK_ID}
AGENT_INSTANCE_ID: audit_{SECOND_TASK_ID}_attempt_001
ROLE: auditor
TASK: {SECOND_TASK_ID}
SUMMARY:
Second task audit passed.
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


UNROUTABLE_AUDIT_FAIL_RESULT = """AUDIT_RESULT:
STATUS: fail
AGENT_INSTANCE_ID: audit_unroutable_attempt_001
ROLE: auditor
TASK: NONE
SUMMARY:
Audit failed without a routable task target.
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
- CHANGED_FILES_SCOPE_STATUS: failed
SCOPE_VERIFICATION:
- TASK_PACKET_SCHEMA_STATUS: failed
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
    markdown_fields = {
        "tz_path": "TZ_PATH",
        "current_phase": "CURRENT_PHASE",
        "project_status": "PROJECT_STATUS",
        "checkpoint_eligibility": "CHECKPOINT_ELIGIBILITY",
        "checkpoint_eligibility_status": "CHECKPOINT_ELIGIBILITY_STATUS",
        "checkpoint_preflight_status": "CHECKPOINT_PREFLIGHT_STATUS",
        "project_checkpoint_status": "PROJECT_CHECKPOINT_STATUS",
        "audit_status": "AUDIT_STATUS",
        "action_semantic": "ACTION_SEMANTIC",
    }
    for key, field in markdown_fields.items():
        if key in updates and isinstance(updates[key], str):
            update_markdown_field(root, "PROJECT_STATE.md", field, str(updates[key]))


def set_current_gate(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "CURRENT_GATE.json")
    body = content(payload)
    body.update(updates)
    write_sidecar(root, "CURRENT_GATE.json", payload)
    markdown_fields = {
        "gate_type": "GATE_TYPE",
        "status": "STATUS",
        "task_id": "TASK_ID",
        "task_packet": "TASK_PACKET",
        "action_semantic": "ACTION_SEMANTIC",
        "checkpoint_eligibility": "CHECKPOINT_ELIGIBILITY",
        "checkpoint_eligibility_status": "CHECKPOINT_ELIGIBILITY_STATUS",
        "project_checkpoint_status": "PROJECT_CHECKPOINT_STATUS",
        "required_next_role": "REQUIRED_NEXT_ROLE",
        "blocking_status": "BLOCKING_STATUS",
    }
    for key, field in markdown_fields.items():
        if key in updates and isinstance(updates[key], str):
            update_markdown_field(root, "CURRENT_GATE.md", field, str(updates[key]))


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


def write_audit_pass(root: Path, *, correction_ref: bool = True) -> Path:
    audit_path = root / AUDIT_PASS_RESULT_REF
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        AUDIT_PASS_RESULT if correction_ref else AUDIT_PASS_RESULT_NO_CORRECTION,
        encoding="utf-8",
    )
    return audit_path


def write_second_audit_pass(root: Path) -> Path:
    audit_path = root / SECOND_AUDIT_PASS_RESULT_REF
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(SECOND_AUDIT_PASS_RESULT, encoding="utf-8")
    return audit_path


def audit_fail_result(check_id: str, agent_suffix: str) -> str:
    return f"""AUDIT_RESULT:
STATUS: fail
TASK_ID: {TASK_ID}
AGENT_INSTANCE_ID: audit_{TASK_ID}_{agent_suffix}
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
- {check_id}: failed
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


def audit_pass_result(correction_refs: list[str]) -> str:
    correction_lines = "\n".join(f"- CORRECTION_REF: {ref}" for ref in correction_refs)
    evidence_lines = f"- SOURCE_RESULT_REF: {SOURCE_RESULT_REF}\n"
    if correction_lines:
        evidence_lines += correction_lines + "\n"
    evidence_lines += "- CHANGED_FILES_SCOPE_STATUS: passed"
    return f"""AUDIT_RESULT:
STATUS: pass
TASK_ID: {TASK_ID}
AGENT_INSTANCE_ID: audit_{TASK_ID}_pass_003
ROLE: auditor
TASK: {TASK_ID}
SUMMARY:
Audit passed after correction.
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
{evidence_lines}
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


def write_audit_ref(root: Path, ref: str, text: str) -> Path:
    audit_path = root / ref
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(text, encoding="utf-8")
    return audit_path


def write_resolution_fixture(root: Path, correction_refs: list[str]) -> None:
    source_path = root / SOURCE_RESULT_REF
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(WORKER_RESULT, encoding="utf-8")
    write_audit_ref(root, FAIL_001_AUDIT_REF, audit_fail_result("SCOPE_A", "fail_001"))
    write_audit_ref(root, FAIL_002_AUDIT_REF, audit_fail_result("SCOPE_B", "fail_002"))
    write_audit_ref(root, PASS_003_AUDIT_REF, audit_pass_result(correction_refs))


def configure_checkpoint_attempt(root: Path, audit_refs: list[str], correction_links: list[str] | None = None) -> None:
    make_tz_valid(root)
    set_next_action(
        root,
        action_type="update_state",
        action_semantic="normal",
        checkpoint_policy="local_only",
        checkpoint_preflight_required=True,
        checkpoint_receipt_required=True,
    )
    set_project_state(root, checkpoint_eligibility="local_only", checkpoint_eligibility_status="eligible")
    set_task(
        root,
        status="audit_passed",
        audit_refs=audit_refs,
        correction_links=correction_links or [],
    )


def write_unroutable_audit_fail(root: Path) -> Path:
    audit_path = root / UNROUTABLE_AUDIT_FAIL_REF
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(UNROUTABLE_AUDIT_FAIL_RESULT, encoding="utf-8")
    return audit_path


def append_task(root: Path, *, task_id: str, status: str, audit_refs: list[str]) -> None:
    payload = load_sidecar(root, "TASK_REGISTRY.json")
    body = content(payload)
    tasks = body["tasks"]
    if not isinstance(tasks, list) or not tasks or not isinstance(tasks[0], dict):
        raise AssertionError("fixture task registry must contain one task")
    task = dict(tasks[0])
    task.update(
        {
            "task_id": task_id,
            "task_title": f"Fixture task {task_id}",
            "status": status,
            "task_packet": f"project-runtime/tasks/active/{task_id}.md",
            "audit_refs": audit_refs,
            "result_refs": [],
            "correction_links": [],
        }
    )
    tasks.append(task)
    write_sidecar(root, "TASK_REGISTRY.json", payload)


def clone_task_packet(root: Path, task_id: str) -> None:
    source = root / f"project-runtime/tasks/active/{TASK_ID}.md"
    target = root / f"project-runtime/tasks/active/{task_id}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8").replace(TASK_ID, task_id)
    target.write_text(text, encoding="utf-8")


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
        self.assertEqual(correction["severity"], "error")
        self.assertEqual(correction["target_role"], "developer")
        self.assertEqual(correction["target_correction_role"], "developer")
        self.assertIn("CHANGED_FILES_SCOPE_STATUS", correction["failed_checks"])
        self.assertEqual(correction["correction_task_packet_ref"], f"project-runtime/tasks/active/TASK_CORRECTION_{TASK_ID}.md")
        self.assertIn(AUDIT_RESULT_REF, correction["required_context_refs"])
        self.assertIn(SOURCE_RESULT_REF, correction["required_context_refs"])
        self.assertTrue(correction["checkpoint_preflight_blocked"])

    def test_audit_pass_allows_checkpoint_without_correction_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_audit_pass(root, correction_ref=False)
            set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            set_project_state(root, checkpoint_eligibility="local_only", checkpoint_eligibility_status="eligible")
            set_task(root, status="audit_passed", audit_refs=[AUDIT_PASS_RESULT_REF])
            json_out = Path(tmp) / "plan-next-pass.json"

            result = run_aso(root, "plan-next", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertEqual(report["route_status"], "ready")
            self.assertEqual(report["correction_routing"], {})
            self.assertTrue(report["evidence"]["audit_pass_evidence"]["present"])

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

    def test_fail_then_correction_pass_unblocks_checkpoint_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result_pair(root)
            write_audit_pass(root, correction_ref=True)
            set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            set_project_state(root, checkpoint_eligibility="local_only", checkpoint_eligibility_status="eligible")
            set_task(
                root,
                status="audit_passed",
                audit_refs=[AUDIT_RESULT_REF, AUDIT_PASS_RESULT_REF],
                correction_links=[AUDIT_RESULT_REF],
            )
            json_out = Path(tmp) / "plan-next-correction-pass.json"
            checkpoint_json = Path(tmp) / "checkpoint-correction-pass.json"

            result = run_aso(root, "plan-next", "--strict", "--json-out", str(json_out))
            checkpoint = run_aso(
                root,
                "checkpoint-preflight",
                "--mode",
                "workspace",
                "--strict",
                "--json-out",
                str(checkpoint_json),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertEqual(report["correction_routing"], {})
            evidence = report["evidence"]["audit_pass_evidence"]
            self.assertTrue(evidence["present"])
            self.assertEqual(evidence["invalid_audit_results"], [])
            self.assertEqual(evidence["resolved_audit_failures"][0]["ref"], AUDIT_RESULT_REF)
            self.assertEqual(evidence["resolved_audit_failures"][0]["resolved_by_audit_ref"], AUDIT_PASS_RESULT_REF)

            self.assertEqual(checkpoint.returncode, 0, checkpoint.stdout + checkpoint.stderr)
            checkpoint_report = json.loads(checkpoint_json.read_text(encoding="utf-8"))
            self.assertTrue(checkpoint_report["eligible"])
            self.assertEqual(checkpoint_report["correction_routing"], {})

    def test_partial_explicit_audit_resolution_keeps_uncited_fail_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            write_resolution_fixture(root, [FAIL_001_AUDIT_REF])
            configure_checkpoint_attempt(
                root,
                [FAIL_001_AUDIT_REF, FAIL_002_AUDIT_REF, PASS_003_AUDIT_REF],
                correction_links=[FAIL_001_AUDIT_REF],
            )
            verify_json = Path(tmp) / "verify-partial-resolution.json"
            plan_json = Path(tmp) / "plan-partial-resolution.json"
            checkpoint_json = Path(tmp) / "checkpoint-partial-resolution.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))
            checkpoint = run_aso(
                root,
                "checkpoint-preflight",
                "--mode",
                "workspace",
                "--strict",
                "--json-out",
                str(checkpoint_json),
            )

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = json.loads(verify_json.read_text(encoding="utf-8"))
            self.assertIn(FAIL_002_AUDIT_REF, json.dumps(verify_report["findings"], sort_keys=True))

            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(plan_report["correction_routing"]["source_audit_result_ref"], FAIL_002_AUDIT_REF)
            transition = plan_report["evidence"]["transition_engine"]["audit_failure_evidence"]
            self.assertEqual(
                [item["ref"] for item in transition["resolved_audit_failures"]],
                [FAIL_001_AUDIT_REF],
            )
            self.assertEqual(
                [item["ref"] for item in transition["unresolved_audit_failures"]],
                [FAIL_002_AUDIT_REF],
            )

            self.assertEqual(checkpoint.returncode, 1, checkpoint.stdout + checkpoint.stderr)
            checkpoint_report = json.loads(checkpoint_json.read_text(encoding="utf-8"))
            self.assertFalse(checkpoint_report["eligible"])
            self.assertEqual(checkpoint_report["correction_routing"]["source_audit_result_ref"], FAIL_002_AUDIT_REF)

    def test_multiple_explicit_audit_resolution_refs_unblock_checkpoint_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            write_resolution_fixture(root, [FAIL_001_AUDIT_REF, FAIL_002_AUDIT_REF])
            configure_checkpoint_attempt(
                root,
                [FAIL_001_AUDIT_REF, FAIL_002_AUDIT_REF, PASS_003_AUDIT_REF],
                correction_links=[FAIL_001_AUDIT_REF],
            )
            plan_json = Path(tmp) / "plan-full-resolution.json"
            checkpoint_json = Path(tmp) / "checkpoint-full-resolution.json"

            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))
            checkpoint = run_aso(
                root,
                "checkpoint-preflight",
                "--mode",
                "workspace",
                "--strict",
                "--json-out",
                str(checkpoint_json),
            )

            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertEqual(plan_report["correction_routing"], {})
            transition = plan_report["evidence"]["transition_engine"]["audit_failure_evidence"]
            self.assertEqual(transition["unresolved_audit_failures"], [])
            self.assertEqual(
                [item["ref"] for item in transition["resolved_audit_failures"]],
                [FAIL_001_AUDIT_REF, FAIL_002_AUDIT_REF],
            )

            self.assertEqual(checkpoint.returncode, 0, checkpoint.stdout + checkpoint.stderr)
            checkpoint_report = json.loads(checkpoint_json.read_text(encoding="utf-8"))
            self.assertTrue(checkpoint_report["eligible"])
            self.assertEqual(checkpoint_report["correction_routing"], {})

    def test_passing_audit_without_explicit_resolution_refs_does_not_resolve_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            write_resolution_fixture(root, [])
            configure_checkpoint_attempt(root, [FAIL_001_AUDIT_REF, PASS_003_AUDIT_REF])
            verify_json = Path(tmp) / "verify-missing-resolution-ref.json"
            plan_json = Path(tmp) / "plan-missing-resolution-ref.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = json.loads(verify_json.read_text(encoding="utf-8"))
            rule_ids = {finding["rule_id"] for finding in verify_report["findings"]}
            self.assertIn("PASS_AUDIT_WITHOUT_EXPLICIT_RESOLUTION_REFS", rule_ids)

            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(plan_report["correction_routing"]["source_audit_result_ref"], FAIL_001_AUDIT_REF)

    def test_passing_audit_with_invalid_resolution_ref_does_not_resolve_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            invalid_ref = f"project-runtime/results/audit/AUDIT_RESULT_{TASK_ID}_ATTEMPT_999.md"
            write_resolution_fixture(root, [invalid_ref])
            configure_checkpoint_attempt(root, [FAIL_001_AUDIT_REF, PASS_003_AUDIT_REF])
            verify_json = Path(tmp) / "verify-invalid-resolution-ref.json"
            plan_json = Path(tmp) / "plan-invalid-resolution-ref.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = json.loads(verify_json.read_text(encoding="utf-8"))
            rule_ids = {finding["rule_id"] for finding in verify_report["findings"]}
            self.assertIn("AUDIT_PASS_REFERENCES_UNKNOWN_FAILURE_REF", rule_ids)

            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(plan_report["correction_routing"]["source_audit_result_ref"], FAIL_001_AUDIT_REF)
            transition = plan_report["evidence"]["transition_engine"]["audit_failure_evidence"]
            self.assertEqual(transition["resolved_audit_failures"], [])
            self.assertEqual(
                [item["ref"] for item in transition["unresolved_audit_failures"]],
                [FAIL_001_AUDIT_REF],
            )

    def test_unresolved_audit_fail_blocks_terminal_and_checkpoint_agreement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result_pair(root)
            set_project_state(
                root,
                current_phase="completed",
                project_status="completed",
                audit_status="passed",
                checkpoint_eligibility="not_applicable",
                checkpoint_eligibility_status="eligible",
                checkpoint_preflight_status="passed",
                project_checkpoint_status="passed",
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
                dependency_status="completed",
                action_semantic="stop_terminal",
                checkpoint_policy="no_checkpoint",
                checkpoint_preflight_required=False,
                checkpoint_receipt_required=False,
            )
            set_task(root, status="audit_passed", audit_refs=[AUDIT_RESULT_REF])
            verify_json = Path(tmp) / "verify-unresolved-fail.json"
            status_json = Path(tmp) / "status-unresolved-fail.json"
            plan_json = Path(tmp) / "plan-unresolved-fail.json"
            checkpoint_json = Path(tmp) / "checkpoint-unresolved-fail.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            status = run_aso(root, "status", "--json-out", str(status_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))
            checkpoint = run_aso(
                root,
                "checkpoint-preflight",
                "--mode",
                "workspace",
                "--strict",
                "--json-out",
                str(checkpoint_json),
            )

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = json.loads(verify_json.read_text(encoding="utf-8"))
            verify_rule_ids = {finding["rule_id"] for finding in verify_report["findings"]}
            self.assertIn("SIDECAR_AUDIT_FAIL_UNRESOLVED", verify_rule_ids)

            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
            status_report = json.loads(status_json.read_text(encoding="utf-8"))
            self.assertEqual(status_report["status"], "failed")
            self.assertEqual(status_report["summary"]["runtime_consistency"], "FAIL")

            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(plan_report["route_status"], "ready")
            self.assertNotIn(plan_report["recommended_next_action"], {"CHECKPOINT_PREFLIGHT", "NO_NEXT_ACTION"})
            self.assertEqual(plan_report["correction_routing"]["route"], "CORRECTION_REQUIRED")

            self.assertEqual(checkpoint.returncode, 1, checkpoint.stdout + checkpoint.stderr)
            checkpoint_report = json.loads(checkpoint_json.read_text(encoding="utf-8"))
            self.assertFalse(checkpoint_report["eligible"])
            self.assertEqual(checkpoint_report["correction_routing"]["route"], "CORRECTION_REQUIRED")

    def test_all_task_unresolved_audit_fail_without_active_fallback_routes_correction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result_pair(root)
            write_second_audit_pass(root)
            clone_task_packet(root, SECOND_TASK_ID)
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
                dependency_status="completed",
                action_semantic="stop_terminal",
                checkpoint_policy="no_checkpoint",
                checkpoint_preflight_required=False,
                checkpoint_receipt_required=False,
            )
            set_task(root, status="audit_passed", audit_refs=[AUDIT_RESULT_REF])
            append_task(root, task_id=SECOND_TASK_ID, status="audit_passed", audit_refs=[SECOND_AUDIT_PASS_RESULT_REF])
            verify_json = Path(tmp) / "verify-all-task-fail.json"
            plan_json = Path(tmp) / "plan-all-task-fail.json"
            checkpoint_json = Path(tmp) / "checkpoint-all-task-fail.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))
            checkpoint = run_aso(
                root,
                "checkpoint-preflight",
                "--mode",
                "workspace",
                "--strict",
                "--json-out",
                str(checkpoint_json),
            )

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = json.loads(verify_json.read_text(encoding="utf-8"))
            verify_rule_ids = {finding["rule_id"] for finding in verify_report["findings"]}
            self.assertIn("SIDECAR_AUDIT_FAIL_UNRESOLVED", verify_rule_ids)

            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertNotEqual(plan_report["recommended_next_action"], "NONE")
            self.assertEqual(plan_report["route_status"], "ready")
            self.assertEqual(plan_report["correction_routing"]["route"], "CORRECTION_REQUIRED")
            self.assertEqual(plan_report["correction_routing"]["task_id"], TASK_ID)
            self.assertEqual(plan_report["correction_routing"]["source_audit_result_ref"], AUDIT_RESULT_REF)
            transition = plan_report["evidence"]["transition_engine"]
            self.assertEqual(transition["canonical_recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(transition["current_state"], "CORRECTION_REQUIRED")
            self.assertTrue(transition["audit_failure_evidence"]["present"])

            self.assertEqual(checkpoint.returncode, 1, checkpoint.stdout + checkpoint.stderr)
            checkpoint_report = json.loads(checkpoint_json.read_text(encoding="utf-8"))
            self.assertFalse(checkpoint_report["eligible"])
            self.assertEqual(checkpoint_report["correction_routing"]["route"], "CORRECTION_REQUIRED")
            self.assertEqual(checkpoint_report["correction_routing"]["source_audit_result_ref"], AUDIT_RESULT_REF)

    def test_non_current_historical_unresolved_audit_fail_blocks_current_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result_pair(root)
            write_second_audit_pass(root)
            clone_task_packet(root, SECOND_TASK_ID)
            set_task(root, status="audit_passed", audit_refs=[AUDIT_RESULT_REF])
            append_task(root, task_id=SECOND_TASK_ID, status="audit_passed", audit_refs=[SECOND_AUDIT_PASS_RESULT_REF])
            set_project_state(
                root,
                active_branches=[{"current_task": SECOND_TASK_ID, "current_agent_role": "developer"}],
                audit_status="passed",
                checkpoint_eligibility="local_only",
                checkpoint_eligibility_status="eligible",
            )
            set_current_gate(
                root,
                gate_type="implementation",
                status="open",
                task_id=SECOND_TASK_ID,
                task_packet=f"project-runtime/tasks/active/{SECOND_TASK_ID}.md",
                required_next_role="developer",
                checkpoint_eligibility="local_only",
                checkpoint_eligibility_status="eligible",
            )
            set_next_action(
                root,
                action_type="update_state",
                target_role="orchestrator",
                task_id=SECOND_TASK_ID,
                task_packet=f"project-runtime/tasks/active/{SECOND_TASK_ID}.md",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            plan_json = Path(tmp) / "plan-non-current-fail.json"

            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))

            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(plan_report["correction_routing"]["source_audit_result_ref"], AUDIT_RESULT_REF)
            self.assertEqual(plan_report["correction_routing"]["task_id"], TASK_ID)
            self.assertNotEqual(plan_report["task_id"], SECOND_TASK_ID)

    def test_unroutable_unresolved_audit_fail_fails_closed_with_diagnostic_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_unroutable_audit_fail(root)
            set_project_state(
                root,
                current_phase="completed",
                project_status="completed",
                active_branches=[],
                checkpoint_eligibility="not_applicable",
                checkpoint_eligibility_status="eligible",
            )
            set_current_gate(
                root,
                gate_type="terminal",
                status="passed",
                task_id="NONE",
                task_packet="NONE",
                gate_evidence=[UNROUTABLE_AUDIT_FAIL_REF],
                required_next_role="none",
            )
            set_next_action(
                root,
                action_type="stop",
                target_role="none",
                task_id="NONE",
                task_packet="NONE",
                dependency_status="completed",
                action_semantic="stop_terminal",
                checkpoint_policy="no_checkpoint",
                checkpoint_preflight_required=False,
                checkpoint_receipt_required=False,
            )
            verify_json = Path(tmp) / "verify-unroutable-fail.json"
            plan_json = Path(tmp) / "plan-unroutable-fail.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = json.loads(verify_json.read_text(encoding="utf-8"))
            verify_rule_ids = {finding["rule_id"] for finding in verify_report["findings"]}
            self.assertIn("UNROUTABLE_UNRESOLVED_AUDIT_FAIL", verify_rule_ids)

            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CORRECTION_REQUIRED")
            route = plan_report["correction_routing"]
            self.assertEqual(route["route"], "CORRECTION_REQUIRED")
            self.assertEqual(route["route_source"], "unroutable_unresolved_audit_fail")
            self.assertEqual(route["diagnostic_rule_id"], "UNROUTABLE_UNRESOLVED_AUDIT_FAIL")
            self.assertEqual(route["routing_issue"], "CORRECTION_REQUIRED_TARGET_UNRESOLVED")
            rule_ids = {rule["rule_id"] for rule in plan_report["blocking_rules"]}
            self.assertIn("UNROUTABLE_UNRESOLVED_AUDIT_FAIL", rule_ids)

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
