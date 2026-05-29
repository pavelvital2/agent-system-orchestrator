from __future__ import annotations

import hashlib
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
TASK_ID = "TASK_FIXTURE_STATE_001"
RESULT_REF = f"project-runtime/results/worker/RESULT_{TASK_ID}_ATTEMPT_001.md"


def run_aso(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *extra, "--root", str(root)],
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


def make_tz_valid(root: Path) -> Path:
    tz_path = root / "project-input" / "TZ.md"
    tz_path.parent.mkdir(parents=True, exist_ok=True)
    tz_path.write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
    payload = load_sidecar(root, "PROJECT_STATE.json")
    content = payload["content"]
    assert isinstance(content, dict)
    content["tz_path"] = "project-input/TZ.md"
    write_sidecar(root, "PROJECT_STATE.json", payload)
    markdown_path = root / "project-runtime/PROJECT_STATE.md"
    lines = markdown_path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith("TZ_PATH:"):
            lines[index] = "TZ_PATH: project-input/TZ.md"
            break
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tz_path


def write_result_and_lifecycle(root: Path) -> Path:
    result_path = root / RESULT_REF
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        "\n".join(
            [
                "# RESULT",
                "",
                "STATUS: pass",
                f"TASK_ID: {TASK_ID}",
                f"AGENT_INSTANCE_ID: agent_{TASK_ID}_attempt_001",
                "ROLE: developer",
                f"TASK: {TASK_ID}",
                "SUMMARY:",
                "State reconcile fixture.",
                "REUSE_ALLOWED: false",
                "AGENT_TERMINATION_REQUIRED: true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    event = {
        "event": "agent_result_received",
        "event_type": "RESULT_RECEIVED",
        "task_id": TASK_ID,
        "agent_role": "developer",
        "role": "developer",
        "agent_instance_id": f"agent_{TASK_ID}_attempt_001",
        "result_ref": RESULT_REF,
        "timestamp_utc": "2026-05-25T10:00:00Z",
        "created_by": "orchestrator",
        "reuse_allowed": False,
    }
    events_path = root / "project-runtime" / "agents" / "instances.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")
    return result_path


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StateReconcileCommandTests(unittest.TestCase):
    def test_dry_run_reports_deterministic_diff_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result_and_lifecycle(root)
            registry_before = (root / "project-runtime/state/TASK_REGISTRY.json").read_text(encoding="utf-8")

            first = run_aso(root, "state", "reconcile", "--dry-run", "--format", "json")
            second = run_aso(root, "state", "reconcile", "--dry-run", "--format", "json")

            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            first_report = json.loads(first.stdout)
            second_report = json.loads(second.stdout)
            self.assertEqual(first_report["status"], "changes_pending")
            self.assertFalse(first_report["mutations_performed"])
            self.assertEqual(first_report["diff"], second_report["diff"])
            self.assertIn("TASK_REGISTRY", first_report["changed_sidecars"])
            self.assertEqual(first_report["evidence"]["lifecycle_log"]["event_count"], 1)
            self.assertEqual(first_report["evidence"]["results"]["profile_result_count"], 1)
            self.assertEqual((root / "project-runtime/state/TASK_REGISTRY.json").read_text(encoding="utf-8"), registry_before)
            self.assertFalse((root / "project-runtime/receipts/state-reconciliation").exists())

    def test_confirm_write_updates_state_writes_receipt_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            tz_path = make_tz_valid(root)
            result_path = write_result_and_lifecycle(root)
            accepted_manifest = root / "project-runtime/artifacts/accepted/TASK_FIXTURE_STATE_001/LOCKED/manifest.json"
            accepted_manifest.parent.mkdir(parents=True, exist_ok=True)
            accepted_manifest.write_text('{"artifact_type":"LOCKED"}\n', encoding="utf-8")
            immutable_hashes = {
                "tz": file_hash(tz_path),
                "result": file_hash(result_path),
                "accepted": file_hash(accepted_manifest),
            }

            first = run_aso(root, "state", "reconcile", "--confirm-write", "--format", "json")
            second = run_aso(root, "state", "reconcile", "--confirm-write", "--format", "json")

            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            first_report = json.loads(first.stdout)
            self.assertEqual(first_report["status"], "written")
            self.assertTrue(first_report["mutations_performed"])
            self.assertTrue((root / first_report["receipt_ref"]).is_file())
            self.assertEqual(first_report["state_verify_after"]["status"], "passed")
            task = load_sidecar(root, "TASK_REGISTRY.json")["content"]["tasks"][0]  # type: ignore[index]
            self.assertIn(RESULT_REF, task["result_refs"])  # type: ignore[index]
            next_action = load_sidecar(root, "NEXT_ACTION.json")["content"]  # type: ignore[index]
            self.assertEqual(next_action["action_type"], "update_state")  # type: ignore[index]
            self.assertIn("ACCEPT_ARTIFACT", next_action["instruction_for_orchestrator"])  # type: ignore[index]
            self.assertEqual(next_action["target_role"], "orchestrator")  # type: ignore[index]
            self.assertEqual(file_hash(tz_path), immutable_hashes["tz"])
            self.assertEqual(file_hash(result_path), immutable_hashes["result"])
            self.assertEqual(file_hash(accepted_manifest), immutable_hashes["accepted"])

            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            second_report = json.loads(second.stdout)
            self.assertEqual(second_report["status"], "no_changes")
            self.assertFalse(second_report["mutations_performed"])
            self.assertEqual(second_report["files_written"], [])

    def test_corrupt_sidecar_blocks_confirm_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            corrupt_path = root / "project-runtime/state/NEXT_ACTION.json"
            corrupt_path.write_text('{"sidecar_type": "NEXT_ACTION",', encoding="utf-8")

            result = run_aso(root, "state", "reconcile", "--confirm-write", "--format", "json")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "blocked")
            self.assertFalse(report["mutations_performed"])
            self.assertEqual(corrupt_path.read_text(encoding="utf-8"), '{"sidecar_type": "NEXT_ACTION",')
            rule_ids = {finding["rule_id"] for finding in report["findings"]}
            self.assertIn("STATE_RECONCILE_JSON_INVALID", rule_ids)
            self.assertFalse((root / "project-runtime/receipts/state-reconciliation").exists())

    def test_dry_run_blocks_invalid_markdown_source_without_mutation(self) -> None:
        invalid_cases = (
            ("../outside.md", "REGISTRY_REVISION: stale\n"),
            ("project-runtime/results/outside.md", "REGISTRY_REVISION: stale\n"),
        )
        for markdown_source, outside_content in invalid_cases:
            with self.subTest(markdown_source=markdown_source), tempfile.TemporaryDirectory() as tmp:
                root = copy_valid_workspace(tmp)
                make_tz_valid(root)
                write_result_and_lifecycle(root)
                registry_path = root / "project-runtime/state/TASK_REGISTRY.json"
                registry = load_sidecar(root, "TASK_REGISTRY.json")
                registry["markdown_source"] = markdown_source
                write_sidecar(root, "TASK_REGISTRY.json", registry)
                registry_before = registry_path.read_text(encoding="utf-8")
                outside_path = root / markdown_source
                outside_path.parent.mkdir(parents=True, exist_ok=True)
                outside_path.write_text(outside_content, encoding="utf-8")

                result = run_aso(root, "state", "reconcile", "--dry-run", "--format", "json")

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report["status"], "blocked")
                self.assertFalse(report["mutations_performed"])
                self.assertEqual(report["files_written"], [])
                self.assertEqual(outside_path.read_text(encoding="utf-8"), outside_content)
                self.assertEqual(registry_path.read_text(encoding="utf-8"), registry_before)
                rule_ids = {finding["rule_id"] for finding in report["findings"]}
                self.assertIn("STATE_RECONCILE_MARKDOWN_SOURCE_FORBIDDEN", rule_ids)
                self.assertFalse((root / "project-runtime/receipts/state-reconciliation").exists())

    def test_confirm_write_blocks_invalid_markdown_source_before_writes(self) -> None:
        invalid_cases = (
            ("../outside.md", "REGISTRY_REVISION: stale\n"),
            ("project-runtime/results/outside.md", "REGISTRY_REVISION: stale\n"),
        )
        for markdown_source, outside_content in invalid_cases:
            with self.subTest(markdown_source=markdown_source), tempfile.TemporaryDirectory() as tmp:
                root = copy_valid_workspace(tmp)
                make_tz_valid(root)
                write_result_and_lifecycle(root)
                registry_path = root / "project-runtime/state/TASK_REGISTRY.json"
                registry = load_sidecar(root, "TASK_REGISTRY.json")
                registry["markdown_source"] = markdown_source
                write_sidecar(root, "TASK_REGISTRY.json", registry)
                registry_before = registry_path.read_text(encoding="utf-8")
                outside_path = root / markdown_source
                outside_path.parent.mkdir(parents=True, exist_ok=True)
                outside_path.write_text(outside_content, encoding="utf-8")

                result = run_aso(root, "state", "reconcile", "--confirm-write", "--format", "json")

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report["status"], "blocked")
                self.assertFalse(report["mutations_performed"])
                self.assertEqual(report["files_written"], [])
                self.assertEqual(outside_path.read_text(encoding="utf-8"), outside_content)
                self.assertEqual(registry_path.read_text(encoding="utf-8"), registry_before)
                rule_ids = {finding["rule_id"] for finding in report["findings"]}
                self.assertIn("STATE_RECONCILE_MARKDOWN_SOURCE_FORBIDDEN", rule_ids)
                self.assertFalse((root / "project-runtime/receipts/state-reconciliation").exists())

    def test_confirm_write_blocks_non_reconcilable_pre_verify_failure_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            write_result_and_lifecycle(root)
            registry_path = root / "project-runtime/state/TASK_REGISTRY.json"
            registry_before = registry_path.read_text(encoding="utf-8")
            project_state = load_sidecar(root, "PROJECT_STATE.json")
            content = project_state["content"]
            assert isinstance(content, dict)
            content["project_name"] = ""
            write_sidecar(root, "PROJECT_STATE.json", project_state)

            result = run_aso(root, "state", "reconcile", "--confirm-write", "--format", "json")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "blocked")
            self.assertFalse(report["mutations_performed"])
            self.assertTrue(report["read_only"])
            self.assertEqual(report["files_written"], [])
            self.assertEqual(registry_path.read_text(encoding="utf-8"), registry_before)
            rule_ids = {finding["rule_id"] for finding in report["findings"]}
            self.assertIn("STATE_RECONCILE_PRE_VERIFY_FAILED", rule_ids)
            pre_verify_rule_ids = {
                finding["rule_id"]
                for finding in report["state_verify_before_blocking_findings"]
                if isinstance(finding, dict)
            }
            self.assertIn("SIDECAR_REQUIRED_FIELD_EMPTY", pre_verify_rule_ids)
            self.assertFalse((root / "project-runtime/receipts/state-reconciliation").exists())


if __name__ == "__main__":
    unittest.main()
