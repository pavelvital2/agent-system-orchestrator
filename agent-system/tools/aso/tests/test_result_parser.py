from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]

sys.path.insert(0, str(CLI.parents[0]))

from agent_system_orchestrator_aso.aso_tool import result_parser  # noqa: E402
from agent_system_orchestrator_aso.aso_tool.commands import record_result  # noqa: E402


def canonical_result(status: str = "pass") -> str:
    return f"""RESULT:
STATUS:
{status}

TASK_ID:
TASK_DEMO_001

AGENT_INSTANCE_ID:
agent_TASK_DEMO_001_attempt_001

ROLE:
developer

TASK:
TASK_DEMO_001

SUMMARY:
Done.
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
- RESULT_STATUS: {status}
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
- ROUTE_CORRECTION
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""


AUDIT_RESULT = """AUDIT_RESULT:
STATUS: fail
TASK_ID: TASK_DEMO_001
AGENT_INSTANCE_ID: audit_TASK_DEMO_001_attempt_001
ROLE: auditor
TASK: TASK_DEMO_001
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
- SOURCE_RESULT_REF: project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md
- CHANGED_FILES_SCOPE_STATUS: failed
SCOPE_VERIFICATION:
- TASK_PACKET_SCHEMA_STATUS: passed
FORBIDDEN_CHANGES_CHECK:
- FORBIDDEN_PATH_STATUS: passed
FINDINGS:
- Changed-files scope check failed.
FAILED_CHECKS:
- CHANGED_FILES_SCOPE_STATUS
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


