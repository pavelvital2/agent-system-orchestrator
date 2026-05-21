from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "09_validators" / "schemas" / "product_artifacts"
TEMPLATE_DIR = ROOT / "03_templates" / "product_artifacts"
AGGREGATE_SCHEMA = SCHEMA_DIR / "product_artifact.schema.json"

ARTIFACTS = {
    "PRODUCT_INTAKE": {
        "schema": "product_intake.schema.json",
        "template": "product_intake.template.json",
        "definition": "productIntakeArtifact",
    },
    "OPEN_QUESTIONS": {
        "schema": "open_questions.schema.json",
        "template": "open_questions.template.json",
        "definition": "openQuestionsArtifact",
    },
    "OWNER_DECISION_CARDS": {
        "schema": "owner_decision_cards.schema.json",
        "template": "owner_decision_cards.template.json",
        "definition": "ownerDecisionCardsArtifact",
    },
    "PRODUCT_SPEC": {
        "schema": "product_spec.schema.json",
        "template": "product_spec.template.json",
        "definition": "productSpecArtifact",
    },
    "USER_STORIES": {
        "schema": "user_stories.schema.json",
        "template": "user_stories.template.json",
        "definition": "userStoriesArtifact",
    },
    "ACCEPTANCE_CRITERIA": {
        "schema": "acceptance_criteria.schema.json",
        "template": "acceptance_criteria.template.json",
        "definition": "acceptanceCriteriaArtifact",
    },
    "CAPABILITY_MATRIX": {
        "schema": "capability_matrix.schema.json",
        "template": "capability_matrix.template.json",
        "definition": "capabilityMatrixArtifact",
    },
    "PRODUCT_PLAN": {
        "schema": "product_plan.schema.json",
        "template": "product_plan.template.json",
        "definition": "productPlanArtifact",
    },
}

COMMON_FIELDS = {
    "artifact_id",
    "artifact_type",
    "schema_version",
    "package_version",
    "runtime_schema_version",
    "created_at",
    "created_by",
    "target_root",
    "profile",
    "readiness_mode",
    "status",
    "source_refs",
    "human_summary",
}

