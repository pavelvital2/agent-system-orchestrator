from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"


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


RUNTIME_CONTENT = {
    "PROJECT_STATE.md": """# PROJECT_STATE

PROJECT_SLUG: demo-project
WORKSPACE_TYPE: target_workspace
PROJECT_STATUS: active
EXPECTED_GIT_REMOTE: https://example.invalid/demo.git
ACTUAL_GIT_REMOTE: https://example.invalid/demo.git
EXPECTED_BRANCH: main
ACTUAL_BRANCH: main
PROJECT_CHECKPOINT_STATUS: pending
CHECKPOINT_ELIGIBILITY: eligible
CHECKPOINT_BLOCKED_BY: NONE
PUSH_ALLOWED: false
PACKAGE_VERSION: 3.0.2
GOVERNANCE_RULESET_VERSION: 3.0.2
RUNTIME_SCHEMA_VERSION: 3.0.0
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
    "REPOSITORY_LOCK.md": """# REPOSITORY_LOCK

REPOSITORY_LOCK_STATUS: accepted
EXPECTED_GIT_REMOTE: https://example.invalid/demo.git
ACTUAL_GIT_REMOTE: https://example.invalid/demo.git
EXPECTED_BRANCH: main
ACTUAL_BRANCH_AT_LOCK: main
PUSH_ALLOWED: false
""",
    "WORKSPACE_IDENTITY.md": """# WORKSPACE_IDENTITY

PROJECT_SLUG: demo-project
PROJECT_NAME: Demo Project
WORKSPACE_TYPE: target_workspace
EXPECTED_GIT_REMOTE: https://example.invalid/demo.git
ACTUAL_GIT_REMOTE: https://example.invalid/demo.git
EXPECTED_BRANCH: main
ACTUAL_BRANCH: main
PUSH_ALLOWED: false
""",
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


def init_git(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, text=True, capture_output=True)


def write_package_fixture(root: Path) -> list[Path]:
    paths: list[Path] = []
    for relpath, text in {
        "README.md": PACKAGE_README,
        "agent-system/README.md": PACKAGE_README,
        "agent-system/PACKAGE_VERSIONING.md": """# PACKAGE_VERSIONING

## Active version constants

CURRENT_PACKAGE_VERSION: 3.0.2
CURRENT_GOVERNANCE_RULESET_VERSION: 3.0.2
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
""",
        "pyproject.toml": """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "agent-system-orchestrator"
version = "3.0.2"

[project.scripts]
aso = "agent_system_orchestrator_aso.cli:main"
""",
        "Makefile": """.PHONY: test smoke doctor lint

test:
\tpython3 -m unittest discover -s agent-system/tools/aso/tests

smoke:
\tpython3 agent-system/tools/aso/aso.py --help

doctor:
\tpython3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict

lint:
\tpython3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
""",
        ".gitignore": "/project-runtime/\n/project-input/\n/project-archive/\n",
        "agent-system/tools/aso/aso.py": 'from commands import doctor\n"doctor"\nhandler=doctor.run\n',
        "agent-system/tools/aso/commands/status.py": "",
        "agent-system/tools/aso/commands/lint.py": "",
        "agent-system/tools/aso/commands/archive_verify.py": "",
        "agent-system/tools/aso/commands/doctor.py": "",
        "agent-system/tools/aso/commands/validate_context_pack.py": "",
        "agent_system_orchestrator_aso/__init__.py": '__version__ = "3.0.2"\n',
        "agent_system_orchestrator_aso/cli.py": "",
        "agent-system/tools/aso/tests/test_placeholder.py": "",
    }.items():
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    project_input = root / "project-input"
    project_input.mkdir()
    local_note = project_input / "local-task.md"
    local_note.write_text("local only\n", encoding="utf-8")
    paths.append(local_note)
    return paths


def write_workspace(root: Path, overrides: dict[str, str] | None = None) -> list[Path]:
    runtime = root / "project-runtime"
    runtime.mkdir()
    paths: list[Path] = []
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
                '{"event":"agent_result_received","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","result_ref":"project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md","reuse_allowed":false}',
                '{"event":"agent_instance_terminated","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","reuse_allowed":false}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    paths.append(instances_path)
    return paths


def run_doctor(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "doctor", "--root", str(root), *extra],
        check=False,
        text=True,
        capture_output=True,
    )


class DoctorCommandTests(unittest.TestCase):
    def test_package_doctor_writes_json_and_does_not_mutate_forbidden_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git(root)
            paths = write_package_fixture(root)
            mtimes_before = {path: path.stat().st_mtime_ns for path in paths}
            forbidden_before = sorted(path.relative_to(root).as_posix() for path in (root / "project-input").rglob("*"))
            json_out = root / "doctor.json"

            result = run_doctor(root, "--mode", "package", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO doctor: PASSED", result.stdout)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["tool"], "aso")
            self.assertEqual(report["command"], "doctor")
            self.assertEqual(report["mode"], "package")
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["summary"]["errors"], 0)
            self.assertEqual(report["summary"]["warnings"], 0)
            self.assertGreaterEqual(report["summary"]["info"], 1)

            self.assertEqual(mtimes_before, {path: path.stat().st_mtime_ns for path in paths})
            forbidden_after = sorted(path.relative_to(root).as_posix() for path in (root / "project-input").rglob("*"))
            self.assertEqual(forbidden_before, forbidden_after)

    def test_doctor_strict_fails_on_warning_only_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workspace(
                root,
                {
                    "WORKSPACE_IDENTITY.md": """# WORKSPACE_IDENTITY

PROJECT_SLUG: demo-project
PROJECT_NAME: Demo Project
EXPECTED_GIT_REMOTE: https://example.invalid/demo.git
ACTUAL_GIT_REMOTE: https://example.invalid/demo.git
EXPECTED_BRANCH: main
ACTUAL_BRANCH: main
PUSH_ALLOWED: false
""",
                },
            )

            non_strict = run_doctor(root, "--mode", "workspace")
            strict = run_doctor(root, "--mode", "workspace", "--strict")

            self.assertEqual(non_strict.returncode, 0, non_strict.stdout + non_strict.stderr)
            self.assertIn("ASO doctor: WARNING", non_strict.stdout)
            self.assertIn("DOCTOR_WS_IDENTITY_001", non_strict.stdout)
            self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
            self.assertIn("ASO doctor: FAILED", strict.stdout)
            self.assertIn("DOCTOR_WS_IDENTITY_001", strict.stdout)

    def test_workspace_doctor_passes_clean_workspace_and_preserves_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_workspace(root)
            mtimes_before = {path: path.stat().st_mtime_ns for path in paths}
            json_out = root / "workspace-doctor.json"

            result = run_doctor(root, "--mode", "workspace", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO doctor: PASSED", result.stdout)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "workspace")
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["summary"], {"errors": 0, "warnings": 0, "info": 0})
            self.assertEqual(mtimes_before, {path: path.stat().st_mtime_ns for path in paths})

    def test_workspace_doctor_reports_actionable_missing_runtime_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

            result = run_doctor(root, "--mode", "workspace", "--strict")

            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("DOCTOR_WS_ROOT_001", result.stdout)
            self.assertIn("LINT_IO_002", result.stdout)
            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
