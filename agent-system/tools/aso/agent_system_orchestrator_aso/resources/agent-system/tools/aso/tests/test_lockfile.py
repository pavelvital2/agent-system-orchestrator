from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - optional dependency in minimal runtimes.
    Draft202012Validator = None


REPO_ROOT = Path(__file__).resolve().parents[4]
ASO_TOOL_ROOT = REPO_ROOT / "agent-system" / "tools" / "aso"
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "aso_lock"
SCHEMA_PATH = REPO_ROOT / "agent-system" / "09_validators" / "schemas" / "aso_lock.schema.json"

sys.path.insert(0, str(ASO_TOOL_ROOT))

from agent_system_orchestrator_aso.aso_tool import lockfile  # noqa: E402


class LockfileHelperTests(unittest.TestCase):
    def test_generate_lockfile_uses_project_factory_defaults(self) -> None:
        generated = lockfile.generate_lockfile(
            project_name="Demo Project",
            project_slug="demo-project",
            repo_url="https://github.com/example/demo-project.git",
        )

        result = lockfile.validate_lockfile(generated)
        aso_engine = generated["aso_engine"]
        publication_boundary = generated["publication_boundary"]

        self.assertTrue(result.ok, result.to_json())
        self.assertEqual(aso_engine["version"], lockfile.PACKAGE_VERSION)
        self.assertEqual(aso_engine["runtime_schema"], lockfile.RUNTIME_SCHEMA_VERSION)
        self.assertEqual(aso_engine["engine_mode"], "vendored")
        self.assertEqual(lockfile.SUPPORTED_ENGINE_MODES, ("vendored", "reference"))
        self.assertEqual(publication_boundary["ignored_roots"], list(lockfile.REQUIRED_PUBLICATION_ROOTS))
        self.assertEqual(
            publication_boundary["forbidden_tracked_roots"],
            list(lockfile.REQUIRED_PUBLICATION_ROOTS),
        )

    def test_generate_lockfile_records_source_provenance_without_schema_bump(self) -> None:
        vendored_hash = "sha256:" + ("a" * 64)
        generated = lockfile.generate_lockfile(
            project_name="Demo Project",
            project_slug="demo-project",
            repo_url="https://github.com/example/demo-project.git",
            source_repository="git@github.com:example/agent-system-orchestrator.git",
            source_branch="main",
            source_commit="abc123",
            source_dirty=False,
            vendored_tree_hash=vendored_hash,
        )

        result = lockfile.validate_lockfile(generated)
        aso_engine = generated["aso_engine"]

        self.assertTrue(result.ok, result.to_json())
        self.assertEqual(generated["lockfile_version"], "1.0")
        self.assertEqual(aso_engine["version"], lockfile.PACKAGE_VERSION)
        self.assertEqual(aso_engine["runtime_schema"], lockfile.RUNTIME_SCHEMA_VERSION)
        self.assertEqual(aso_engine["source_repository"], "git@github.com:example/agent-system-orchestrator.git")
        self.assertEqual(aso_engine["source_branch"], "main")
        self.assertEqual(aso_engine["source_commit"], "abc123")
        self.assertFalse(aso_engine["source_dirty"])
        self.assertEqual(aso_engine["vendored_tree_hash"], vendored_hash)

    def test_generate_lockfile_accepts_reference_engine_mode(self) -> None:
        generated = lockfile.generate_lockfile(
            project_name="Reference Project",
            project_slug="reference-project",
            repo_url=None,
            engine_mode="reference",
        )

        result = lockfile.validate_lockfile(generated)

        self.assertTrue(result.ok, result.to_json())
        self.assertEqual(generated["aso_engine"]["version"], lockfile.PACKAGE_VERSION)
        self.assertEqual(generated["aso_engine"]["runtime_schema"], lockfile.RUNTIME_SCHEMA_VERSION)
        self.assertEqual(generated["aso_engine"]["engine_mode"], "reference")

    def test_valid_fixture_passes_validation(self) -> None:
        result = lockfile.validate_lockfile_path(FIXTURE_ROOT / "valid_aso.lock")

        self.assertTrue(result.ok, result.to_json())
        self.assertEqual(result.findings, ())

    def test_compatible_p0_package_version_passes_validation(self) -> None:
        generated = lockfile.generate_lockfile(
            project_name="Demo Project",
            project_slug="demo-project",
            repo_url=None,
            package_version="3.2.0",
            runtime_schema="3.0.0",
        )

        result = lockfile.validate_lockfile(generated)

        self.assertTrue(result.ok, result.to_json())

    def test_legacy_compatible_p57_package_version_passes_validation(self) -> None:
        generated = lockfile.generate_lockfile(
            project_name="Demo Project",
            project_slug="demo-project",
            repo_url=None,
            package_version="3.7.8",
            runtime_schema="3.1.1",
        )

        result = lockfile.validate_lockfile(generated)

        self.assertTrue(result.ok, result.to_json())

    def test_mixed_compatible_version_tuples_fail_validation(self) -> None:
        cases = (
            ("3.2.0", "3.1.0"),
            ("3.3.0", "3.1.0"),
        )

        for package_version, runtime_schema in cases:
            with self.subTest(package_version=package_version, runtime_schema=runtime_schema):
                generated = lockfile.generate_lockfile(
                    project_name="Demo Project",
                    project_slug="demo-project",
                    repo_url=None,
                    package_version=package_version,
                    runtime_schema=runtime_schema,
                )

                result = lockfile.validate_lockfile(generated)

                self.assertFalse(result.ok)
                self.assertEqual(result.findings[0].rule_id, "ASO_LOCK_012")
                self.assertEqual(result.findings[0].path, "$.aso_engine")
                self.assertEqual(result.findings[0].evidence, f"{package_version}/{runtime_schema}")

    def test_invalid_fixture_fails_with_deterministic_errors(self) -> None:
        result = lockfile.validate_lockfile_path(FIXTURE_ROOT / "invalid_aso.lock")

        self.assertFalse(result.ok)
        self.assertEqual(
            [finding.rule_id for finding in result.findings],
            [
                "ASO_LOCK_008",
                "ASO_LOCK_009",
                "ASO_LOCK_010",
                "ASO_LOCK_010",
            ],
        )
        self.assertEqual(result.findings[0].path, "$.aso_engine.runtime_schema")
        self.assertIn("3.1.0", result.findings[0].message)

    def test_required_non_null_fields_reject_json_null(self) -> None:
        cases = (
            ("aso_engine.runtime_schema", ("aso_engine", "runtime_schema"), "$.aso_engine.runtime_schema"),
            ("aso_engine.engine_mode", ("aso_engine", "engine_mode"), "$.aso_engine.engine_mode"),
            ("project.name", ("project", "name"), "$.project.name"),
            (
                "publication_boundary.ignored_roots",
                ("publication_boundary", "ignored_roots"),
                "$.publication_boundary.ignored_roots",
            ),
        )

        for label, path_keys, expected_path in cases:
            with self.subTest(field=label):
                generated = lockfile.generate_lockfile(
                    project_name="Demo Project",
                    project_slug="demo-project",
                    repo_url=None,
                )
                mutated = copy.deepcopy(generated)
                section, field = path_keys
                mutated[section][field] = None

                result = lockfile.validate_lockfile(mutated)

                self.assertFalse(result.ok)
                self.assertEqual(result.findings[0].rule_id, "ASO_LOCK_007")
                self.assertEqual(result.findings[0].path, expected_path)
                self.assertEqual(result.findings[0].evidence, "null")

    def test_missing_and_malformed_files_fail_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            malformed = root / "aso.lock"
            malformed.write_text("{not-json\n", encoding="utf-8")

            missing_result = lockfile.validate_lockfile_path(root / "missing.lock")
            malformed_result = lockfile.validate_lockfile_path(malformed)

        self.assertFalse(missing_result.ok)
        self.assertEqual(missing_result.findings[0].rule_id, "ASO_LOCK_001")
        self.assertFalse(malformed_result.ok)
        self.assertEqual(malformed_result.findings[0].rule_id, "ASO_LOCK_002")

    def test_write_lockfile_round_trips_null_repo_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / lockfile.LOCKFILE_NAME
            generated = lockfile.generate_lockfile(
                project_name="Demo Project",
                project_slug="demo-project",
                repo_url=None,
            )

            lockfile.write_lockfile(path, generated)
            decoded = lockfile.read_lockfile(path)
            result = lockfile.validate_lockfile(decoded)

        self.assertTrue(result.ok, result.to_json())
        self.assertIsNone(decoded["project"]["repo_url"])

    def test_machine_readable_schema_tuples_remain_supported_by_lockfile_contract(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        aso_engine_properties = schema["$defs"]["aso_engine"]["properties"]
        aso_engine_tuple_constraints = schema["$defs"]["aso_engine"]["oneOf"]
        schema_tuples = [
            (
                constraint["properties"]["version"]["const"],
                constraint["properties"]["runtime_schema"]["const"],
            )
            for constraint in aso_engine_tuple_constraints
        ]

        self.assertIn(lockfile.PACKAGE_VERSION, lockfile.COMPATIBLE_PACKAGE_VERSIONS)
        schema_versions = set(aso_engine_properties["version"]["enum"])
        schema_tuples_set = set(schema_tuples)
        source_supported_tuples = set(lockfile.COMPATIBLE_ENGINE_VERSION_TUPLES)
        self.assertEqual(schema_versions, set(lockfile.COMPATIBLE_PACKAGE_VERSIONS))
        self.assertTrue(
            set(aso_engine_properties["runtime_schema"]["enum"]).issubset(lockfile.COMPATIBLE_RUNTIME_SCHEMA_VERSIONS)
        )
        self.assertEqual(
            aso_engine_properties["engine_mode"]["enum"],
            list(lockfile.SUPPORTED_ENGINE_MODES),
        )
        self.assertEqual(schema_tuples_set, source_supported_tuples)

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_machine_readable_schema_rejects_mixed_version_tuples(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        cases = (
            ("3.2.0", "3.1.0"),
            ("3.3.0", "3.1.0"),
        )

        for package_version, runtime_schema in cases:
            with self.subTest(package_version=package_version, runtime_schema=runtime_schema):
                generated = lockfile.generate_lockfile(
                    project_name="Demo Project",
                    project_slug="demo-project",
                    repo_url=None,
                    package_version=package_version,
                    runtime_schema=runtime_schema,
                )

                errors = list(validator.iter_errors(generated))

                self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
