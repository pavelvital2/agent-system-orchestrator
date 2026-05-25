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
- SOURCE_RESULT_REF: project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md
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


PACKAGE_README = """# Package

Use the read-only ASO helper at `agent-system/tools/aso/aso.py`.

```text
python3 agent-system/tools/aso/aso.py status --root . --mode package
python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
python3 agent-system/tools/aso/aso.py status --root /path/to/project --mode workspace
python3 agent-system/tools/aso/aso.py lint --root /path/to/project --mode workspace --strict
```

It does not provide mutation, dispatch, or checkpoint commands.
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

    results = runtime / "results" / "worker"
    results.mkdir(parents=True)
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
                '{"event":"agent_result_received","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","result_ref":"project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md","reuse_allowed":false,"timestamp_utc":"2026-05-17T10:30:00Z"}',
                '{"event":"agent_instance_terminated","event_type":"AGENT_TERMINATED","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","agent_role":"developer","role":"developer","result_ref":"project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md","termination_reason":"result_submitted","terminated_at":"2026-05-17T10:31:00Z","created_by":"orchestrator","next_allowed_action":"audit_route","reuse_allowed":false,"timestamp_utc":"2026-05-17T10:31:00Z"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    paths.append(instances_path)
    return paths


def write_package_fixture(root: Path, *, include_untracked_input: bool = False) -> None:
    aso_root = root / "agent-system" / "tools" / "aso"
    package = aso_root / "agent_system_orchestrator_aso"
    (package / "aso_tool" / "commands").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "README.md").write_text(PACKAGE_README, encoding="utf-8")
    (root / "agent-system" / "README.md").write_text(PACKAGE_README, encoding="utf-8")
    (aso_root / "aso.py").write_text(
        (
            "import sys\n"
            "from agent_system_orchestrator_aso.aso_tool.aso import build_parser, main\n"
            'if __name__ == "__main__":\n'
            "    sys.exit(main())\n"
        ),
        encoding="utf-8",
    )
    (package / "__init__.py").write_text("\n", encoding="utf-8")
    (package / "cli.py").write_text("from .aso_tool.aso import main\n", encoding="utf-8")
    (package / "aso_tool" / "__init__.py").write_text("\n", encoding="utf-8")
    (package / "aso_tool" / "commands" / "__init__.py").write_text("\n", encoding="utf-8")
    (package / "aso_tool" / "aso.py").write_text(
        (
            "import argparse\n"
            "def build_parser():\n"
            "    return argparse.ArgumentParser(prog='aso')\n"
            "def main(argv=None):\n"
            "    build_parser().parse_args(argv)\n"
            "    return 0\n"
        ),
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        (
            "[project]\n"
            'name = "aso-fixture"\n'
            'version = "0.0.0"\n'
            "\n"
            "[project.scripts]\n"
            'aso = "agent_system_orchestrator_aso.cli:main"\n'
            "\n"
            "[tool.setuptools.packages.find]\n"
            'where = ["agent-system/tools/aso"]\n'
            'include = ["agent_system_orchestrator_aso*"]\n'
        ),
        encoding="utf-8",
    )
    (root / ".gitignore").write_text(
        "/project-runtime/\n/project-input/\n/project-archive/\n",
        encoding="utf-8",
    )
    (root / ".github" / "workflows" / "governance.yml").write_text(
        (
            "name: governance\n"
            "on:\n"
            "  push:\n"
            "    branches:\n"
            "      - main\n"
            "      - upgrade/**\n"
        ),
        encoding="utf-8",
    )
    if include_untracked_input:
        (root / "project-input").mkdir()
        (root / "project-input" / "local-task.md").write_text("local\n", encoding="utf-8")


def init_git(root: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )


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


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
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

    def test_lint_strict_reports_invalid_tz_path_from_state_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init = run_aso("state", "init", "--root", str(root), "--project-slug", "bad-tz", "--confirm-write")
            (root / "project-input").mkdir(exist_ok=True)
            (root / "project-input" / "TZ.md").write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
            render = run_aso("state", "render", "--root", str(root), "--confirm-write")
            project_state = root / "project-runtime" / "state" / "PROJECT_STATE.json"
            payload = json.loads(project_state.read_text(encoding="utf-8"))
            content = payload["content"]
            self.assertIsInstance(content, dict)
            content["tz_path"] = "Europe/Moscow"
            project_state.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            json_out = root / "lint.json"

            result = run_lint(root, "--mode", "workspace", "--strict", "--json-out", str(json_out))

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("BSR_TZ_PATH_TIMEZONE_VALUE", result.stdout)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            by_rule = {finding["rule_id"]: finding for finding in report["findings"]}
            self.assertIn("BSR_TZ_PATH_TIMEZONE_VALUE", by_rule)
            self.assertIn("project-input/TZ.md", by_rule["BSR_TZ_PATH_TIMEZONE_VALUE"]["recommendation"])

    def test_lint_workspace_mode_still_requires_project_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = run_lint(root, "--mode", "workspace", "--strict")

            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("ASO lint: IO_ERROR", result.stdout)
            self.assertIn("LINT_IO_002", result.stdout)

    def test_package_lint_strict_passes_without_project_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git(root)
            write_package_fixture(root, include_untracked_input=True)

            result = run_lint(root, "--mode", "package", "--strict")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO lint: PASSED", result.stdout)
            self.assertIn("Mode: package", result.stdout)
            self.assertIn("Findings: 0", result.stdout)

    def test_package_lint_rejects_tracked_generated_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git(root)
            write_package_fixture(root)
            json_out = root / "package-lint.json"
            (root / "project-runtime").mkdir()
            tracked_runtime_file = root / "project-runtime" / "PROJECT_STATE.md"
            tracked_runtime_file.write_text("# PROJECT_STATE\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "-f", "project-runtime/PROJECT_STATE.md"],
                cwd=root,
                check=True,
                text=True,
                capture_output=True,
            )

            result = run_lint(root, "--mode", "package", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("ASO lint: FAILED", result.stdout)
            self.assertIn("LINT_PKG_001", result.stdout)

            report = json.loads(json_out.read_text(encoding="utf-8"))
            finding = report["findings"][0]
            self.assertEqual(finding["rule_id"], "LINT_PKG_001")
            self.assertEqual(finding["severity"], "error")
            self.assertEqual(finding["mode"], "package")
            self.assertEqual(finding["path"], "project-runtime/PROJECT_STATE.md")
            self.assertIn("project-runtime", finding["message"])

    def test_lint_reports_workspace_traceability_stable_ids_and_json_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(
                root,
                {
                    "TASK_REGISTRY.md": """# TASK_REGISTRY

