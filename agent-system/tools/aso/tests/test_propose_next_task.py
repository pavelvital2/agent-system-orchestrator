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


class ProposeNextTaskCommandTests(unittest.TestCase):
    def test_help_declares_propose_next_task(self) -> None:
        propose_help = run_aso("propose", "--help")
        next_task_help = run_aso("propose", "next-task", "--help")

        self.assertEqual(propose_help.returncode, 0, propose_help.stdout + propose_help.stderr)
        self.assertIn("next-task", propose_help.stdout)
        self.assertEqual(next_task_help.returncode, 0, next_task_help.stdout + next_task_help.stderr)
        self.assertIn("next_task proposal", next_task_help.stdout)
        self.assertIn("--confirm-write", next_task_help.stdout)

    def test_dry_run_json_out_emits_schema_compatible_proposal_without_workspace_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            before = workspace_files(root)
            json_out = Path(tmp) / "next-task-proposal.json"

            result = run_aso("propose", "next-task", "--root", str(root), "--dry-run", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            proposal = json.loads(json_out.read_text(encoding="utf-8"))
            validation = proposal_contracts.validate_proposal_artifact(proposal)
            self.assertTrue(validation.passed, "\n".join(validation.errors))
            self.assertEqual(proposal["proposal_type"], "next_task")
            self.assertEqual(proposal["status"], "proposed")
            self.assertEqual(proposal["safety_class"], "read_only_plan")
            self.assertIn("project-runtime/state/NEXT_ACTION.json", proposal["base_state_hashes"])
            self.assertIn("state_verify_before_apply", proposal["required_validators"])
            self.assertIn("no_agent_dispatch", proposal["required_validators"])
            self.assertEqual(before, workspace_files(root))

    def test_confirm_write_writes_only_under_project_runtime_proposals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            before = workspace_files(root)

            result = run_aso("propose", "next-task", "--root", str(root), "--confirm-write")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            after = workspace_files(root)
            added = after - before
            self.assertEqual(len(added), 1, added)
            written = next(iter(added))
            self.assertTrue(written.startswith("project-runtime/proposals/"), written)
            self.assertTrue(written.endswith(".json"), written)
            proposal = json.loads((root / written).read_text(encoding="utf-8"))
            self.assertEqual(proposal["proposal_type"], "next_task")

    def test_blocked_next_action_returns_blocked_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            next_action = load_sidecar(root, "NEXT_ACTION.json")
            content = next_action["content"]
            self.assertIsInstance(content, dict)
            content["dependency_status"] = "blocked"
            content["blocked_by"] = ["owner_decision_required"]
            write_sidecar(root, "NEXT_ACTION.json", next_action)
            json_out = Path(tmp) / "blocked-proposal.json"

            result = run_aso("propose", "next-task", "--root", str(root), "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            proposal = json.loads(json_out.read_text(encoding="utf-8"))
            validation = proposal_contracts.validate_proposal_artifact(proposal)
            self.assertTrue(validation.passed, "\n".join(validation.errors))
            self.assertEqual(proposal["status"], "blocked")
            self.assertIn("Blocked next-task proposal", proposal["operations"][0]["description"])

    def test_malformed_state_fails_closed_with_blocked_schema_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            (root / "project-runtime" / "state" / "NEXT_ACTION.json").write_text("{not-json\n", encoding="utf-8")
            json_out = Path(tmp) / "malformed-proposal.json"

            result = run_aso("propose", "next-task", "--root", str(root), "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            proposal = json.loads(json_out.read_text(encoding="utf-8"))
            validation = proposal_contracts.validate_proposal_artifact(proposal)
            self.assertTrue(validation.passed, "\n".join(validation.errors))
            self.assertEqual(proposal["status"], "blocked")
            self.assertRegex(proposal["base_state_hashes"]["project-runtime/state/NEXT_ACTION.json"], r"^sha256:")


if __name__ == "__main__":
    unittest.main()
