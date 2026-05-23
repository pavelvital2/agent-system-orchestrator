from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
AUTHORITY_MAP = REPO_ROOT / "agent-system" / "02_runtime" / "CONTRACT_AUTHORITY_MAP.md"
CONTRACT_3_1_0 = REPO_ROOT / "agent-system" / "09_validators" / "schemas" / "runtime_state_3_1_0.contract.json"
CONTRACT_3_1_1 = REPO_ROOT / "agent-system" / "09_validators" / "schemas" / "runtime_state_3_1_1.contract.json"


class ContractAuthorityMapTests(unittest.TestCase):
    def test_p5_authority_map_documents_active_chain(self) -> None:
        authority_map = AUTHORITY_MAP.read_text(encoding="utf-8")

        for phase in ("P5", "P5.1", "P5.2", "P5.3", "P5.4", "P5.5"):
            self.assertIn(f"| {phase} |", authority_map)
        self.assertIn("ARTIFACT_PACKAGE_MODEL_P5_CONTRACT.md", authority_map)
        self.assertIn("ARTIFACT_PACKAGE_MODEL_P5_1_CORRECTION_CONTRACT.md", authority_map)
        self.assertIn("BOOTSTRAP_STATE_RECONCILIATION_P5_2_CONTRACT.md", authority_map)
        self.assertIn("PLANNER_DISPATCHABILITY_GATE_P5_4_CONTRACT.md", authority_map)
        self.assertIn("package_version: 3.7.5", authority_map)
        self.assertIn("runtime_schema_version: 3.1.1", authority_map)

    def test_runtime_schema_3_1_1_uses_mapped_base_contract_file(self) -> None:
        authority_map = AUTHORITY_MAP.read_text(encoding="utf-8")

        self.assertTrue(CONTRACT_3_1_0.is_file())
        self.assertFalse(CONTRACT_3_1_1.exists())
        self.assertIn("runtime_state_3_1_0.contract.json", authority_map)
        self.assertIn("Runtime Schema `3.1.1`", authority_map)
        self.assertIn("Do not add a second `runtime_state_3_1_1.contract.json`", authority_map)


if __name__ == "__main__":
    unittest.main()
