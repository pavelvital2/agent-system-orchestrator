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


def load_dispatchability_schema() -> dict[str, object]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise AssertionError("dispatchability schema must be a dictionary")
    return schema


def object_at(payload: dict[str, object], key: str, context: str) -> dict[str, object]:
    value = payload[key]
    if not isinstance(value, dict):
        raise AssertionError(f"{context}.{key} must be a dictionary")
    return value


def list_at(payload: dict[str, object], key: str, context: str) -> list[object]:
    value = payload[key]
    if not isinstance(value, list):
        raise AssertionError(f"{context}.{key} must be a list")
    return value


def schema_properties(schema: dict[str, object]) -> dict[str, object]:
    return object_at(schema, "properties", "schema")


def schema_defs(schema: dict[str, object]) -> dict[str, object]:
    return object_at(schema, "$defs", "schema")


def find_then_for_const(schema: dict[str, object], property_name: str, const_value: object) -> dict[str, object]:
    for index, rule in enumerate(list_at(schema, "allOf", "schema")):
        if not isinstance(rule, dict):
            raise AssertionError(f"schema.allOf[{index}] must be a dictionary")
        condition = object_at(rule, "if", f"schema.allOf[{index}]")
        condition_props = object_at(condition, "properties", f"schema.allOf[{index}].if")
        if property_name not in condition_props:
            continue
        property_condition = object_at(condition_props, property_name, f"schema.allOf[{index}].if.properties")
        if property_condition.get("const") == const_value:
            return object_at(rule, "then", f"schema.allOf[{index}]")
    raise AssertionError(f"schema must define an allOf condition for {property_name}={const_value!r}")


