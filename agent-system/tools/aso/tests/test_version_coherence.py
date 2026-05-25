from __future__ import annotations

import json
import re
import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


RUNTIME_CONTRACT = REPO_ROOT / "agent-system" / "02_runtime" / "ORCHESTRATOR_RUNTIME_CONTRACT.json"
ACTIVE_SCHEMA_FILES = (
    "agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json",
    "agent-system/09_validators/schemas/schema_manifest.schema.json",
    "agent-system/09_validators/schemas/result_package.schema.json",
    "agent-system/09_validators/schemas/audit_result_package.schema.json",
    "agent-system/09_validators/schemas/structured_artifact.schema.json",
    "agent-system/09_validators/schemas/proposal_artifact.schema.json",
    "agent-system/09_validators/schemas/apply_receipt.schema.json",
)
ACTIVE_TEMPLATE_FILES = (
    "agent-system/03_templates/result_package.template.json",
    "agent-system/03_templates/audit_result_package.template.json",
    "agent-system/03_templates/structured_artifact.template.json",
    "agent-system/03_templates/proposal_artifact.template.json",
    "agent-system/03_templates/apply_receipt.template.json",
)


def _load_json(relpath: str | Path) -> dict[str, object]:
    path = REPO_ROOT / relpath if isinstance(relpath, str) else relpath
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return payload


def _schema_const(schema: dict[str, object], *path: str) -> str:
    current: object = schema
    for part in path:
        if not isinstance(current, dict):
            raise AssertionError(f"schema path {'.'.join(path)} is not an object")
        current = current[part]
    if not isinstance(current, str):
        raise AssertionError(f"schema path {'.'.join(path)} is not a string")
    return current


class VersionCoherenceTests(unittest.TestCase):
    def setUp(self) -> None:
        contract = _load_json(RUNTIME_CONTRACT)
        self.package_version = str(contract["package_version"])
        self.governance_version = str(contract["governance_ruleset_version"])
        self.runtime_schema_version = str(contract["runtime_schema_version"])
        self.artifact_schema_version = str(contract["artifact_package_schema_version"])

    def test_package_metadata_matches_runtime_contract(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        package_versioning = (REPO_ROOT / "agent-system" / "PACKAGE_VERSIONING.md").read_text(encoding="utf-8")
        authority_map = (REPO_ROOT / "agent-system" / "02_runtime" / "CONTRACT_AUTHORITY_MAP.md").read_text(
            encoding="utf-8"
        )
        cross_link_rules = (REPO_ROOT / "agent-system" / "09_validators" / "CROSS_LINK_VALIDATION_RULES.md").read_text(
            encoding="utf-8"
        )

        self.assertEqual(pyproject["project"]["version"], self.package_version)
        self.assertIn(f"CURRENT_PACKAGE_VERSION: {self.package_version}", package_versioning)
        self.assertIn(f"CURRENT_GOVERNANCE_RULESET_VERSION: {self.governance_version}", package_versioning)
        self.assertIn(f"package_version: {self.package_version}", authority_map)
        self.assertIn(f"governance_ruleset_version: {self.governance_version}", authority_map)
        self.assertIn(f"CURRENT_PACKAGE_VERSION: {self.package_version}", cross_link_rules)
        self.assertIn(f"CURRENT_GOVERNANCE_RULESET_VERSION: {self.governance_version}", cross_link_rules)

    def test_active_schemas_and_templates_use_current_versions(self) -> None:
        runtime_contract = _load_json("agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json")
        self.assertEqual(runtime_contract["package_version"], self.package_version)
        self.assertEqual(runtime_contract["governance_ruleset_version"], self.governance_version)

        schema_manifest = _load_json("agent-system/09_validators/schemas/schema_manifest.schema.json")
        manifest_content = schema_manifest["properties"]["content"]["properties"]  # type: ignore[index]
        self.assertEqual(manifest_content["package_version"]["const"], self.package_version)  # type: ignore[index]
        self.assertEqual(manifest_content["governance_ruleset_version"]["const"], self.governance_version)  # type: ignore[index]

        for relpath in ACTIVE_SCHEMA_FILES:
            schema = _load_json(relpath)
            properties = schema.get("properties", {})
            with self.subTest(schema=relpath):
                if "package_version" in properties:
                    self.assertEqual(_schema_const(schema, "properties", "package_version", "const"), self.package_version)
                if "governance_ruleset_version" in properties:
                    self.assertEqual(
                        _schema_const(schema, "properties", "governance_ruleset_version", "const"),
                        self.governance_version,
                    )

        for relpath in ACTIVE_TEMPLATE_FILES:
            template = _load_json(relpath)
            with self.subTest(template=relpath):
                self.assertEqual(template["package_version"], self.package_version)
                if "governance_ruleset_version" in template:
                    self.assertEqual(template["governance_ruleset_version"], self.governance_version)
                self.assertEqual(template["runtime_schema_version"], self.runtime_schema_version)

    def test_active_contracts_do_not_retain_stale_current_version_consts(self) -> None:
        stale_version_pattern = re.compile(r'"const"\s*:\s*"(?:3\.7\.3|3\.7\.8)"')
        for relpath in ACTIVE_SCHEMA_FILES:
            with self.subTest(schema=relpath):
                text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
                self.assertIsNone(stale_version_pattern.search(text))

        for relpath in ACTIVE_TEMPLATE_FILES:
            with self.subTest(template=relpath):
                text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
                self.assertNotIn('"package_version": "3.7.3"', text)
                self.assertNotIn('"package_version": "3.7.8"', text)
                self.assertNotIn('"governance_ruleset_version": "3.7.3"', text)
                self.assertNotIn('"governance_ruleset_version": "3.7.8"', text)

    def test_lockfile_schema_marks_old_current_versions_as_legacy_compatible(self) -> None:
        schema = _load_json("agent-system/09_validators/schemas/aso_lock.schema.json")
        description = str(schema["description"])

        self.assertIn("active P58 3.7.9/3.1.1", description)
        self.assertIn("legacy-compatible P57 3.7.8/3.1.1", description)
        self.assertIn("legacy-compatible P5.3 3.7.3/3.1.1", description)


if __name__ == "__main__":
    unittest.main()
