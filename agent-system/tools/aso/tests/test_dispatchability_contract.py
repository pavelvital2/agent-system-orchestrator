from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - optional dependency in minimal envs
    Draft202012Validator = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_PATH = REPO_ROOT / "agent-system/02_runtime/PLANNER_DISPATCHABILITY_GATE_P5_4_CONTRACT.md"
SCHEMA_PATH = REPO_ROOT / "agent-system/09_validators/schemas/dispatchability_gate.schema.json"
TASK_PACKET_SCHEMA_PATH = REPO_ROOT / "agent-system/09_validators/schemas/task_packet.schema.json"


def load_contract() -> dict[str, object]:
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    match = re.search(r"```json\n(?P<payload>\{.*?\})\n```", text, flags=re.DOTALL)
    if match is None:
        raise AssertionError("dispatchability contract must expose one machine-readable JSON block")
    return json.loads(match.group("payload"))


def all_passed_checks(schema: dict[str, object]) -> list[dict[str, object]]:
    defs = schema["$defs"]
    if not isinstance(defs, dict):
        raise AssertionError("schema defs must be a dictionary")
    check_def = defs["check"]
    if not isinstance(check_def, dict):
        raise AssertionError("check definition must be a dictionary")
    properties = check_def["properties"]
    if not isinstance(properties, dict):
        raise AssertionError("check properties must be a dictionary")
    check_id = properties["check_id"]
    if not isinstance(check_id, dict):
        raise AssertionError("check_id schema must be a dictionary")
    enum = check_id["enum"]
    if not isinstance(enum, list):
        raise AssertionError("check_id enum must be a list")
    return [
        {
            "check_id": str(item),
            "passed": True,
            "severity": "info",
            "reason_code": "none",
            "evidence": "fixture",
        }
        for item in enum
    ]


def valid_create_agent_report(schema: dict[str, object]) -> dict[str, object]:
    return {
        "contract_id": "ASO_PLANNER_DISPATCHABILITY_GATE_P5_4",
        "contract_version": "1.0.0",
        "dispatchable": True,
        "verdict": "dispatchable",
        "recommended_next_action": "CREATE_AGENT",
        "status": "ready",
        "target_role": "developer",
        "role_class": "profile_execution",
        "action_type": "create_agent",
        "action_class": "dispatch",
        "task_id": "TASK_VALID_001",
        "task_packet": "project-runtime/tasks/active/TASK_VALID_001.md",
        "checks": all_passed_checks(schema),
        "reasons": [],
        "live_dispatch_performed": False,
    }


