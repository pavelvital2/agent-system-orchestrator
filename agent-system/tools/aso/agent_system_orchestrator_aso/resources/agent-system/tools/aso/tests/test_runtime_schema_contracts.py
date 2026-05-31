from __future__ import annotations

import json
import unittest
from pathlib import Path

import sys


ASO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool import runtime_schema_contracts  # noqa: E402


CONTRACT_PATH = REPO_ROOT / runtime_schema_contracts.CONTRACT_RELATIVE_PATH


class RuntimeSchemaContractTests(unittest.TestCase):
    def test_packaged_runtime_schema_contract_is_self_consistent(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

        result = runtime_schema_contracts.validate_contract_document(contract)

        self.assertTrue(result.passed, "\n".join(result.errors))

    def test_contract_summary_exposes_current_runtime_schema_sidecars(self) -> None:
        summary = runtime_schema_contracts.contract_summary()

        self.assertEqual(summary["runtime_schema_version"], runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION)
        self.assertEqual(summary["state_root"], "project-runtime/state")
        self.assertIn("SCHEMA_MANIFEST", summary["required_sidecars"])
        self.assertIn("REPOSITORY_LOCK", summary["optional_sidecars"])
        self.assertIn("CHECKPOINT_STATE", summary["optional_sidecars"])

    def test_legacy_schema_versions_have_migration_status(self) -> None:
        self.assertEqual(
            runtime_schema_contracts.compatibility_status("2.0.0"),
            "compatible_migration_available",
        )
        self.assertEqual(
            runtime_schema_contracts.compatibility_status("3.0.0"),
            "compatible_migration_available",
        )
        self.assertEqual(
            runtime_schema_contracts.compatibility_status("3.1.0"),
            "compatible_migration_available",
        )
        self.assertEqual(
            runtime_schema_contracts.compatibility_status("3.1.1"),
            "compatible_migration_available",
        )
        self.assertEqual(
            runtime_schema_contracts.compatibility_status(runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION),
            "current",
        )
        self.assertEqual(runtime_schema_contracts.compatibility_status("9.9.9"), "unsupported")


if __name__ == "__main__":
    unittest.main()
