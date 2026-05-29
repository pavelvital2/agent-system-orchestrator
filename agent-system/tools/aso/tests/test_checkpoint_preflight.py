from __future__ import annotations

import json
import shutil
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
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "state"
VALID_WORKSPACE = FIXTURE_ROOT / "valid_workspace"


PACKAGE_README = """# Package

Use the ASO helper at `agent-system/tools/aso/aso.py` for read-only diagnostics plus explicit confirmed writes.

```text
python3 agent-system/tools/aso/aso.py status --root . --mode package
python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
python3 agent-system/tools/aso/aso.py status --root /path/to/project --mode workspace
python3 agent-system/tools/aso/aso.py lint --root /path/to/project --mode workspace --strict
```

It does not dispatch live agents, execute checkpoints, or run daemons.
"""

AUDIT_FAIL_RESULT = """AUDIT_RESULT:
STATUS: fail
TASK_ID: TASK_FIXTURE_STATE_001
AGENT_INSTANCE_ID: audit_TASK_FIXTURE_STATE_001_attempt_001
ROLE: auditor
TASK: TASK_FIXTURE_STATE_001
SUMMARY:
Audit failed.
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
- SOURCE_RESULT_REF: project-runtime/results/worker/RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md
- CHANGED_FILES_SCOPE_STATUS: failed
SCOPE_VERIFICATION:
- NONE
FORBIDDEN_CHANGES_CHECK:
- NONE
RISKS:
- NONE
LIMITATIONS:
- NONE
BLOCKERS:
- audit_failed
GAPS:
- NONE
NEXT_RECOMMENDED_ACTION:
- ROUTE_CORRECTION
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""

AUDIT_PASS_RESULT = """AUDIT_RESULT:
STATUS: pass
TASK_ID: TASK_FIXTURE_STATE_001
AGENT_INSTANCE_ID: audit_TASK_FIXTURE_STATE_001_attempt_001
ROLE: auditor
TASK: TASK_FIXTURE_STATE_001
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
- SOURCE_RESULT_REF: project-runtime/results/worker/RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md
- CHANGED_FILES_SCOPE_STATUS: passed
SCOPE_VERIFICATION:
- TASK_PACKET_SCHEMA_STATUS: passed
FORBIDDEN_CHANGES_CHECK:
- FORBIDDEN_PATH_STATUS: passed
RISKS:
- NONE
LIMITATIONS:
- NONE
BLOCKERS:
- NONE
GAPS:
- NONE
NEXT_RECOMMENDED_ACTION:
- CHECKPOINT_PREFLIGHT
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""