class DispatchabilityContractTests(unittest.TestCase):
    def test_machine_contract_distinguishes_profile_and_control_roles(self) -> None:
        contract = load_contract()
        task_packet_schema = json.loads(TASK_PACKET_SCHEMA_PATH.read_text(encoding="utf-8"))

        profile_roles = contract["profile_execution_roles"]
        control_roles = contract["control_or_pseudo_roles"]

        self.assertEqual(profile_roles, task_packet_schema["properties"]["TARGET_ROLE"]["enum"])
        self.assertIn("auditor", profile_roles)
        self.assertIn("orchestrator", control_roles)
        self.assertIn("project_owner", control_roles)
        self.assertIn("owner", control_roles)
        self.assertIn("none", control_roles)
        self.assertTrue(set(profile_roles).isdisjoint(set(control_roles)))

    def test_machine_contract_distinguishes_dispatch_from_internal_actions(self) -> None:
        contract = load_contract()

        self.assertEqual(contract["dispatch_capable_action_types"], ["create_agent"])
        non_dispatch = contract["non_dispatch_action_types"]
        if not isinstance(non_dispatch, dict):
            raise AssertionError("non_dispatch_action_types must be a dictionary")

        self.assertEqual(non_dispatch["correction"], "CORRECTION_REQUIRED")
        self.assertEqual(non_dispatch["wait_for_owner"], "ASK_OWNER")
        self.assertEqual(non_dispatch["stop"], "STOP")
        self.assertNotIn("correction", contract["dispatch_capable_action_types"])

    def test_canonical_invalid_tuple_forbids_create_agent(self) -> None:
        contract = load_contract()
        invalid_tuple = contract["canonical_invalid_tuple"]
        if not isinstance(invalid_tuple, dict):
            raise AssertionError("canonical_invalid_tuple must be a dictionary")
        expected = invalid_tuple["expected"]
        if not isinstance(expected, dict):
            raise AssertionError("canonical invalid expected value must be a dictionary")

        self.assertFalse(expected["dispatchable"])
        self.assertEqual(expected["verdict"], "not_dispatchable")
        self.assertEqual(expected["recommended_next_action"], "CORRECTION_REQUIRED")
        self.assertIn("CREATE_AGENT", expected["forbidden_recommended_next_actions"])
        self.assertEqual(
            expected["required_reason_codes"],
            [
                "action_type_not_dispatch_capable",
                "target_role_not_profile_execution",
                "target_role_control_or_pseudo",
                "task_id_none",
                "task_packet_none",
            ],
        )

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_dispatchability_schema_accepts_dispatchable_and_canonical_invalid_reports(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)

        dispatchable = valid_create_agent_report(schema)

        canonical_invalid = {
            "contract_id": "ASO_PLANNER_DISPATCHABILITY_GATE_P5_4",
            "contract_version": "1.0.0",
            "dispatchable": False,
            "verdict": "not_dispatchable",
            "recommended_next_action": "CORRECTION_REQUIRED",
            "status": "correction_required",
            "target_role": "orchestrator",
            "role_class": "control_or_pseudo",
            "action_type": "correction",
            "action_class": "internal_correction",
            "task_id": "NONE",
            "task_packet": "NONE",
            "checks": [
                {
                    "check_id": "DG54_ACTION_TYPE_DISPATCH_CAPABLE",
                    "passed": False,
                    "severity": "error",
                    "reason_code": "action_type_not_dispatch_capable",
                    "evidence": "NEXT_ACTION.content.action_type=correction",
                },
                {
                    "check_id": "DG54_TARGET_ROLE_NOT_CONTROL",
                    "passed": False,
                    "severity": "error",
                    "reason_code": "target_role_control_or_pseudo",
                    "evidence": "NEXT_ACTION.content.target_role=orchestrator",
                },
            ],
            "reasons": [
                {
                    "reason_code": "action_type_not_dispatch_capable",
                    "message": "correction is an internal non-dispatch route",
                    "input_ref": "NEXT_ACTION.content.action_type",
                },
                {
                    "reason_code": "target_role_control_or_pseudo",
                    "message": "orchestrator is a control role",
                    "input_ref": "NEXT_ACTION.content.target_role",
                },
            ],
            "live_dispatch_performed": False,
        }

        self.assertEqual(list(validator.iter_errors(dispatchable)), [])
        self.assertEqual(list(validator.iter_errors(canonical_invalid)), [])

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_schema_rejects_create_agent_for_control_role_or_live_dispatch(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        report = {
            "contract_id": "ASO_PLANNER_DISPATCHABILITY_GATE_P5_4",
            "contract_version": "1.0.0",
            "dispatchable": True,
            "verdict": "dispatchable",
            "recommended_next_action": "CREATE_AGENT",
            "status": "ready",
            "target_role": "orchestrator",
            "role_class": "control_or_pseudo",
            "action_type": "create_agent",
            "action_class": "dispatch",
            "task_id": "TASK_BAD_001",
            "task_packet": "project-runtime/tasks/active/TASK_BAD_001.md",
            "checks": all_passed_checks(schema),
            "reasons": [],
            "live_dispatch_performed": True,
        }

        errors = sorted(validator.iter_errors(report), key=lambda error: list(error.path))
        messages = "\n".join(error.message for error in errors)

        self.assertIn("'profile_execution' was expected", messages)
        self.assertIn("'orchestrator' is not one of", messages)
        self.assertIn("False was expected", messages)

        no_live_dispatch = copy.deepcopy(report)
        no_live_dispatch["target_role"] = "developer"
        no_live_dispatch["role_class"] = "profile_execution"
        no_live_dispatch["live_dispatch_performed"] = False

        self.assertEqual(list(validator.iter_errors(no_live_dispatch)), [])

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_schema_rejects_create_agent_with_none_task_values_or_failed_check(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        report = valid_create_agent_report(schema)
        report["task_id"] = "NONE"
        report["task_packet"] = "NONE"
        report["checks"][0]["passed"] = False
        report["checks"][0]["severity"] = "error"
        report["checks"][0]["reason_code"] = "action_type_not_dispatch_capable"

        errors = sorted(validator.iter_errors(report), key=lambda error: list(error.path))
        messages = "\n".join(error.message for error in errors)

        self.assertIn("'NONE' should not be valid under", messages)
        self.assertIn("should not be valid under {'enum': ['', 'NONE', 'none', 'null', 'UNKNOWN']}", messages)
        self.assertIn("should not be valid under {'contains':", messages)

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_schema_rejects_create_agent_for_canonical_non_dispatch_tuple(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        report = valid_create_agent_report(schema)
        report.update(
            {
                "dispatchable": False,
                "verdict": "not_dispatchable",
                "recommended_next_action": "CREATE_AGENT",
                "status": "correction_required",
                "target_role": "orchestrator",
                "role_class": "control_or_pseudo",
                "action_type": "correction",
                "action_class": "internal_correction",
                "task_id": "NONE",
                "task_packet": "NONE",
            }
        )

        errors = sorted(validator.iter_errors(report), key=lambda error: list(error.path))
        messages = "\n".join(error.message for error in errors)

        self.assertIn("True was expected", messages)
        self.assertIn("'dispatchable' was expected", messages)
        self.assertIn("'profile_execution' was expected", messages)
        self.assertIn("'create_agent' was expected", messages)
        self.assertIn("'dispatch' was expected", messages)
        self.assertIn("'orchestrator' is not one of", messages)
        self.assertIn("'CREATE_AGENT' should not be valid under", messages)


if __name__ == "__main__":
    unittest.main()
