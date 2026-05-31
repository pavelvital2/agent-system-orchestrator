from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
ASO_TOOL_ROOT = TESTS_DIR.parents[0]
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(ASO_TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(ASO_TOOL_ROOT))

from agent_system_orchestrator_aso.aso_tool import aso as aso_cli  # noqa: E402
from test_checkpoint_preflight import init_git, run_preflight, write_package_fixture  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[4]


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        capture_output=True,
    )


def configure_git_identity(root: Path) -> None:
    for key, value in (
        ("user.email", "aso-test@example.invalid"),
        ("user.name", "ASO Test"),
    ):
        result = git(root, "config", key, value)
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)


def commit_fixture(root: Path) -> None:
    add = git(root, "add", ".")
    if add.returncode != 0:
        raise AssertionError(add.stdout + add.stderr)
    commit = git(root, "commit", "-m", "fixture")
    if commit.returncode != 0:
        raise AssertionError(commit.stdout + commit.stderr)


def policy_from(report: dict[str, object]) -> dict[str, object]:
    evidence = report["evidence"]
    if not isinstance(evidence, dict):
        raise AssertionError("checkpoint report evidence must be an object")
    policy = evidence["checkpoint_evidence_policy"]
    if not isinstance(policy, dict):
        raise AssertionError("checkpoint evidence policy must be an object")
    return policy


class CheckpointEvidenceGitPolicyTests(unittest.TestCase):
    def test_ignored_runtime_checkpoint_evidence_keeps_package_freeze_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "package"
            root.mkdir()
            init_git(root)
            configure_git_identity(root)
            write_package_fixture(root)
            commit_fixture(root)
            receipt = root / "project-runtime/checkpoints/CHECKPOINT_ELIGIBILITY_TASK_POLICY_001.md"
            receipt.parent.mkdir(parents=True)
            receipt.write_text("CHECKPOINT_ELIGIBILITY_STATUS: eligible\n", encoding="utf-8")
            status_before = git(root, "status", "--short")
            self.assertEqual(status_before.returncode, 0, status_before.stderr)
            self.assertEqual(status_before.stdout, "")
            json_out = tmp_path / "checkpoint-policy.json"

            result = run_preflight(root, "--mode", "package", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(report["eligible"])
            self.assertEqual(report["evidence"]["generated_roots"]["project-runtime"], "present-untracked")
            self.assertEqual(report["evidence"]["git_tracked_generated_files"], [])
            policy = policy_from(report)
            self.assertEqual(policy["policy_id"], "aso_managed_checkpoint_evidence_policy_v1")
            self.assertEqual(policy["stage1_checkpoint_commit_command"], "not_available_without_owner_acceptance")
            self.assertTrue(policy["ignored_root_force_add_policy"]["manual_git_add_f_forbidden"])
            archived_paths = {
                path
                for item in policy["archived_runtime_only"]
                for path in item["paths"]
            }
            self.assertIn("project-runtime/checkpoints/**", archived_paths)
            status_after = git(root, "status", "--short")
            self.assertEqual(status_after.returncode, 0, status_after.stderr)
            self.assertEqual(status_after.stdout, "")

    def test_force_added_runtime_checkpoint_file_blocks_package_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "package"
            root.mkdir()
            init_git(root)
            configure_git_identity(root)
            write_package_fixture(root)
            commit_fixture(root)
            relpath = "project-runtime/checkpoints/CHECKPOINT_ELIGIBILITY_TASK_POLICY_001.md"
            receipt = root / relpath
            receipt.parent.mkdir(parents=True)
            receipt.write_text("CHECKPOINT_ELIGIBILITY_STATUS: eligible\n", encoding="utf-8")
            add = git(root, "add", "-f", relpath)
            self.assertEqual(add.returncode, 0, add.stdout + add.stderr)
            json_out = tmp_path / "checkpoint-policy-blocked.json"

            result = run_preflight(root, "--mode", "package", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertFalse(report["eligible"])
            self.assertIn(relpath, report["evidence"]["git_tracked_generated_files"])
            self.assertIn("LINT_PKG_001", {item["rule_id"] for item in report["blocking_rules"]})
            policy = policy_from(report)
            self.assertTrue(policy["ignored_root_force_add_policy"]["requires_receipt"])

    def test_policy_docs_define_disposition_and_force_add_hash_receipt(self) -> None:
        combined = "\n".join(
            (REPO_ROOT / path).read_text(encoding="utf-8")
            for path in (
                "agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md",
                "agent-system/02_runtime/RUNTIME_FILE_TAXONOMY.md",
                "README.md",
                "agent-system/README.md",
            )
        )
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

        for required in (
            "aso_managed_checkpoint_evidence_policy_v1",
            "FORCE_ADD_MANIFEST_<TASK_ID>_<ATTEMPT_NO>.json",
            "SHA256_BY_PATH",
            "SIZE_BY_PATH",
            "git add -f --pathspec-from-file=<FORCE_ADD_PATHSPEC> --pathspec-file-nul",
            "Manual `git add -f` selection is forbidden",
            "project-runtime/checkpoints/**",
            "agent-system/11_release/**",
        ):
            self.assertIn(required, combined)
        for root_pattern in ("/project-runtime/", "/project-input/", "/project-archive/"):
            self.assertIn(root_pattern, gitignore)

    def test_checkpoint_commit_command_is_not_added_without_owner_acceptance(self) -> None:
        parser = aso_cli.build_parser()
        command_action = next(action for action in parser._actions if getattr(action, "dest", "") == "command")
        choices = getattr(command_action, "choices", {})

        self.assertIn("checkpoint-preflight", choices)
        self.assertIn("propose", choices)
        self.assertNotIn("checkpoint", choices)


if __name__ == "__main__":
    unittest.main()