AUDIT_PASS_MULTILINE_NORMALIZED_RESULT = """AUDIT_RESULT:
STATUS:
PASS

TASK_ID:
TASK_FIXTURE_STATE_001

AGENT_INSTANCE_ID:
audit_TASK_FIXTURE_STATE_001_attempt_001

ROLE:
Auditor

TASK:
TASK_FIXTURE_STATE_001

SOURCE_RESULT_REF:
project-runtime/results/worker/RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md

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
- SOURCE_BOUNDARY_STATUS: passed
SCOPE_VERIFICATION:
- TASK_PACKET_SCHEMA_STATUS: passed
FORBIDDEN_CHANGES_CHECK:
- FORBIDDEN_PATH_STATUS: passed
RISKS:
- NONE
LIMITATIONS:
- NONE
BLOCKERS:
- NONE
GAPS:
- NONE
NEXT_RECOMMENDED_ACTION:
- CHECKPOINT_PREFLIGHT
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""


def run_preflight(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "checkpoint-preflight", "--root", str(root), *extra],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def init_git(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, text=True, capture_output=True)


def write_package_fixture(root: Path) -> None:
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
        )
        + PYPROJECT_RESOURCE_DATA,
        encoding="utf-8",
    )
    write_minimal_package_resources(package)
    write_resource_manifest_in(root)
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


def content(payload: dict[str, object]) -> dict[str, object]:
    value = payload["content"]
    if not isinstance(value, dict):
        raise AssertionError("sidecar content must be a dictionary")
    return value


def update_markdown_field(root: Path, filename: str, field: str, value: str) -> None:
    path = root / "project-runtime" / filename
    lines = path.read_text(encoding="utf-8").splitlines()
    prefix = f"{field}:"
    updated = False
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{field}: {value}"
            updated = True
            break
    if not updated:
        lines.append(f"{field}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_next_action(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "NEXT_ACTION.json")
    body = content(payload)
    body.update(updates)
    write_sidecar(root, "NEXT_ACTION.json", payload)
    markdown_fields = {
        "action_type": "ACTION_TYPE",
        "target_role": "TARGET_ROLE",
        "task_id": "TASK_ID",
        "dependency_status": "DEPENDENCY_STATUS",
        "action_semantic": "ACTION_SEMANTIC",
        "checkpoint_policy": "CHECKPOINT_POLICY",
        "checkpoint_preflight_required": "CHECKPOINT_PREFLIGHT_REQUIRED",
        "checkpoint_receipt_required": "CHECKPOINT_RECEIPT_REQUIRED",
    }
    for key, field in markdown_fields.items():
        if key in updates:
            value = updates[key]
            if isinstance(value, bool):
                update_markdown_field(root, "NEXT_ACTION.md", field, "yes" if value else "no")
            elif isinstance(value, str):
                update_markdown_field(root, "NEXT_ACTION.md", field, value)


def set_project_state(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "PROJECT_STATE.json")
    body = content(payload)
    body.update(updates)
    write_sidecar(root, "PROJECT_STATE.json", payload)
    markdown_fields = {
        "checkpoint_eligibility": "CHECKPOINT_ELIGIBILITY",
        "checkpoint_eligibility_status": "CHECKPOINT_ELIGIBILITY_STATUS",
        "project_status": "PROJECT_STATUS",
    }
    for key, field in markdown_fields.items():
        if key in updates and isinstance(updates[key], str):
            update_markdown_field(root, "PROJECT_STATE.md", field, str(updates[key]))


def set_current_gate(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "CURRENT_GATE.json")
    body = content(payload)
    body.update(updates)
    write_sidecar(root, "CURRENT_GATE.json", payload)
    markdown_fields = {
        "action_semantic": "ACTION_SEMANTIC",
        "checkpoint_eligibility": "CHECKPOINT_ELIGIBILITY",
        "checkpoint_eligibility_status": "CHECKPOINT_ELIGIBILITY_STATUS",
    }
    for key, field in markdown_fields.items():
        if key in updates and isinstance(updates[key], str):
            update_markdown_field(root, "CURRENT_GATE.md", field, str(updates[key]))


def set_task(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "TASK_REGISTRY.json")
    body = content(payload)
    tasks = body["tasks"]
    if not isinstance(tasks, list) or not tasks or not isinstance(tasks[0], dict):
        raise AssertionError("fixture task registry must contain one task")
    tasks[0].update(updates)
    write_sidecar(root, "TASK_REGISTRY.json", payload)
    if "status" in updates and isinstance(updates["status"], str):
        update_markdown_field(root, "TASK_REGISTRY.md", "STATUS", str(updates["status"]))


class CheckpointPreflightCommandTests(unittest.TestCase):
    def test_help_declares_read_only_behavior(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "checkpoint-preflight", "--help"],
            check=False,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Read-only checkpoint eligibility preflight", result.stdout)
        self.assertIn("without staging, committing, pushing", result.stdout)

    def test_package_preflight_passes_clean_package_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git(root)
            write_package_fixture(root)
            json_out = root / "checkpoint-preflight.json"

            result = run_preflight(root, "--mode", "package", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO checkpoint-preflight: ELIGIBLE", result.stdout)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(report["eligible"])
            self.assertFalse(report["mutations_performed"])
            self.assertEqual(report["blocking_rules"], [])
            self.assertEqual(report["warnings"], [])
            self.assertFalse(report["evidence"]["script_integration"]["checkpoint_preflight_sh_invoked"])

    def test_package_preflight_blocks_tracked_forbidden_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_git(root)
            write_package_fixture(root)
            json_out = root / "checkpoint-preflight.json"
            (root / "project-input").mkdir()
            tracked_file = root / "project-input" / "local-task.md"
            tracked_file.write_text("local\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "-f", "project-input/local-task.md"],
                cwd=root,
                check=True,
                text=True,
                capture_output=True,
            )

            result = run_preflight(root, "--mode", "package", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertFalse(report["eligible"])
            rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
            self.assertIn("LINT_PKG_002", rule_ids)
            self.assertFalse(report["mutations_performed"])

    def test_workspace_preflight_blocks_checkpoint_without_audit_pass_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            set_project_state(root, checkpoint_eligibility="local_only", checkpoint_eligibility_status="not_checked")
            set_current_gate(root, action_semantic="normal", checkpoint_eligibility="local_only", checkpoint_eligibility_status="not_checked")
            json_out = Path(tmp) / "checkpoint-preflight.json"

            result = run_preflight(root, "--mode", "workspace", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertFalse(report["eligible"])
            self.assertFalse(report["mutations_performed"])
            rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
            self.assertIn("GOV-CHECKPOINT-AUDIT-GATE", rule_ids)
            self.assertFalse(report["evidence"]["audit_pass_evidence"]["present"])

    def test_workspace_preflight_allows_checkpoint_with_audit_pass_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            audit_ref = "project-runtime/results/audit/AUDIT_RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md"
            audit_path = root / audit_ref
            audit_path.parent.mkdir(parents=True)
            audit_path.write_text(AUDIT_PASS_RESULT, encoding="utf-8")
            set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            set_project_state(root, checkpoint_eligibility="local_only", checkpoint_eligibility_status="eligible")
            set_current_gate(root, action_semantic="normal", checkpoint_eligibility="local_only", checkpoint_eligibility_status="eligible")
            set_task(
                root,
                status="audit_passed",
                audit_refs=[audit_ref],
            )
            json_out = Path(tmp) / "checkpoint-preflight.json"

            result = run_preflight(root, "--mode", "workspace", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(report["eligible"])
            self.assertEqual(report["blocking_rules"], [])
            self.assertFalse(report["mutations_performed"])
            evidence = report["evidence"]["audit_pass_evidence"]
            self.assertTrue(evidence["present"])
            self.assertEqual(evidence["passed_audit_refs"], [audit_ref])
            self.assertEqual(evidence["unparsed_audit_refs"], [])

    def test_workspace_preflight_uses_normalized_parser_output_from_current_gate_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            audit_ref = "project-runtime/results/audit/AUDIT_RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md"
            audit_path = root / audit_ref
            audit_path.parent.mkdir(parents=True)
            audit_path.write_text(AUDIT_PASS_MULTILINE_NORMALIZED_RESULT, encoding="utf-8")
            set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            set_project_state(root, checkpoint_eligibility="local_only", checkpoint_eligibility_status="eligible")
            set_current_gate(
                root,
                action_semantic="normal",
                checkpoint_eligibility="local_only",
                checkpoint_eligibility_status="eligible",
                gate_evidence=[audit_ref],
            )
            set_task(root, status="audit_passed", audit_refs=[])
            json_out = Path(tmp) / "checkpoint-preflight.json"

            result = run_preflight(root, "--mode", "workspace", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            evidence = report["evidence"]["audit_pass_evidence"]
            self.assertTrue(evidence["present"])
            self.assertEqual(evidence["task_audit_refs"], [])
            self.assertEqual(evidence["current_gate_audit_evidence_refs"], [audit_ref])
            self.assertEqual(evidence["passed_audit_refs"], [audit_ref])
            self.assertEqual(evidence["parsed_audit_results"][0]["status"], "pass")

    def test_workspace_preflight_blocks_missing_audit_result_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            missing_ref = "project-runtime/results/audit/AUDIT_RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_404.md"
            set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            set_project_state(root, checkpoint_eligibility="local_only", checkpoint_eligibility_status="eligible")
            set_current_gate(root, action_semantic="normal", checkpoint_eligibility="local_only", checkpoint_eligibility_status="eligible")
            set_task(root, status="audit_passed", audit_refs=[missing_ref])
            json_out = Path(tmp) / "checkpoint-preflight.json"

            result = run_preflight(root, "--mode", "workspace", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertFalse(report["eligible"])
            evidence = report["evidence"]["audit_pass_evidence"]
            self.assertFalse(evidence["present"])
            self.assertEqual(evidence["passed_audit_refs"], [])
            self.assertEqual(evidence["unparsed_audit_refs"], [missing_ref])
            self.assertEqual(evidence["invalid_audit_results"], [])
            self.assertTrue(
                any("missing or unreadable" in item["message"] for item in report["blocking_rules"])
            )

    def test_workspace_preflight_blocks_non_utf8_audit_result_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            audit_ref = "project-runtime/results/audit/AUDIT_RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md"
            audit_path = root / audit_ref
            audit_path.parent.mkdir(parents=True)
            audit_path.write_bytes(b"\xff\xfe\xfa")
            set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            set_project_state(root, checkpoint_eligibility="local_only", checkpoint_eligibility_status="eligible")
            set_current_gate(root, action_semantic="normal", checkpoint_eligibility="local_only", checkpoint_eligibility_status="eligible")
            set_task(root, status="audit_passed", audit_refs=[audit_ref])
            json_out = Path(tmp) / "checkpoint-preflight.json"

            result = run_preflight(root, "--mode", "workspace", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertFalse(report["eligible"])
            evidence = report["evidence"]["audit_pass_evidence"]
            self.assertFalse(evidence["present"])
            self.assertEqual(evidence["passed_audit_refs"], [])
            self.assertEqual(evidence["unparsed_audit_refs"], [])
            invalid = evidence["invalid_audit_results"]
            self.assertEqual(invalid[0]["ref"], audit_ref)
            self.assertEqual(invalid[0]["reason"], "audit_result_unreadable")
            self.assertIn("UnicodeDecodeError", invalid[0]["evidence"])
            self.assertTrue(
                any("audit_result_unreadable" in item["evidence"] for item in report["blocking_rules"])
            )

    def test_workspace_preflight_blocks_parsed_audit_result_fail_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            audit_ref = "project-runtime/results/audit/AUDIT_RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md"
            audit_path = root / audit_ref
            audit_path.parent.mkdir(parents=True)
            audit_path.write_text(AUDIT_FAIL_RESULT, encoding="utf-8")
            set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            set_project_state(root, checkpoint_eligibility="local_only", checkpoint_eligibility_status="eligible")
            set_current_gate(root, action_semantic="normal", checkpoint_eligibility="local_only", checkpoint_eligibility_status="eligible")
            set_task(root, status="audit_passed", audit_refs=[audit_ref])
            json_out = Path(tmp) / "checkpoint-preflight.json"

            result = run_preflight(root, "--mode", "workspace", "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertFalse(report["eligible"])
            invalid = report["evidence"]["audit_pass_evidence"]["invalid_audit_results"]
            self.assertEqual(invalid[0]["reason"], "audit_result_status_not_pass")
