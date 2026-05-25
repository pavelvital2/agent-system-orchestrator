from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from package_fixture_helpers import PYPROJECT_RESOURCE_DATA, write_minimal_package_resources, write_resource_manifest_in


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
PACKAGE_VERSION: 3.1.1
GOVERNANCE_RULESET_VERSION: 3.1.1
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

CURRENT_PACKAGE_VERSION: 3.1.1
CURRENT_GOVERNANCE_RULESET_VERSION: 3.1.1
CURRENT_RUNTIME_SCHEMA_VERSION: 3.0.0
""",
        "pyproject.toml": """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "agent-system-orchestrator"
version = "3.1.1"

[project.scripts]
aso = "agent_system_orchestrator_aso.cli:main"

[tool.setuptools.packages.find]
where = ["agent-system/tools/aso"]
include = ["agent_system_orchestrator_aso*"]
"""
        + PYPROJECT_RESOURCE_DATA,
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
        ".github/workflows/governance.yml": """name: governance
on:
  push:
    branches:
      - main
      - upgrade/**
""",
        "agent-system/tools/aso/aso.py": (
            "import sys\n"
            "from agent_system_orchestrator_aso.aso_tool.aso import build_parser, main\n"
            'if __name__ == "__main__":\n'
            "    sys.exit(main())\n"
        ),
        "agent-system/tools/aso/agent_system_orchestrator_aso/__init__.py": '__version__ = "3.1.1"\n',
        "agent-system/tools/aso/agent_system_orchestrator_aso/cli.py": "from .aso_tool.aso import main\n",
        "agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/__init__.py": "",
        "agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/aso.py": (
            "import argparse\n"
            "from .commands import doctor\n"
            "def build_parser():\n"
            "    parser = argparse.ArgumentParser(prog='aso')\n"
            "    subparsers = parser.add_subparsers(dest='command')\n"
            '    doctor_parser = subparsers.add_parser("doctor")\n'
            "    doctor_parser.set_defaults(handler=doctor.run)\n"
            "    return parser\n"
            "def main(argv=None):\n"
            "    build_parser().parse_args(argv)\n"
            "    return 0\n"
        ),
        "agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/__init__.py": "",
        "agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/status.py": "",
        "agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/lint.py": "",
        "agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/archive_verify.py": "",
        "agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/doctor.py": "def run(args):\n    return 0\n",
        "agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/validate_context_pack.py": "",
        "agent-system/tools/aso/tests/test_placeholder.py": "",
    }.items():
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    paths.extend(
        write_minimal_package_resources(
            root / "agent-system" / "tools" / "aso" / "agent_system_orchestrator_aso"
        )
    )
    paths.append(write_resource_manifest_in(root))
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
                '{"event":"agent_instance_terminated","event_type":"AGENT_TERMINATED","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","agent_role":"developer","role":"developer","result_ref":"project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md","termination_reason":"result_submitted","terminated_at":"2026-05-17T10:31:00Z","created_by":"orchestrator","next_allowed_action":"audit_route","reuse_allowed":false}',
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


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
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
            self.assertEqual(report["summary"]["info"], 0)

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

    def test_workspace_doctor_reports_bootstrap_repair_hints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project-input").mkdir(exist_ok=True)
            (root / "project-input" / "TZ.md").write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-slug",
                "doctor-bsr",
                "--tz",
                "project-input/TZ.md",
                "--confirm-write",
            )
            render = run_aso("state", "render", "--root", str(root), "--confirm-write")
            project_state = root / "project-runtime" / "state" / "PROJECT_STATE.json"
            project_payload = json.loads(project_state.read_text(encoding="utf-8"))
            project_content = project_payload["content"]
            self.assertIsInstance(project_content, dict)
            project_content["tz_path"] = "Europe/Moscow"
            project_state.write_text(json.dumps(project_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            next_action = root / "project-runtime" / "state" / "NEXT_ACTION.json"
            next_payload = json.loads(next_action.read_text(encoding="utf-8"))
            next_content = next_payload["content"]
            self.assertIsInstance(next_content, dict)
            next_content["action_type"] = "stop"
            next_content["action_semantic"] = "stop_terminal"
            next_action.write_text(json.dumps(next_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            json_out = root / "doctor.json"

            result = run_doctor(root, "--mode", "workspace", "--strict", "--json-out", str(json_out))

            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("BSR_TZ_PATH_TIMEZONE_VALUE", result.stdout)
            self.assertIn("BSR_BOOTSTRAP_STOP_TERMINAL_INVALID", result.stdout)
            self.assertIn("Repair PROJECT_STATE.content.tz_path", result.stdout)
            self.assertIn("bootstrap reconciliation", result.stdout)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            by_rule = {finding["rule_id"]: finding for finding in report["findings"]}
            self.assertIn("project-input/TZ.md", by_rule["BSR_TZ_PATH_TIMEZONE_VALUE"]["recommendation"])
            self.assertIn("aso plan-next --root WORKSPACE --strict", by_rule["BSR_BOOTSTRAP_STOP_TERMINAL_INVALID"]["recommendation"])

    def test_package_doctor_rejects_workspace_root_with_mode_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workspace(root)
            (root / "aso.lock").write_text('{"package_version":"3.6.1"}\n', encoding="utf-8")
            (root / "agent-system" / "tools" / "aso").mkdir(parents=True)
            json_out = root / "doctor.json"

            result = run_doctor(root, "--mode", "package", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("MODE_GUARD_001", result.stdout)
            self.assertIn("Use --mode workspace", result.stdout)
            self.assertNotIn("PACKAGE_LAYOUT_006", result.stdout)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["findings"][0]["rule_id"], "MODE_GUARD_001")


if __name__ == "__main__":
    unittest.main()
