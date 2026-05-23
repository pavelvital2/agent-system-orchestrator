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
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "results"

sys.path.insert(0, str(CLI.parents[0]))

from agent_system_orchestrator_aso.aso_tool.commands import record_result  # noqa: E402


def fixture(name: str) -> Path:
    return FIXTURE_ROOT / name


def run_record_result(path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "record-result",
            "--result",
            str(path),
            "--dry-run",
            "--json",
            *extra,
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def report_from(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    return json.loads(result.stdout)


def add_accepted_result_package(
    root: Path,
    result_path: Path,
    *,
    artifact_ref: str = "project-runtime/artifacts/accepted/RESULT_PACKAGE_TASK_DEMO_001_ATTEMPT_001.json",
    package_payload: dict[str, object] | None = None,
    write_package: bool = True,
) -> None:
    result_ref = result_path.relative_to(root).as_posix()
    default_payload: dict[str, object] = {
        "package_id": "RESULT_PACKAGE_TASK_DEMO_001_ATTEMPT_001",
        "schema_version": "1.0.0",
        "package_version": record_result.RESULT_PACKAGE_CONSTANTS["package_version"],
        "governance_ruleset_version": record_result.RESULT_PACKAGE_CONSTANTS["governance_ruleset_version"],
        "runtime_schema_version": record_result.RESULT_PACKAGE_CONSTANTS["runtime_schema_version"],
        "artifact_package_schema_version": record_result.RESULT_PACKAGE_CONSTANTS["artifact_package_schema_version"],
        "result_ref": result_ref,
        "task_id": "TASK_DEMO_001",
        "agent_instance_id": "agent_TASK_DEMO_001_attempt_001",
        "role": "developer",
        "status": "pass",
        "acceptance_status": "accepted",
        "changed_files": "NONE",
        "created_files": "NONE",
        "deleted_files": "NONE",
        "structured_artifacts": "NONE",
        "commands_run": "NONE",
        "tests_run": "NONE",
        "evidence": ["fixture"],
        "scope_verification": ["fixture"],
        "forbidden_changes_check": ["fixture"],
        "risks": "NONE",
        "limitations": "NONE",
        "blockers": "NONE",
        "gaps": "NONE",
        "next_recommended_action": ["CREATE_AUDITOR"],
        "reuse_allowed": False,
        "agent_termination_required": True,
        "validation": {
            "status": "passed",
            "validators": ["fixture"],
            "notes": "NONE",
        },
    }
    if write_package:
        package_path = Path(artifact_ref) if Path(artifact_ref).is_absolute() else root / artifact_ref
        package_path.parent.mkdir(parents=True, exist_ok=True)
        package_path.write_text(
            json.dumps(
                default_payload if package_payload is None else package_payload,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    accepted_path = root / "project-runtime" / "state" / "ACCEPTED_ARTIFACTS.json"
    accepted_path.parent.mkdir(parents=True, exist_ok=True)
    accepted_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0.0",
                "sidecar_type": "ACCEPTED_ARTIFACTS",
                "markdown_source": "project-runtime/ACCEPTED_ARTIFACTS.md",
                "state_revision": 1,
                "updated_at": "2026-01-01T00:00:00Z",
                "updated_by": "orchestrator",
                "content": {
                    "artifacts": [
                        {
                            "accepted_at": "2026-01-01T00:00:00Z",
                            "artifact_id": "RESULT_PACKAGE_TASK_DEMO_001_ATTEMPT_001",
                            "artifact_ref": artifact_ref,
                            "artifact_type": "RESULT_PACKAGE",
                            "audit_ref": "NONE",
                            "branch": "NONE",
                            "checkpoint_ref": "NONE",
                            "commit_hash": "NONE",
                            "notes": "fixture",
                            "push_status": "not_required",
                            "source_result_ref": result_ref,
                            "source_task": "TASK_DEMO_001",
                            "status": "accepted",
                            "superseded_by": "NONE",
                            "supersedes": "NONE",
                            "updated_at": "2026-01-01T00:00:00Z",
                        }
                    ]
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def terminate_agent(root: Path, result_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "lifecycle",
            "terminate-agent",
            "--root",
            str(root),
            "--from-result",
            str(result_path),
            "--confirm-write",
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def write_termination_event(root: Path, result_path: Path) -> None:
    events_path = root / "project-runtime" / "agents" / "instances.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        json.dumps(
            {
                "event": "agent_instance_terminated",
                "event_type": "AGENT_TERMINATED",
                "task_id": "TASK_DEMO_001",
                "agent_role": "developer",
                "role": "developer",
                "agent_instance_id": "agent_TASK_DEMO_001_attempt_001",
                "result_ref": result_path.relative_to(root).as_posix(),
                "timestamp_utc": "2026-05-22T00:00:00Z",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


class RecordResultCommandTests(unittest.TestCase):
    def test_help_declares_dry_run_read_only(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "record-result", "--help"],
            check=False,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Dry-run/read-only", result.stdout)
        self.assertIn("without mutating state", result.stdout)
        self.assertIn("--json", result.stdout)
        self.assertNotIn("--json-out", result.stdout)

    def test_dry_run_flag_is_required(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "record-result",
                "--result",
                str(fixture("RESULT_TASK_DEMO_001_PASS.md")),
            ],
            check=False,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--dry-run", result.stderr)

    def test_profile_pass_routes_to_auditor_and_does_not_mutate_fixture(self) -> None:
        path = fixture("RESULT_TASK_DEMO_001_PASS.md")
        before = path.stat().st_mtime_ns

        result = run_record_result(path, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["report_status"], "ready")
        self.assertEqual(report["result_type"], "profile_result")
        self.assertEqual(report["task_id"], "TASK_DEMO_001")
        self.assertEqual(report["role"], "developer")
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["audit_required"])
        self.assertFalse(report["checkpoint_candidate"])
        self.assertEqual(report["recommended_next_action"], "CREATE_AUDITOR")
        self.assertTrue(report["dry_run"])
        self.assertTrue(report["read_only"])
        self.assertFalse(report["mutations_performed"])
        self.assertEqual(path.stat().st_mtime_ns, before)
        rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
        self.assertIn("GOV-CHECKPOINT-AUDIT-GATE", rule_ids)

    def test_strict_rejects_transitional_markdown_result_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "RESULT_TASK_DEMO_001_PASS.md"
            text = fixture("RESULT_TASK_DEMO_001_PASS.md").read_text(encoding="utf-8")
            path.write_text(text.replace("RESULT:", "# RESULT", 1), encoding="utf-8")

            result = run_record_result(path, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = report_from(result)
        rule_ids = {item["rule_id"] for item in report["validation_errors"]}
        self.assertIn("RESULT_FORMAT_002", rule_ids)
        evidence = "; ".join(item["evidence"] for item in report["validation_errors"])
        self.assertIn("# RESULT", evidence)

    def test_profile_pass_inside_workspace_requires_termination_before_audit_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_path = root / "project-runtime" / "results" / "worker" / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.parent.mkdir(parents=True)
            shutil.copyfile(fixture("RESULT_TASK_DEMO_001_PASS.md"), result_path)
            add_accepted_result_package(root, result_path)

            before = run_record_result(result_path, "--strict")
            write_termination_event(root, result_path)
            after = run_record_result(result_path, "--strict")

        self.assertEqual(before.returncode, 1, before.stdout + before.stderr)
        before_report = report_from(before)
        self.assertEqual(before_report["recommended_next_action"], "NONE")
        rule_ids = {item["rule_id"] for item in before_report["validation_errors"]}
        self.assertIn("RESULT_LIFECYCLE_001", rule_ids)
        self.assertEqual(after.returncode, 0, after.stdout + after.stderr)
        after_report = report_from(after)
        self.assertEqual(after_report["recommended_next_action"], "CREATE_AUDITOR")

    def test_profile_pass_inside_workspace_requires_accepted_result_package_before_audit_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_path = root / "project-runtime" / "results" / "worker" / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.parent.mkdir(parents=True)
            shutil.copyfile(fixture("RESULT_TASK_DEMO_001_PASS.md"), result_path)
            write_termination_event(root, result_path)
            result = run_record_result(result_path, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["recommended_next_action"], "NONE")
        self.assertFalse(report["checkpoint_candidate"])
        rule_ids = {item["rule_id"] for item in report["validation_errors"]}
        self.assertIn("RESULT_PACKAGE_ACCEPTANCE_001", rule_ids)

    def test_strict_rejects_raw_accepted_artifact_ref_for_result_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_path = root / "project-runtime" / "results" / "worker" / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.parent.mkdir(parents=True)
            shutil.copyfile(fixture("RESULT_TASK_DEMO_001_PASS.md"), result_path)
            add_accepted_result_package(
                root,
                result_path,
                artifact_ref="project-runtime/artifacts/raw/RESULT_PACKAGE_TASK_DEMO_001_ATTEMPT_001.json",
            )
            write_termination_event(root, result_path)
            result = run_record_result(result_path, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["recommended_next_action"], "NONE")
        rule_ids = {item["rule_id"] for item in report["validation_errors"]}
        self.assertIn("RESULT_PACKAGE_ACCEPTANCE_001", rule_ids)
        evidence = "; ".join(item["evidence"] for item in report["validation_errors"])
        self.assertIn("project-runtime/artifacts/accepted/RESULT_PACKAGE_*.json", evidence)

    def test_strict_rejects_absolute_out_of_workspace_accepted_artifact_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            outside = Path(tmp) / "outside" / "RESULT_PACKAGE_TASK_DEMO_001_ATTEMPT_001.json"
            result_path = root / "project-runtime" / "results" / "worker" / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.parent.mkdir(parents=True)
            shutil.copyfile(fixture("RESULT_TASK_DEMO_001_PASS.md"), result_path)
            add_accepted_result_package(root, result_path, artifact_ref=str(outside))
            write_termination_event(root, result_path)
            result = run_record_result(result_path, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["recommended_next_action"], "NONE")
        rule_ids = {item["rule_id"] for item in report["validation_errors"]}
        self.assertIn("RESULT_PACKAGE_ACCEPTANCE_001", rule_ids)
        evidence = "; ".join(item["evidence"] for item in report["validation_errors"])
        self.assertIn("workspace-relative", evidence)

    def test_strict_rejects_out_of_workspace_accepted_package_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            outside = Path(tmp) / "outside"
            result_path = root / "project-runtime" / "results" / "worker" / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.parent.mkdir(parents=True)
            outside.mkdir(parents=True)
            shutil.copyfile(fixture("RESULT_TASK_DEMO_001_PASS.md"), result_path)
            accepted_dir = root / "project-runtime" / "artifacts" / "accepted"
            accepted_dir.parent.mkdir(parents=True)
            accepted_dir.symlink_to(outside, target_is_directory=True)
            add_accepted_result_package(
                root,
                result_path,
                artifact_ref="project-runtime/artifacts/accepted/RESULT_PACKAGE_TASK_DEMO_001_ATTEMPT_001.json",
            )
            write_termination_event(root, result_path)
            result = run_record_result(result_path, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["recommended_next_action"], "NONE")
        rule_ids = {item["rule_id"] for item in report["validation_errors"]}
        self.assertIn("RESULT_PACKAGE_ACCEPTANCE_001", rule_ids)
        evidence = "; ".join(item["evidence"] for item in report["validation_errors"])
        self.assertIn("outside workspace", evidence)

    def test_strict_rejects_incomplete_accepted_result_package_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_path = root / "project-runtime" / "results" / "worker" / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.parent.mkdir(parents=True)
            shutil.copyfile(fixture("RESULT_TASK_DEMO_001_PASS.md"), result_path)
            add_accepted_result_package(
                root,
                result_path,
                package_payload={
                    "package_id": "RESULT_PACKAGE_TASK_DEMO_001_ATTEMPT_001",
                    "result_ref": result_path.relative_to(root).as_posix(),
                    "task_id": "TASK_DEMO_001",
                    "agent_instance_id": "agent_TASK_DEMO_001_attempt_001",
                    "role": "developer",
                    "status": "pass",
                    "acceptance_status": "accepted",
                    "reuse_allowed": False,
                    "agent_termination_required": True,
                },
            )
            write_termination_event(root, result_path)
            result = run_record_result(result_path, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["recommended_next_action"], "NONE")
        rule_ids = {item["rule_id"] for item in report["validation_errors"]}
        self.assertIn("RESULT_PACKAGE_ACCEPTANCE_001", rule_ids)
        evidence = "; ".join(item["evidence"] for item in report["validation_errors"])
        self.assertIn("schema_version is required", evidence)
        self.assertIn("validation is required", evidence)

    def test_audit_pass_routes_to_checkpoint_preflight_candidate(self) -> None:
        result = run_record_result(fixture("AUDIT_RESULT_TASK_DEMO_001_PASS.md"), "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["report_status"], "ready")
        self.assertEqual(report["result_type"], "audit_result")
        self.assertEqual(report["role"], "auditor")
        self.assertEqual(report["status"], "pass")
        self.assertFalse(report["audit_required"])
        self.assertTrue(report["checkpoint_candidate"])
        self.assertEqual(report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
        evidence = report["evidence"]
        self.assertIsInstance(evidence, dict)
        self.assertEqual(
            evidence["source_result_refs"],
            ["agent-system/tests/fixtures/results/RESULT_TASK_DEMO_001_PASS.md"],
        )
        self.assertEqual(report["blocking_rules"], [])

    def test_audit_pass_inside_workspace_requires_auditor_termination_before_checkpoint_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_path = root / "project-runtime" / "results" / "audit" / "AUDIT_RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.parent.mkdir(parents=True)
            shutil.copyfile(fixture("AUDIT_RESULT_TASK_DEMO_001_PASS.md"), result_path)

            before = run_record_result(result_path, "--strict")
            events_path = root / "project-runtime" / "agents" / "instances.jsonl"
            events_path.parent.mkdir(parents=True, exist_ok=True)
            events_path.write_text(
                json.dumps(
                    {
                        "event": "auditor_agent_terminated",
                        "event_type": "AUDITOR_AGENT_TERMINATED",
                        "task_id": "TASK_DEMO_001",
                        "agent_role": "auditor",
                        "role": "auditor",
                        "agent_instance_id": "audit_TASK_DEMO_001_attempt_001",
                        "result_ref": result_path.relative_to(root).as_posix(),
                        "timestamp_utc": "2026-05-22T00:00:00Z",
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            after = run_record_result(result_path, "--strict")

        self.assertEqual(before.returncode, 1, before.stdout + before.stderr)
        before_report = report_from(before)
        self.assertFalse(before_report["checkpoint_candidate"])
        rule_ids = {item["rule_id"] for item in before_report["validation_errors"]}
        self.assertIn("RESULT_LIFECYCLE_001", rule_ids)
        self.assertEqual(after.returncode, 0, after.stdout + after.stderr)
        after_report = report_from(after)
        self.assertTrue(after_report["checkpoint_candidate"])
        self.assertEqual(after_report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")

    def test_profile_failed_result_never_becomes_checkpoint_ready(self) -> None:
        result = run_record_result(fixture("RESULT_TASK_DEMO_001_FAIL.md"), "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["result_type"], "profile_result")
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["checkpoint_candidate"])
        self.assertEqual(report["recommended_next_action"], "ROUTE_CORRECTION")
        rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
        self.assertIn("GOV-PROFILE-FAIL-NO-CHECKPOINT", rule_ids)

    def test_audit_non_pass_statuses_never_become_checkpoint_ready(self) -> None:
        cases = {
            "AUDIT_RESULT_TASK_DEMO_001_FAIL.md": ("fail", "ROUTE_CORRECTION"),
            "AUDIT_RESULT_TASK_DEMO_001_BLOCKED.md": ("blocked", "ORCHESTRATOR_BLOCKED_ROUTING"),
            "AUDIT_RESULT_TASK_DEMO_001_GAP.md": ("gap", "REGISTER_GAP"),
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                result = run_record_result(fixture(filename), "--strict")

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                report = report_from(result)
                self.assertEqual(report["result_type"], "audit_result")
                self.assertEqual(report["status"], expected[0])
                self.assertFalse(report["checkpoint_candidate"])
                self.assertEqual(report["recommended_next_action"], expected[1])

    def test_strict_rejects_profile_audit_bypass_attempt(self) -> None:
        result = run_record_result(fixture("RESULT_TASK_DEMO_001_BYPASS.md"), "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["report_status"], "rejected")
        self.assertFalse(report["checkpoint_candidate"])
        self.assertEqual(report["recommended_next_action"], "CREATE_AUDITOR")
        rule_ids = {item["rule_id"] for item in report["validation_errors"]}
        self.assertIn("RESULT_BYPASS_001", rule_ids)

    def test_strict_rejects_malformed_result(self) -> None:
        result = run_record_result(fixture("RESULT_TASK_DEMO_001_MALFORMED.md"), "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = report_from(result)
        self.assertEqual(report["report_status"], "rejected")
        self.assertFalse(report["checkpoint_candidate"])
        rule_ids = {item["rule_id"] for item in report["validation_errors"]}
        self.assertIn("RESULT_FORMAT_003", rule_ids)
        self.assertIn("RESULT_FORMAT_004", rule_ids)


if __name__ == "__main__":
    unittest.main()
