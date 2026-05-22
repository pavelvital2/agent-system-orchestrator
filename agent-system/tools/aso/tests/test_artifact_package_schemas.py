from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - optional test dependency
    Draft202012Validator = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[4]

SCHEMA_TEMPLATE_PAIRS = (
    (
        "agent-system/09_validators/schemas/artifact_package_manifest.schema.json",
        "agent-system/03_templates/artifact_package_manifest.template.json",
    ),
    (
        "agent-system/09_validators/schemas/result_package.schema.json",
        "agent-system/03_templates/result_package.template.json",
    ),
    (
        "agent-system/09_validators/schemas/audit_result_package.schema.json",
        "agent-system/03_templates/audit_result_package.template.json",
    ),
    (
        "agent-system/09_validators/schemas/structured_artifact.schema.json",
        "agent-system/03_templates/structured_artifact.template.json",
    ),
)

MANIFEST_REQUIRED_FIELDS = {
    "artifact_package_schema_version",
    "artifact_type",
    "artifact_id",
    "task_id",
    "role",
    "attempt_no",
    "status",
    "main_document",
    "structured_artifacts",
    "evidence_refs",
    "created_at",
    "producer",
}

ALLOWED_ARTIFACT_TYPES = [
    "RESULT",
    "AUDIT_RESULT",
    "TASK_PACKET",
    "GAP_REGISTER",
    "OWNER_QUESTION_CARD",
    "OWNER_DECISION",
    "LIFECYCLE_EVENT",
    "EVIDENCE_PACK",
]

MANDATORY_AUDIT_CHECKS = [
    "CHANGED_FILES_SCOPE_STATUS",
    "TASK_PACKET_SCHEMA_STATUS",
    "REPOSITORY_IDENTITY_STATUS",
    "FORBIDDEN_PATH_STATUS",
    "RUNTIME_MUTATION_STATUS",
    "EVIDENCE_STATUS",
    "SECRET_EXPOSURE_STATUS",
    "REASONING_LEVEL_COMPLIANCE",
    "VALIDATED_TASK_PACKETS",
]


