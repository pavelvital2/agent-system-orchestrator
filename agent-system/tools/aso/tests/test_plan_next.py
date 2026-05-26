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


def run_plan_next(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "plan-next", "--root", str(root), *extra],
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
        "task_packet": "TASK_PACKET",
        "dependency_status": "DEPENDENCY_STATUS",
        "action_semantic": "ACTION_SEMANTIC",
        "workspace_identity_required": "WORKSPACE_IDENTITY_REQUIRED",
        "repository_lock_required": "REPOSITORY_LOCK_REQUIRED",
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
        "current_phase": "CURRENT_PHASE",
        "project_status": "PROJECT_STATUS",
        "identity_validation_status": "IDENTITY_VALIDATION_STATUS",
        "repository_lock_status": "REPOSITORY_LOCK_STATUS",
        "baseline_tracking_status": "BASELINE_TRACKING_STATUS",
        "checkpoint_eligibility": "CHECKPOINT_ELIGIBILITY",
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
        "status": "STATUS",
        "gate_type": "GATE_TYPE",
        "task_id": "TASK_ID",
        "task_packet": "TASK_PACKET",
        "action_semantic": "ACTION_SEMANTIC",
        "baseline_tracking_status": "BASELINE_TRACKING_STATUS",
        "required_next_role": "REQUIRED_NEXT_ROLE",
    }
    for key, field in markdown_fields.items():
        if key in updates and isinstance(updates[key], str):
            update_markdown_field(root, "CURRENT_GATE.md", field, str(updates[key]))


def make_tz_valid(root: Path) -> None:
    tz_dir = root / "project-input"
    tz_dir.mkdir(exist_ok=True)
    (tz_dir / "TZ.md").write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
    set_project_state(root, tz_path="project-input/TZ.md")
    update_markdown_field(root, "PROJECT_STATE.md", "TZ_PATH", "project-input/TZ.md")


def make_tz_placeholder(root: Path) -> None:
    tz_dir = root / "project-input"
    tz_dir.mkdir(exist_ok=True)
    (tz_dir / "TZ.md").write_text(
        "# TZ Placeholder\n\nSTATUS: placeholder\nMUST_REPLACE_BEFORE_LIFECYCLE: true\n",
        encoding="utf-8",
    )
    set_project_state(root, tz_path="project-input/TZ.md")
    update_markdown_field(root, "PROJECT_STATE.md", "TZ_PATH", "project-input/TZ.md")


def set_task(root: Path, **updates: object) -> None:
    payload = load_sidecar(root, "TASK_REGISTRY.json")
    body = content(payload)
    tasks = body["tasks"]
    if not isinstance(tasks, list) or not tasks or not isinstance(tasks[0], dict):
        raise AssertionError("fixture task registry must contain one task")
    tasks[0].update(updates)
    write_sidecar(root, "TASK_REGISTRY.json", payload)
    markdown_fields = {
        "task_id": "TASK_ID",
        "task_title": "TASK_TITLE",
        "task_type": "TASK_TYPE",
        "task_kind": "TASK_KIND",
        "owner_role": "OWNER_ROLE",
        "status": "STATUS",
        "task_packet": "TASK_PACKET",
    }
    for key, field in markdown_fields.items():
        if key in updates and isinstance(updates[key], str):
            update_markdown_field(root, "TASK_REGISTRY.md", field, str(updates[key]))


def update_task_packet_field(root: Path, task_packet: str, field: str, value: str) -> None:
    path = root / task_packet
    lines = path.read_text(encoding="utf-8").splitlines()
    prefix = f"{field}:"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{field}: {value}"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
    raise AssertionError(f"{field} was not found in {task_packet}")


