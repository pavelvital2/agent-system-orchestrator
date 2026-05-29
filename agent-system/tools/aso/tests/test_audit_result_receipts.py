from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
TASK_ID = "TASK_DEMO_001"
WORKER_RESULT_REF = f"project-runtime/results/worker/RESULT_{TASK_ID}_ATTEMPT_001.md"
AUDIT_RESULT_REF = f"project-runtime/results/audit/AUDIT_RESULT_{TASK_ID}_ATTEMPT_001.md"


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


def write_audit_result(root: Path, *, mode: str = "", artifact_required: bool | None = None) -> Path:
    path = root / AUDIT_RESULT_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata: list[str] = []
    if mode:
        metadata.append(f"RESULT_ACCEPTANCE_MODE: {mode}")
    if artifact_required is not None:
        metadata.append(f"ARTIFACT_PACKAGE_REQUIRED: {'true' if artifact_required else 'false'}")
    path.write_text(
        "\n".join(
            [
                "AUDIT_RESULT:",
                "STATUS: pass",
                f"TASK_ID: {TASK_ID}",
                f"AGENT_INSTANCE_ID: audit_{TASK_ID}_attempt_001",
                "ROLE: auditor",
                f"TASK: {TASK_ID}",
                *metadata,
                "SUMMARY:",
                "- Audit passed.",
                "READ_DOCS:",
                "- NONE",
                "READ_INPUTS:",
                f"- {WORKER_RESULT_REF}",
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
                f"- SOURCE_RESULT_REF: {WORKER_RESULT_REF}",
                "- CHANGED_FILES_SCOPE_STATUS: passed",
                "SCOPE_VERIFICATION:",
                "- TASK_PACKET_SCHEMA_STATUS: passed",
                "- FORBIDDEN_PATH_STATUS: passed",
                "FORBIDDEN_CHANGES_CHECK:",
                "- FORBIDDEN_PATH_STATUS: passed",
                "FAILED_CHECKS:",
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
                "- CHECKPOINT_PREFLIGHT",
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


class AuditResultReceiptTests(unittest.TestCase):
    def test_audit_result_markdown_is_receipted_without_p5_artifact_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_path = write_audit_result(root)

            receive = run_aso(
                root,
                "lifecycle",
                "receive-result",
                "--from-result",
                AUDIT_RESULT_REF,
                "--confirm-write",
            )
            terminate = run_aso(
                root,
                "lifecycle",
                "terminate-agent",
                "--from-result",
                AUDIT_RESULT_REF,
                "--confirm-write",
            )
            record = run_record_result(result_path, "--strict")

            self.assertEqual(receive.returncode, 0, receive.stdout + receive.stderr)
            receive_report = json.loads(receive.stdout)
            event = receive_report["event"]
            self.assertEqual(event["event_type"], "AUDIT_RESULT_RECEIVED")
            self.assertEqual(event["receipt_type"], "AUDIT_RESULT_RECEIPT")
            self.assertEqual(event["result_acceptance_mode"], "result_only")
            self.assertFalse(event["artifact_package_required"])
            self.assertEqual(event["result_receipt"]["receipt_type"], "AUDIT_RESULT_RECEIPT")
            self.assertEqual(event["result_receipt"]["audit_result"]["status"], "pass")
            self.assertEqual(event["result_receipt"]["audit_result"]["source_result_refs"], [WORKER_RESULT_REF])
            self.assertEqual(receive_report["result_acceptance_events"], [])

            self.assertEqual(terminate.returncode, 0, terminate.stdout + terminate.stderr)
            events = lifecycle_events(root)
            self.assertEqual(
                [event["event_type"] for event in events],
                ["AUDIT_RESULT_RECEIVED", "AUDITOR_AGENT_TERMINATED", "AUDIT_ROUTE_READY"],
            )
            self.assertFalse(any(event["event_type"] == "ARTIFACT_ACCEPTED" for event in events))
            termination_event = events[1]
            self.assertEqual(termination_event["artifact_ids"], [])
            self.assertEqual(termination_event["artifact_receipt_refs"], [])

            self.assertEqual(record.returncode, 0, record.stdout + record.stderr)
            record_report = json.loads(record.stdout)
            self.assertTrue(record_report["checkpoint_candidate"])
            self.assertEqual(record_report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertEqual(record_report["evidence"]["result_acceptance_mode"], "result_only")
            self.assertFalse(record_report["evidence"]["artifact_package_required"])

    def test_audit_result_package_mode_requires_artifact_acceptance_when_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_audit_result(root, mode="artifact_package", artifact_required=True)

            receive = run_aso(
                root,
                "lifecycle",
                "receive-result",
                "--from-result",
                AUDIT_RESULT_REF,
                "--confirm-write",
            )
            terminate = run_aso(
                root,
                "lifecycle",
                "terminate-agent",
                "--from-result",
                AUDIT_RESULT_REF,
                "--confirm-write",
            )

            self.assertEqual(receive.returncode, 0, receive.stdout + receive.stderr)
            receive_report = json.loads(receive.stdout)
            self.assertEqual(receive_report["event"]["result_acceptance_mode"], "artifact_package")
            self.assertTrue(receive_report["event"]["artifact_package_required"])
            self.assertEqual(terminate.returncode, 1, terminate.stdout + terminate.stderr)
            terminate_report = json.loads(terminate.stdout)
            rule_ids = {finding["rule_id"] for finding in terminate_report["findings"]}
            self.assertIn("LIFECYCLE_SEQUENCE_002", rule_ids)
            self.assertIn("ARTIFACT_ACCEPTED", terminate_report["findings"][0]["message"])


if __name__ == "__main__":
    unittest.main()
