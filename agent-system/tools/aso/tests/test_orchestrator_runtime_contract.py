from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - optional test dependency
    Draft202012Validator = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[4]
ASO_TOOL_ROOT = REPO_ROOT / "agent-system" / "tools" / "aso"

sys.path.insert(0, str(ASO_TOOL_ROOT))

from agent_system_orchestrator_aso.aso_tool import transition_engine  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import runtime_contract_fallback  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import role_registry  # noqa: E402


class OrchestratorRuntimeContractTests(unittest.TestCase):
    def _load_json(self, relpath: str) -> dict[str, object]:
        payload = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
        self.assertIsInstance(payload, dict, relpath)
        return payload

    def test_contract_loads_and_passes_stdlib_validation(self) -> None:
        contract = transition_engine.load_runtime_contract()
        validation = transition_engine.validate_runtime_contract(contract)

        self.assertTrue(validation.passed, validation.errors)
        self.assertEqual(contract["contract_version"], "1.0.0")
        self.assertEqual(contract["runtime_schema_version"], "3.1.1")
        self.assertEqual(contract["artifact_package_schema_version"], "1.1.0")

    def test_installed_package_fallback_matches_source_contract(self) -> None:
        contract = self._load_json("agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json")
        fallback = json.loads(runtime_contract_fallback.ORCHESTRATOR_RUNTIME_CONTRACT_JSON)

        self.assertEqual(fallback, contract)
        self.assertTrue(transition_engine.validate_runtime_contract(fallback).passed)

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_contract_matches_json_schema(self) -> None:
        contract = self._load_json("agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json")
        schema = self._load_json("agent-system/09_validators/schemas/orchestrator_runtime_contract.schema.json")

        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(contract), key=lambda error: list(error.path))

        self.assertEqual(errors, [], "\n".join(error.message for error in errors))

    def test_contract_defines_roles_events_artifacts_and_context_policy(self) -> None:
        contract = transition_engine.load_runtime_contract()

        allowed_roles = set(contract["allowed_roles"])
        forbidden_roles = set(contract["forbidden_dispatch_roles"])
        self.assertIn("developer", allowed_roles)
        self.assertIn("auditor", allowed_roles)
        self.assertNotIn("orchestrator", allowed_roles)
        self.assertIn("orchestrator", forbidden_roles)
        self.assertFalse(allowed_roles & forbidden_roles)

        for event_name in (
            "CREATE_AGENT_DISPATCHED",
            "RESULT_RECEIVED",
            "ARTIFACT_ACCEPTED",
            "AGENT_TERMINATED",
            "AUDIT_ROUTE_READY",
            "AUDIT_RESULT_RECEIVED_PASS",
            "AUDIT_RESULT_RECEIVED_FAIL",
        ):
            self.assertIn(event_name, contract["allowed_events"])

        artifact_contracts = contract["artifact_contracts"]
        self.assertEqual(artifact_contracts["candidate_manifest_canonical"], "manifest.json")
        self.assertIn("artifact_package_manifest.json", artifact_contracts["candidate_manifest_legacy_aliases"])
        self.assertEqual(artifact_contracts["accepted_manifest_canonical"], "manifest.json")

        context_policy = contract["routine_context_policy"]
        self.assertIn("ORCHESTRATOR_RUNTIME_CONTRACT.json", context_policy["orchestrator_must_read"])
        self.assertIn("all_role_docs", context_policy["orchestrator_must_not_read_routinely"])

        handoff_context = contract["handoff_context_builder_contract"]
        self.assertEqual(handoff_context["normal_context_mode"], "routine")
        self.assertIn("debug", handoff_context["allowed_context_modes"])
        self.assertIn("explain", handoff_context["allowed_context_modes"])
        self.assertIn("agent-system/03_templates/", handoff_context["routine_handoff_excludes"])
        self.assertIn("developer", handoff_context["target_role_doc_map"])
        self.assertEqual(
            handoff_context["target_role_doc_map"]["developer"],
            "agent-system/01_roles/DEVELOPER.md",
        )

    def test_roles_have_reasoning_floors_and_required_docs(self) -> None:
        contract = transition_engine.load_runtime_contract()

        for role in contract["allowed_roles"]:
            with self.subTest(role=role):
                self.assertIn(role, contract["reasoning_floor_by_role"])
                self.assertIn(contract["reasoning_floor_by_role"][role], {"medium", "high", "xhigh", "maximum"})
                self.assertIn(role, contract["required_docs_by_role"])
                self.assertGreater(len(contract["required_docs_by_role"][role]), 0)

    def test_dispatch_roles_are_derived_from_runtime_contract(self) -> None:
        contract = transition_engine.load_runtime_contract()
        expected = tuple(
            role
            for role in contract["allowed_roles"]
            if role not in set(contract["forbidden_dispatch_roles"])
        )

        self.assertEqual(role_registry.dispatchable_roles(contract), expected)
        self.assertNotIn("release_manager", role_registry.dispatchable_roles(contract))
        self.assertNotIn("devops_setup_engineer", role_registry.dispatchable_roles(contract))
        self.assertNotIn("designer", role_registry.dispatchable_roles(contract))
        self.assertIn("release_manager", role_registry.legacy_lifecycle_system_roles())

    def test_contract_defines_external_dispatch_receipt_contract(self) -> None:
        contract = transition_engine.load_runtime_contract()
        receipt_contract = contract["dispatch_receipt_contract"]

        self.assertEqual(
            receipt_contract["schema_ref"],
            "agent-system/09_validators/schemas/dispatch_receipt.schema.json",
        )
        self.assertEqual(
            receipt_contract["receipt_ref_template"],
            "project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json",
        )
        self.assertEqual(receipt_contract["runner"], "external_codex_cli")
        self.assertFalse(receipt_contract["live_dispatch_performed_by_aso"])
        self.assertIn("model_reasoning_effort", receipt_contract["external_runner_command_template"])
        self.assertTrue(
            {
                "runner",
                "model",
                "reasoning_effort",
                "prompt_ref",
                "task_id",
                "role",
                "started_at",
                "handoff_ref",
            }.issubset(set(receipt_contract["required_fields"]))
        )

    def test_contract_defines_profile_agent_handoff_artifact_contract(self) -> None:
        contract = transition_engine.load_runtime_contract()
        handoff_contract = contract["handoff_artifact_contract"]

        self.assertEqual(
            handoff_contract["schema_ref"],
            "agent-system/09_validators/schemas/orchestrator_handoff.schema.json",
        )
        self.assertEqual(
            handoff_contract["template_ref"],
            "agent-system/03_templates/orchestrator_handoff.template.json",
        )
        self.assertEqual(handoff_contract["handoff_ref_template"], "project-runtime/handoffs/<TASK_ID>.json")
        self.assertEqual(handoff_contract["prompt_ref_template"], "project-runtime/handoffs/<TASK_ID>.prompt.md")
        self.assertEqual(
            handoff_contract["expected_artifact_package_ref_template"],
            "project-runtime/artifacts/candidates/<TASK_ID>/manifest.json",
        )
        self.assertEqual(handoff_contract["runner"], "external_codex_cli")
        self.assertFalse(handoff_contract["live_dispatch_performed_by_aso"])
        self.assertIn("model_reasoning_effort", handoff_contract["external_runner_command_template"])
        self.assertIn("full governance corpus", handoff_contract["forbidden_governance_corpus_rule"])
        self.assertTrue(
            {
                "task_id",
                "role",
                "resolved_reasoning_level",
                "required_docs",
                "forbidden_docs",
                "prompt_ref",
                "expected_result_path",
                "expected_artifact_package_path",
                "lifecycle_policy",
            }.issubset(set(handoff_contract["required_fields"]))
        )


if __name__ == "__main__":
    unittest.main()
