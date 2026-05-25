from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from importlib import util
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib


REPO_ROOT = Path(__file__).resolve().parents[4]
ASO_TOOL_ROOT = REPO_ROOT / "agent-system" / "tools" / "aso"
CLI = ASO_TOOL_ROOT / "aso.py"


RUNTIME_CONTRACT = REPO_ROOT / "agent-system" / "02_runtime" / "ORCHESTRATOR_RUNTIME_CONTRACT.json"
WRAPPER_INIT = REPO_ROOT / "agent-system" / "tools" / "aso" / "agent_system_orchestrator_aso" / "__init__.py"
PACKAGED_CROSS_LINK_RULES = (
    ASO_TOOL_ROOT
    / "agent_system_orchestrator_aso"
    / "resources"
    / "agent-system"
    / "09_validators"
    / "CROSS_LINK_VALIDATION_RULES.md"
)
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

if str(ASO_TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(ASO_TOOL_ROOT))

from agent_system_orchestrator_aso.aso_tool import lockfile  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import runtime_contract_fallback  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import runtime_schema_contracts  # noqa: E402


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


def _run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ASO_TOOL_ROOT)
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )


class VersionCoherenceTests(unittest.TestCase):
    def setUp(self) -> None:
        contract = _load_json(RUNTIME_CONTRACT)
        self.package_version = str(contract["package_version"])
        self.governance_version = str(contract["governance_ruleset_version"])
        self.runtime_schema_version = str(contract["runtime_schema_version"])
        self.artifact_schema_version = str(contract["artifact_package_schema_version"])

    def test_active_runtime_constants_match_current_contract_tuple(self) -> None:
        fallback = json.loads(runtime_contract_fallback.ORCHESTRATOR_RUNTIME_CONTRACT_JSON)

        self.assertEqual(runtime_schema_contracts.ACTIVE_PACKAGE_VERSION, self.package_version)
        self.assertEqual(runtime_schema_contracts.ACTIVE_GOVERNANCE_RULESET_VERSION, self.governance_version)
        self.assertEqual(runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION, self.runtime_schema_version)
        self.assertEqual(
            runtime_schema_contracts.ACTIVE_ARTIFACT_PACKAGE_SCHEMA_VERSION,
            self.artifact_schema_version,
        )
        self.assertEqual(lockfile.PACKAGE_VERSION, self.package_version)
        self.assertEqual(lockfile.RUNTIME_SCHEMA_VERSION, self.runtime_schema_version)
        self.assertEqual(fallback["package_version"], self.package_version)
        self.assertEqual(fallback["governance_ruleset_version"], self.governance_version)
        self.assertNotEqual(runtime_schema_contracts.ACTIVE_PACKAGE_VERSION, "3.7.8")
        self.assertNotEqual(runtime_schema_contracts.ACTIVE_GOVERNANCE_RULESET_VERSION, "3.7.8")

    def test_package_metadata_matches_runtime_contract(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        package_versioning = (REPO_ROOT / "agent-system" / "PACKAGE_VERSIONING.md").read_text(encoding="utf-8")
        authority_map = (REPO_ROOT / "agent-system" / "02_runtime" / "CONTRACT_AUTHORITY_MAP.md").read_text(
            encoding="utf-8"
        )
        cross_link_rule_paths = (
            REPO_ROOT / "agent-system" / "09_validators" / "CROSS_LINK_VALIDATION_RULES.md",
            PACKAGED_CROSS_LINK_RULES,
        )

        self.assertEqual(pyproject["project"]["version"], self.package_version)
        spec = util.spec_from_file_location("agent_system_orchestrator_aso", WRAPPER_INIT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        wrapper = util.module_from_spec(spec)
        spec.loader.exec_module(wrapper)
        self.assertEqual(wrapper.__version__, self.package_version)
        self.assertIn(f"CURRENT_PACKAGE_VERSION: {self.package_version}", package_versioning)
        self.assertIn(f"CURRENT_GOVERNANCE_RULESET_VERSION: {self.governance_version}", package_versioning)
        self.assertIn(f"package_version: {self.package_version}", authority_map)
        self.assertIn(f"governance_ruleset_version: {self.governance_version}", authority_map)
        for path in cross_link_rule_paths:
            with self.subTest(cross_link_rules=path):
                cross_link_rules = path.read_text(encoding="utf-8")
                self.assertIn(f"CURRENT_PACKAGE_VERSION: {self.package_version}", cross_link_rules)
                self.assertIn(f"CURRENT_GOVERNANCE_RULESET_VERSION: {self.governance_version}", cross_link_rules)
                self.assertNotIn("CURRENT_PACKAGE_VERSION: 3.7.8", cross_link_rules)
                self.assertNotIn("CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.8", cross_link_rules)

    def test_generated_state_and_lockfile_use_active_tuple_without_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project-input").mkdir()
            (root / "project-input" / "TZ.md").write_text("# TZ\n\nVersion coherence.\n", encoding="utf-8")

            init = _run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Version Coherence",
                "--project-slug",
                "version-coherence",
                "--tz",
                "project-input/TZ.md",
                "--confirm-write",
                "--deterministic-timestamps",
            )
            generated_lockfile = lockfile.generate_lockfile(
                project_name="Version Coherence",
                project_slug="version-coherence",
                repo_url=None,
            )
            lockfile_validation = lockfile.validate_lockfile(generated_lockfile)

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            self.assertTrue(lockfile_validation.ok, lockfile_validation.to_json())
            project_state = _load_json(root / "project-runtime" / "state" / "PROJECT_STATE.json")
            schema_manifest = _load_json(root / "project-runtime" / "state" / "SCHEMA_MANIFEST.json")
            project_state_content = project_state["content"]
            schema_manifest_content = schema_manifest["content"]
            self.assertIsInstance(project_state_content, dict)
            self.assertIsInstance(schema_manifest_content, dict)
            self.assertEqual(project_state_content["package_version"], self.package_version)
            self.assertEqual(project_state_content["governance_ruleset_version"], self.governance_version)
            self.assertEqual(schema_manifest_content["package_version"], self.package_version)
            self.assertEqual(generated_lockfile["aso_engine"]["version"], self.package_version)  # type: ignore[index]

            generated_outputs = {
                "state_init_receipt": init.stdout,
                "project_state": json.dumps(project_state, sort_keys=True),
                "schema_manifest": json.dumps(schema_manifest, sort_keys=True),
                "aso_lock": lockfile.lockfile_json(generated_lockfile),
            }
            for label, text in generated_outputs.items():
                with self.subTest(output=label):
                    self.assertNotIn('"package_version": "3.7.8"', text)
                    self.assertNotIn('"governance_ruleset_version": "3.7.8"', text)
                    self.assertNotIn('"version": "3.7.8"', text)

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