FORBIDDEN_PRODUCT_COMPLETION_STATUSES = {
    "implemented",
    "mvp_ready",
    "product_pass",
    "final_acceptance",
    "checkpoint_done",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return loaded


def resolve_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/$defs/"):
        raise AssertionError(f"unsupported test ref: {ref}")
    name = ref.rsplit("/", 1)[1]
    resolved = root_schema["$defs"][name]
    if not isinstance(resolved, dict):
        raise AssertionError(f"schema definition is not an object: {name}")
    return resolved


def collect_properties(root_schema: dict[str, Any], schema: dict[str, Any]) -> set[str]:
    if "$ref" in schema:
        return collect_properties(root_schema, resolve_ref(root_schema, str(schema["$ref"])))
    properties = set(schema.get("properties", {}).keys())
    for item in schema.get("allOf", []):
        if isinstance(item, dict):
            properties.update(collect_properties(root_schema, item))
    return properties


def validate_schema_fragment(root_schema: dict[str, Any], schema: dict[str, Any], value: Any, path: str) -> list[str]:
    if "$ref" in schema:
        return validate_schema_fragment(root_schema, resolve_ref(root_schema, str(schema["$ref"])), value, path)

    errors: list[str] = []
    for item in schema.get("allOf", []):
        if isinstance(item, dict):
            errors.extend(validate_schema_fragment(root_schema, item, value, path))

    one_of = schema.get("oneOf")
    if isinstance(one_of, list):
        passing = [
            branch
            for branch in one_of
            if isinstance(branch, dict) and not validate_schema_fragment(root_schema, branch, value, path)
        ]
        if len(passing) != 1:
            errors.append(f"{path}: expected exactly one matching artifact schema, got {len(passing)}")
        return errors

    expected_type = schema.get("type")
    if expected_type == "object" and not isinstance(value, dict):
        return [f"{path}: expected object"]
    if expected_type == "array" and not isinstance(value, list):
        return [f"{path}: expected array"]
    if expected_type == "string" and not isinstance(value, str):
        return [f"{path}: expected string"]
    if expected_type == "boolean" and not isinstance(value, bool):
        return [f"{path}: expected boolean"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in enum")
    if isinstance(value, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            errors.append(f"{path}: string shorter than {min_length}")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and not re.match(pattern, value):
            errors.append(f"{path}: value {value!r} does not match {pattern!r}")
    if isinstance(value, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(f"{path}: array shorter than {min_items}")
        items = schema.get("items")
        if isinstance(items, dict):
            for index, item in enumerate(value):
                errors.extend(validate_schema_fragment(root_schema, items, item, f"{path}[{index}]"))
    if isinstance(value, dict):
        for field in schema.get("required", []):
            if field not in value:
                errors.append(f"{path}: missing required field {field}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for field, field_schema in properties.items():
                if field in value and isinstance(field_schema, dict):
                    errors.extend(validate_schema_fragment(root_schema, field_schema, value[field], f"{path}.{field}"))
        if schema.get("additionalProperties") is False or schema.get("unevaluatedProperties") is False:
            allowed = collect_properties(root_schema, schema)
            for field in value:
                if field not in allowed:
                    errors.append(f"{path}: unexpected field {field}")
    return errors


def artifact_definition(root_schema: dict[str, Any], artifact_type: str) -> dict[str, Any]:
    name = ARTIFACTS[artifact_type]["definition"]
    definition = root_schema["$defs"][name]
    if not isinstance(definition, dict):
        raise AssertionError(f"artifact definition is not an object: {name}")
    return definition


class ProductArtifactSchemaTests(unittest.TestCase):
    def test_schema_files_are_present_and_link_to_aggregate_definitions(self) -> None:
        aggregate = load_json(AGGREGATE_SCHEMA)
        self.assertEqual(aggregate["$schema"], "https://json-schema.org/draft/2020-12/schema")

        common_required = set(aggregate["$defs"]["commonEnvelope"]["required"])
        self.assertEqual(common_required, COMMON_FIELDS)

        one_of_refs = {entry["$ref"] for entry in aggregate["oneOf"]}
        for artifact_type, config in ARTIFACTS.items():
            schema = load_json(SCHEMA_DIR / config["schema"])
            definition_ref = f"product_artifact.schema.json#/$defs/{config['definition']}"
            self.assertEqual(schema["title"], artifact_type)
            self.assertEqual(schema["$ref"], definition_ref)
            self.assertIn(f"#/$defs/{config['definition']}", one_of_refs)

            definition = aggregate["$defs"][config["definition"]]
            self.assertEqual(definition["properties"]["artifact_type"]["const"], artifact_type)

    def test_templates_conform_to_stdlib_schema_checks(self) -> None:
        aggregate = load_json(AGGREGATE_SCHEMA)
        for artifact_type, config in ARTIFACTS.items():
            with self.subTest(artifact_type=artifact_type):
                template = load_json(TEMPLATE_DIR / config["template"])
                errors = validate_schema_fragment(aggregate, aggregate, template, "$")
                self.assertEqual(errors, [])
                self.assertEqual(template["artifact_type"], artifact_type)
                self.assertEqual(template["schema_version"], "1.0.0")
                self.assertEqual(template["package_version"], "3.6.0")
                self.assertEqual(template["runtime_schema_version"], "3.1.0")
                self.assertEqual(template["created_by"], "aso")
                self.assertTrue(str(template["target_root"]).startswith("project-runtime/product/"))
                self.assertNotIn(template["status"], FORBIDDEN_PRODUCT_COMPLETION_STATUSES)

    def test_templates_do_not_store_secret_values(self) -> None:
        for config in ARTIFACTS.values():
            template = load_json(TEMPLATE_DIR / config["template"])
            raw = json.dumps(template, sort_keys=True)
            self.assertNotIn("secret_value", raw)
            for secret in template.get("required_secrets", []):
                self.assertNotIn("value", secret)
                self.assertEqual(secret["value_status"], "not_collected")
                self.assertRegex(secret["name"], r"^[A-Z][A-Z0-9_]*$")

    def test_product_plan_template_is_non_executable(self) -> None:
        template = load_json(TEMPLATE_DIR / ARTIFACTS["PRODUCT_PLAN"]["template"])
        self.assertFalse(template["creates_task_packets"])
        self.assertFalse(template["queues_dispatches"])
        self.assertFalse(template["executes_checkpoints"])
        self.assertFalse(template["performs_commits"])
        self.assertFalse(template["performs_deployments"])
        self.assertIn("no_live_dispatch", template["non_executable_constraints"])
        self.assertIn("no_secret_collection", template["non_executable_constraints"])

    def test_negative_missing_common_field_fails_stdlib_schema_checks(self) -> None:
        aggregate = load_json(AGGREGATE_SCHEMA)
        template = load_json(TEMPLATE_DIR / ARTIFACTS["PRODUCT_INTAKE"]["template"])
        invalid = copy.deepcopy(template)
        invalid.pop("artifact_id")

        errors = validate_schema_fragment(aggregate, artifact_definition(aggregate, "PRODUCT_INTAKE"), invalid, "$")

        self.assertTrue(any("missing required field artifact_id" in error for error in errors), errors)

    def test_negative_executable_product_plan_fails_stdlib_schema_checks(self) -> None:
        aggregate = load_json(AGGREGATE_SCHEMA)
        template = load_json(TEMPLATE_DIR / ARTIFACTS["PRODUCT_PLAN"]["template"])
        invalid = copy.deepcopy(template)
        invalid["creates_task_packets"] = True

        errors = validate_schema_fragment(aggregate, artifact_definition(aggregate, "PRODUCT_PLAN"), invalid, "$")

        self.assertTrue(any("expected const False" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
