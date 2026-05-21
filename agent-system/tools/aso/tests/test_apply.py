from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ASO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
CLI = ASO_DIR / "aso.py"
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "proposal_apply_p3"
P2_VALID_WORKSPACE = FIXTURE_ROOT / "valid_workspace"
NEGATIVE_FIXTURES = FIXTURE_ROOT / "negative"

if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool import proposal_contracts  # noqa: E402
from agent_system_orchestrator_aso.aso_tool.commands import apply as apply_command  # noqa: E402


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def copy_p2_workspace(tmp: str) -> Path:
    root = Path(tmp) / "workspace"
    shutil.copytree(P2_VALID_WORKSPACE, root)
    return root


def workspace_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            snapshot[path.relative_to(root).as_posix()] = path.read_bytes().hex()
    return snapshot


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class ApplyDryRunCommandTests(unittest.TestCase):
    def _proposal(self, root: Path, tmp: str) -> Path:
        proposal_path = Path(tmp) / "proposal.json"
        result = run_aso("propose", "next-task", "--root", str(root), "--json-out", str(proposal_path))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return proposal_path

    def _apply_plan(
        self, root: Path, proposal_path: Path, tmp: str
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        plan_path = Path(tmp) / "apply-plan.json"
        result = run_aso(
            "apply",
            "--root",
            str(root),
            "--proposal",
            str(proposal_path),
            "--dry-run",
            "--json-out",
            str(plan_path),
        )
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        return result, plan

    def test_help_declares_apply_dry_run(self) -> None:
        result = run_aso("apply", "--help")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("--proposal", result.stdout)
        self.assertIn("--dry-run", result.stdout)
        self.assertIn("--confirm-apply", result.stdout)

    def test_valid_proposal_dry_run_json_plan_without_state_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            before = workspace_snapshot(root)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertTrue(plan["would_apply"])
            self.assertEqual(plan["blocked_reasons"], [])
            self.assertEqual(plan["proposal_type"], "next_task")
            self.assertIn("state_verify_before_apply", plan["validators_run"])
            self.assertIn("base_hash_staleness", plan["validators_run"])
            self.assertIn("project-runtime/state/PROJECT_STATE.json", plan["base_hashes"])
            self.assertIsInstance(plan["planned_operations"], list)
            self.assertEqual(before, workspace_snapshot(root))

    def test_stale_proposal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            sidecar_path = root / "project-runtime" / "state" / "NEXT_ACTION.json"
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            sidecar["state_revision"] = 2
            write_json(sidecar_path, sidecar)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("base_hash_stale", "\n".join(plan["blocked_reasons"]))

    def test_wrong_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            other_root = Path(tmp) / "other"
            shutil.copytree(P2_VALID_WORKSPACE, other_root)
            proposal_path = self._proposal(root, tmp)

            result, plan = self._apply_plan(other_root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("wrong_root", "\n".join(plan["blocked_reasons"]))

    def test_forbidden_path_operation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["operations"][0]["target"] = "project-input/owner-note.json"
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("operation_path_guard", "\n".join(plan["blocked_reasons"]))

    def test_git_checkout_execution_request_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["operations"][0]["description"] = "execute git checkout for checkpoint preparation"
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("forbidden_execution_guard", "\n".join(plan["blocked_reasons"]))

    def test_bare_gh_and_github_execution_request_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["operations"][0]["description"] = "run gh workflow and GitHub Actions release checks"
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("forbidden_execution_guard", "\n".join(plan["blocked_reasons"]))

    def test_agent_dispatch_execution_request_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["operations"][0]["metadata"] = {"next": "dispatch agent to reuse correction profile"}
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("forbidden_execution_guard", "\n".join(plan["blocked_reasons"]))

    def test_checkpoint_execution_request_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["operations"][0]["description"] = "prepare checkpoint execution before applying state"
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("forbidden_execution_guard", "\n".join(plan["blocked_reasons"]))

    def test_unsupported_proposal_type_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["proposal_type"] = "checkpoint_execution"
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("unsupported_proposal_type", "\n".join(plan["blocked_reasons"]))

    def test_malformed_proposal_is_rejected_with_json_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = NEGATIVE_FIXTURES / "malformed_json.json"

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("malformed_json", "\n".join(plan["blocked_reasons"]))

    def test_non_object_proposal_is_rejected_with_json_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = NEGATIVE_FIXTURES / "non_object_json.json"

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("malformed_json", "\n".join(plan["blocked_reasons"]))

    def test_missing_required_proposal_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            del proposal["proposal_id"]
            del proposal["base_state_hashes"]
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            reasons = "\n".join(plan["blocked_reasons"])
            self.assertIn("proposal_schema: proposal_id is required", reasons)
            self.assertIn("proposal_schema: base_state_hashes is required", reasons)

    def test_missing_proposal_type_is_rejected_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            del proposal["proposal_type"]
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            reasons = "\n".join(plan["blocked_reasons"])
            self.assertIn("proposal_schema: proposal_type is required", reasons)
            self.assertIn("unsupported_proposal_type", reasons)

    def test_missing_target_root_is_rejected_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            del proposal["target_root"]
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            reasons = "\n".join(plan["blocked_reasons"])
            self.assertIn("proposal_schema: target_root is required", reasons)
            self.assertIn("wrong_root", reasons)

    def test_invalid_general_safety_class_is_rejected_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["safety_class"] = "executes_workspace_changes"
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("proposal_schema: safety_class must be one of", "\n".join(plan["blocked_reasons"]))

    def test_workspace_identity_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["target_workspace_identity"]["workspace_id"] = "WORKSPACE-DIFFERENT"
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("workspace_identity_mismatch: workspace_id", "\n".join(plan["blocked_reasons"]))

    def test_repository_lock_mismatch_when_present_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["target_workspace_identity"]["expected_branch"] = "release"
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("repository_lock_mismatch: expected_branch != branch", "\n".join(plan["blocked_reasons"]))

    def test_missing_required_sidecar_is_rejected_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            (root / "project-runtime" / "state" / "NEXT_ACTION.json").unlink()
            before = workspace_snapshot(root)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            reasons = "\n".join(plan["blocked_reasons"])
            self.assertIn("state_verify_before_apply_failed", reasons)
            self.assertIn("base_hash_stale", reasons)
            self.assertEqual(before, workspace_snapshot(root))

    def test_malformed_current_sidecar_is_rejected_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            sidecar_path = root / "project-runtime" / "state" / "NEXT_ACTION.json"
            sidecar_path.write_text("{not-json\n", encoding="utf-8")
            before = workspace_snapshot(root)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            reasons = "\n".join(plan["blocked_reasons"])
            self.assertIn("state_verify_before_apply_failed", reasons)
            self.assertIn("base_hash_stale", reasons)
            self.assertEqual(before, workspace_snapshot(root))

    def test_forbidden_source_and_owner_roots_are_rejected(self) -> None:
        forbidden_targets = (
            "agent-system/tools/aso/aso.py",
            "project-input/owner-note.json",
            "project-archive/old-state.json",
            "../outside.json",
        )
        for target in forbidden_targets:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = copy_p2_workspace(tmp)
                proposal_path = self._proposal(root, tmp)
                proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
                proposal["operations"][0]["target"] = target
                write_json(proposal_path, proposal)

                result, plan = self._apply_plan(root, proposal_path, tmp)

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertFalse(plan["would_apply"])
                self.assertIn("operation_path_guard", "\n".join(plan["blocked_reasons"]))

    def test_git_commit_push_execution_request_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["operations"][0]["description"] = "execute git commit and git push before apply"
            write_json(proposal_path, proposal)

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("forbidden_execution_guard", "\n".join(plan["blocked_reasons"]))

    def test_confirm_apply_succeeds_for_valid_report_write_proposal_and_writes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            state_before = workspace_snapshot(root / "project-runtime" / "state")
            receipt_copy = Path(tmp) / "apply-receipt.json"

            result = run_aso(
                "apply",
                "--root",
                str(root),
                "--proposal",
                str(proposal_path),
                "--confirm-apply",
                "--json-out",
                str(receipt_copy),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            receipt = json.loads(receipt_copy.read_text(encoding="utf-8"))
            receipt_validation = proposal_contracts.validate_apply_receipt(receipt)
            self.assertTrue(receipt_validation.passed, "\n".join(receipt_validation.errors))
            self.assertEqual(receipt["outcome"], "applied")
            self.assertEqual(receipt["proposal_type"], "next_task")
            self.assertIn("state_verify_after_apply", receipt["validators_passed"])
            self.assertIn("project-runtime/reports/next-task-proposal.json", receipt["result_state_hashes"])
            receipts = sorted((root / "project-runtime" / "receipts").glob("*.json"))
            self.assertEqual(len(receipts), 1)
            self.assertEqual(json.loads(receipts[0].read_text(encoding="utf-8")), receipt)
            self.assertTrue((root / "project-runtime" / "reports" / "next-task-proposal.json").is_file())
            self.assertEqual(state_before, workspace_snapshot(root / "project-runtime" / "state"))

            verify = run_aso("state", "verify", "--root", str(root), "--strict")
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)

    def test_confirm_apply_forced_multi_operation_write_failure_removes_partials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            second_operation = dict(proposal["operations"][0])
            second_operation["operation_id"] = "write-second-report"
            second_operation["target"] = "project-runtime/reports/second-report.json"
            proposal["operations"].append(second_operation)
            write_json(proposal_path, proposal)
            state_before = workspace_snapshot(root / "project-runtime" / "state")
            original_atomic_write = apply_command._atomic_write_json

            def fail_second_report(path: Path, payload: dict[str, object], *, overwrite: bool) -> tuple[bool, str]:
                if path.name == "second-report.json":
                    return False, "forced write failure"
                return original_atomic_write(path, payload, overwrite=overwrite)

            with mock.patch.object(apply_command, "_atomic_write_json", side_effect=fail_second_report):
                result, exit_code = apply_command._run_confirmed_apply(root, proposal_path)

            self.assertEqual(exit_code, apply_command.EXIT_IO_ERROR)
            self.assertFalse(result["would_apply"])
            self.assertIn("atomic_write_failed", "\n".join(result["blocked_reasons"]))
            self.assertEqual(state_before, workspace_snapshot(root / "project-runtime" / "state"))
            self.assertFalse((root / "project-runtime" / "reports" / "next-task-proposal.json").exists())
            self.assertFalse((root / "project-runtime" / "reports" / "second-report.json").exists())
            self.assertFalse((root / "project-runtime" / "receipts").exists())

    def test_confirm_apply_after_verify_failure_rolls_back_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            state_before = workspace_snapshot(root / "project-runtime" / "state")
            verify_before_report, verify_before_exit = apply_command.state_verify._report(root, True)
            self.assertEqual(verify_before_exit, 0)

            failed_verify_report = {
                "status": "failed",
                "summary": {"errors": 1},
                "findings": [{"severity": "error", "rule_id": "forced_after_apply_failure"}],
            }
            with mock.patch.object(
                apply_command.state_verify,
                "_report",
                side_effect=[(verify_before_report, 0), (failed_verify_report, 1)],
            ):
                result, exit_code = apply_command._run_confirmed_apply(root, proposal_path)

            self.assertEqual(exit_code, apply_command.EXIT_BLOCKED)
            self.assertFalse(result["would_apply"])
            self.assertIn("state_verify_after_apply_failed", "\n".join(result["blocked_reasons"]))
            self.assertFalse((root / "project-runtime" / "reports" / "next-task-proposal.json").exists())
            self.assertFalse((root / "project-runtime" / "receipts").exists())
            self.assertEqual(state_before, workspace_snapshot(root / "project-runtime" / "state"))

    def test_missing_confirm_apply_prevents_workspace_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            before = workspace_snapshot(root)
            plan_path = Path(tmp) / "apply-plan.json"

            result = run_aso(
                "apply",
                "--root",
                str(root),
                "--proposal",
                str(proposal_path),
                "--json-out",
                str(plan_path),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertTrue(plan["would_apply"])
            self.assertFalse((root / "project-runtime" / "receipts").exists())
            self.assertFalse((root / "project-runtime" / "reports" / "next-task-proposal.json").exists())
            self.assertEqual(before, workspace_snapshot(root))

    def test_confirm_apply_stale_proposal_prevents_workspace_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            sidecar_path = root / "project-runtime" / "state" / "NEXT_ACTION.json"
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            sidecar["state_revision"] = 2
            write_json(sidecar_path, sidecar)
            before = workspace_snapshot(root)
            plan_path = Path(tmp) / "stale-apply.json"

            result = run_aso(
                "apply",
                "--root",
                str(root),
                "--proposal",
                str(proposal_path),
                "--confirm-apply",
                "--json-out",
                str(plan_path),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertFalse(plan["would_apply"])
            self.assertIn("base_hash_stale", "\n".join(plan["blocked_reasons"]))
            self.assertEqual(before, workspace_snapshot(root))

    def test_confirm_apply_forbidden_mutation_prevents_workspace_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["operations"][0]["target"] = "project-input/owner-note.json"
            write_json(proposal_path, proposal)
            before = workspace_snapshot(root)
            plan_path = Path(tmp) / "forbidden-apply.json"

            result = run_aso(
                "apply",
                "--root",
                str(root),
                "--proposal",
                str(proposal_path),
                "--confirm-apply",
                "--json-out",
                str(plan_path),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertFalse(plan["would_apply"])
            self.assertIn("operation_path_guard", "\n".join(plan["blocked_reasons"]))
            self.assertEqual(before, workspace_snapshot(root))

    def test_confirm_apply_unsupported_sidecar_patch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            proposal["operations"][0]["operation_type"] = "sidecar_patch"
            proposal["operations"][0]["target"] = "project-runtime/state/NEXT_ACTION.json"
            write_json(proposal_path, proposal)
            before = workspace_snapshot(root)
            plan_path = Path(tmp) / "unsupported-apply.json"

            result = run_aso(
                "apply",
                "--root",
                str(root),
                "--proposal",
                str(proposal_path),
                "--confirm-apply",
                "--json-out",
                str(plan_path),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertFalse(plan["would_apply"])
            self.assertIn("confirmed_apply_supported_scope", "\n".join(plan["blocked_reasons"]))
            self.assertEqual(before, workspace_snapshot(root))


if __name__ == "__main__":
    unittest.main()