TASK_ID: TASK_DEMO_001
STATUS: completed
RESULT_REFS: project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md
AUDIT_REFS: NONE
COMMIT_HASH: NONE
BRANCH: NONE
ACCEPTED_FILES: NONE
CHECKPOINT_REF: NONE
""",
                },
            )
            json_out = root / "workspace-lint.json"

            result = run_lint(root, "--mode", "workspace", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("LINT_RT_002", result.stdout)
            self.assertIn("LINT_RT_003", result.stdout)
            self.assertIn("LINT_RT_004", result.stdout)

            report = json.loads(json_out.read_text(encoding="utf-8"))
            by_rule = {finding["rule_id"]: finding for finding in report["findings"]}
            finding = by_rule["LINT_RT_002"]
            self.assertEqual(finding["severity"], "error")
            self.assertEqual(finding["mode"], "workspace")
            self.assertEqual(finding["path"], "project-runtime/TASK_REGISTRY.md")
            self.assertIn("AUDIT_REFS", finding["message"])

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
            self.assertIn("LINT_RT_005", result.stdout)

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
                        '{"event":"agent_instance_terminated","event_type":"AGENT_TERMINATED","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_OTHER_002","agent_role":"developer","role":"developer","result_ref":"project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md","termination_reason":"result_submitted","terminated_at":"2026-05-17T10:31:00Z","created_by":"orchestrator","next_allowed_action":"audit_route","reuse_allowed":false}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_lint(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("LINT_AGENT_004", result.stdout)
            self.assertIn("LINT_AGENT_006", result.stdout)

    def test_lint_agent_003_rejects_wrong_termination_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            instances_path = root / "project-runtime" / "agents" / "instances.jsonl"
            text = instances_path.read_text(encoding="utf-8")
            instances_path.write_text(text.replace('"task_id":"TASK_DEMO_001","agent_role"', '"task_id":"TASK_OTHER_002","agent_role"'), encoding="utf-8")
            json_out = root / "lint.json"

            result = run_lint(root, "--json-out", str(json_out))
            report = json.loads(json_out.read_text(encoding="utf-8"))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            agent_findings = [item for item in report["findings"] if item["rule_id"] == "LINT_AGENT_003"]
            self.assertEqual(len(agent_findings), 1)
            self.assertIn("task_id=TASK_OTHER_002", agent_findings[0]["details"])

    def test_lint_agent_003_rejects_wrong_termination_result_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            instances_path = root / "project-runtime" / "agents" / "instances.jsonl"
            text = instances_path.read_text(encoding="utf-8")
            old_ref = '"result_ref":"project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md"'
            before_termination_ref, termination_ref_and_after = text.split(old_ref, 1)
            instances_path.write_text(
                before_termination_ref
                + old_ref
                + termination_ref_and_after.replace(
                    old_ref,
                    '"result_ref":"project-runtime/results/worker/RESULT_TASK_OTHER_002_ATTEMPT_001.md"',
                    1,
                ),
                encoding="utf-8",
            )
            json_out = root / "lint.json"

            result = run_lint(root, "--json-out", str(json_out))
            report = json.loads(json_out.read_text(encoding="utf-8"))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            agent_findings = [item for item in report["findings"] if item["rule_id"] == "LINT_AGENT_003"]
            self.assertEqual(len(agent_findings), 1)
            self.assertIn(
                "result_ref=project-runtime/results/worker/RESULT_TASK_OTHER_002_ATTEMPT_001.md",
                agent_findings[0]["details"],
            )

    def test_lint_errors_when_result_references_task_missing_from_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            result_path = root / "project-runtime" / "results" / "worker" / "RESULT_TASK_DEMO_001_ATTEMPT_001.md"
            result_path.write_text(RESULT.replace("TASK_ID: TASK_DEMO_001", "TASK_ID: TASK_UNKNOWN_999"), encoding="utf-8")

            result = run_lint(root)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("LINT_NAMING_005", result.stdout)
            self.assertIn("LINT_RT_001", result.stdout)

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
                    '{"event":"auditor_agent_terminated","event_type":"AUDITOR_AGENT_TERMINATED","agent_instance_id":"audit_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","agent_role":"auditor","role":"auditor","result_ref":"project-runtime/results/audit/AUDIT_RESULT_TASK_DEMO_001_ATTEMPT_001.md","termination_reason":"result_submitted","terminated_at":"2026-05-17T10:31:00Z","created_by":"orchestrator","next_allowed_action":"checkpoint_preflight","reuse_allowed":false}',
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
                "- SOURCE_RESULT_REF: project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md",
                "- NONE",
            )
            (audit_dir / "AUDIT_RESULT_TASK_DEMO_001_ATTEMPT_001.md").write_text(audit_text, encoding="utf-8")
            append_agent_events(
                root,
                [
                    '{"event":"agent_result_received","agent_instance_id":"audit_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","result_ref":"project-runtime/results/audit/AUDIT_RESULT_TASK_DEMO_001_ATTEMPT_001.md","reuse_allowed":false}',
                    '{"event":"auditor_agent_terminated","event_type":"AUDITOR_AGENT_TERMINATED","agent_instance_id":"audit_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","agent_role":"auditor","role":"auditor","result_ref":"project-runtime/results/audit/AUDIT_RESULT_TASK_DEMO_001_ATTEMPT_001.md","termination_reason":"result_submitted","terminated_at":"2026-05-17T10:31:00Z","created_by":"orchestrator","next_allowed_action":"checkpoint_preflight","reuse_allowed":false}',
                ],
            )

            result = run_lint(root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("LINT_NAMING_008", result.stdout)

    def test_package_lint_rejects_workspace_root_with_mode_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_runtime(root)
            (root / "aso.lock").write_text('{"package_version":"3.6.1"}\n', encoding="utf-8")
            (root / "agent-system" / "tools" / "aso").mkdir(parents=True)

            result = run_lint(root, "--mode", "package", "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("MODE_GUARD_001", result.stdout)
            self.assertNotIn("PACKAGE_LAYOUT_006", result.stdout)


if __name__ == "__main__":
    unittest.main()
