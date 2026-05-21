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

if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool import proposal_contracts  # noqa: E402


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


def load_sidecar(root: Path, name: str) -> dict[str, object]:
    return json.loads((root / "project-runtime" / "state" / name).read_text(encoding="utf-8"))


def write_sidecar(root: Path, name: str, payload: dict[str, object]) -> None:
    (root / "project-runtime" / "state" / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def workspace_files(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def make_checkpoint_attempt(root: Path, *, audit_passed: bool) -> None:
    next_action = load_sidecar(root, "NEXT_ACTION.json")
    next_content = next_action["content"]
    assert isinstance(next_content, dict)
    next_content["action_type"] = "update_state"
    next_content["action_semantic"] = "normal"
    next_content["checkpoint_policy"] = "local_only"
    next_content["checkpoint_preflight_required"] = True
    next_content["checkpoint_receipt_required"] = True
    next_content["dependency_status"] = "ready"
    next_content["task_id"] = "TASK_CHECKPOINT_001"
    next_content["task_packet"] = "project-runtime/tasks/TASK_CHECKPOINT_001.md"
    write_sidecar(root, "NEXT_ACTION.json", next_action)

    task_registry = load_sidecar(root, "TASK_REGISTRY.json")
    registry_content = task_registry["content"]
    assert isinstance(registry_content, dict)
    registry_content["tasks"] = [
        {
            "accepted_files": [],
            "audit_refs": ["project-runtime/audits/AUDIT_TASK_CHECKPOINT_001_PASS.md"] if audit_passed else [],
            "branch": "NONE",
            "checkpoint_ref": "NONE",
            "commit_hash": "NONE",
            "correction_links": [],
            "created_at": "2026-05-21T00:00:00Z",
            "dependencies": [],
            "owner_role": "developer",
            "push_status": "not_required",
            "requested_by_role": "NONE",
            "requested_by_task": "NONE",
            "research_question_id": "NONE",
            "result_refs": ["project-runtime/results/RESULT_TASK_CHECKPOINT_001.md"],
            "return_task_after_audit_pass": "NONE",
            "return_to_requester_after_audit_pass": False,
            "return_to_role_after_audit_pass": "none",
            "status": "audit_passed" if audit_passed else "completed",
            "task_id": "TASK_CHECKPOINT_001",
            "task_kind": "normal",
            "task_packet": "project-runtime/tasks/TASK_CHECKPOINT_001.md",
            "task_title": "Checkpoint fixture task",
            "task_type": "developer",
            "updated_at": "2026-05-21T00:00:00Z",
        }
    ]
    write_sidecar(root, "TASK_REGISTRY.json", task_registry)

    accepted_artifacts = load_sidecar(root, "ACCEPTED_ARTIFACTS.json")
    accepted_content = accepted_artifacts["content"]
    assert isinstance(accepted_content, dict)
    accepted_content["artifacts"] = [
        {
            "accepted_at": "2026-05-21T00:00:00Z",
            "artifact_id": "ARTIFACT-TASK-CHECKPOINT-001",
            "artifact_ref": "agent-system/tools/aso/aso.py",
            "artifact_type": "code",
            "audit_ref": "project-runtime/audits/AUDIT_TASK_CHECKPOINT_001_PASS.md" if audit_passed else "NONE",
            "branch": "NONE",
            "checkpoint_ref": "NONE",
            "commit_hash": "NONE",
            "notes": "Fixture artifact.",
            "push_status": "not_required",
            "source_result_ref": "project-runtime/results/RESULT_TASK_CHECKPOINT_001.md",
            "source_task": "TASK_CHECKPOINT_001",
            "status": "accepted",
            "superseded_by": "NONE",
            "supersedes": "NONE",
            "updated_at": "2026-05-21T00:00:00Z",
        }
    ]
    write_sidecar(root, "ACCEPTED_ARTIFACTS.json", accepted_artifacts)


class ProposeCheckpointCommandTests(unittest.TestCase):
    def test_help_declares_propose_checkpoint_without_execution(self) -> None:
        propose_help = run_aso("propose", "--help")
        checkpoint_help = run_aso("propose", "checkpoint", "--help")

        self.assertEqual(propose_help.returncode, 0, propose_help.stdout + propose_help.stderr)
        self.assertIn("checkpoint", propose_help.stdout)
        self.assertEqual(checkpoint_help.returncode, 0, checkpoint_help.stdout + checkpoint_help.stderr)
        self.assertIn("checkpoint proposal", checkpoint_help.stdout)
        self.assertIn("P3 checkpoint execution is not", checkpoint_help.stdout)
        self.assertIn("--confirm-write", checkpoint_help.stdout)

    def test_not_required_dry_run_json_out_is_schema_compatible_without_workspace_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            before = workspace_files(root)
            json_out = Path(tmp) / "checkpoint-not-required.json"

            result = run_aso("propose", "checkpoint", "--root", str(root), "--dry-run", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            proposal = json.loads(json_out.read_text(encoding="utf-8"))
            validation = proposal_contracts.validate_proposal_artifact(proposal)
            self.assertTrue(validation.passed, "\n".join(validation.errors))
            self.assertEqual(proposal["proposal_type"], "checkpoint")
            self.assertEqual(proposal["status"], "proposed")
            self.assertEqual(proposal["checkpoint_decision"], "not_required")
            self.assertEqual(proposal["safety_class"], "checkpoint_proposal_only")
            self.assertFalse(proposal["checkpoint_execution_performed"])
            self.assertFalse(proposal["checkpoint_receipt_created"])
            self.assertIn("project-runtime/state/CHECKPOINT_STATE.json", proposal["base_state_hashes"])
            self.assertEqual(before, workspace_files(root))

    def test_eligible_checkpoint_dry_run_json_out_is_schema_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            make_checkpoint_attempt(root, audit_passed=True)
            before = workspace_files(root)
            json_out = Path(tmp) / "checkpoint-eligible.json"

            result = run_aso("propose", "checkpoint", "--root", str(root), "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            proposal = json.loads(json_out.read_text(encoding="utf-8"))
            validation = proposal_contracts.validate_proposal_artifact(proposal)
            self.assertTrue(validation.passed, "\n".join(validation.errors))
            self.assertEqual(proposal["status"], "proposed")
            self.assertEqual(proposal["checkpoint_decision"], "eligible")
            self.assertIn("checkpoint_preflight_read_only", proposal["required_validators"])
            self.assertEqual(before, workspace_files(root))

    def test_ineligible_checkpoint_emits_reasons_without_workspace_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            make_checkpoint_attempt(root, audit_passed=False)
            before = workspace_files(root)
            json_out = Path(tmp) / "checkpoint-ineligible.json"

            result = run_aso("propose", "checkpoint", "--root", str(root), "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            proposal = json.loads(json_out.read_text(encoding="utf-8"))
            validation = proposal_contracts.validate_proposal_artifact(proposal)
            self.assertTrue(validation.passed, "\n".join(validation.errors))
            self.assertEqual(proposal["status"], "blocked")
            self.assertEqual(proposal["checkpoint_decision"], "ineligible")
            self.assertIn("audit-pass evidence", proposal["operations"][0]["description"])
            self.assertEqual(before, workspace_files(root))

    def test_confirm_write_writes_only_proposal_under_project_runtime_proposals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            make_checkpoint_attempt(root, audit_passed=True)
            before = workspace_files(root)

            result = run_aso("propose", "checkpoint", "--root", str(root), "--confirm-write")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            added = workspace_files(root) - before
            self.assertEqual(len(added), 1, added)
            written = next(iter(added))
            self.assertTrue(written.startswith("project-runtime/proposals/"), written)
            proposal = json.loads((root / written).read_text(encoding="utf-8"))
            self.assertEqual(proposal["proposal_type"], "checkpoint")
            self.assertEqual(proposal["safety_class"], "checkpoint_proposal_only")
            self.assertFalse(proposal["checkpoint_receipt_created"])


if __name__ == "__main__":
    unittest.main()
