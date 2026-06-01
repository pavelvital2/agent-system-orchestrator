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
    content(payload)["tz_path"] = "project-input/TZ.md"
    write_sidecar(root, "PROJECT_STATE.json", payload)
    update_markdown_field(root, "PROJECT_STATE.md", "TZ_PATH", "project-input/TZ.md")


def write_result(root: Path, *, mode: str, artifact_required: bool) -> Path:
    path = root / RESULT_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "RESULT:",
                "STATUS: pass",
                f"TASK_ID: {TASK_ID}",
                f"AGENT_INSTANCE_ID: agent_{TASK_ID}_attempt_001",
                "ROLE: developer",
                f"TASK: {TASK_ID}",
                f"RESULT_ACCEPTANCE_MODE: {mode}",
                f"ARTIFACT_PACKAGE_REQUIRED: {'true' if artifact_required else 'false'}",
                "SUMMARY:",
                "- Lifecycle mode fixture.",
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
                "- NONE",
                "SCOPE_VERIFICATION:",
                "- NONE",
                "FORBIDDEN_CHANGES_CHECK:",
                "- NONE",
                "RISKS:",
                "- NONE",
                "LIMITATIONS:",
                "- NONE",
                "BLOCKERS:",
                "- NONE",
                "GAPS:",
                "- NONE",
                "NEXT_RECOMMENDED_ACTION:",
                "- NONE",
                "REUSE_ALLOWED: false",
                "AGENT_TERMINATION_REQUIRED: true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def lifecycle_events(root: Path) -> list[dict[str, object]]:
    path = root / "project-runtime" / "agents" / "instances.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class ResultLifecycleModeTests(unittest.TestCase):
    def test_result_only_profile_result_routes_to_audit_without_synthetic_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result(root, mode="result_only", artifact_required=False)
            before_artifacts = content(load_sidecar(root, "ACCEPTED_ARTIFACTS.json"))["artifacts"]

            receive = run_aso(
                root,
                "lifecycle",
                "receive-result",
                "--from-result",
                RESULT_REF,
                "--confirm-write",
            )
            verify_after_receive_json = Path(tmp) / "verify-after-receive.json"
            verify_after_receive = run_aso(root, "state", "verify", "--strict", "--json-out", str(verify_after_receive_json))
            terminate = run_aso(
                root,
                "lifecycle",
                "terminate-agent",
                "--from-result",
                RESULT_REF,
                "--confirm-write",
            )
            plan_json = Path(tmp) / "plan.json"
            plan = run_aso(root, "plan-next", "--strict", "--json-out", str(plan_json))

            self.assertEqual(receive.returncode, 0, receive.stdout + receive.stderr)
            receive_report = json.loads(receive.stdout)
            self.assertEqual(receive_report["event"]["result_acceptance_mode"], "result_only")
            self.assertFalse(receive_report["event"]["artifact_package_required"])
            self.assertEqual(
                [event["event_type"] for event in receive_report["result_acceptance_events"]],
                ["RESULT_VALIDATED", "RESULT_ACCEPTED"],
            )
            self.assertEqual(verify_after_receive.returncode, 0, verify_after_receive.stdout + verify_after_receive.stderr)
            receive_verify = json.loads(verify_after_receive_json.read_text(encoding="utf-8"))
            self.assertEqual(receive_verify["reconciliation"]["current_state"], "RESULT_ACCEPTED")
            self.assertEqual(
                receive_verify["reconciliation"]["next_action"]["recommended_next_action"],
                "TERMINATE_AGENT",
            )
            self.assertEqual(terminate.returncode, 0, terminate.stdout + terminate.stderr)
            events = lifecycle_events(root)
            self.assertEqual(
                [event["event_type"] for event in events],
                ["RESULT_RECEIVED", "RESULT_VALIDATED", "RESULT_ACCEPTED", "AGENT_TERMINATED", "AUDIT_ROUTE_READY"],
            )
            termination_event = events[3]
            self.assertEqual(termination_event["artifact_ids"], [])
            self.assertEqual(termination_event["artifact_refs"], [])
            self.assertEqual(termination_event["artifact_receipt_refs"], [])

            after_artifacts = content(load_sidecar(root, "ACCEPTED_ARTIFACTS.json"))["artifacts"]
            self.assertEqual(after_artifacts, before_artifacts)
            self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["recommended_next_action"], "CREATE_AUDITOR")
            self.assertTrue(plan_report["dispatchable"])
            self.assertTrue(plan_report["dispatchability"]["dispatchable"])
            self.assertEqual(plan_report["evidence"]["transition_engine"]["current_state"], "AGENT_TERMINATED")

    def test_artifact_package_profile_result_still_requires_artifact_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result(root, mode="artifact_package", artifact_required=True)

            receive = run_aso(
                root,
                "lifecycle",
                "receive-result",
                "--from-result",
                RESULT_REF,
                "--confirm-write",
            )
            terminate = run_aso(
                root,
                "lifecycle",
                "terminate-agent",
                "--from-result",
                RESULT_REF,
                "--confirm-write",
            )

            self.assertEqual(receive.returncode, 0, receive.stdout + receive.stderr)
            receive_report = json.loads(receive.stdout)
            self.assertEqual(receive_report["result_acceptance_events"], [])
            self.assertEqual(terminate.returncode, 1, terminate.stdout + terminate.stderr)
            terminate_report = json.loads(terminate.stdout)
            rule_ids = {finding["rule_id"] for finding in terminate_report["findings"]}
            self.assertIn("LIFECYCLE_SEQUENCE_002", rule_ids)
            self.assertIn("ARTIFACT_ACCEPTED", terminate_report["findings"][0]["message"])


if __name__ == "__main__":
    unittest.main()
