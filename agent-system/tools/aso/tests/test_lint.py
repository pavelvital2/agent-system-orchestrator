from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"


RUNTIME_CONTENT = {
    "PROJECT_STATE.md": """# PROJECT_STATE

PROJECT_SLUG: demo-project
PROJECT_STATUS: active
PROJECT_CHECKPOINT_STATUS: pending
PUSH_ALLOWED: false
""",
    "CURRENT_GATE.md": """# CURRENT_GATE

STATUS: open
TASK_ID: TASK_DEMO_001
""",
    "NEXT_ACTION.md": """# NEXT_ACTION

ACTION_TYPE: create_agent
TARGET_ROLE: developer
TASK_ID: TASK_DEMO_001
TASK_PACKET: project-runtime/tasks/TASK_DEMO_001.md
CHECKPOINT_POLICY: forbidden
CHECKPOINT_RECEIPT_REQUIRED: no
CHECKPOINT_RECEIPT_REF: NONE
""",
    "TASK_REGISTRY.md": """# TASK_REGISTRY

TASK_ID: TASK_DEMO_001
STATUS: ready
RESULT_REFS: NONE
AUDIT_REFS: NONE
COMMIT_HASH: NONE
BRANCH: NONE
ACCEPTED_FILES: NONE
CHECKPOINT_REF: NONE
""",
    "ACCEPTED_ARTIFACTS.md": "# ACCEPTED_ARTIFACTS\n\nNONE\n",
    "REPOSITORY_LOCK.md": "# REPOSITORY_LOCK\n\nPUSH_ALLOWED: false\n",
    "WORKSPACE_IDENTITY.md": "# WORKSPACE_IDENTITY\n\nPUSH_ALLOWED: false\n",
}


TASK_PACKET = """# TASK_DEMO_001

TASK_ID: TASK_DEMO_001
TARGET_ROLE: developer
REASONING_LEVEL: high
STATUS: pending
"""


RESULT = """# RESULT

STATUS: pass
TASK_ID: TASK_DEMO_001
AGENT_INSTANCE_ID: agent_TASK_DEMO_001_attempt_001
ROLE: developer
TASK: TASK_DEMO_001
SUMMARY:
Done.
READ_DOCS:
- NONE
READ_INPUTS:
- NONE
CHANGED_FILES:
- NONE
CREATED_FILES:
- NONE
DELETED_FILES:
- NONE
COMMANDS_RUN:
- NONE
TESTS_RUN:
- NONE
EVIDENCE:
- NONE
SCOPE_VERIFICATION:
- NONE
FORBIDDEN_CHANGES_CHECK:
- NONE
RISKS:
- NONE
LIMITATIONS:
- NONE
BLOCKERS:
- NONE
GAPS:
- NONE
NEXT_RECOMMENDED_ACTION:
- NONE
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""


AUDIT_RESULT = """# AUDIT_RESULT

STATUS: pass
TASK_ID: TASK_DEMO_001
AGENT_INSTANCE_ID: audit_TASK_DEMO_001_attempt_001
ROLE: auditor
TASK: TASK_DEMO_001
SUMMARY:
Audit passed.
READ_DOCS:
- NONE
READ_INPUTS:
- NONE
CHANGED_FILES:
- NONE
CREATED_FILES:
- NONE
DELETED_FILES:
- NONE
COMMANDS_RUN:
- NONE
TESTS_RUN:
- NONE
EVIDENCE:
- SOURCE_RESULT_REF: project-runtime/results/RESULT_TASK_DEMO_001_ATTEMPT_001.md
SCOPE_VERIFICATION:
- NONE
FORBIDDEN_CHANGES_CHECK:
- NONE
RISKS:
- NONE
LIMITATIONS:
- NONE
BLOCKERS:
- NONE
GAPS:
- NONE
NEXT_RECOMMENDED_ACTION:
- NONE
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""