class ArtifactPackageSchemaTests(unittest.TestCase):
    def _load_json(self, relpath: str) -> dict[str, object]:
        payload = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
        self.assertIsInstance(payload, dict, relpath)
        return payload

    def test_packaged_schema_and_template_json_files_parse(self) -> None:
        for schema_path, template_path in SCHEMA_TEMPLATE_PAIRS:
            with self.subTest(path=schema_path):
                self._load_json(schema_path)
            with self.subTest(path=template_path):
                self._load_json(template_path)

    def test_templates_keep_p5_version_tuple(self) -> None:
        for _, template_path in SCHEMA_TEMPLATE_PAIRS:
            with self.subTest(path=template_path):
                template = self._load_json(template_path)

                self.assertEqual(template["artifact_package_schema_version"], "1.0.0")
                if template_path == "agent-system/03_templates/artifact_package_manifest.template.json":
                    continue

                self.assertEqual(template["schema_version"], "1.0.0")
                self.assertEqual(template["package_version"], "3.7.0")
                self.assertEqual(template["governance_ruleset_version"], "3.7.0")
                self.assertEqual(template["runtime_schema_version"], "3.1.0")

    def test_contract_document_references_all_new_schemas_and_templates(self) -> None:
        contract = (
            REPO_ROOT / "agent-system/02_runtime/ARTIFACT_PACKAGE_SCHEMA_P5_1_0_CONTRACT.md"
        ).read_text(encoding="utf-8")

        for schema_path, template_path in SCHEMA_TEMPLATE_PAIRS:
            with self.subTest(path=schema_path):
                self.assertIn(schema_path, contract)
            with self.subTest(path=template_path):
                self.assertIn(template_path, contract)

        self.assertIn("project-input/", contract)
        self.assertIn("project-runtime/", contract)
        self.assertIn("project-archive/", contract)
        self.assertIn(".venv/", contract)

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_templates_match_their_json_schemas(self) -> None:
        for schema_path, template_path in SCHEMA_TEMPLATE_PAIRS:
            with self.subTest(schema=schema_path, template=template_path):
                schema = self._load_json(schema_path)
                template = self._load_json(template_path)
                Draft202012Validator.check_schema(schema)
                validator = Draft202012Validator(schema)

                errors = sorted(validator.iter_errors(template), key=lambda error: list(error.path))

                self.assertEqual(errors, [], "\n".join(error.message for error in errors))

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_manifest_rejects_workspace_local_artifact_paths(self) -> None:
        schema = self._load_json("agent-system/09_validators/schemas/artifact_package_manifest.schema.json")
        template = self._load_json("agent-system/03_templates/artifact_package_manifest.template.json")
        invalid_manifest = copy.deepcopy(template)
        invalid_manifest["main_document"] = "project-runtime/results/worker/RESULT_TASK_BAD_ATTEMPT_001.md"

        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(invalid_manifest), key=lambda error: list(error.path))

        self.assertGreater(len(errors), 0)
        self.assertIn("project-runtime", "\n".join(error.message for error in errors))

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_manifest_requires_canonical_schema_spec_fields(self) -> None:
        schema = self._load_json("agent-system/09_validators/schemas/artifact_package_manifest.schema.json")
        template = self._load_json("agent-system/03_templates/artifact_package_manifest.template.json")
        self.assertEqual(set(schema["required"]), MANIFEST_REQUIRED_FIELDS)
        self.assertEqual(set(template), MANIFEST_REQUIRED_FIELDS)

        validator = Draft202012Validator(schema)
        for field_name in sorted(MANIFEST_REQUIRED_FIELDS):
            with self.subTest(missing=field_name):
                invalid_manifest = copy.deepcopy(template)
                invalid_manifest.pop(field_name)
                errors = sorted(validator.iter_errors(invalid_manifest), key=lambda error: list(error.path))

                self.assertGreater(len(errors), 0)
                self.assertIn(field_name, "\n".join(error.message for error in errors))

    def test_manifest_allowed_artifact_types_match_schema_spec(self) -> None:
        schema = self._load_json("agent-system/09_validators/schemas/artifact_package_manifest.schema.json")

        self.assertEqual(schema["$defs"]["artifactType"]["enum"], ALLOWED_ARTIFACT_TYPES)

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_manifest_rejects_artifact_type_drift(self) -> None:
        schema = self._load_json("agent-system/09_validators/schemas/artifact_package_manifest.schema.json")
        template = self._load_json("agent-system/03_templates/artifact_package_manifest.template.json")
        invalid_manifest = copy.deepcopy(template)
        invalid_manifest["artifact_type"] = "UNDECLARED_ARTIFACT_TYPE"

        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(invalid_manifest), key=lambda error: list(error.path))

        self.assertGreater(len(errors), 0)
        self.assertIn("UNDECLARED_ARTIFACT_TYPE", "\n".join(error.message for error in errors))

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_audit_result_requires_every_mandatory_check_label(self) -> None:
        schema = self._load_json("agent-system/09_validators/schemas/audit_result_package.schema.json")
        template = self._load_json("agent-system/03_templates/audit_result_package.template.json")
        self.assertEqual(
            [check["check_id"] for check in template["mandatory_checks"]],
            MANDATORY_AUDIT_CHECKS,
        )

        validator = Draft202012Validator(schema)
        for check_id in MANDATORY_AUDIT_CHECKS:
            with self.subTest(missing=check_id):
                invalid_audit = copy.deepcopy(template)
                invalid_audit["mandatory_checks"] = [
                    check for check in invalid_audit["mandatory_checks"] if check["check_id"] != check_id
                ]
                errors = sorted(validator.iter_errors(invalid_audit), key=lambda error: list(error.path))

                self.assertGreater(len(errors), 0)
                self.assertIn("does not contain items matching the given schema", "\n".join(error.message for error in errors))

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_result_packages_preserve_lifecycle_termination_constants(self) -> None:
        schema = self._load_json("agent-system/09_validators/schemas/result_package.schema.json")
        template = self._load_json("agent-system/03_templates/result_package.template.json")
        invalid_result = copy.deepcopy(template)
        invalid_result["reuse_allowed"] = True
        invalid_result["agent_termination_required"] = False

        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(invalid_result), key=lambda error: list(error.path))
        messages = "\n".join(error.message for error in errors)

        self.assertIn("False was expected", messages)
        self.assertIn("True was expected", messages)


if __name__ == "__main__":
    unittest.main()
