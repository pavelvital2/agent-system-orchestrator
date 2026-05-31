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
ASO_TOOL_ROOT = REPO_ROOT / "agent-system" / "tools" / "aso"
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "state"
VALID_WORKSPACE = FIXTURE_ROOT / "valid_workspace"
P2_VALID_WORKSPACE = FIXTURE_ROOT / "p2_valid_workspace"

sys.path.insert(0, str(ASO_TOOL_ROOT))

from agent_system_orchestrator_aso.aso_tool import runtime_schema_contracts  # noqa: E402

ACTIVE_PACKAGE_VERSION = runtime_schema_contracts.ACTIVE_PACKAGE_VERSION
ACTIVE_RUNTIME_SCHEMA_VERSION = runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION


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


def copy_p2_valid_workspace(tmp: str) -> Path:
    root = Path(tmp) / "p2-workspace"
    shutil.copytree(P2_VALID_WORKSPACE, root)
    return root


def load_sidecar(root: Path, name: str) -> dict[str, object]:
    return json.loads((root / "project-runtime" / "state" / name).read_text(encoding="utf-8"))


def write_sidecar(root: Path, name: str, payload: dict[str, object]) -> None:
    (root / "project-runtime" / "state" / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, str(CLI), "state", "render", "--root", str(root), "--confirm-write"],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def write_sidecar_raw(root: Path, name: str, payload: dict[str, object]) -> None:
    (root / "project-runtime" / "state" / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def normalize_current_p2_fixture(root: Path) -> None:
    state_root = root / "project-runtime" / "state"
    for path in sorted(state_root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        payload["schema_version"] = ACTIVE_RUNTIME_SCHEMA_VERSION
        payload["runtime_schema_version"] = ACTIVE_RUNTIME_SCHEMA_VERSION
        content = payload.get("content")
        if isinstance(content, dict):
            if "runtime_schema_version" in content:
                content["runtime_schema_version"] = ACTIVE_RUNTIME_SCHEMA_VERSION
            if "package_version" in content:
                content["package_version"] = ACTIVE_PACKAGE_VERSION
            if "governance_ruleset_version" in content:
                content["governance_ruleset_version"] = ACTIVE_PACKAGE_VERSION
            if payload.get("sidecar_type") == "PROJECT_STATE":
                content["semantic_reason"] = "Current Runtime Schema 3.2.0 test fixture."
            if payload.get("sidecar_type") == "SCHEMA_MANIFEST":
                entries = content.get("sidecars")
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, dict):
                            entry["runtime_schema_version"] = ACTIVE_RUNTIME_SCHEMA_VERSION
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    render_result = subprocess.run(
        [sys.executable, str(CLI), "state", "render", "--root", str(root), "--confirm-write"],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )
    if render_result.returncode != 0:
        raise AssertionError(render_result.stdout + render_result.stderr)


def write_tz_file(root: Path) -> None:
    tz_file = root / "project-input" / "TZ.md"
    tz_file.parent.mkdir(parents=True, exist_ok=True)
    tz_file.write_text("Europe/Moscow\n", encoding="utf-8")


def set_tz_path(root: Path, value: str) -> None:
    payload = load_sidecar(root, "PROJECT_STATE.json")
    content = payload["content"]
    assert isinstance(content, dict)
    content["tz_path"] = value
    write_sidecar(root, "PROJECT_STATE.json", payload)

    markdown = root / "project-runtime" / "PROJECT_STATE.md"
    if markdown.is_file():
        text = markdown.read_text(encoding="utf-8")
        text = text.replace("TZ_PATH: Europe/Moscow", f"TZ_PATH: {value}")
        markdown.write_text(text, encoding="utf-8")


def make_valid_tz_path(root: Path) -> None:
    write_tz_file(root)
    set_tz_path(root, "project-input/TZ.md")


def make_bootstrap_next_action_non_terminal(root: Path) -> None:
    payload = load_sidecar(root, "NEXT_ACTION.json")
    content = payload["content"]
    assert isinstance(content, dict)
    content["action_id"] = "ACTION-BOOTSTRAP-PREP-001"
    content["action_type"] = "correction"
    content["action_semantic"] = "normal"
    content["dependency_status"] = "ready"
    content["instruction_for_orchestrator"] = "Prepare bootstrap inputs before first profile-agent dispatch."
    write_sidecar(root, "NEXT_ACTION.json", payload)


def copy_valid_workspace_with_valid_tz(tmp: str) -> Path:
    root = copy_valid_workspace(tmp)
    make_valid_tz_path(root)
    return root


def copy_p2_valid_workspace_with_valid_bootstrap_state(tmp: str) -> Path:
    root = copy_p2_valid_workspace(tmp)
    normalize_current_p2_fixture(root)
    make_valid_tz_path(root)
    make_bootstrap_next_action_non_terminal(root)
    return root


def fixture_task(
    task_id: str,
    *,
    task_kind: str = "normal",
    task_type: str = "developer",
    owner_role: str = "developer",
    task_packet: str | None = None,
) -> dict[str, object]:
    return {
        "accepted_files": [],
        "audit_refs": [],
        "branch": "NONE",
        "checkpoint_ref": "NONE",
        "commit_hash": "NONE",
        "correction_links": [],
        "created_at": "2026-05-21T00:00:00Z",
        "dependencies": [],
        "owner_role": owner_role,
        "push_status": "not_required",
        "requested_by_role": "NONE",
        "requested_by_task": "NONE",
        "research_question_id": "NONE",
        "result_refs": [],
        "return_task_after_audit_pass": "NONE",
        "return_to_requester_after_audit_pass": False,
        "return_to_role_after_audit_pass": "none",
        "status": "ready",
        "task_id": task_id,
        "task_kind": task_kind,
        "task_packet": task_packet or f"project-runtime/tasks/active/{task_id}.md",
        "task_title": "Fixture task",
        "task_type": task_type,
        "updated_at": "2026-05-21T00:00:00Z",
    }


CANONICAL_MULTILINE_AUDIT_PASS = """AUDIT_RESULT:
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


class StateVerifyCommandTests(unittest.TestCase):
    def test_state_cli_help_declares_runtime_state_commands(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "state", "--help"],
            check=False,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for command in ("init", "verify", "migrate", "render"):
            with self.subTest(command=command):
                self.assertIn(command, result.stdout)

    def test_valid_workspace_passes_strict_and_writes_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace_with_valid_tz(tmp)
            json_out = Path(tmp) / "state-verify.json"

            result = run_state_verify(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO state verify: PASSED", result.stdout)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(report["command"], "state verify")
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["summary"], {"errors": 0, "warnings": 0, "info": 0})
            self.assertEqual(report["state"]["sidecars_missing"], [])
            self.assertTrue(report["read_only"])

    def test_current_p2_fixture_passes_strict_with_all_expected_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_valid_workspace_with_valid_bootstrap_state(tmp)
            json_out = Path(tmp) / "p2-state-verify.json"

            result = run_state_verify(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO state verify: PASSED", result.stdout)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(report["state"]["runtime_schema_current_p2"])
            self.assertEqual(report["state"]["required_sidecars_missing"], [])
            self.assertEqual(report["state"]["optional_sidecars_missing"], [])
            self.assertEqual(report["runtime_schema_contract"]["runtime_schema_version"], "3.2.0")

    def test_strict_verify_flags_stale_checkpoint_cache_for_active_running_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_valid_workspace_with_valid_bootstrap_state(tmp)
            active_task_id = "TASK_ACTIVE_LIFECYCLE"
            old_task_id = "TASK_OLD_CHECKPOINT_DONE"
            active_packet = f"project-runtime/tasks/active/{active_task_id}.md"
            old_packet = f"project-runtime/tasks/active/{old_task_id}.md"

            registry = load_sidecar(root, "TASK_REGISTRY.json")
            old_task = fixture_task(old_task_id, task_packet=old_packet)
            old_task["status"] = "checkpoint_done"
            old_task["audit_refs"] = ["project-runtime/results/audit/AUDIT_RESULT_OLD_ATTEMPT_001.md"]
            active_task = fixture_task(active_task_id, task_packet=active_packet)
            active_task["status"] = "running"
            registry["content"]["tasks"] = [old_task, active_task]
            write_sidecar_raw(root, "TASK_REGISTRY.json", registry)

            accepted = load_sidecar(root, "ACCEPTED_ARTIFACTS.json")
            accepted["content"]["artifacts"] = []
            write_sidecar_raw(root, "ACCEPTED_ARTIFACTS.json", accepted)

            project_state = load_sidecar(root, "PROJECT_STATE.json")
            project_state["content"].update(
                {
                    "current_phase": "implementation",
                    "project_status": "active",
                    "active_branches": [],
                    "active_blockers": [],
                    "checkpoint_blocked_by": [],
                    "checkpoint_eligibility": "not_applicable",
                    "checkpoint_eligibility_status": "not_checked",
                    "project_checkpoint_status": "not_required",
                }
            )
            write_sidecar_raw(root, "PROJECT_STATE.json", project_state)

            current_gate = load_sidecar(root, "CURRENT_GATE.json")
            current_gate["content"].update(
                {
                    "status": "open",
                    "task_id": "NONE",
                    "task_packet": "NONE",
                    "required_next_role": "none",
                    "checkpoint_eligibility": "not_applicable",
                    "checkpoint_eligibility_status": "not_checked",
                    "project_checkpoint_status": "not_required",
                }
            )
            write_sidecar_raw(root, "CURRENT_GATE.json", current_gate)

            next_action = load_sidecar(root, "NEXT_ACTION.json")
            next_action["content"].update(
                {
                    "action_type": "update_state",
                    "target_role": "orchestrator",
                    "task_id": old_task_id,
                    "task_packet": old_packet,
                    "dependency_status": "ready",
                    "blocked_by": [],
                    "action_semantic": "normal",
                    "checkpoint_policy": "local_only",
                    "checkpoint_preflight_required": True,
                    "checkpoint_receipt_required": True,
                }
            )
            write_sidecar_raw(root, "NEXT_ACTION.json", next_action)

            json_out = Path(tmp) / "state-verify.json"

            result = run_state_verify(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            rule_ids = {finding["rule_id"] for finding in report["findings"]}
            self.assertIn("RUNTIME_NEXT_ACTION_STALE", rule_ids)
            self.assertIn("STALE_NEXT_ACTION_TASK_ID", rule_ids)
            self.assertEqual(report["reconciliation"]["canonical_recommended_next_action"], "WAIT_FOR_RESULT")
            self.assertEqual(report["reconciliation"]["derived_next_action_cache"]["task_id"], active_task_id)

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
            root = copy_valid_workspace_with_valid_tz(tmp)
            path = root / "project-runtime" / "state" / "NEXT_ACTION.json"
            path.write_text("{not valid json\n", encoding="utf-8")

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("SIDECAR_JSON_PARSE_ERROR", result.stdout)

    def test_missing_sidecar_uses_markdown_fallback_warning_and_strict_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace_with_valid_tz(tmp)
            (root / "project-runtime" / "state" / "NEXT_ACTION.json").unlink()

            non_strict = run_state_verify(root)
            strict = run_state_verify(root, "--strict")

            self.assertEqual(non_strict.returncode, 0, non_strict.stdout + non_strict.stderr)
            self.assertIn("ASO state verify: WARNING", non_strict.stdout)
            self.assertIn("SIDECAR_MISSING_MARKDOWN_FALLBACK_USED", non_strict.stdout)
            self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
            self.assertIn("ASO state verify: FAILED", strict.stdout)

    def test_current_p2_missing_required_sidecar_fails_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_valid_workspace_with_valid_bootstrap_state(tmp)
            (root / "project-runtime" / "state" / "SCHEMA_MANIFEST.json").unlink()

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("SIDECAR_REQUIRED_SIDECAR_MISSING", result.stdout)

    def test_current_p2_mismatched_schema_versions_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_valid_workspace_with_valid_bootstrap_state(tmp)
            payload = load_sidecar(root, "PROJECT_STATE.json")
            payload["runtime_schema_version"] = "3.0.0"
            write_sidecar(root, "PROJECT_STATE.json", payload)

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("SIDECAR_RUNTIME_SCHEMA_VERSION_INVALID", result.stdout)

    def test_current_p2_next_action_unknown_task_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_valid_workspace_with_valid_bootstrap_state(tmp)
            registry = load_sidecar(root, "TASK_REGISTRY.json")
            registry_content = registry["content"]
            self.assertIsInstance(registry_content, dict)
            registry_content["tasks"] = [fixture_task("TASK_FIXTURE_EXISTS")]
            write_sidecar(root, "TASK_REGISTRY.json", registry)

            next_action = load_sidecar(root, "NEXT_ACTION.json")
            next_content = next_action["content"]
            self.assertIsInstance(next_content, dict)
            next_content["action_type"] = "create_agent"
            next_content["target_role"] = "developer"
            next_content["task_id"] = "TASK_FIXTURE_MISSING"
            next_content["task_packet"] = "project-runtime/tasks/active/TASK_FIXTURE_MISSING.md"
            next_content["dependency_status"] = "ready"
            next_content["action_semantic"] = "normal"
            next_content["workspace_identity_required"] = True
            next_content["repository_lock_required"] = True
            write_sidecar_raw(root, "NEXT_ACTION.json", next_action)

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("SIDECAR_TASK_REFERENCE_UNKNOWN", result.stdout)

    def test_task_registry_bootstrap_task_kind_passes_pre_dispatch_reference_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_valid_workspace_with_valid_bootstrap_state(tmp)
            task_id = "TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001"
            task_packet = "project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md"
            registry = load_sidecar(root, "TASK_REGISTRY.json")
            registry_content = registry["content"]
            self.assertIsInstance(registry_content, dict)
            registry_content["tasks"] = [
                fixture_task(
                    task_id,
                    task_kind="bootstrap",
                    task_type="requirements_analyst",
                    owner_role="requirements_analyst",
                    task_packet=task_packet,
                )
            ]
            write_sidecar(root, "TASK_REGISTRY.json", registry)

            next_action = load_sidecar(root, "NEXT_ACTION.json")
            next_content = next_action["content"]
            self.assertIsInstance(next_content, dict)
            next_content["action_id"] = "ACTION-BOOTSTRAP-DISPATCH-001"
            next_content["action_type"] = "create_agent"
            next_content["target_role"] = "requirements_analyst"
            next_content["task_id"] = task_id
            next_content["task_packet"] = task_packet
            next_content["dependency_status"] = "ready"
            next_content["action_semantic"] = "normal"
            next_content["checkpoint_policy"] = "no_checkpoint"
            next_content["checkpoint_preflight_required"] = False
            next_content["checkpoint_receipt_required"] = False
            write_sidecar(root, "NEXT_ACTION.json", next_action)

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO state verify: PASSED", result.stdout)

    def test_task_registry_unknown_task_kind_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_valid_workspace_with_valid_bootstrap_state(tmp)
            registry = load_sidecar(root, "TASK_REGISTRY.json")
            registry_content = registry["content"]
            self.assertIsInstance(registry_content, dict)
            registry_content["tasks"] = [fixture_task("TASK_FIXTURE_UNKNOWN_KIND", task_kind="surprising")]
            write_sidecar(root, "TASK_REGISTRY.json", registry)

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("SIDECAR_ENUM_VALUE_INVALID", result.stdout)

    def test_invalid_status_value_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace_with_valid_tz(tmp)
            payload = load_sidecar(root, "CURRENT_GATE.json")
            content = payload["content"]
            self.assertIsInstance(content, dict)
            content["status"] = "surprising"
            write_sidecar(root, "CURRENT_GATE.json", payload)

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("SIDECAR_ENUM_VALUE_INVALID", result.stdout)

    def test_project_state_not_required_readiness_statuses_fail_strict_verify(self) -> None:
        cases = (
            ("identity_validation_status", "PROJECT_STATE.content.identity_validation_status"),
            ("repository_lock_status", "PROJECT_STATE.content.repository_lock_status"),
            ("baseline_tracking_status", "PROJECT_STATE.content.baseline_tracking_status"),
        )
        for field, expected_detail in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = copy_valid_workspace_with_valid_tz(tmp)
                payload = load_sidecar(root, "PROJECT_STATE.json")
                body = payload["content"]
                self.assertIsInstance(body, dict)
                body[field] = "not_required"
                write_sidecar(root, "PROJECT_STATE.json", payload)

                json_out = Path(tmp) / f"state-verify-{field}.json"
                result = run_state_verify(root, "--strict", "--json-out", str(json_out))

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(json_out.read_text(encoding="utf-8"))
                self.assertEqual(report["status"], "failed")
                findings = report["findings"]
                self.assertTrue(
                    any(
                        finding["rule_id"] == "SIDECAR_ENUM_VALUE_INVALID"
                        and finding["field"] == f"content.{field}"
                        and expected_detail in finding["details"]
                        for finding in findings
                    ),
                    findings,
                )

    def test_invalid_identity_and_repository_statuses_fail_strict_verify(self) -> None:
        cases = (
            ("identity_validation_status", "surprising", "PROJECT_STATE.content.identity_validation_status"),
            ("repository_lock_status", "surprising", "PROJECT_STATE.content.repository_lock_status"),
        )
        for field, value, expected_detail in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = copy_valid_workspace_with_valid_tz(tmp)
                payload = load_sidecar(root, "PROJECT_STATE.json")
                body = payload["content"]
                self.assertIsInstance(body, dict)
                body[field] = value
                write_sidecar(root, "PROJECT_STATE.json", payload)

                json_out = Path(tmp) / f"state-verify-invalid-{field}.json"
                result = run_state_verify(root, "--strict", "--json-out", str(json_out))

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(json_out.read_text(encoding="utf-8"))
                self.assertEqual(report["status"], "failed")
                findings = report["findings"]
                self.assertTrue(
                    any(
                        finding["rule_id"] == "SIDECAR_ENUM_VALUE_INVALID"
                        and finding["field"] == f"content.{field}"
                        and expected_detail in finding["details"]
                        for finding in findings
                    ),
                    findings,
                )

    def test_stale_next_action_action_types_fail(self) -> None:
        for action_type in ("run_audit", "checkpoint", "return_to_requester", "manual", "none"):
            with self.subTest(action_type=action_type), tempfile.TemporaryDirectory() as tmp:
                root = copy_valid_workspace_with_valid_tz(tmp)
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
            root = copy_valid_workspace_with_valid_tz(tmp)
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
            root = copy_valid_workspace_with_valid_tz(tmp)
            payload = load_sidecar(root, "NEXT_ACTION.json")
            content = payload["content"]
            self.assertIsInstance(content, dict)
            content["checkpoint_policy"] = "commit_and_push"
            content["checkpoint_preflight_required"] = True
            content["checkpoint_receipt_required"] = True
            content["checkpoint_receipt_ref"] = "project-runtime/checkpoints/CHECKPOINT_ELIGIBILITY_TASK_FIXTURE_STATE_001_1.md"
            write_sidecar_raw(root, "NEXT_ACTION.json", payload)

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("SIDECAR_CHECKPOINT_POLICY_INVALID", result.stdout)

    def test_next_action_checkpoint_blocks_missing_audit_result_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace_with_valid_tz(tmp)
            missing_ref = "project-runtime/results/audit/AUDIT_RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_404.md"
            payload = load_sidecar(root, "NEXT_ACTION.json")
            content = payload["content"]
            self.assertIsInstance(content, dict)
            content["checkpoint_policy"] = "commit_and_push"
            content["checkpoint_preflight_required"] = True
            content["checkpoint_receipt_required"] = True
            content["checkpoint_receipt_ref"] = "project-runtime/checkpoints/CHECKPOINT_ELIGIBILITY_TASK_FIXTURE_STATE_001_1.md"
            write_sidecar_raw(root, "NEXT_ACTION.json", payload)

            task_payload = load_sidecar(root, "TASK_REGISTRY.json")
            task_content = task_payload["content"]
            self.assertIsInstance(task_content, dict)
            tasks = task_content["tasks"]
            self.assertIsInstance(tasks, list)
            self.assertIsInstance(tasks[0], dict)
            tasks[0]["status"] = "audit_passed"
            tasks[0]["audit_refs"] = [missing_ref]
            write_sidecar(root, "TASK_REGISTRY.json", task_payload)
            json_out = Path(tmp) / "state-verify.json"

            result = run_state_verify(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            findings = report["findings"]
            self.assertTrue(
                any(
                    finding["rule_id"] == "SIDECAR_CHECKPOINT_AUDIT_RESULT_INVALID"
                    and missing_ref in finding["details"]
                    and "unparsed_refs" in finding["details"]
                    for finding in findings
                ),
                findings,
            )

    def test_next_action_checkpoint_blocks_non_utf8_audit_result_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace_with_valid_tz(tmp)
            audit_ref = "project-runtime/results/audit/AUDIT_RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md"
            audit_path = root / audit_ref
            audit_path.parent.mkdir(parents=True)
            audit_path.write_bytes(b"\xff\xfe\xfa")
            payload = load_sidecar(root, "NEXT_ACTION.json")
            content = payload["content"]
            self.assertIsInstance(content, dict)
            content["checkpoint_policy"] = "commit_and_push"
            content["checkpoint_preflight_required"] = True
            content["checkpoint_receipt_required"] = True
            content["checkpoint_receipt_ref"] = "project-runtime/checkpoints/CHECKPOINT_ELIGIBILITY_TASK_FIXTURE_STATE_001_1.md"
            write_sidecar_raw(root, "NEXT_ACTION.json", payload)

            task_payload = load_sidecar(root, "TASK_REGISTRY.json")
            task_content = task_payload["content"]
            self.assertIsInstance(task_content, dict)
            tasks = task_content["tasks"]
            self.assertIsInstance(tasks, list)
            self.assertIsInstance(tasks[0], dict)
            tasks[0]["status"] = "audit_passed"
            tasks[0]["audit_refs"] = [audit_ref]
            write_sidecar(root, "TASK_REGISTRY.json", task_payload)
            json_out = Path(tmp) / "state-verify.json"

            result = run_state_verify(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            findings = report["findings"]
            self.assertTrue(
                any(
                    finding["rule_id"] == "SIDECAR_CHECKPOINT_AUDIT_RESULT_INVALID"
                    and audit_ref in finding["details"]
                    and "audit_result_unreadable" in finding["details"]
                    and "UnicodeDecodeError" in finding["details"]
                    and "invalid_refs" in finding["details"]
                    for finding in findings
                ),
                findings,
            )

    def test_checkpoint_audit_evidence_uses_normalized_parser_output_from_current_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace_with_valid_tz(tmp)
            audit_ref = "project-runtime/results/audit/AUDIT_RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md"
            audit_path = root / audit_ref
            audit_path.parent.mkdir(parents=True)
            audit_path.write_text(CANONICAL_MULTILINE_AUDIT_PASS, encoding="utf-8")

            next_action = load_sidecar(root, "NEXT_ACTION.json")
            next_content = next_action["content"]
            self.assertIsInstance(next_content, dict)
            next_content["checkpoint_policy"] = "commit_and_push"
            next_content["checkpoint_preflight_required"] = True
            next_content["checkpoint_receipt_required"] = True
            next_content["checkpoint_receipt_ref"] = "project-runtime/checkpoints/CHECKPOINT_ELIGIBILITY_TASK_FIXTURE_STATE_001_1.md"
            write_sidecar(root, "NEXT_ACTION.json", next_action)

            gate = load_sidecar(root, "CURRENT_GATE.json")
            gate_content = gate["content"]
            self.assertIsInstance(gate_content, dict)
            gate_content["gate_evidence"] = [audit_ref]
            write_sidecar(root, "CURRENT_GATE.json", gate)

            task_payload = load_sidecar(root, "TASK_REGISTRY.json")
            task_content = task_payload["content"]
            self.assertIsInstance(task_content, dict)
            tasks = task_content["tasks"]
            self.assertIsInstance(tasks, list)
            self.assertIsInstance(tasks[0], dict)
            tasks[0]["status"] = "audit_passed"
            tasks[0]["audit_refs"] = []
            write_sidecar(root, "TASK_REGISTRY.json", task_payload)
            json_out = Path(tmp) / "state-verify.json"

            result = run_state_verify(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertFalse(
                any(finding["rule_id"].startswith("SIDECAR_CHECKPOINT") for finding in report["findings"]),
                report["findings"],
            )

    def test_active_open_bootstrap_with_terminal_stop_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_p2_valid_workspace(tmp)
            make_valid_tz_path(root)
            payload = load_sidecar(root, "NEXT_ACTION.json")
            content = payload["content"]
            self.assertIsInstance(content, dict)
            content["action_type"] = "stop"
            content["action_semantic"] = "stop_terminal"
            write_sidecar_raw(root, "NEXT_ACTION.json", payload)

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("BSR_BOOTSTRAP_STOP_TERMINAL_INVALID", result.stdout)

    def test_tz_path_timezone_value_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            set_tz_path(root, "Europe/Moscow")

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("BSR_TZ_PATH_TIMEZONE_VALUE", result.stdout)

    def test_tz_path_must_use_project_input_tz_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace(tmp)
            write_tz_file(root)
            other_tz = root / "project-input" / "ALT_TZ.md"
            other_tz.write_text("Europe/Moscow\n", encoding="utf-8")
            set_tz_path(root, "project-input/ALT_TZ.md")

            result = run_state_verify(root, "--strict")

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("BSR_TZ_PATH_CANONICAL_MISMATCH", result.stdout)

    def test_project_completed_with_unresolved_blockers_fails_transition_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_valid_workspace_with_valid_tz(tmp)
            project_state = load_sidecar(root, "PROJECT_STATE.json")
            project_content = project_state["content"]
            self.assertIsInstance(project_content, dict)
            project_content.update(
                {
                    "current_phase": "completed",
                    "project_status": "completed",
                    "audit_status": "passed",
                    "project_checkpoint_status": "passed",
                    "active_blockers": ["OWNER-BLOCKER-001"],
                    "checkpoint_blocked_by": [],
                }
            )
            write_sidecar(root, "PROJECT_STATE.json", project_state)

            current_gate = load_sidecar(root, "CURRENT_GATE.json")
            gate_content = current_gate["content"]
            self.assertIsInstance(gate_content, dict)
            gate_content.update(
                {
                    "gate_type": "terminal",
                    "status": "passed",
                    "action_semantic": "stop_terminal",
                    "required_next_role": "none",
                    "blocking_status": "NONE",
                }
            )
            write_sidecar(root, "CURRENT_GATE.json", current_gate)

            next_action = load_sidecar(root, "NEXT_ACTION.json")
            next_content = next_action["content"]
            self.assertIsInstance(next_content, dict)
            next_content.update(
                {
                    "action_type": "stop",
                    "target_role": "none",
                    "dependency_status": "completed",
                    "blocked_by": [],
                    "action_semantic": "stop_terminal",
                    "checkpoint_policy": "no_checkpoint",
                    "checkpoint_preflight_required": False,
                    "checkpoint_receipt_required": False,
                }
            )
            write_sidecar(root, "NEXT_ACTION.json", next_action)

            task_registry = load_sidecar(root, "TASK_REGISTRY.json")
            task_content = task_registry["content"]
            self.assertIsInstance(task_content, dict)
            tasks = task_content["tasks"]
            self.assertIsInstance(tasks, list)
            self.assertIsInstance(tasks[0], dict)
            tasks[0]["status"] = "blocked"
            write_sidecar(root, "TASK_REGISTRY.json", task_registry)
            json_out = Path(tmp) / "state-verify.json"

            result = run_state_verify(root, "--strict", "--json-out", str(json_out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads(json_out.read_text(encoding="utf-8"))
            rule_ids = {finding["rule_id"] for finding in report["findings"]}
            self.assertIn("PROJECT_COMPLETED_UNRESOLVED_TASKS", rule_ids)
            self.assertIn("PROJECT_COMPLETED_STALE_BLOCKERS", rule_ids)
            self.assertEqual(report["reconciliation"]["current_state"], "PROJECT_COMPLETED")
            self.assertEqual(report["reconciliation"]["canonical_recommended_next_action"], "NO_NEXT_ACTION")


if __name__ == "__main__":
    unittest.main()
