from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - optional test dependency
    Draft202012Validator = None  # type: ignore[assignment]


ASO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool import correction_routing  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import handoff_artifacts  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import result_parser  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import source_boundary  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import transition_engine  # noqa: E402


TASK_ID = "TASK_SOURCE_BOUNDARY_001"
AUDIT_REF = f"project-runtime/results/audit/AUDIT_RESULT_{TASK_ID}_ATTEMPT_001.md"
TASK_PACKET = f"project-runtime/tasks/active/{TASK_ID}.md"


def audit_result(*, severity: str, source_ref: str, status: str = "fail") -> str:
    return f"""AUDIT_RESULT:
STATUS: {status}
TASK_ID: {TASK_ID}
AGENT_INSTANCE_ID: audit_{TASK_ID}_attempt_001
ROLE: auditor
TASK: {TASK_ID}
SUMMARY:
Source-boundary audit fixture.
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
- SOURCE_RESULT_REF: project-runtime/results/worker/RESULT_{TASK_ID}_ATTEMPT_001.md
- SOURCE_BOUNDARY_STATUS: failed
- SOURCE_BOUNDARY_SEVERITY: {severity}
- SOURCE_BOUNDARY_RECOMMENDED_ACTION: ROUTE_BY_SEVERITY
- SOURCE_BOUNDARY_REF: {source_ref}
SCOPE_VERIFICATION:
- SOURCE_BOUNDARY_STATUS: failed
FORBIDDEN_CHANGES_CHECK:
- FORBIDDEN_PATH_STATUS: passed
RISKS:
- NONE
LIMITATIONS:
- NONE
BLOCKERS:
- source_boundary
GAPS:
- NONE
NEXT_RECOMMENDED_ACTION:
- ROUTE_CORRECTION
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""


class SourceBoundarySeverityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="aso-source-boundary-"))
        self.root = self.tmpdir / "workspace"
        (self.root / "project-runtime" / "results" / "audit").mkdir(parents=True)
        (self.root / "project-runtime" / "tasks" / "active").mkdir(parents=True)
        (self.root / TASK_PACKET).write_text("# TASK PACKET\n\nTASK_ID: TASK_SOURCE_BOUNDARY_001\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def _write_audit(self, text: str) -> Path:
        path = self.root / AUDIT_REF
        path.write_text(text, encoding="utf-8")
        return path

    def _task_registry_sidecars(self) -> dict[str, dict[str, object]]:
        return {
            "TASK_REGISTRY": {
                "content": {
                    "tasks": [
                        {
                            "task_id": TASK_ID,
                            "status": "failed",
                            "owner_role": "developer",
                            "audit_refs": [AUDIT_REF],
                        }
                    ]
                }
            }
        }

    def test_contract_defines_all_severity_tiers_and_allowed_sources_schema(self) -> None:
        contract = transition_engine.load_runtime_contract()
        source_contract = contract["source_boundary_contract"]

        self.assertEqual(source_contract["severity_order"], list(source_boundary.SEVERITIES))
        self.assertEqual(set(source_contract["correction_required_for"]), {"SB3_BLOCKING", "SB4_INVALIDATING"})
        self.assertIn("SB0_ALLOWED", source_contract["severity_tiers"])
        self.assertIn("own_handoff", source_contract["allowed_delivery_context_classes"])
        self.assertEqual(
            source_contract["schema_ref"],
            "agent-system/09_validators/schemas/allowed_sources.schema.json",
        )

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_generated_allowed_sources_json_validates_and_allows_own_delivery_context(self) -> None:
        contract = transition_engine.load_runtime_contract()
        payload = handoff_artifacts.build_handoff_artifact(
            contract=contract,
            task_id=TASK_ID,
            role="tester",
            resolved_reasoning_level="high",
            task_packet=TASK_PACKET,
        )
        allowed_sources = payload["allowed_sources"]
        schema = json.loads(
            (REPO_ROOT / "agent-system/09_validators/schemas/allowed_sources.schema.json").read_text(
                encoding="utf-8"
            )
        )

        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(allowed_sources), key=lambda error: list(error.path))

        self.assertEqual(errors, [], "\n".join(error.message for error in errors))
        allowed_refs = {entry["ref"]: entry for entry in allowed_sources["allowed_refs"]}
        self.assertEqual(allowed_refs[f"project-runtime/handoffs/{TASK_ID}.json"]["severity"], "SB0_ALLOWED")
        self.assertEqual(allowed_refs[f"project-runtime/handoffs/{TASK_ID}.prompt.md"]["severity"], "SB0_ALLOWED")
        self.assertEqual(allowed_refs[TASK_PACKET]["severity"], "SB0_ALLOWED")
        self.assertIn(source_boundary.DISPATCH_RECEIPT_REF_TEMPLATE, allowed_refs)
        forbidden_refs = {entry["ref"]: entry for entry in allowed_sources["forbidden_refs"]}
        self.assertEqual(forbidden_refs["agent-system/09_validators/"]["severity"], "SB3_BLOCKING")

    def test_reporting_only_own_prompt_source_boundary_fail_does_not_route_correction(self) -> None:
        audit_path = self._write_audit(
            audit_result(
                severity="SB1_REPORTING_ONLY",
                source_ref=f"project-runtime/handoffs/{TASK_ID}.prompt.md",
            )
        )
        parsed = result_parser.parse_result_file(audit_path)

        classification = parsed.audit.to_json()["source_boundary_evidence"]
        route = correction_routing.from_parsed_audit_result(root=self.root, result_path=audit_path, parsed=parsed)
        audit_evidence = transition_engine.audit_failure_evidence_from_sidecars(
            self.root,
            self._task_registry_sidecars(),
        )

        self.assertTrue(classification)
        self.assertEqual(route, {})
        self.assertEqual(audit_evidence["unresolved_audit_failures"], [])
        invalid = audit_evidence["task_evidence"][0]["invalid_audit_results"]
        self.assertTrue(invalid[0]["nonblocking_source_boundary_finding"])
        self.assertEqual(
            invalid[0]["source_boundary_classification"]["recommended_action"],
            "REPORT_ONLY",
        )

    def test_forbidden_critical_source_boundary_fail_routes_blocking_correction(self) -> None:
        audit_path = self._write_audit(
            audit_result(
                severity="SB3_BLOCKING",
                source_ref="agent-system/09_validators/RESULT_VALIDATION_RULES.md",
            )
        )
        parsed = result_parser.parse_result_file(audit_path)

        route = correction_routing.from_parsed_audit_result(root=self.root, result_path=audit_path, parsed=parsed)
        audit_evidence = transition_engine.audit_failure_evidence_from_sidecars(
            self.root,
            self._task_registry_sidecars(),
        )

        self.assertEqual(route["route"], "CORRECTION_REQUIRED")
        self.assertEqual(route["source_boundary_severity"], "SB3_BLOCKING")
        self.assertEqual(route["source_boundary_classification"]["recommended_action"], "ROUTE_CORRECTION")
        self.assertEqual(route["correction_task_packet_ref"], f"project-runtime/tasks/active/TASK_CORRECTION_{TASK_ID}.md")
        self.assertEqual(len(audit_evidence["unresolved_audit_failures"]), 1)

    def test_unclassified_source_boundary_failure_fails_closed_to_blocking(self) -> None:
        classification = source_boundary.classify_audit_result(
            failed_checks=["SOURCE_BOUNDARY_STATUS"],
            findings=[],
            source_boundary_evidence=[],
        )

        self.assertEqual(classification["severity"], "SB3_BLOCKING")
        self.assertTrue(classification["correction_required"])
        self.assertEqual(classification["recommended_action"], "ROUTE_CORRECTION")

    def test_invalidating_source_boundary_fail_requires_fresh_agent(self) -> None:
        audit_path = self._write_audit(
            audit_result(
                severity="SB4_INVALIDATING",
                source_ref=".env",
            )
        )
        parsed = result_parser.parse_result_file(audit_path)

        route = correction_routing.from_parsed_audit_result(root=self.root, result_path=audit_path, parsed=parsed)

        self.assertEqual(route["source_boundary_severity"], "SB4_INVALIDATING")
        self.assertTrue(route["fresh_agent_required"])
        self.assertEqual(
            route["source_boundary_classification"]["recommended_action"],
            "INVALIDATE_AND_REDISPATCH_FRESH_AGENT",
        )


if __name__ == "__main__":
    unittest.main()
