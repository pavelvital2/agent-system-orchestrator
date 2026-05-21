from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import sys


ASO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool import proposal_contracts  # noqa: E402


class ProposalApplyContractTests(unittest.TestCase):
    def _load_json(self, relpath: str) -> dict[str, object]:
        return json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))

    def test_packaged_schema_and_template_json_files_parse(self) -> None:
        for relpath in (
            proposal_contracts.PROPOSAL_SCHEMA_RELATIVE_PATH,
            proposal_contracts.APPLY_RECEIPT_SCHEMA_RELATIVE_PATH,
            proposal_contracts.PROPOSAL_TEMPLATE_RELATIVE_PATH,
            proposal_contracts.APPLY_RECEIPT_TEMPLATE_RELATIVE_PATH,
        ):
            payload = self._load_json(relpath)
            self.assertIsInstance(payload, dict, relpath)

    def test_proposal_template_matches_required_contract(self) -> None:
        template = self._load_json(proposal_contracts.PROPOSAL_TEMPLATE_RELATIVE_PATH)

        result = proposal_contracts.validate_proposal_artifact(template)

        self.assertTrue(result.passed, "\n".join(result.errors))

    def test_apply_receipt_template_matches_required_contract(self) -> None:
        template = self._load_json(proposal_contracts.APPLY_RECEIPT_TEMPLATE_RELATIVE_PATH)

        result = proposal_contracts.validate_apply_receipt(template)

        self.assertTrue(result.passed, "\n".join(result.errors))

    def test_invalid_proposal_type_is_rejected(self) -> None:
        proposal = self._load_json(proposal_contracts.PROPOSAL_TEMPLATE_RELATIVE_PATH)
        proposal["proposal_type"] = "checkpoint_execution"

        result = proposal_contracts.validate_proposal_artifact(proposal)

        self.assertFalse(result.passed)
        self.assertIn("proposal_type", "\n".join(result.errors))

    def test_checkpoint_proposal_requires_checkpoint_proposal_safety_class(self) -> None:
        proposal = self._load_json(proposal_contracts.PROPOSAL_TEMPLATE_RELATIVE_PATH)
        proposal["proposal_type"] = "checkpoint"
        proposal["safety_class"] = "runtime_state_only"

        result = proposal_contracts.validate_proposal_artifact(proposal)

        self.assertFalse(result.passed)
        self.assertIn("checkpoint proposal_type requires safety_class", "\n".join(result.errors))

    def test_missing_receipt_required_field_is_rejected(self) -> None:
        receipt = copy.deepcopy(self._load_json(proposal_contracts.APPLY_RECEIPT_TEMPLATE_RELATIVE_PATH))
        receipt.pop("result_state_hashes")

        result = proposal_contracts.validate_apply_receipt(receipt)

        self.assertFalse(result.passed)
        self.assertIn("result_state_hashes is required", result.errors)

    def test_invalid_receipt_outcome_is_rejected(self) -> None:
        receipt = self._load_json(proposal_contracts.APPLY_RECEIPT_TEMPLATE_RELATIVE_PATH)
        receipt["outcome"] = "checkpoint_executed"

        result = proposal_contracts.validate_apply_receipt(receipt)

        self.assertFalse(result.passed)
        self.assertIn("outcome", "\n".join(result.errors))


if __name__ == "__main__":
    unittest.main()
