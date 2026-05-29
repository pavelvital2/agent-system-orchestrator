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


def make_tz_valid(root: Path) -> None:
    tz_path = root / "project-input" / "TZ.md"
    tz_path.parent.mkdir(parents=True, exist_ok=True)
    tz_path.write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
    payload = load_sidecar(root, "PROJECT_STATE.json")
    content = payload["content"]
    assert isinstance(content, dict)
    content["tz_path"] = "project-input/TZ.md"
    write_sidecar(root, "PROJECT_STATE.json", payload)
    update_markdown_field(root, "PROJECT_STATE.md", "TZ_PATH", "project-input/TZ.md")


def write_result(root: Path, ref: str = RESULT_REF, *, status: str = "pass", role: str = "developer") -> None:
    agent_instance_id = f"audit_{TASK_ID}_attempt_001" if role == "auditor" else f"agent_{TASK_ID}_attempt_001"
    path = root / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# RESULT",
                "",
                f"STATUS: {status}",
                f"TASK_ID: {TASK_ID}",
                f"AGENT_INSTANCE_ID: {agent_instance_id}",
                f"ROLE: {role}",
                f"TASK: {TASK_ID}",
                "SUMMARY:",
                "Lifecycle reconciliation fixture.",
                "REUSE_ALLOWED: false",
                "AGENT_TERMINATION_REQUIRED: true",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_artifact_refs(
    root: Path,
    *,
    artifact_id: str = f"RESULT_{TASK_ID}_ATTEMPT_001",
) -> tuple[str, str, str]:
    artifact_ref = f"project-runtime/artifacts/accepted/{TASK_ID}/{artifact_id}/manifest.json"
    package_ref = f"project-runtime/artifacts/accepted/{TASK_ID}/{artifact_id}"
    receipt_ref = f"project-runtime/receipts/artifacts/{TASK_ID}/{artifact_id}.acceptance.json"
    manifest_path = root / artifact_ref
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text('{"artifact_type":"RESULT"}\n', encoding="utf-8")
    receipt_path = root / receipt_ref
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text('{"receipt_type":"ARTIFACT_ACCEPTANCE_RECEIPT"}\n', encoding="utf-8")
    return artifact_ref, package_ref, receipt_ref


def write_lifecycle_events(root: Path, events: list[dict[str, object]]) -> None:
    path = root / "project-runtime" / "agents" / "instances.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8")


def result_received_event() -> dict[str, object]:
    return {
        "event": "agent_result_received",
        "event_type": "RESULT_RECEIVED",
        "task_id": TASK_ID,
        "agent_role": "developer",
        "role": "developer",
        "agent_instance_id": f"agent_{TASK_ID}_attempt_001",
        "result_ref": RESULT_REF,
        "timestamp_utc": "2026-05-25T10:00:00Z",
        "created_by": "orchestrator",
        "reuse_allowed": False,
    }


def artifact_accepted_event(
    artifact_ref: str,
    package_ref: str,
    receipt_ref: str,
    *,
    role: str = "developer",
    result_ref: str = RESULT_REF,
    artifact_id: str = f"RESULT_{TASK_ID}_ATTEMPT_001",
    timestamp: str = "2026-05-25T10:01:00Z",
) -> dict[str, object]:
    agent_prefix = "audit" if role == "auditor" else "agent"
    return {
        "event": "artifact_accepted",
        "event_type": "ARTIFACT_ACCEPTED",
        "task_id": TASK_ID,
        "agent_role": role,
        "role": role,
        "agent_instance_id": f"{agent_prefix}_{TASK_ID}_attempt_001",
        "result_ref": result_ref,
        "artifact_id": artifact_id,
        "artifact_ref": artifact_ref,
        "artifact_package_ref": package_ref,
        "receipt_ref": receipt_ref,
        "timestamp_utc": timestamp,
        "created_by": "orchestrator",
    }


