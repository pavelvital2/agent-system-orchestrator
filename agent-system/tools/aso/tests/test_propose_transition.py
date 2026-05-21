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


def mark_bootstrap_gate_passed(root: Path) -> None:
    current_gate = load_sidecar(root, "CURRENT_GATE.json")
    content = current_gate["content"]
    assert isinstance(content, dict)
    content["status"] = "passed"
    content["gate_evidence"] = ["project-runtime/results/RESULT_BOOTSTRAP_PASS.md"]
    write_sidecar(root, "CURRENT_GATE.json", current_gate)


class ProposeTransitionCommandTests(unittest.TestCase):
    def test_help_declares_propose_transition(self) -> None:
        propose_help = run_aso("propose", "--help")
        transition_help = run_aso("propose", "transition", "--help")

        self.assertEqual(propose_help.returncode, 0, propose_help.stdout + propose_help.stderr)
        self.assertIn("transition", propose_help.stdout)
        self.assertEqual(transition_help.returncode, 0, transition_help.stdout + transition_help.stderr)
        self.assertIn("transition proposal", transition_help.stdout)
        self.assertIn("--confirm-write", transition_help.stdout)

    def test_valid_transition_dry_run_json_out_is_schema_compatible_without_workspace_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            mark_bootstrap_gate_passed(root)
            before = workspace_files(root)
            json_out = Path(tmp) / "transition-proposal.json"

            result = run_aso(
                "propose",
                "transition",
                "--root",
                str(root),
                "--to",
                "implementation",
                "--dry-run",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            proposal = json.loads(json_out.read_text(encoding="utf-8"))
            validation = proposal_contracts.validate_proposal_artifact(proposal)
            self.assertTrue(validation.passed, "\n".join(validation.errors))
            self.assertEqual(proposal["proposal_type"], "transition")
            self.assertEqual(proposal["status"], "proposed")
            self.assertEqual(proposal["safety_class"], "runtime_state_only")
            self.assertIn("project-runtime/state/PROJECT_STATE.json", proposal["base_state_hashes"])
            self.assertIn("lifecycle_transition_allowed", proposal["required_validators"])
            self.assertEqual(before, workspace_files(root))

    def test_confirm_write_writes_only_under_project_runtime_proposals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            mark_bootstrap_gate_passed(root)
            before = workspace_files(root)

            result = run_aso(
                "propose",
                "transition",
                "--root",
                str(root),
                "--to",
                "implementation",
                "--confirm-write",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            added = workspace_files(root) - before
            self.assertEqual(len(added), 1, added)
            written = next(iter(added))
            self.assertTrue(written.startswith("project-runtime/proposals/"), written)
            self.assertTrue(written.endswith(".json"), written)
            proposal = json.loads((root / written).read_text(encoding="utf-8"))
            self.assertEqual(proposal["proposal_type"], "transition")

    def test_project_runtime_proposal_json_out_requires_confirm_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            mark_bootstrap_gate_passed(root)
            before = workspace_files(root)
            proposals_dir = root / "project-runtime" / "proposals"
            proposals_dir.mkdir(parents=True)
            json_out = proposals_dir / "manual-transition-proposal.json"

            result = run_aso(
                "propose",
                "transition",
                "--root",
                str(root),
                "--to",
                "implementation",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("--confirm-write is required", result.stderr)
            self.assertFalse(json_out.exists())
            self.assertEqual(before, workspace_files(root))

    def test_unknown_lifecycle_target_returns_blocked_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            mark_bootstrap_gate_passed(root)
            json_out = Path(tmp) / "unknown-transition.json"

            result = run_aso(
                "propose",
                "transition",
                "--root",
                str(root),
                "--to",
                "moon",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            proposal = json.loads(json_out.read_text(encoding="utf-8"))
            validation = proposal_contracts.validate_proposal_artifact(proposal)
            self.assertTrue(validation.passed, "\n".join(validation.errors))
            self.assertEqual(proposal["status"], "blocked")
            self.assertIn("unknown_lifecycle_target", proposal["operations"][0]["description"])

    def test_missing_evidence_returns_blocked_proposal_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            before = workspace_files(root)
            json_out = Path(tmp) / "missing-evidence-transition.json"

            result = run_aso(
                "propose",
                "transition",
                "--root",
                str(root),
                "--to",
                "implementation",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            proposal = json.loads(json_out.read_text(encoding="utf-8"))
            validation = proposal_contracts.validate_proposal_artifact(proposal)
            self.assertTrue(validation.passed, "\n".join(validation.errors))
            self.assertEqual(proposal["status"], "blocked")
            self.assertIn("missing_evidence", proposal["operations"][0]["description"])
            self.assertEqual(before, workspace_files(root))

    def test_blocked_gate_returns_blocked_proposal_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_workspace(tmp)
            current_gate = load_sidecar(root, "CURRENT_GATE.json")
            content = current_gate["content"]
            self.assertIsInstance(content, dict)
            content["status"] = "blocked"
            content["blocking_status"] = {
                "blocker_id": "BLOCKER-001",
                "blocker_type": "governance",
                "blocks": ["implementation"],
                "blocked_by": ["missing_evidence"],
                "resolution_path": "Provide gate evidence.",
            }
            write_sidecar(root, "CURRENT_GATE.json", current_gate)
            before = workspace_files(root)
            json_out = Path(tmp) / "blocked-transition.json"

            result = run_aso(
                "propose",
                "transition",
                "--root",
                str(root),
                "--to",
                "implementation",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            proposal = json.loads(json_out.read_text(encoding="utf-8"))
            validation = proposal_contracts.validate_proposal_artifact(proposal)
            self.assertTrue(validation.passed, "\n".join(validation.errors))
            self.assertEqual(proposal["status"], "blocked")
            self.assertIn("blocked_gate", proposal["operations"][0]["description"])
            self.assertEqual(before, workspace_files(root))


if __name__ == "__main__":
    unittest.main()