def write_runtime(root: Path, overrides: dict[str, str] | None = None) -> list[Path]:
    runtime = root / "project-runtime"
    runtime.mkdir()
    paths = []
    content = dict(RUNTIME_CONTENT)
    if overrides:
        content.update(overrides)
    for name, text in content.items():
        path = runtime / name
        path.write_text(text, encoding="utf-8")
        paths.append(path)

    tasks = runtime / "tasks"
    tasks.mkdir()
    task_path = tasks / "TASK_DEMO_001.md"
    task_path.write_text(TASK_PACKET, encoding="utf-8")
    paths.append(task_path)

    results = runtime / "results"
    results.mkdir()
    result_path = results / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
    result_path.write_text(RESULT, encoding="utf-8")
    paths.append(result_path)

    agents = runtime / "agents"
    agents.mkdir()
    instances_path = agents / "instances.jsonl"
    instances_path.write_text(
        "\n".join(
            [
                '{"event":"agent_instance_created","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","role":"developer","timestamp_utc":"2026-05-17T10:00:00Z"}',
                '{"event":"agent_task_dispatched","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","role":"developer","timestamp_utc":"2026-05-17T10:01:00Z"}',
                '{"event":"agent_result_received","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","result_ref":"project-runtime/results/RESULT_TASK_DEMO_001_ATTEMPT_001.md","reuse_allowed":false,"timestamp_utc":"2026-05-17T10:30:00Z"}',
                '{"event":"agent_instance_terminated","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","reuse_allowed":false,"timestamp_utc":"2026-05-17T10:31:00Z"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    paths.append(instances_path)
    return paths


def append_agent_events(root: Path, events: list[str]) -> None:
    instances_path = root / "project-runtime" / "agents" / "instances.jsonl"
    with instances_path.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(event + "\n")


def run_lint(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "lint", "--root", str(root), *extra],
        check=False,
        text=True,
        capture_output=True,
    )


class LintCommandTests(unittest.TestCase):
    def test_lint_passes_clean_runtime_and_does_not_mutate_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_runtime(root)
            mtimes_before = {path: path.stat().st_mtime_ns for path in paths}

            result = run_lint(root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO lint: PASSED", result.stdout)
            self.assertIn("Errors: 0", result.stdout)
            self.assertIn("Warnings: 0", result.stdout)
            self.assertIn("Findings: 0", result.stdout)
            self.assertEqual(mtimes_before, {path: path.stat().st_mtime_ns for path in paths})

    def test_lint_writes_json_out_only_to_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            json_out = root / "lint.json"

            result = run_lint(root, "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["tool"], "aso")
            self.assertEqual(report["command"], "lint")
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["summary"], {"errors": 0, "warnings": 0, "info": 0})
            self.assertEqual(report["findings"], [])

    def test_lint_returns_io_error_for_missing_required_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project-runtime").mkdir()

            result = run_lint(root)

            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("ASO lint: IO_ERROR", result.stdout)
            self.assertIn("LINT_IO_004", result.stdout)

    def test_lint_detects_state_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(
                root,
                {
                    "PROJECT_STATE.md": """# PROJECT_STATE

PROJECT_STATUS: active
PROJECT_CHECKPOINT_STATUS: passed
PUSH_ALLOWED: false
PUSH_ALLOWED: true
""",
                    "NEXT_ACTION.md": """# NEXT_ACTION

ACTION_TYPE: create_agent
TARGET_ROLE: developer
TASK_ID: TASK_DONE_001
TASK_PACKET: project-runtime/tasks/TASK_DONE_001.md
CHECKPOINT_POLICY: local_only
CHECKPOINT_RECEIPT_REQUIRED: yes
CHECKPOINT_RECEIPT_REF: NONE
""",
                    "TASK_REGISTRY.md": """# TASK_REGISTRY

TASK_ID: TASK_DONE_001
STATUS: checkpoint_done
RESULT_REFS: NONE
AUDIT_REFS: NONE
COMMIT_HASH: NONE
BRANCH: NONE
ACCEPTED_FILES: NONE
CHECKPOINT_REF: NONE
""",
                    "ACCEPTED_ARTIFACTS.md": """# ACCEPTED_ARTIFACTS

ARTIFACT_ID: ART_001
ARTIFACT_REF: missing/product.md
STATUS: accepted
""",
                    "REPOSITORY_LOCK.md": "# REPOSITORY_LOCK\n\nPUSH_ALLOWED: false\n",
                    "WORKSPACE_IDENTITY.md": "# WORKSPACE_IDENTITY\n\nPUSH_ALLOWED: true\n",
                },
            )

            result = run_lint(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("LINT_STATE_001", result.stdout)
            self.assertIn("LINT_STATE_002", result.stdout)
            self.assertIn("LINT_STATE_007", result.stdout)
            self.assertIn("LINT_STATE_008", result.stdout)
            self.assertIn("LINT_TASK_001", result.stdout)
            self.assertIn("LINT_TASK_002", result.stdout)
            self.assertIn("LINT_TASK_003", result.stdout)
            self.assertIn("LINT_ARTIFACT_002", result.stdout)

    def test_lint_detects_post_checkpoint_transaction_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(
                root,
                {
                    "PROJECT_STATE.md": """# PROJECT_STATE

PROJECT_STATUS: active
PROJECT_CHECKPOINT_STATUS: passed
CHECKPOINT_RECEIPT_REF: NONE
PUSH_ALLOWED: false
""",
                    "CURRENT_GATE.md": """# CURRENT_GATE

STATUS: open
TASK_ID: TASK_DEMO_001
""",
                    "NEXT_ACTION.md": """# NEXT_ACTION

ACTION_TYPE: stop
TARGET_ROLE: orchestrator
TASK_ID: TASK_DEMO_001
TASK_PACKET: NONE
CHECKPOINT_POLICY: commit_and_push
CHECKPOINT_RECEIPT_REQUIRED: yes
CHECKPOINT_RECEIPT_REF: NONE
""",
                },
            )

            result = run_lint(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("LINT_STATE_002", result.stdout)
            self.assertIn("LINT_STATE_007", result.stdout)
            self.assertIn("LINT_STATE_009", result.stdout)

    def test_lint_allows_passed_checkpoint_after_next_action_recalculation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(
                root,
                {
                    "PROJECT_STATE.md": """# PROJECT_STATE

PROJECT_STATUS: active
PROJECT_CHECKPOINT_STATUS: passed
CHECKPOINT_RECEIPT_REF: project-runtime/checkpoints/CHECKPOINT_TASK_DEMO_001_ATTEMPT_001.md
PUSH_ALLOWED: false
""",
                    "CURRENT_GATE.md": """# CURRENT_GATE

STATUS: closed
TASK_ID: TASK_DEMO_001
""",
                    "NEXT_ACTION.md": """# NEXT_ACTION

ACTION_TYPE: stop
TARGET_ROLE: orchestrator
TASK_ID: TASK_DEMO_001
TASK_PACKET: NONE
CHECKPOINT_POLICY: no_checkpoint
CHECKPOINT_RECEIPT_REQUIRED: no
CHECKPOINT_RECEIPT_REF: NONE
""",
                },
            )

            result = run_lint(root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("LINT_STATE_002", result.stdout)
            self.assertNotIn("LINT_STATE_007", result.stdout)
            self.assertNotIn("LINT_STATE_009", result.stdout)

    def test_strict_fails_on_warning_only_designer_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(
                root,
                {
                    "NEXT_ACTION.md": RUNTIME_CONTENT["NEXT_ACTION.md"].replace(
                        "TARGET_ROLE: developer", "TARGET_ROLE: designer"
                    )
                },
            )

            non_strict = run_lint(root)
            strict = run_lint(root, "--strict")

            self.assertEqual(non_strict.returncode, 0, non_strict.stdout + non_strict.stderr)
            self.assertIn("LINT_ROLE_002", non_strict.stdout)
            self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
            self.assertIn("ASO lint: FAILED", strict.stdout)

    def test_deprecated_reasoning_warns_and_strict_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            task_path = root / "project-runtime" / "tasks" / "TASK_DEMO_001.md"
            task_path.write_text(
                TASK_PACKET.replace("REASONING_LEVEL: high", "REASONING_LEVEL: role_default"),
                encoding="utf-8",
            )

            non_strict = run_lint(root)
            strict = run_lint(root, "--strict")

            self.assertEqual(non_strict.returncode, 0, non_strict.stdout + non_strict.stderr)
            self.assertIn("LINT_REASONING_002", non_strict.stdout)
            self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
            self.assertIn("ASO lint: FAILED", strict.stdout)

    def test_lint_rejects_reasoning_below_explicit_floor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            task_path = root / "project-runtime" / "tasks" / "TASK_DEMO_001.md"
            task_path.write_text(
                TASK_PACKET.replace("REASONING_LEVEL: high", "REASONING_LEVEL: medium")
                + "REASONING_LEVEL_REQUIRED_FLOOR: high\n",
                encoding="utf-8",
            )

            result = run_lint(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("LINT_REASONING_005", result.stdout)

    def test_lint_detects_reasoning_lifecycle_naming_and_skeleton_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            task_path = root / "project-runtime" / "tasks" / "TASK_DEMO_001.md"
            task_path.write_text(TASK_PACKET.replace("REASONING_LEVEL: high", "REASONING_LEVEL: role_default"), encoding="utf-8")
            result_path = root / "project-runtime" / "results" / "TASK_DEMO_001.md"
            result_path.write_text(
                """# RESULT

TASK_ID: TASK_DEMO_001
AGENT_INSTANCE_ID: agent_missing_termination
SKELETON_STATUS: passed
MVP_READY: true
REUSE_ALLOWED: true
AGENT_TERMINATION_REQUIRED: false
""",
                encoding="utf-8",
            )

            result = run_lint(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("LINT_REASONING_002", result.stdout)
            self.assertIn("LINT_NAMING_001", result.stdout)
            self.assertIn("LINT_NAMING_002", result.stdout)
            self.assertIn("LINT_AGENT_001", result.stdout)
            self.assertIn("LINT_AGENT_002", result.stdout)
            self.assertIn("LINT_AGENT_003", result.stdout)
            self.assertIn("LINT_AGENT_005", result.stdout)
            self.assertIn("LINT_PRODUCT_001", result.stdout)

    def test_lint_detects_agent_reuse_in_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            instances_path = root / "project-runtime" / "agents" / "instances.jsonl"
            instances_path.write_text(
                "\n".join(
                    [
                        '{"event":"agent_result_received","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","reuse_allowed":true}',
                        '{"event":"agent_instance_terminated","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_OTHER_002","reuse_allowed":false}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_lint(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("LINT_AGENT_004", result.stdout)
            self.assertIn("LINT_AGENT_006", result.stdout)

    def test_lint_warns_when_result_references_unknown_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            result_path = root / "project-runtime" / "results" / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.write_text(RESULT.replace("TASK_ID: TASK_DEMO_001", "TASK_ID: TASK_UNKNOWN_999"), encoding="utf-8")

            result = run_lint(root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("LINT_NAMING_005", result.stdout)

    def test_lint_validates_audit_result_task_and_result_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            audit_dir = root / "project-runtime" / "results" / "audit"
            audit_dir.mkdir()
            (audit_dir / "AUDIT_RESULT_TASK_DEMO_001_ATTEMPT_001.md").write_text(AUDIT_RESULT, encoding="utf-8")
            append_agent_events(
                root,
                [
                    '{"event":"agent_result_received","agent_instance_id":"audit_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","result_ref":"project-runtime/results/audit/AUDIT_RESULT_TASK_DEMO_001_ATTEMPT_001.md","reuse_allowed":false}',
                    '{"event":"agent_instance_terminated","agent_instance_id":"audit_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","reuse_allowed":false}',
                ],
            )

            result = run_lint(root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("LINT_NAMING_008", result.stdout)
            self.assertNotIn("LINT_NAMING_009", result.stdout)

    def test_lint_warns_when_audit_result_lacks_worker_result_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            audit_dir = root / "project-runtime" / "results" / "audit"
            audit_dir.mkdir()
            audit_text = AUDIT_RESULT.replace(
                "- SOURCE_RESULT_REF: project-runtime/results/RESULT_TASK_DEMO_001_ATTEMPT_001.md",
                "- NONE",
            )
            (audit_dir / "AUDIT_RESULT_TASK_DEMO_001_ATTEMPT_001.md").write_text(audit_text, encoding="utf-8")
            append_agent_events(
                root,
                [
                    '{"event":"agent_result_received","agent_instance_id":"audit_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","result_ref":"project-runtime/results/audit/AUDIT_RESULT_TASK_DEMO_001_ATTEMPT_001.md","reuse_allowed":false}',
                    '{"event":"agent_instance_terminated","agent_instance_id":"audit_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","reuse_allowed":false}',
                ],
            )

            result = run_lint(root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("LINT_NAMING_008", result.stdout)


if __name__ == "__main__":
    unittest.main()