def required_passed_check_ids(schema: dict[str, object]) -> set[str]:
    defs = schema_defs(schema)
    required_checks = object_at(defs, "createAgentRequiredPassedChecks", "schema.$defs")
    check_ids: set[str] = set()
    for index, rule in enumerate(list_at(required_checks, "allOf", "createAgentRequiredPassedChecks")):
        if not isinstance(rule, dict):
            raise AssertionError(f"createAgentRequiredPassedChecks.allOf[{index}] must be a dictionary")
        contains = object_at(rule, "contains", f"createAgentRequiredPassedChecks.allOf[{index}]")
        required = list_at(contains, "required", f"createAgentRequiredPassedChecks.allOf[{index}].contains")
        if required != ["check_id", "passed"]:
            raise AssertionError(f"required passed check rule {index} must require check_id and passed")
        properties = object_at(contains, "properties", f"createAgentRequiredPassedChecks.allOf[{index}].contains")
        check_id = object_at(properties, "check_id", f"createAgentRequiredPassedChecks.allOf[{index}].contains.properties")
        passed = object_at(properties, "passed", f"createAgentRequiredPassedChecks.allOf[{index}].contains.properties")
        if passed.get("const") is not True:
            raise AssertionError(f"required passed check rule {index} must require passed=true")
        const = check_id.get("const")
        if not isinstance(const, str):
            raise AssertionError(f"required passed check rule {index} must require a concrete check_id")
        check_ids.add(const)
    return check_ids


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

    def test_dispatchability_schema_stdlib_preserves_root_required_contract(self) -> None:
        schema = load_dispatchability_schema()
        properties = schema_properties(schema)

        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["type"], "object")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            list_at(schema, "required", "schema"),
            [
                "contract_id",
                "contract_version",
                "dispatchable",
                "verdict",
                "recommended_next_action",
                "status",
                "target_role",
                "role_class",
                "action_type",
                "action_class",
                "task_id",
                "task_packet",
                "checks",
                "reasons",
                "live_dispatch_performed",
            ],
        )
        self.assertEqual(object_at(properties, "contract_id", "schema.properties")["const"], "ASO_PLANNER_DISPATCHABILITY_GATE_P5_4")
        self.assertEqual(object_at(properties, "contract_version", "schema.properties")["const"], "1.0.0")
        self.assertEqual(object_at(properties, "live_dispatch_performed", "schema.properties")["const"], False)
        self.assertIn("CREATE_AGENT", list_at(object_at(properties, "recommended_next_action", "schema.properties"), "enum", "recommended_next_action"))
        self.assertIn("profile_execution", list_at(object_at(properties, "role_class", "schema.properties"), "enum", "role_class"))
        self.assertIn("dispatch", list_at(object_at(properties, "action_class", "schema.properties"), "enum", "action_class"))

    def test_dispatchability_schema_stdlib_preserves_create_agent_constraints(self) -> None:
        schema = load_dispatchability_schema()
        then = find_then_for_const(schema, "recommended_next_action", "CREATE_AGENT")
        properties = object_at(then, "properties", "CREATE_AGENT.then")

        self.assertEqual(object_at(properties, "dispatchable", "CREATE_AGENT.then.properties")["const"], True)
        self.assertEqual(object_at(properties, "verdict", "CREATE_AGENT.then.properties")["const"], "dispatchable")
        self.assertEqual(object_at(properties, "role_class", "CREATE_AGENT.then.properties")["const"], "profile_execution")
        self.assertEqual(object_at(properties, "action_type", "CREATE_AGENT.then.properties")["const"], "create_agent")
        self.assertEqual(object_at(properties, "action_class", "CREATE_AGENT.then.properties")["const"], "dispatch")
        self.assertEqual(object_at(properties, "task_id", "CREATE_AGENT.then.properties")["$ref"], "#/$defs/realDispatchValue")
        self.assertEqual(object_at(properties, "task_packet", "CREATE_AGENT.then.properties")["$ref"], "#/$defs/realDispatchValue")
        self.assertEqual(
            list_at(object_at(properties, "target_role", "CREATE_AGENT.then.properties"), "enum", "CREATE_AGENT.target_role"),
            [
                "requirements_analyst",
                "solution_architect",
                "designer",
                "developer",
                "tester",
                "technical_writer",
                "devops_setup_engineer",
                "release_manager",
            ],
        )

    def test_dispatchability_schema_stdlib_preserves_required_passed_checks(self) -> None:
        schema = load_dispatchability_schema()
        check_def = object_at(schema_defs(schema), "check", "schema.$defs")
        check_properties = object_at(check_def, "properties", "schema.$defs.check")
        check_ids = set(list_at(object_at(check_properties, "check_id", "schema.$defs.check.properties"), "enum", "check_id"))

        self.assertEqual(required_passed_check_ids(schema), check_ids)

        then = find_then_for_const(schema, "recommended_next_action", "CREATE_AGENT")
        checks = object_at(object_at(then, "properties", "CREATE_AGENT.then"), "checks", "CREATE_AGENT.then.properties")
        check_rules = list_at(checks, "allOf", "CREATE_AGENT.then.properties.checks")
        self.assertEqual(check_rules[0], {"$ref": "#/$defs/createAgentRequiredPassedChecks"})
        no_failed_checks = object_at(check_rules[1], "not", "CREATE_AGENT.then.properties.checks.allOf[1]")
        contains = object_at(no_failed_checks, "contains", "CREATE_AGENT.then.properties.checks.allOf[1].not")
        self.assertEqual(list_at(contains, "required", "CREATE_AGENT.then.properties.checks.allOf[1].not.contains"), ["passed"])
        passed = object_at(object_at(contains, "properties", "CREATE_AGENT.then.properties.checks.allOf[1].not.contains"), "passed", "contains.properties")
        self.assertEqual(passed["const"], False)

    def test_dispatchability_schema_stdlib_preserves_non_dispatch_and_sentinel_constraints(self) -> None:
        schema = load_dispatchability_schema()
        defs = schema_defs(schema)
        real_dispatch_value = object_at(defs, "realDispatchValue", "schema.$defs")
        self.assertEqual(real_dispatch_value["type"], "string")
        self.assertEqual(real_dispatch_value["minLength"], 1)
        self.assertEqual(
            list_at(object_at(real_dispatch_value, "not", "schema.$defs.realDispatchValue"), "enum", "realDispatchValue.not"),
            ["", "NONE", "none", "null", "UNKNOWN"],
        )

        non_dispatch_then = find_then_for_const(schema, "dispatchable", False)
        non_dispatch_properties = object_at(non_dispatch_then, "properties", "dispatchable_false.then")
        self.assertEqual(object_at(non_dispatch_properties, "verdict", "dispatchable_false.then.properties")["const"], "not_dispatchable")
        self.assertEqual(
            object_at(object_at(non_dispatch_properties, "recommended_next_action", "dispatchable_false.then.properties"), "not", "recommended_next_action")["const"],
            "CREATE_AGENT",
        )
        self.assertEqual(list_at(non_dispatch_then, "required", "dispatchable_false.then"), ["reasons"])

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
