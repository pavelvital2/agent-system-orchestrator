from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_audit_correction_routing as audit_helpers  # noqa: E402


class CheckpointCommandCompatibilityTests(unittest.TestCase):
    def test_checkpoint_preflight_blocks_failed_audit_with_correction_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = audit_helpers.copy_valid_workspace(tmp)
            audit_helpers.make_tz_valid(root)
            audit_helpers.write_result_pair(root)
            audit_helpers.set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            audit_helpers.set_project_state(root, checkpoint_eligibility="local_only")
            audit_helpers.set_task(root, status="audit_passed", audit_refs=[audit_helpers.AUDIT_RESULT_REF])
            json_out = Path(tmp) / "checkpoint-preflight.json"

            result = audit_helpers.run_aso(
                root,
                "checkpoint-preflight",
                "--mode",
                "workspace",
                "--strict",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertFalse(report["eligible"])
            self.assertEqual(report["correction_routing"]["route"], "CORRECTION_REQUIRED")
            self.assertEqual(report["correction_routing"]["source_audit_result_ref"], audit_helpers.AUDIT_RESULT_REF)
            rule_ids = {rule["rule_id"] for rule in report["blocking_rules"]}
            self.assertIn("GOV-AUDIT-FAIL-NO-CHECKPOINT", rule_ids)


if __name__ == "__main__":
    unittest.main()