AUDIT_PASS_WITH_REFERENCES = """AUDIT_RESULT:
STATUS:
PASS

TASK_ID:
TASK_DEMO_001

AGENT_INSTANCE_ID:
audit_TASK_DEMO_001_attempt_001

ROLE:
Auditor

TASK:
TASK_DEMO_001

SOURCE_RESULT_REF:
project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md

SUMMARY:
Audit passed with reference evidence.
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
- CANDIDATE_ARTIFACT_PACKAGE: project-runtime/artifacts/candidates/TASK_DEMO_001/manifest.json
- ACCEPTED_RESULT_PACKAGE_REF: project-runtime/artifacts/accepted/RESULT_PACKAGE_TASK_DEMO_001_ATTEMPT_001.json
- CORRECTION_TASK_REF: project-runtime/tasks/active/TASK_CORRECTION_TASK_DEMO_001.md
- FINAL_RUN_RECEIPT_REF: project-runtime/receipts/lifecycle/PROJECT_FINALIZATION_RECEIPT.json
- DISPATCH_RECEIPT_REF: project-runtime/agents/dispatches/audit_TASK_DEMO_001_attempt_001.json
- SOURCE_BOUNDARY_STATUS: passed
SCOPE_VERIFICATION:
- TASK_PACKET_SCHEMA_STATUS: passed
FORBIDDEN_CHANGES_CHECK:
- FORBIDDEN_PATH_STATUS: passed
FINDINGS:
- NONE
FAILED_CHECKS:
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
- CHECKPOINT_PREFLIGHT
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""


class ResultParserTests(unittest.TestCase):
    def test_strict_parser_accepts_template_scalar_values_on_next_line(self) -> None:
        parsed = result_parser.parse_result(canonical_result(), strict=True)

        self.assertFalse(parsed.has_error, [issue.to_json() for issue in parsed.issues])
        self.assertEqual(parsed.result_type, "profile_result")
        self.assertEqual(parsed.status, "pass")
        self.assertEqual(parsed.task_id, "TASK_DEMO_001")
        self.assertEqual(parsed.agent_instance_id, "agent_TASK_DEMO_001_attempt_001")
        self.assertEqual(parsed.role, "developer")

    def test_audit_result_details_include_findings_failed_checks_and_source_tasks(self) -> None:
        parsed = result_parser.parse_result(AUDIT_RESULT, strict=True)

        self.assertEqual(parsed.result_type, "audit_result")
        self.assertEqual(parsed.audit.status, "fail")
        self.assertIn("Changed-files scope check failed.", parsed.audit.findings)
        self.assertIn("CHANGED_FILES_SCOPE_STATUS", parsed.audit.failed_checks)
        self.assertEqual(
            list(parsed.audit.source_result_refs),
            ["project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md"],
        )
        self.assertIn("TASK_DEMO_001", parsed.audit.source_task_refs)

    def test_parser_normalizes_legacy_aliases_and_scalar_values(self) -> None:
        legacy = (
            canonical_result("PASS")
            .replace("STATUS:\nPASS", "RESULT_STATUS: PASS")
            .replace("ROLE:\ndeveloper", "ROLE: Developer")
            .replace("NEXT_RECOMMENDED_ACTION:", "NEXT_REQUIRED_ACTION:")
        )

        parsed = result_parser.parse_result(legacy, strict=True)

        self.assertFalse(parsed.has_error, [issue.to_json() for issue in parsed.issues])
        self.assertEqual(parsed.fields["STATUS"], "pass")
        self.assertEqual(parsed.status, "pass")
        self.assertEqual(parsed.role, "developer")
        self.assertIn("NEXT_RECOMMENDED_ACTION", parsed.fields)

    def test_parser_extracts_audit_reference_buckets_from_fields_and_evidence(self) -> None:
        parsed = result_parser.parse_result(AUDIT_PASS_WITH_REFERENCES, strict=True)

        self.assertFalse(parsed.has_error, [issue.to_json() for issue in parsed.issues])
        self.assertEqual(parsed.result_type, "audit_result")
        self.assertEqual(parsed.status, "pass")
        self.assertEqual(parsed.role, "auditor")
        self.assertEqual(
            list(parsed.references.source_result_refs),
            ["project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md"],
        )
        self.assertIn(
            "project-runtime/artifacts/accepted/RESULT_PACKAGE_TASK_DEMO_001_ATTEMPT_001.json",
            parsed.references.artifact_package_refs,
        )
        self.assertIn(
            "project-runtime/tasks/active/TASK_CORRECTION_TASK_DEMO_001.md",
            parsed.references.correction_refs,
        )
        self.assertEqual(
            list(parsed.references.final_run_receipt_refs),
            ["project-runtime/receipts/lifecycle/PROJECT_FINALIZATION_RECEIPT.json"],
        )
        self.assertEqual(
            list(parsed.references.dispatch_receipt_refs),
            ["project-runtime/agents/dispatches/audit_TASK_DEMO_001_attempt_001.json"],
        )
        self.assertEqual(list(parsed.references.source_boundary_evidence), ["SOURCE_BOUNDARY_STATUS: passed"])
        self.assertEqual(parsed.audit.to_json()["artifact_package_refs"], list(parsed.references.artifact_package_refs))

    def test_result_only_mode_normalizes_acceptance_metadata(self) -> None:
        text = canonical_result().replace(
            "SUMMARY:\nDone.",
            "\n".join(
                [
                    "RESULT_ACCEPTANCE_MODE: result_only",
                    "ARTIFACT_PACKAGE_REQUIRED: false",
                    "SUMMARY:",
                    "Done.",
                ]
            ),
        )

        parsed = result_parser.parse_result(text, strict=True)
        metadata = result_parser.result_acceptance_metadata(parsed.fields, parsed.result_type)

        self.assertFalse(parsed.has_error, [issue.to_json() for issue in parsed.issues])
        self.assertEqual(metadata["result_acceptance_mode"], "result_only")
        self.assertFalse(metadata["artifact_package_required"])

    def test_terminal_final_audit_receipt_reference_is_normalized(self) -> None:
        text = AUDIT_PASS_WITH_REFERENCES.replace("TASK_DEMO_001", "TASK_FINAL_AUDIT_DEMO_001")

        parsed = result_parser.parse_result(text, strict=True)

        self.assertFalse(parsed.has_error, [issue.to_json() for issue in parsed.issues])
        self.assertEqual(parsed.result_type, "audit_result")
        self.assertEqual(parsed.status, "pass")
        self.assertEqual(
            list(parsed.references.final_run_receipt_refs),
            ["project-runtime/receipts/lifecycle/PROJECT_FINALIZATION_RECEIPT.json"],
        )

    def test_inspect_audit_references_classifies_non_utf8_ref_as_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_ref = "project-runtime/results/audit/AUDIT_RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            audit_path = root / audit_ref
            audit_path.parent.mkdir(parents=True)
            audit_path.write_bytes(b"\xff\xfe\xfa")

            evidence = result_parser.inspect_audit_references(root, [audit_ref], task_id="TASK_DEMO_001", strict=True)

            self.assertEqual(evidence["passed_refs"], [])
            self.assertEqual(evidence["unparsed_refs"], [])
            invalid = evidence["invalid_refs"]
            self.assertEqual(len(invalid), 1)
            self.assertEqual(invalid[0]["ref"], audit_ref)
            self.assertEqual(invalid[0]["reason"], "audit_result_unreadable")
            self.assertIn("UnicodeDecodeError", invalid[0]["evidence"])

    def test_strict_parser_emits_shared_reason_codes_for_missing_identity_fields(self) -> None:
        parsed = result_parser.parse_result("RESULT:\nTASK: incomplete\n", strict=True)

        reason_codes = {issue.reason_code for issue in parsed.issues}
        self.assertIn(result_parser.REASON_MISSING_STATUS, reason_codes)
        self.assertIn(result_parser.REASON_MISSING_TASK_ID, reason_codes)
        self.assertIn(result_parser.REASON_MISSING_AGENT_INSTANCE_ID, reason_codes)
        self.assertIn(result_parser.REASON_MISSING_ROLE, reason_codes)

    def test_record_result_and_lifecycle_use_multiline_identity_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_path = root / "project-runtime" / "results" / "worker" / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.parent.mkdir(parents=True)
            result_path.write_text(canonical_result("fail"), encoding="utf-8")

            report, exit_code = record_result.build_report(result_path, strict=True)
            received = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "lifecycle",
                    "receive-result",
                    "--root",
                    str(root),
                    "--from-result",
                    str(result_path),
                    "--confirm-write",
                ],
                check=False,
                text=True,
                capture_output=True,
                cwd=REPO_ROOT,
            )

        self.assertEqual(exit_code, 0, report)
        self.assertEqual(report["role"], "developer")
        self.assertEqual(report["status"], "fail")
        self.assertEqual(received.returncode, 0, received.stdout + received.stderr)
        receive_report = json.loads(received.stdout)
        self.assertEqual(receive_report["event"]["role"], "developer")
        self.assertEqual(receive_report["event"]["agent_instance_id"], "agent_TASK_DEMO_001_attempt_001")


if __name__ == "__main__":
    unittest.main()