def agent_terminated_event(
    artifact_ref: str,
    receipt_ref: str,
    *,
    role: str = "developer",
    event_type: str = "AGENT_TERMINATED",
    result_ref: str = RESULT_REF,
    timestamp: str = "2026-05-25T10:02:00Z",
) -> dict[str, object]:
    agent_prefix = "audit" if role == "auditor" else "agent"
    return {
        "event": "auditor_agent_terminated" if role == "auditor" else "agent_instance_terminated",
        "event_type": event_type,
        "task_id": TASK_ID,
        "agent_role": role,
        "role": role,
        "agent_instance_id": f"{agent_prefix}_{TASK_ID}_attempt_001",
        "result_ref": result_ref,
        "artifact_refs": [artifact_ref],
        "artifact_receipt_refs": [receipt_ref],
        "timestamp_utc": timestamp,
        "created_by": "orchestrator",
    }


def audit_route_ready_event(
    artifact_ref: str,
    receipt_ref: str,
    *,
    role: str = "developer",
    previous_event_type: str = "AGENT_TERMINATED",
    result_ref: str = RESULT_REF,
    timestamp: str = "2026-05-25T10:02:01Z",
) -> dict[str, object]:
    agent_prefix = "audit" if role == "auditor" else "agent"
    return {
        "event": "audit_route_ready",
        "event_type": "AUDIT_ROUTE_READY",
        "task_id": TASK_ID,
        "agent_role": role,
        "role": role,
        "agent_instance_id": f"{agent_prefix}_{TASK_ID}_attempt_001",
        "result_ref": result_ref,
        "artifact_refs": [artifact_ref],
        "artifact_receipt_refs": [receipt_ref],
        "timestamp_utc": timestamp,
        "created_by": "orchestrator",
        "previous_event_type": previous_event_type,
        "next_allowed_action": "checkpoint_preflight" if role == "auditor" else "audit_route",
    }


def audit_result_received_event(status: str) -> dict[str, object]:
    return {
        "event": "audit_result_received",
        "event_type": "AUDIT_RESULT_RECEIVED",
        "status": status,
        "task_id": TASK_ID,
        "agent_role": "auditor",
        "role": "auditor",
        "agent_instance_id": f"audit_{TASK_ID}_attempt_001",
        "result_ref": AUDIT_RESULT_REF,
        "timestamp_utc": "2026-05-25T10:03:00Z",
        "created_by": "orchestrator",
    }


def full_auditor_lifecycle_events(root: Path, audit_status: str) -> list[dict[str, object]]:
    profile_artifact_ref, profile_package_ref, profile_receipt_ref = write_artifact_refs(root)
    audit_artifact_id = f"AUDIT_RESULT_{TASK_ID}_ATTEMPT_001"
    audit_artifact_ref, audit_package_ref, audit_receipt_ref = write_artifact_refs(
        root,
        artifact_id=audit_artifact_id,
    )
    return [
        result_received_event(),
        artifact_accepted_event(profile_artifact_ref, profile_package_ref, profile_receipt_ref),
        agent_terminated_event(profile_artifact_ref, profile_receipt_ref),
        audit_route_ready_event(profile_artifact_ref, profile_receipt_ref),
        audit_result_received_event(audit_status),
        artifact_accepted_event(
            audit_artifact_ref,
            audit_package_ref,
            audit_receipt_ref,
            role="auditor",
            result_ref=AUDIT_RESULT_REF,
            artifact_id=audit_artifact_id,
            timestamp="2026-05-25T10:04:00Z",
        ),
        agent_terminated_event(
            audit_artifact_ref,
            audit_receipt_ref,
            role="auditor",
            event_type="AUDITOR_AGENT_TERMINATED",
            result_ref=AUDIT_RESULT_REF,
            timestamp="2026-05-25T10:05:00Z",
        ),
        audit_route_ready_event(
            audit_artifact_ref,
            audit_receipt_ref,
            role="auditor",
            previous_event_type="AUDITOR_AGENT_TERMINATED",
            result_ref=AUDIT_RESULT_REF,
            timestamp="2026-05-25T10:05:01Z",
        ),
    ]


