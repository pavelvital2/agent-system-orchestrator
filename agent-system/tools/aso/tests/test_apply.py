from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ASO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
CLI = ASO_DIR / "aso.py"
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "state"
P2_VALID_WORKSPACE = FIXTURE_ROOT / "p2_valid_workspace"


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
            proposal_path = Path(tmp) / "malformed.json"
            proposal_path.write_text("{not-json\n", encoding="utf-8")

            result, plan = self._apply_plan(root, proposal_path, tmp)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse(plan["would_apply"])
            self.assertIn("malformed_json", "\n".join(plan["blocked_reasons"]))

    def test_confirm_apply_fails_closed_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            proposal_path = self._proposal(root, tmp)
            before = workspace_snapshot(root)
            plan_path = Path(tmp) / "confirm-plan.json"

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
            self.assertIn("confirm_apply_not_implemented", "\n".join(plan["blocked_reasons"]))
            self.assertEqual(before, workspace_snapshot(root))


if __name__ == "__main__":
    unittest.main()
