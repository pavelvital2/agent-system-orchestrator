from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ASO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool import handoff_artifacts  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import result_parser  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import role_output_contracts  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import transition_engine  # noqa: E402


class RoleOutputContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = transition_engine.load_runtime_contract()

    def test_runtime_contract_declares_role_output_contracts_for_dispatchable_roles(self) -> None:
        role_contracts = self.contract["role_output_contracts"]

        self.assertEqual(role_contracts["contract_version"], "1.0.0")
        self.assertEqual(role_contracts["common_result_required_fields"], list(result_parser.REQUIRED_RESULT_FIELDS))
        self.assertTrue(role_contracts["self_validation"]["required_before_result"])
        self.assertIn("VALIDATION_NOT_RUN_REASON", role_contracts["self_validation"]["required_evidence_labels"])
        self.assertTrue(role_contracts["first_pass_acceptance_metrics"]["stage1_final_report_required"])
        self.assertIn("first_pass_accepted", role_contracts["first_pass_acceptance_metrics"]["fields"])

        for role in transition_engine.load_runtime_contract()["allowed_roles"]:
            with self.subTest(role=role):
                role_contract = role_contracts["roles"][role]
                self.assertIn("expected_result_path_template", role_contract)
                self.assertIn("required_skeletons", role_contract)
                self.assertIn("output_paths", role_contract)

    def test_role_summary_materializes_worker_skeletons_and_paths(self) -> None:
        summary = role_output_contracts.result_contract_summary(
            self.contract,
            "developer",
            self.contract["required_docs_by_role"]["developer"],
        )

        self.assertEqual(summary["role"], "developer")
        self.assertEqual(summary["result_kind"], "worker_result")
        self.assertEqual(
            summary["expected_result_path_template"],
            "project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_001.md",
        )
        self.assertIn("RESULT_ACCEPTANCE_MODE", summary["result_acceptance"]["mode_field"])
        self.assertIn("STATUS", summary["required_result_fields"])
        self.assertEqual(summary["required_result_constants"]["REUSE_ALLOWED"], "false")
        self.assertIn("result_file", summary["minimal_skeletons"])
        self.assertIn("artifact_manifest", summary["minimal_skeletons"])
        self.assertIn("correction_result", summary["minimal_skeletons"])
        self.assertEqual(summary["minimal_skeletons"]["result_file"]["marker"], "RESULT:")
        self.assertIn("VALIDATION_STATUS: passed | not_run", summary["minimal_skeletons"]["result_file"]["validation_evidence_minimum"])
        self.assertTrue(summary["self_validation"]["required_before_result"])
        self.assertIn("schema validation fails", summary["pass_status_rule"])
        self.assertIn("first_pass_accepted", summary["first_pass_acceptance_metrics"]["fields"])

    def test_role_summary_materializes_audit_result_skeleton(self) -> None:
        summary = role_output_contracts.result_contract_summary(
            self.contract,
            "auditor",
            self.contract["required_docs_by_role"]["auditor"],
        )

        self.assertEqual(summary["result_kind"], "audit_result")
        self.assertEqual(
            summary["expected_result_path_template"],
            "project-runtime/results/audit/AUDIT_RESULT_<TASK_ID>_ATTEMPT_001.md",
        )
        self.assertIn("audit_result_file", summary["minimal_skeletons"])
        audit_skeleton = summary["minimal_skeletons"]["audit_result_file"]
        self.assertEqual(audit_skeleton["marker"], "AUDIT_RESULT:")
        self.assertIn("SOURCE_RESULT_REF: project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_<N>.md", audit_skeleton["validation_evidence_minimum"])
        self.assertIn("REASONING_LEVEL_COMPLIANCE", audit_skeleton["mandatory_audit_labels"])
        self.assertNotIn("correction_result", summary["minimal_skeletons"])

    def test_handoff_payload_uses_compact_role_output_contract_without_template_doc(self) -> None:
        payload = handoff_artifacts.build_handoff_artifact(
            contract=self.contract,
            task_id="TASK_DEMO_001",
            role="developer",
            resolved_reasoning_level="high",
            task_packet="project-runtime/tasks/active/TASK_DEMO_001.md",
        )
        validation = handoff_artifacts.validate_handoff_artifact(payload)

        self.assertTrue(validation.passed, validation.errors)
        result_summary = payload["result_contract_summary"]
        self.assertEqual(result_summary["role"], "developer")
        self.assertIn("minimal_skeletons", result_summary)
        self.assertIn("self_validation", result_summary)
        self.assertIn("first_pass_acceptance_metrics", result_summary)
        self.assertEqual(
            result_summary["output_paths"]["candidate_artifact_manifest"],
            "project-runtime/artifacts/candidates/<TASK_ID>/manifest.json",
        )

        required_paths = {doc["path"] for doc in payload["required_docs"]}
        self.assertNotIn("agent-system/03_templates/AGENT_RESULT_TEMPLATE.md", required_paths)
        self.assertNotIn("agent-system/01_roles/DEVELOPER.md", required_paths)

    def test_orchestrator_handoff_template_includes_role_output_contract_summary(self) -> None:
        template = json.loads(
            (REPO_ROOT / "agent-system/03_templates/orchestrator_handoff.template.json").read_text(encoding="utf-8")
        )
        result_summary = template["result_contract_summary"]

        self.assertIn("role_output_contract_summary", template["routine_context_includes"])
        self.assertIn("self_validation_contract", template["routine_context_includes"])
        self.assertIn("first_pass_acceptance_metrics", template["routine_context_includes"])
        self.assertIn("minimal_skeletons", result_summary)
        self.assertIn("self_validation", result_summary)
        self.assertIn("first_pass_acceptance_metrics", result_summary)
        self.assertIn("artifact_manifest", result_summary["minimal_skeletons"])


if __name__ == "__main__":
    unittest.main()