class LifecycleStateReconciliationTests(unittest.TestCase):
    def test_manual_result_received_log_without_sidecar_materialization_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result(root)
            write_lifecycle_events(root, [result_received_event()])
            verify_json = Path(tmp) / "state-verify.json"
            plan_json = Path(tmp) / "plan-next.json"
            status_json = Path(tmp) / "status.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))
            status = run_aso(root, "status", "--mode", "workspace", "--json-out", str(status_json))

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            verify_report = json.loads(verify_json.read_text(encoding="utf-8"))
            rule_ids = {finding["rule_id"] for finding in verify_report["findings"]}
            self.assertIn("RUNTIME_NEXT_ACTION_STALE", rule_ids)
            self.assertIn("RUNTIME_LIFECYCLE_RESULT_REGISTRY_STALE", rule_ids)
            self.assertEqual(verify_report["reconciliation"]["current_state"], "RESULT_PENDING_ARTIFACT_ACCEPTANCE")
            self.assertEqual(
                verify_report["reconciliation"]["next_action"]["recommended_next_action"],
                "ACCEPT_ARTIFACT",
            )

            self.assertEqual(plan.returncode, 1, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "ACCEPT_ARTIFACT")
            self.assertNotEqual(plan_report["recommended_next_action"], "CREATE_AGENT")
            self.assertEqual(plan_report["evidence"]["next_action"]["routing_source"], "transition_engine")
            self.assertEqual(plan_report["evidence"]["transition_engine"]["current_state"], "RESULT_PENDING_ARTIFACT_ACCEPTANCE")

            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
            status_report = json.loads(status_json.read_text(encoding="utf-8"))
            status_rule_ids = {finding["rule_id"] for finding in status_report["findings"]}
            self.assertIn("RUNTIME_NEXT_ACTION_STALE", status_rule_ids)
            self.assertEqual(status_report["summary"]["runtime_consistency"], "FAIL")

    def test_confirmed_receive_result_materializes_accept_artifact_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result(root)
            receive = run_aso(
                root,
                "lifecycle",
                "receive-result",
                "--from-result",
                RESULT_REF,
                "--confirm-write",
            )
            verify_json = Path(tmp) / "state-verify.json"
            plan_json = Path(tmp) / "plan-next.json"

            verify = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_json))
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))

            self.assertEqual(receive.returncode, 0, receive.stdout + receive.stderr)
            receive_report = json.loads(receive.stdout)
            self.assertEqual(receive_report["state_materialization"]["status"], "written")
            receipt_ref = receive_report["state_materialization"]["receipt_ref"]
            self.assertTrue((root / receipt_ref).is_file())
            receipt = json.loads((root / receipt_ref).read_text(encoding="utf-8"))
            self.assertEqual(receipt["receipt_type"], "STATE_RECONCILIATION_RECEIPT")
            self.assertEqual(receipt["state_verify_after"]["status"], "passed")
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            verify_report = json.loads(verify_json.read_text(encoding="utf-8"))
            self.assertEqual(verify_report["status"], "passed")
            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "ACCEPT_ARTIFACT")
            self.assertEqual(plan_report["route_status"], "ready")
            self.assertFalse(plan_report["fatal"])

    def test_manual_agent_terminated_log_routes_auditor_but_remains_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result(root)
            artifact_ref, package_ref, receipt_ref = write_artifact_refs(root)
            write_lifecycle_events(
                root,
                [
                    result_received_event(),
                    artifact_accepted_event(artifact_ref, package_ref, receipt_ref),
                    agent_terminated_event(artifact_ref, receipt_ref),
                ],
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_aso(root, "plan-next", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "CREATE_AUDITOR")
            self.assertNotEqual(report["recommended_next_action"], "CREATE_AGENT")
            self.assertEqual(report["target_role"], "auditor")
            self.assertEqual(report["evidence"]["transition_engine"]["current_state"], "AGENT_TERMINATED")

    def test_audit_fail_lifecycle_routes_correction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result(root)
            write_result(root, AUDIT_RESULT_REF, status="fail", role="auditor")
            write_lifecycle_events(
                root,
                [
                    result_received_event(),
                    audit_result_received_event("fail"),
                ],
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_aso(root, "plan-next", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(report["route_status"], "ready")
            self.assertEqual(report["evidence"]["transition_engine"]["current_state"], "CORRECTION_REQUIRED")

    def test_full_auditor_fail_lifecycle_keeps_correction_route_after_auditor_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result(root)
            write_result(root, AUDIT_RESULT_REF, status="fail", role="auditor")
            events = full_auditor_lifecycle_events(root, "fail")
            write_lifecycle_events(root, events)
            json_out = Path(tmp) / "plan-next.json"

            result = run_aso(root, "plan-next", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(report["route_status"], "ready")
            self.assertNotEqual(report["recommended_next_action"], "WAIT_FOR_AUDIT_RESULT")
            transition = report["evidence"]["transition_engine"]
            self.assertEqual(transition["current_state"], "CORRECTION_REQUIRED")
            self.assertEqual(transition["transition_selected"]["derivation"], "lifecycle_log")
            lifecycle_events = transition["inputs"]["sidecar_state_signals"]["lifecycle_events"]
            self.assertEqual(
                [event["event"] for event in lifecycle_events[-4:]],
                ["AUDIT_RESULT_RECEIVED_FAIL", "ARTIFACT_ACCEPTED", "AGENT_TERMINATED", "AUDIT_ROUTE_READY"],
            )
            self.assertTrue(lifecycle_events[-2]["auditor_event"])
            self.assertFalse(lifecycle_events[-2]["applied_to_state"])
            self.assertEqual(lifecycle_events[-2]["state_after"], "CORRECTION_REQUIRED")
            self.assertTrue(lifecycle_events[-1]["auditor_event"])
            self.assertFalse(lifecycle_events[-1]["applied_to_state"])
            self.assertEqual(lifecycle_events[-1]["state_after"], "CORRECTION_REQUIRED")

    def test_full_auditor_pass_lifecycle_keeps_checkpoint_route_after_auditor_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result(root)
            write_result(root, AUDIT_RESULT_REF, status="pass", role="auditor")
            events = full_auditor_lifecycle_events(root, "pass")
            write_lifecycle_events(root, events)
            json_out = Path(tmp) / "plan-next.json"

            result = run_aso(root, "plan-next", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertNotEqual(report["recommended_next_action"], "WAIT_FOR_AUDIT_RESULT")
            transition = report["evidence"]["transition_engine"]
            self.assertEqual(transition["current_state"], "CHECKPOINT_ELIGIBLE")
            self.assertEqual(transition["transition_selected"]["derivation"], "lifecycle_log")
            lifecycle_events = transition["inputs"]["sidecar_state_signals"]["lifecycle_events"]
            self.assertEqual(
                [event["event"] for event in lifecycle_events[-4:]],
                ["AUDIT_RESULT_RECEIVED_PASS", "ARTIFACT_ACCEPTED", "AGENT_TERMINATED", "AUDIT_ROUTE_READY"],
            )
            self.assertTrue(lifecycle_events[-2]["auditor_event"])
            self.assertFalse(lifecycle_events[-2]["applied_to_state"])
            self.assertEqual(lifecycle_events[-2]["state_after"], "CHECKPOINT_ELIGIBLE")
            self.assertTrue(lifecycle_events[-1]["auditor_event"])
            self.assertFalse(lifecycle_events[-1]["applied_to_state"])
            self.assertEqual(lifecycle_events[-1]["state_after"], "CHECKPOINT_ELIGIBLE")


if __name__ == "__main__":
    unittest.main()
