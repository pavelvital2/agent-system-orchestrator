from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "state"
VALID_WORKSPACE = FIXTURE_ROOT / "valid_workspace"


def run_state_verify(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "state", "verify", "--root", str(root), *extra],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def copy_valid_workspace(tmp: str) -> Path:
    root = Path(tmp) / "workspace"
    shutil.copytree(VALID_WORKSPACE, root)
    return root


def load_sidecar(root: Path, name: str) -> dict[str, object]:
    return json.loads((root / "project-runtime" / "state" / name).read_text(encoding="utf-8"))


def write_sidecar(root: Path, name: str, payload: dict[str, object]) -> None:
    (root / "project-runtime" / "state" / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class StateVerifyCommandTests(unittest.TestCase):
    def test_valid_workspace_passes_strict_and_writes_json_report(self) -> None:
        tracked = [path for path in VALID_WORKSPACE.rglob("*") if path.is_file()]
        mtimes_before = {path: path.stat().st_mtime_ns for path in tracked}
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "state-verify.json"

            result = run_state_verify(VALID_WORKSPACE, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO state verify: PASSED", result.stdout)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["command"], "state verify")
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["summary"], {"errors": 0, "warnings": 0, "info": 0})
            self.assertEqual(report["state"]["sidecars_missing"], [])
            self.assertTrue(report["read_only"])
        self.assertEqual(mtimes_before, {path: path.stat().st_mtime_ns for path in tracked})

    def test_existing_negative_fixtures_fail_with_stable_rule_ids(self) -> None:
        cases = {
            "invalid_bad_schema_version": "SIDECAR_SCHEMA_VERSION_MISSING_OR_INVALID",
            "invalid_checkpoint_policy_not_required": "SIDECAR_ENUM_VALUE_INVALID",
            "invalid_current_gate_status_active": "SIDECAR_ENUM_VALUE_INVALID",
            "invalid_dispatch_action_semantic": "SIDECAR_ENUM_VALUE_INVALID",
            "invalid_markdown_json_drift": "SIDECAR_MARKDOWN_DRIFT",
            "invalid_missing_required": "SIDECAR_REQUIRED_FIELD_MISSING",
            "invalid_runtime_architect": "SIDECAR_ENUM_VALUE_INVALID",
        }
        for fixture_name, rule_id in cases.items():
            with self.subTest(fixture_name=fixture_name):
                result = run_state_verify(FIXTURE_ROOT / fixture_name, "--strict")

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("ASO state verify: FAILED", result.stdout)
                self.assertIn(rule_id, result.stdout)

    def test_invalid_json_fails_with_parse_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            path = root / "project-runtime" / "state" / "NEXT_ACTION.json"
            path.write_text("{not valid json\n", encoding="utf-8")

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("SIDECAR_JSON_PARSE_ERROR", result.stdout)

    def test_missing_sidecar_uses_markdown_fallback_warning_and_strict_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            (root / "project-runtime" / "state" / "NEXT_ACTION.json").unlink()

            non_strict = run_state_verify(root)
            strict = run_state_verify(root, "--strict")

            self.assertEqual(non_strict.returncode, 0, non_strict.stdout + non_strict.stderr)
            self.assertIn("ASO state verify: WARNING", non_strict.stdout)
            self.assertIn("SIDECAR_MISSING_MARKDOWN_FALLBACK_USED", non_strict.stdout)
            self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
            self.assertIn("ASO state verify: FAILED", strict.stdout)

    def test_invalid_status_value_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            payload = load_sidecar(root, "CURRENT_GATE.json")
            content = payload["content"]
            self.assertIsInstance(content, dict)
            content["status"] = "surprising"
            write_sidecar(root, "CURRENT_GATE.json", payload)

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("SIDECAR_ENUM_VALUE_INVALID", result.stdout)

    def test_stale_next_action_action_types_fail(self) -> None:
        for action_type in ("run_audit", "checkpoint", "return_to_requester", "manual", "none"):
            with self.subTest(action_type=action_type), tempfile.TemporaryDirectory() as tmp:
                root = copy_valid_workspace(tmp)
                payload = load_sidecar(root, "NEXT_ACTION.json")
                content = payload["content"]
                self.assertIsInstance(content, dict)
                content["action_type"] = action_type
                write_sidecar(root, "NEXT_ACTION.json", payload)

                result = run_state_verify(root, "--strict")

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("SIDECAR_ENUM_VALUE_INVALID", result.stdout)

    def test_active_task_reference_must_exist_in_task_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            payload = load_sidecar(root, "PROJECT_STATE.json")
            content = payload["content"]
            self.assertIsInstance(content, dict)
            branches = content["active_branches"]
            self.assertIsInstance(branches, list)
            branch = branches[0]
            self.assertIsInstance(branch, dict)
            branch["current_task"] = "TASK_FIXTURE_STATE_MISSING"
            write_sidecar(root, "PROJECT_STATE.json", payload)

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("SIDECAR_TASK_REFERENCE_UNKNOWN", result.stdout)

    def test_next_action_checkpoint_requires_audit_pass_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            payload = load_sidecar(root, "NEXT_ACTION.json")
            content = payload["content"]
            self.assertIsInstance(content, dict)
            content["checkpoint_policy"] = "commit_and_push"
            content["checkpoint_preflight_required"] = True
            content["checkpoint_receipt_required"] = True
            content["checkpoint_receipt_ref"] = "project-runtime/checkpoints/CHECKPOINT_ELIGIBILITY_TASK_FIXTURE_STATE_001_1.md"
            write_sidecar(root, "NEXT_ACTION.json", payload)

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("SIDECAR_CHECKPOINT_POLICY_INVALID", result.stdout)


if __name__ == "__main__":
    unittest.main()