class PlanNextCommandTests(unittest.TestCase):
    def test_help_declares_dry_run_read_only(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "plan-next", "--help"],
            check=False,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Dry-run/read-only", result.stdout)
        self.assertIn("mutating state", result.stdout)

    def test_valid_workspace_recommends_create_agent_and_does_not_edit_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            tracked = [path for path in root.rglob("*") if path.is_file()]
            mtimes_before = {path: path.stat().st_mtime_ns for path in tracked}
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO plan-next: READY", result.stdout)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(report["dry_run"])
            self.assertTrue(report["read_only"])
            self.assertFalse(report["mutations_performed"])
            self.assertEqual(report["recommended_next_action"], "CREATE_AGENT")
            self.assertTrue(report["dispatchable"])
            self.assertTrue(report["dispatchability"]["dispatchable"])
            self.assertEqual(report["dispatchability"]["verdict"], "dispatchable")
            self.assertEqual(report["dispatchability"]["recommended_next_action"], "CREATE_AGENT")
            self.assertEqual(report["dispatchability"]["reasons"], [])
            self.assertEqual(report["target_role"], "developer")
            self.assertEqual(report["task_packet"], "project-runtime/tasks/active/TASK_FIXTURE_STATE_001.md")
            self.assertEqual(report["resolved_reasoning_level"], "high")
            self.assertEqual(report["reasoning_source"], "runtime_contract.reasoning_floor_by_role")
            self.assertEqual(report["dispatchability"]["resolved_reasoning_level"], "high")
            self.assertEqual(report["dispatchability"]["dispatch_receipt_ref_template"], "project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json")
            self.assertTrue(report["dispatch_receipt"]["required"])
            self.assertIn("codex exec", report["dispatch_receipt"]["external_runner_command_template"])
            self.assertEqual(report["blocking_rules"], [])
            self.assertEqual(mtimes_before, {path: path.stat().st_mtime_ns for path in tracked})

    def test_placeholder_tz_blocks_dispatchability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_placeholder(root)
            json_out = Path(tmp) / "plan-next-placeholder.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")
            self.assertFalse(report["dispatchable"])
            self.assertIn("placeholder TZ document", json.dumps(report["blocking_rules"]))

    def test_correction_orchestrator_none_is_not_dispatchable(self) -> None:
        root = FIXTURE_ROOT / "p2_valid_workspace"
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "correction_required")
            self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertNotEqual(report["recommended_next_action"], "CREATE_AGENT")
            self.assertFalse(report["dispatchable"])
            dispatchability = report["dispatchability"]
            self.assertFalse(dispatchability["dispatchable"])
            self.assertEqual(dispatchability["verdict"], "not_dispatchable")
            self.assertEqual(dispatchability["status"], "correction_required")
            self.assertEqual(dispatchability["target_role"], "orchestrator")
            self.assertEqual(dispatchability["role_class"], "control_or_pseudo")
            reason_codes = {reason["reason_code"] for reason in dispatchability["reasons"]}
            self.assertTrue(
                {
                    "action_type_not_dispatch_capable",
                    "target_role_not_profile_execution",
                    "target_role_control_or_pseudo",
                    "task_id_none",
                    "task_packet_none",
                }.issubset(reason_codes)
            )

    def test_create_agent_missing_task_packet_is_blocked_by_dispatchability_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            set_next_action(root, task_packet="project-runtime/tasks/active/MISSING_TASK.md")
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertFalse(report["dispatchable"])
            reason_codes = {reason["reason_code"] for reason in report["dispatchability"]["reasons"]}
            self.assertIn("task_packet_missing", reason_codes)

    def test_invalid_project_state_readiness_statuses_are_not_dispatch_ready(self) -> None:
        cases = (
            (
                "identity_validation_status",
                "DG54_WORKSPACE_IDENTITY_READY",
                "workspace_identity_not_ready",
            ),
            (
                "repository_lock_status",
                "DG54_REPOSITORY_LOCK_READY",
                "repository_lock_not_ready",
            ),
            (
                "baseline_tracking_status",
                "DG54_BASELINE_READY_OR_BOOTSTRAP_EXCEPTION",
                "baseline_not_ready",
            ),
        )
        for field, check_id, reason_code in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = copy_valid_workspace(tmp)
                make_tz_valid(root)
                set_project_state(root, **{field: "not_required"})
                json_out = Path(tmp) / f"plan-next-{field}.json"

                result = run_plan_next(root, "--strict", "--json-out", str(json_out))

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(json_out.read_text(encoding="utf-8"))
                self.assertEqual(report["status"], "blocked")
                self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
                self.assertNotEqual(report["recommended_next_action"], "CREATE_AGENT")
                self.assertFalse(report["dispatchable"])
                self.assertFalse(report["dispatchability"]["dispatchable"])
                self.assertEqual(report["dispatchability"]["verdict"], "not_dispatchable")
                checks = {
                    check["check_id"]: check
                    for check in report["dispatchability"]["checks"]
                    if isinstance(check, dict)
                }
                self.assertIn(check_id, checks)
                self.assertFalse(checks[check_id]["passed"])
                self.assertEqual(checks[check_id]["reason_code"], reason_code)
                reason_codes = {reason["reason_code"] for reason in report["dispatchability"]["reasons"]}
                self.assertIn(reason_code, reason_codes)
                rule_ids = {rule["rule_id"] for rule in report["blocking_rules"]}
                self.assertIn("GOV-ACTION-SEMANTICS", rule_ids)

    def test_invalid_identity_and_repository_statuses_are_not_dispatch_passed(self) -> None:
        cases = (
            (
                "identity_validation_status",
                "DG54_WORKSPACE_IDENTITY_READY",
                "workspace_identity_not_ready",
                "PROJECT_STATE.content.identity_validation_status",
            ),
            (
                "repository_lock_status",
                "DG54_REPOSITORY_LOCK_READY",
                "repository_lock_not_ready",
                "PROJECT_STATE.content.repository_lock_status",
            ),
        )
        for field, check_id, reason_code, input_ref in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = copy_valid_workspace(tmp)
                make_tz_valid(root)
                set_project_state(root, **{field: "surprising"})
                json_out = Path(tmp) / f"plan-next-invalid-{field}.json"

                result = run_plan_next(root, "--strict", "--json-out", str(json_out))

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(json_out.read_text(encoding="utf-8"))
                self.assertEqual(report["status"], "blocked")
                self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
                self.assertFalse(report["dispatchable"])
                self.assertFalse(report["dispatchability"]["dispatchable"])
                checks = {
                    check["check_id"]: check
                    for check in report["dispatchability"]["checks"]
                    if isinstance(check, dict)
                }
                self.assertIn(check_id, checks)
                self.assertFalse(checks[check_id]["passed"])
                self.assertEqual(checks[check_id]["reason_code"], reason_code)
                self.assertIn("is invalid", checks[check_id]["evidence"])
                reason_codes = {reason["reason_code"] for reason in report["dispatchability"]["reasons"]}
                self.assertIn(reason_code, reason_codes)
                self.assertTrue(
                    any(
                        finding["rule_id"] == "SIDECAR_ENUM_VALUE_INVALID"
                        and finding["field"] == f"content.{field}"
                        for finding in report["evidence"]["state_verify"]["findings"]
                    )
                )
                matching_reason = next(
                    reason for reason in report["dispatchability"]["reasons"] if reason["reason_code"] == reason_code
                )
                self.assertEqual(matching_reason["input_ref"], input_ref)

    def test_valid_first_bootstrap_readiness_passes_without_identity_or_lock_requirements(self) -> None:
        packet = "project-runtime/tasks/active/TASK_FIXTURE_STATE_001.md"
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            set_project_state(
                root,
                current_phase="bootstrap",
                identity_validation_status="not_checked",
                repository_lock_status="draft",
                baseline_tracking_status="not_checked",
            )
            set_current_gate(
                root,
                gate_type="bootstrap",
                baseline_tracking_status="not_checked",
                required_next_role="requirements_analyst",
            )
            set_next_action(
                root,
                target_role="requirements_analyst",
                workspace_identity_required=False,
                repository_lock_required=False,
            )
            set_task(
                root,
                task_type="requirements_analyst",
                task_kind="bootstrap",
                owner_role="requirements_analyst",
            )
            update_task_packet_field(root, packet, "TASK_KIND", "bootstrap")
            update_task_packet_field(root, packet, "TASK_TYPE", "requirements_analyst")
            update_task_packet_field(root, packet, "TARGET_ROLE", "requirements_analyst")
            json_out = Path(tmp) / "plan-next-bootstrap.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "CREATE_AGENT")
            self.assertTrue(report["dispatchable"])
            checks = {
                check["check_id"]: check
                for check in report["dispatchability"]["checks"]
                if isinstance(check, dict)
            }
            self.assertTrue(checks["DG54_WORKSPACE_IDENTITY_READY"]["passed"])
            self.assertIn(
                "workspace_identity_required=false",
                checks["DG54_WORKSPACE_IDENTITY_READY"]["evidence"],
            )
            self.assertTrue(checks["DG54_REPOSITORY_LOCK_READY"]["passed"])
            self.assertIn(
                "repository_lock_required=false",
                checks["DG54_REPOSITORY_LOCK_READY"]["evidence"],
            )
            self.assertTrue(checks["DG54_BASELINE_READY_OR_BOOTSTRAP_EXCEPTION"]["passed"])
            self.assertIn(
                "first-bootstrap exception",
                checks["DG54_BASELINE_READY_OR_BOOTSTRAP_EXCEPTION"]["evidence"],
            )

    def test_dispatchability_gate_matrix_across_actions_roles_and_packets(self) -> None:
        packet = "project-runtime/tasks/active/TASK_FIXTURE_STATE_001.md"

        def correction_orchestrator_none(root: Path) -> None:
            set_next_action(
                root,
                action_type="correction",
                target_role="orchestrator",
                task_id="NONE",
                task_packet="NONE",
            )

        def create_agent_profile_none(root: Path) -> None:
            set_next_action(root, task_packet="NONE")

        def create_agent_orchestrator_packet(root: Path) -> None:
            set_next_action(root, target_role="orchestrator")

        def stop_none(root: Path) -> None:
            set_next_action(
                root,
                action_type="stop",
                target_role="none",
                task_id="NONE",
                task_packet="NONE",
                dependency_status="not_applicable",
                action_semantic="stop_terminal",
                checkpoint_policy="no_checkpoint",
            )

        def wait_owner(root: Path) -> None:
            set_next_action(root, action_type="wait_for_owner", dependency_status="ready")

        def create_agent_missing_registry_entry(root: Path) -> None:
            missing_task_id = "TASK_UNREGISTERED_001"
            missing_packet = "project-runtime/tasks/active/TASK_UNREGISTERED_001.md"
            source = root / packet
            target = root / missing_packet
            target.write_text(
                source.read_text(encoding="utf-8").replace("TASK_FIXTURE_STATE_001", missing_task_id),
                encoding="utf-8",
            )
            set_next_action(root, task_id=missing_task_id, task_packet=missing_packet)
            set_current_gate(root, task_id=missing_task_id, task_packet=missing_packet)

        def task_registry_owner_role_mismatch(root: Path) -> None:
            set_task(root, task_type="tester", owner_role="tester")

        def current_gate_task_id_mismatch(root: Path) -> None:
            set_current_gate(root, task_id="TASK_OTHER_001")

        def identity_not_passed(root: Path) -> None:
            set_project_state(root, identity_validation_status="failed")

        def repository_lock_not_passed(root: Path) -> None:
            set_project_state(root, repository_lock_status="revoked")

        def gate_status_forbids_dispatch(root: Path) -> None:
            set_current_gate(root, status="blocked")

        def auditor_route_not_required(root: Path) -> None:
            set_next_action(root, target_role="auditor")

        def lifecycle_system_role_forbidden(root: Path) -> None:
            set_next_action(root, target_role="release_manager")
            set_current_gate(root, required_next_role="release_manager")
            set_task(root, task_type="release_manager", owner_role="release_manager")
            update_task_packet_field(root, packet, "TASK_TYPE", "release_manager")
            update_task_packet_field(root, packet, "TARGET_ROLE", "release_manager")

        def bootstrap_valid_packet(root: Path) -> None:
            set_project_state(root, current_phase="bootstrap", baseline_tracking_status="not_checked")
            set_current_gate(root, gate_type="bootstrap", baseline_tracking_status="not_checked", required_next_role="tester")
            set_next_action(root, target_role="tester")
            set_task(root, task_type="tester", task_kind="bootstrap", owner_role="tester")
            update_task_packet_field(root, packet, "TASK_KIND", "bootstrap")
            update_task_packet_field(root, packet, "TASK_TYPE", "tester")
            update_task_packet_field(root, packet, "TARGET_ROLE", "tester")

        def bootstrap_after_first_dispatch(root: Path) -> None:
            bootstrap_valid_packet(root)
            instances = root / "project-runtime" / "agents" / "instances.jsonl"
            instances.parent.mkdir(parents=True, exist_ok=True)
            instances.write_text('{"event_type":"agent_task_dispatched"}\n', encoding="utf-8")

        def unknown_role(root: Path) -> None:
            set_next_action(root, target_role="wizard")

        cases = [
            {
                "name": "correction/orchestrator/NONE",
                "configure": correction_orchestrator_none,
                "returncode": 1,
                "status": "correction_required",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "control_or_pseudo",
                "target_role": "orchestrator",
                "reason_codes": {
                    "action_type_not_dispatch_capable",
                    "target_role_not_profile_execution",
                    "target_role_control_or_pseudo",
                    "task_id_none",
                    "task_packet_none",
                },
            },
            {
                "name": "create_agent/profile/valid_packet",
                "configure": lambda root: None,
                "returncode": 0,
                "status": "ready",
                "recommended": "CREATE_AGENT",
                "dispatchable": True,
                "role_class": "profile_execution",
                "target_role": "developer",
                "reason_codes": set(),
            },
            {
                "name": "create_agent/profile/NONE",
                "configure": create_agent_profile_none,
                "returncode": 1,
                "status": "blocked",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "profile_execution",
                "target_role": "developer",
                "reason_codes": {"task_packet_none", "task_packet_missing", "task_packet_not_dispatch_valid"},
            },
            {
                "name": "create_agent/orchestrator/packet",
                "configure": create_agent_orchestrator_packet,
                "returncode": 1,
                "status": "blocked",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "control_or_pseudo",
                "target_role": "orchestrator",
                "reason_codes": {
                    "target_role_not_profile_execution",
                    "target_role_control_or_pseudo",
                    "task_packet_not_dispatch_valid",
                },
            },
            {
                "name": "create_agent/profile/valid_packet/missing_registry_entry",
                "configure": create_agent_missing_registry_entry,
                "returncode": 1,
                "status": "blocked",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "profile_execution",
                "target_role": "developer",
                "reason_codes": {"task_registry_incompatible"},
            },
            {
                "name": "create_agent/profile/task_registry_owner_role_mismatch",
                "configure": task_registry_owner_role_mismatch,
                "returncode": 1,
                "status": "blocked",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "profile_execution",
                "target_role": "developer",
                "reason_codes": {"task_registry_incompatible"},
            },
            {
                "name": "create_agent/profile/current_gate_task_id_mismatch",
                "configure": current_gate_task_id_mismatch,
                "returncode": 1,
                "status": "blocked",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "profile_execution",
                "target_role": "developer",
                "reason_codes": {"current_gate_blocks_dispatch"},
            },
            {
                "name": "create_agent/profile/identity_not_passed",
                "configure": identity_not_passed,
                "returncode": 1,
                "status": "blocked",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "profile_execution",
                "target_role": "developer",
                "reason_codes": {"workspace_identity_not_ready"},
            },
            {
                "name": "create_agent/profile/repository_lock_not_passed",
                "configure": repository_lock_not_passed,
                "returncode": 1,
                "status": "blocked",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "profile_execution",
                "target_role": "developer",
                "reason_codes": {"repository_lock_not_ready"},
            },
            {
                "name": "create_agent/profile/current_gate_status_forbids_dispatch",
                "configure": gate_status_forbids_dispatch,
                "returncode": 1,
                "status": "blocked",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "profile_execution",
                "target_role": "developer",
                "reason_codes": {"current_gate_blocks_dispatch"},
            },
            {
                "name": "create_agent/auditor/audit_route_not_required",
                "configure": auditor_route_not_required,
                "returncode": 1,
                "status": "blocked",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "profile_execution",
                "target_role": "auditor",
                "reason_codes": {"current_gate_blocks_dispatch"},
            },
            {
                "name": "create_agent/lifecycle_system_role/forbidden",
                "configure": lifecycle_system_role_forbidden,
                "returncode": 1,
                "status": "blocked",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "unknown",
                "target_role": "release_manager",
                "reason_codes": {
                    "target_role_not_profile_execution",
                    "task_packet_not_dispatch_valid",
                    "reasoning_floor_unresolved",
                },
            },
            {
                "name": "stop",
                "configure": stop_none,
                "returncode": 0,
                "status": "ready",
                "recommended": "STOP",
                "dispatchable": False,
                "role_class": "control_or_pseudo",
                "target_role": "none",
                "reason_codes": {"action_type_not_dispatch_capable", "task_id_none", "task_packet_none"},
            },
            {
                "name": "wait_owner",
                "configure": wait_owner,
                "returncode": 1,
                "status": "blocked",
                "recommended": "ASK_OWNER",
                "dispatchable": False,
                "role_class": "profile_execution",
                "target_role": "developer",
                "reason_codes": {"action_type_not_dispatch_capable"},
                "blocking_rule_ids": {"GOV-ACTION-SEMANTICS"},
            },
            {
                "name": "bootstrap valid packet",
                "configure": bootstrap_valid_packet,
                "returncode": 0,
                "status": "ready",
                "recommended": "CREATE_AGENT",
                "dispatchable": True,
                "role_class": "profile_execution",
                "target_role": "tester",
                "reason_codes": set(),
                "required_check": "DG54_BASELINE_READY_OR_BOOTSTRAP_EXCEPTION",
                "required_check_evidence": "first-bootstrap exception",
            },
            {
                "name": "bootstrap exception after first dispatch is blocked",
                "configure": bootstrap_after_first_dispatch,
                "returncode": 1,
                "status": "blocked",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "profile_execution",
                "target_role": "tester",
                "reason_codes": {"baseline_not_ready"},
            },
            {
                "name": "unknown roles",
                "configure": unknown_role,
                "returncode": 1,
                "status": "blocked",
                "recommended": "CORRECTION_REQUIRED",
                "dispatchable": False,
                "role_class": "unknown",
                "target_role": "wizard",
                "reason_codes": {"target_role_not_profile_execution"},
                "blocking_rule_ids": {"GOV-ACTION-SEMANTICS"},
            },
        ]

        for case in cases:
            with self.subTest(case=case["name"]), tempfile.TemporaryDirectory() as tmp:
                root = copy_valid_workspace(tmp)
                make_tz_valid(root)
                case["configure"](root)
                json_out = Path(tmp) / "plan-next.json"

                result = run_plan_next(root, "--strict", "--json-out", str(json_out))

                self.assertEqual(result.returncode, case["returncode"], result.stdout + result.stderr)
                report = json.loads(json_out.read_text(encoding="utf-8"))
                self.assertTrue(report["dry_run"])
                self.assertTrue(report["read_only"])
                self.assertFalse(report["mutations_performed"])
                self.assertEqual(report["status"], case["status"])
                self.assertEqual(report["recommended_next_action"], case["recommended"])
                self.assertEqual(report["target_role"], case["target_role"])
                self.assertEqual(report["dispatchable"], case["dispatchable"])
                self.assertNotEqual(report["recommended_next_action"], "CREATE_AUDITOR")
                if not case["dispatchable"]:
                    self.assertNotEqual(report["recommended_next_action"], "CREATE_AGENT")

                dispatchability = report["dispatchability"]
                self.assertFalse(dispatchability["live_dispatch_performed"])
                self.assertEqual(dispatchability["dispatchable"], case["dispatchable"])
                self.assertEqual(dispatchability["target_role"], case["target_role"])
                self.assertEqual(dispatchability["role_class"], case["role_class"])
                reason_codes = {reason["reason_code"] for reason in dispatchability["reasons"]}
                self.assertTrue(case["reason_codes"].issubset(reason_codes))
                if case["dispatchable"]:
                    self.assertEqual(reason_codes, set())
                    self.assertEqual(dispatchability["verdict"], "dispatchable")
                else:
                    self.assertEqual(dispatchability["verdict"], "not_dispatchable")

                expected_rule_ids = case.get("blocking_rule_ids", set())
                rule_ids = {rule["rule_id"] for rule in report["blocking_rules"]}
                self.assertTrue(expected_rule_ids.issubset(rule_ids))

                required_check = case.get("required_check")
                if required_check:
                    checks = {
                        check["check_id"]: check
                        for check in dispatchability["checks"]
                        if isinstance(check, dict)
                    }
                    self.assertIn(required_check, checks)
                    self.assertTrue(checks[required_check]["passed"])
                    self.assertIn(case["required_check_evidence"], checks[required_check]["evidence"])

    def test_checkpoint_with_audit_pass_evidence_recommends_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
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
            set_task(
                root,
                status="audit_passed",
                audit_refs=[audit_ref],
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertEqual(report["blocking_rules"], [])
            self.assertTrue(report["evidence"]["audit_pass_evidence"]["present"])
            self.assertEqual(report["evidence"]["audit_pass_evidence"]["passed_audit_refs"], [audit_ref])
            self.assertEqual(report["evidence"]["audit_pass_evidence"]["unparsed_audit_refs"], [])

    def test_checkpoint_with_missing_audit_result_ref_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            missing_ref = "project-runtime/results/audit/AUDIT_RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_404.md"
            set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            set_task(root, status="audit_passed", audit_refs=[missing_ref])
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")
            self.assertNotEqual(report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            evidence = report["evidence"]["audit_pass_evidence"]
            self.assertFalse(evidence["present"])
            self.assertEqual(evidence["passed_audit_refs"], [])
            self.assertEqual(evidence["unparsed_audit_refs"], [missing_ref])
            self.assertEqual(evidence["invalid_audit_results"], [])
            self.assertTrue(
                any("missing or unreadable" in item["message"] for item in report["blocking_rules"])
            )

    def test_checkpoint_with_non_utf8_audit_result_ref_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
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
            set_task(root, status="audit_passed", audit_refs=[audit_ref])
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")
            self.assertNotEqual(report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
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

    def test_checkpoint_without_audit_pass_evidence_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(report["target_role"], "auditor")
            self.assertFalse(report["dispatchability"]["dispatchable"])
            self.assertEqual(report["dispatchability"]["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(report["dispatchability"]["target_role"], "auditor")
            reason_codes = {reason["reason_code"] for reason in report["dispatchability"]["reasons"]}
            self.assertIn("task_packet_not_dispatch_valid", reason_codes)
            self.assertIn("task_registry_incompatible", reason_codes)
            rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
            self.assertIn("GOV-CHECKPOINT-AUDIT-GATE", rule_ids)
            self.assertFalse(report["evidence"]["audit_pass_evidence"]["present"])

    def test_checkpoint_without_audit_pass_evidence_recommends_auditor_for_valid_audit_packet(self) -> None:
        packet = "project-runtime/tasks/active/TASK_FIXTURE_STATE_001.md"
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            set_next_action(
                root,
                action_type="update_state",
                action_semantic="normal",
                checkpoint_policy="local_only",
                checkpoint_preflight_required=True,
                checkpoint_receipt_required=True,
            )
            set_current_gate(root, gate_type="audit", required_next_role="auditor")
            set_task(root, task_type="auditor", task_kind="audit", owner_role="auditor")
            update_task_packet_field(root, packet, "TASK_KIND", "audit")
            update_task_packet_field(root, packet, "TASK_TYPE", "auditor")
            update_task_packet_field(root, packet, "TARGET_ROLE", "auditor")
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["recommended_next_action"], "CREATE_AUDITOR")
            self.assertEqual(report["target_role"], "auditor")
            self.assertTrue(report["dispatchability"]["dispatchable"])
            self.assertEqual(report["dispatchability"]["recommended_next_action"], "CREATE_AUDITOR")
            self.assertEqual(report["dispatchability"]["target_role"], "auditor")
            self.assertEqual(report["dispatchability"]["reasons"], [])
            rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
            self.assertIn("GOV-CHECKPOINT-AUDIT-GATE", rule_ids)
            self.assertFalse(report["evidence"]["audit_pass_evidence"]["present"])

    def test_checkpoint_completed_or_checkpoint_done_without_audit_refs_is_blocked(self) -> None:
        for status in ("completed", "checkpoint_done"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                root = copy_valid_workspace(tmp)
                make_tz_valid(root)
                set_next_action(
                    root,
                    action_type="update_state",
                    action_semantic="normal",
                    checkpoint_policy="local_only",
                    checkpoint_preflight_required=True,
                    checkpoint_receipt_required=True,
                )
                set_task(root, status=status, audit_refs=[])
                json_out = Path(tmp) / f"plan-next-{status}.json"

                result = run_plan_next(root, "--strict", "--json-out", str(json_out))

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(json_out.read_text(encoding="utf-8"))
                self.assertEqual(report["status"], "blocked")
                self.assertEqual(report["recommended_next_action"], "CORRECTION_REQUIRED")
                self.assertFalse(report["dispatchability"]["dispatchable"])
                rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
                self.assertIn("GOV-CHECKPOINT-AUDIT-GATE", rule_ids)
                audit_evidence = report["evidence"]["audit_pass_evidence"]
                self.assertFalse(audit_evidence["present"])
                self.assertEqual(audit_evidence["task_status"], status)
                self.assertEqual(audit_evidence["task_audit_refs"], [])

    def test_stop_action_recommends_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            set_next_action(
                root,
                action_type="stop",
                target_role="none",
                dependency_status="not_applicable",
                action_semantic="stop_terminal",
                checkpoint_policy="no_checkpoint",
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "STOP")
            self.assertEqual(report["blocking_rules"], [])

    def test_active_bootstrap_with_inputs_does_not_recommend_ready_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            make_tz_valid(root)
            set_project_state(root, current_phase="bootstrap", project_status="active")
            set_current_gate(root, gate_type="bootstrap", status="open", task_id="NONE", task_packet="NONE")
            set_next_action(
                root,
                action_type="stop",
                target_role="none",
                task_id="NONE",
                task_packet="NONE",
                dependency_status="not_applicable",
                action_semantic="stop_terminal",
                checkpoint_policy="no_checkpoint",
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["recommended_next_action"], "BOOTSTRAP_PREP")
            self.assertNotEqual(report["recommended_next_action"], "STOP")
            self.assertEqual(report["target_role"], "orchestrator")
            messages = " ".join(str(rule.get("message", "")) for rule in report["blocking_rules"])
            self.assertIn("bootstrap", messages.lower())

    def test_blocked_gap_owner_decision_recommends_ask_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            set_project_state(
                root,
                project_status="blocked",
                active_blockers=["GAP-001 owner_decision_required"],
            )
            set_next_action(
                root,
                action_type="wait_for_owner",
                dependency_status="blocked",
                blocked_by=["GAP-001 owner_decision_required"],
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "ASK_OWNER")
            rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
            self.assertIn("GOV-ACTION-SEMANTICS", rule_ids)

    def test_incident_state_recommends_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            set_project_state(
                root,
                current_phase="incident_recovery",
                project_status="blocked",
                active_blockers=["incident_recovery: wrong_branch_push"],
            )
            set_next_action(
                root,
                action_type="wait_for_owner",
                dependency_status="blocked",
                blocked_by=["incident_recovery: wrong_branch_push"],
            )
            json_out = Path(tmp) / "plan-next.json"

            result = run_plan_next(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["recommended_next_action"], "FREEZE")
            rule_ids = {item["rule_id"] for item in report["blocking_rules"]}
            self.assertIn("GOV-ACTION-SEMANTICS", rule_ids)


if __name__ == "__main__":
    unittest.main()
