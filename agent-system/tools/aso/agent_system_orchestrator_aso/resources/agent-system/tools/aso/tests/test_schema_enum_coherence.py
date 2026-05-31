from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
ASO_DIR = REPO_ROOT / "agent-system" / "tools" / "aso"
if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool import enum_registry  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import result_parser  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import role_registry  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import runtime_schema_contracts  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import state_materialization  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import transition_engine  # noqa: E402
from agent_system_orchestrator_aso.aso_tool.commands import lifecycle, state_verify  # noqa: E402


def _load_schema(name: str) -> dict[str, object]:
    path = REPO_ROOT / "agent-system" / "09_validators" / "schemas" / name
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{name} must contain a JSON object")
    return payload


def _at(payload: dict[str, object], *path: str) -> object:
    current: object = payload
    for part in path:
        if not isinstance(current, dict):
            raise AssertionError(f"{'.'.join(path)} is not an object")
        current = current[part]
    return current


def _enum(payload: dict[str, object], *path: str) -> tuple[str, ...]:
    value = _at(payload, *path)
    if not isinstance(value, list):
        raise AssertionError(f"{'.'.join(path)} is not an enum list")
    return tuple(str(item) for item in value)


class SchemaEnumCoherenceTests(unittest.TestCase):
    def test_task_kind_failure_type_and_acceptance_enums_match_registry(self) -> None:
        task_packet = _load_schema("task_packet.schema.json")
        task_registry = _load_schema("task_registry.schema.json")
        result_schema = _load_schema("result.schema.json")

        self.assertEqual(
            _enum(task_packet, "properties", "TASK_KIND", "enum"),
            enum_registry.TASK_KINDS,
        )
        self.assertEqual(
            _enum(task_registry, "$defs", "taskEntry", "properties", "task_kind", "enum"),
            enum_registry.TASK_KINDS,
        )
        self.assertEqual(
            _enum(task_packet, "properties", "FAILURE_TYPE", "enum"),
            enum_registry.FAILURE_TYPES,
        )
        self.assertEqual(
            _enum(task_packet, "properties", "RESULT_ACCEPTANCE_MODE", "enum"),
            enum_registry.RESULT_ACCEPTANCE_MODES,
        )
        self.assertEqual(
            _enum(task_registry, "$defs", "taskEntry", "properties", "result_acceptance_mode", "enum"),
            enum_registry.RESULT_ACCEPTANCE_MODES,
        )
        self.assertEqual(
            _enum(result_schema, "properties", "RESULT_ACCEPTANCE_MODE", "enum"),
            enum_registry.RESULT_ACCEPTANCE_MODES,
        )

    def test_runtime_status_schema_enums_match_registry(self) -> None:
        project_state = _load_schema("project_state.schema.json")
        current_gate = _load_schema("current_gate.schema.json")
        next_action = _load_schema("next_action.schema.json")

        self.assertEqual(
            _enum(project_state, "$defs", "content", "properties", "current_phase", "enum"),
            enum_registry.LIFECYCLE_STATUSES,
        )
        self.assertEqual(
            _enum(project_state, "$defs", "content", "properties", "audit_status", "enum"),
            enum_registry.AUDIT_STATUSES,
        )
        self.assertEqual(
            _enum(project_state, "$defs", "content", "properties", "project_checkpoint_status", "enum"),
            enum_registry.PROJECT_CHECKPOINT_STATUSES,
        )
        self.assertEqual(
            _enum(current_gate, "$defs", "content", "properties", "project_checkpoint_status", "enum"),
            enum_registry.PROJECT_CHECKPOINT_STATUSES,
        )
        self.assertEqual(
            _enum(next_action, "$defs", "content", "properties", "action_type", "enum"),
            enum_registry.ACTION_TYPES,
        )
        self.assertEqual(
            _enum(next_action, "$defs", "content", "properties", "dependency_status", "enum"),
            enum_registry.ACTION_STATUSES,
        )

    def test_active_versions_match_runtime_contract_and_runtime_state_contract(self) -> None:
        contract = transition_engine.load_runtime_contract()
        state_contract = _load_schema("runtime_state_3_1_0.contract.json")

        self.assertEqual(contract["package_version"], enum_registry.ACTIVE_PACKAGE_VERSION)
        self.assertEqual(contract["governance_ruleset_version"], enum_registry.ACTIVE_GOVERNANCE_RULESET_VERSION)
        self.assertEqual(contract["runtime_schema_version"], enum_registry.ACTIVE_RUNTIME_SCHEMA_VERSION)
        self.assertEqual(state_contract["package_version"], enum_registry.ACTIVE_PACKAGE_VERSION)
        self.assertEqual(state_contract["governance_ruleset_version"], enum_registry.ACTIVE_GOVERNANCE_RULESET_VERSION)
        self.assertEqual(state_contract["runtime_schema_version"], enum_registry.ACTIVE_RUNTIME_SCHEMA_VERSION)
        self.assertEqual(runtime_schema_contracts.validate_contract_document(state_contract).errors, ())

    def test_invalid_enums_are_rejected(self) -> None:
        issues = result_parser.result_acceptance_issues(
            {"RESULT_ACCEPTANCE_MODE": "zip_file", "ARTIFACT_PACKAGE_REQUIRED": "false"},
            "profile_result",
        )
        self.assertEqual([issue.reason_code for issue in issues], ["invalid_result_acceptance_mode"])

        spec = state_verify.SIDECAR_BY_TYPE["TASK_REGISTRY"]
        content = {
            "registry_revision": 1,
            "tasks": [
                {
                    "task_id": "TASK_BAD_KIND",
                    "task_title": "Bad kind",
                    "task_type": "developer",
                    "task_kind": "runtime_magic",
                    "owner_role": "developer",
                    "status": "ready",
                    "task_packet": "project-runtime/tasks/TASK_BAD_KIND.md",
                    "dependencies": "NONE",
                    "requested_by_role": "NONE",
                    "requested_by_task": "NONE",
                    "return_to_requester_after_audit_pass": False,
                    "return_to_role_after_audit_pass": "none",
                    "return_task_after_audit_pass": "NONE",
                    "research_question_id": "NONE",
                    "result_refs": "NONE",
                    "audit_refs": "NONE",
                    "correction_links": "NONE",
                    "commit_hash": "NONE",
                    "branch": "NONE",
                    "push_status": "not_required",
                    "accepted_files": "NONE",
                    "checkpoint_ref": "NONE",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ],
        }
        findings = state_verify._validate_enum_values(spec, content, "project-runtime/state/TASK_REGISTRY.json")
        self.assertEqual([finding.rule_id for finding in findings], ["SIDECAR_ENUM_VALUE_INVALID"])

    def test_legacy_boolean_text_normalizes_with_warning_and_rendering_is_canonical(self) -> None:
        parsed = result_parser.parse_result(
            """RESULT:
STATUS: pass
TASK_ID: TASK_BOOL
AGENT_INSTANCE_ID: agent_TASK_BOOL_attempt_001
ROLE: developer
TASK: Boolean compatibility
SUMMARY: ok
READ_DOCS: NONE
READ_INPUTS: NONE
CHANGED_FILES: NONE
CREATED_FILES: NONE
DELETED_FILES: NONE
COMMANDS_RUN: NONE
TESTS_RUN: NONE
EVIDENCE: NONE
SCOPE_VERIFICATION: NONE
FORBIDDEN_CHANGES_CHECK: NONE
RISKS: NONE
LIMITATIONS: NONE
BLOCKERS: NONE
GAPS: NONE
NEXT_RECOMMENDED_ACTION: NONE
RESULT_ACCEPTANCE_MODE: artifact_package
ARTIFACT_PACKAGE_REQUIRED: yes
REUSE_ALLOWED: no
AGENT_TERMINATION_REQUIRED: yes
""",
            strict=True,
        )

        self.assertEqual(parsed.as_string("ARTIFACT_PACKAGE_REQUIRED"), "true")
        self.assertEqual(parsed.as_string("REUSE_ALLOWED"), "false")
        self.assertEqual(parsed.as_string("AGENT_TERMINATION_REQUIRED"), "true")
        self.assertTrue(
            all(issue.rule_id == "RESULT_FORMAT_LEGACY_BOOLEAN_NORMALIZED" for issue in parsed.issues)
        )
        self.assertEqual(state_materialization._markdown_value(True), "true")
        self.assertEqual(state_materialization._markdown_value(False), "false")
        self.assertEqual(lifecycle._markdown_value(True), "true")
        self.assertEqual(lifecycle._markdown_value(False), "false")

    def test_unknown_dispatch_ref_governed_field_is_rejected_until_schema_approved(self) -> None:
        spec = state_verify.SIDECAR_BY_TYPE["TASK_REGISTRY"]
        task_entry = {
            "task_id": "TASK_DISPATCH_REF",
            "task_title": "Dispatch ref rejection",
            "task_type": "developer",
            "task_kind": "normal",
            "owner_role": "developer",
            "status": "ready",
            "task_packet": "project-runtime/tasks/TASK_DISPATCH_REF.md",
            "dependencies": "NONE",
            "requested_by_role": "NONE",
            "requested_by_task": "NONE",
            "return_to_requester_after_audit_pass": False,
            "return_to_role_after_audit_pass": "none",
            "return_task_after_audit_pass": "NONE",
            "research_question_id": "NONE",
            "result_refs": "NONE",
            "audit_refs": "NONE",
            "correction_links": "NONE",
            "commit_hash": "NONE",
            "branch": "NONE",
            "push_status": "not_required",
            "accepted_files": "NONE",
            "checkpoint_ref": "NONE",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "dispatch_ref": "project-runtime/agents/dispatches/agent_TASK_DISPATCH_REF_attempt_001.json",
        }
        findings = state_verify._validate_required_fields(
            spec,
            {"registry_revision": 1, "tasks": [task_entry]},
            "project-runtime/state/TASK_REGISTRY.json",
        )

        self.assertIn("SIDECAR_UNKNOWN_GOVERNED_FIELD", [finding.rule_id for finding in findings])

    def test_runtime_contract_role_registry_is_canonical(self) -> None:
        contract = transition_engine.load_runtime_contract()

        self.assertEqual(role_registry.role_registry_errors(contract), ())
        self.assertEqual(role_registry.dispatchable_roles(contract), enum_registry.DISPATCHABLE_ROLE_IDS)
        self.assertEqual(role_registry.legacy_lifecycle_system_roles(), enum_registry.LEGACY_LIFECYCLE_SYSTEM_ROLE_IDS)
        self.assertEqual(role_registry.control_or_pseudo_roles(contract), enum_registry.CONTROL_OR_PSEUDO_ROLE_IDS)


if __name__ == "__main__":
    unittest.main()
