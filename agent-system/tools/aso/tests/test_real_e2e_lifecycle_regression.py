from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
REAL_TZ_FIXTURE = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "real_tz_e2e" / "TZ_REAL_E2E_TELEGRAM_BOT.md"
TASK_ID = "TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001"
TASK_PACKET = f"project-runtime/bootstrap/{TASK_ID}.md"
AGENT_INSTANCE_ID = f"agent_{TASK_ID}_attempt_001"
AUDIT_AGENT_INSTANCE_ID = f"auditor_{TASK_ID}_attempt_001"
RESULT_REF = f"project-runtime/results/worker/RESULT_{TASK_ID}_ATTEMPT_001.md"
AUDIT_RESULT_REF = f"project-runtime/results/audit/AUDIT_RESULT_{TASK_ID}_ATTEMPT_001.md"
PACKAGE_REF = f"project-runtime/artifacts/candidates/{TASK_ID}/PACKAGE"
MANIFEST_REF = f"{PACKAGE_REF}/manifest.json"


def run_aso(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(CLI), *args, "--root", str(root)],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )


def require_success(result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode != 0:
        raise AssertionError(
            f"command failed with exit code {result.returncode}: {' '.join(result.args)}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def event_types(root: Path) -> list[str]:
    events_path = root / "project-runtime" / "agents" / "instances.jsonl"
    return [json.loads(line)["event_type"] for line in events_path.read_text(encoding="utf-8").splitlines()]


def write_requirements_result_and_manifest(root: Path) -> None:
    result_path = root / RESULT_REF
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_text = f"""RESULT:
STATUS: pass
TASK_ID: {TASK_ID}
AGENT_INSTANCE_ID: {AGENT_INSTANCE_ID}
ROLE: requirements_analyst
TASK: {TASK_ID}
SUMMARY:
Synthetic requirements result for real-E2E lifecycle regression.
READ_DOCS:
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json
- project-input/TZ.md
READ_INPUTS:
- project-input/TZ.md
CHANGED_FILES:
- {MANIFEST_REF}
CREATED_FILES:
- {MANIFEST_REF}
DELETED_FILES:
- NONE
COMMANDS_RUN:
- NONE
TESTS_RUN:
- NONE
EVIDENCE:
- {MANIFEST_REF}
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
- CREATE_AUDITOR
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
"""
    result_path.write_text(result_text, encoding="utf-8")

    package = root / PACKAGE_REF
    structured = package / "structured"
    structured.mkdir(parents=True, exist_ok=True)
    (package / f"RESULT_{TASK_ID}_ATTEMPT_001.md").write_text(result_text, encoding="utf-8")
    (structured / "result_package.json").write_text(
        json.dumps({"package_id": f"RESULT_PACKAGE_{TASK_ID}_ATTEMPT_001"}) + "\n",
        encoding="utf-8",
    )
    (package / "manifest.json").write_text(
        json.dumps(
            {
                "artifact_package_schema_version": "1.1.0",
                "artifact_type": "RESULT",
                "artifact_id": f"RESULT_{TASK_ID}_ATTEMPT_001",
                "task_id": TASK_ID,
                "role": "requirements_analyst",
                "attempt_no": 1,
                "status": "pass",
                "main_document": f"RESULT_{TASK_ID}_ATTEMPT_001.md",
                "structured_artifacts": ["structured/result_package.json"],
                "evidence_refs": "NONE",
                "created_at": "2026-05-25T00:00:00Z",
                "producer": {
                    "agent_instance_id": AGENT_INSTANCE_ID,
                    "role": "requirements_analyst",
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_failed_audit_result(root: Path) -> None:
    audit_path = root / AUDIT_RESULT_REF
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        f"""AUDIT_RESULT:
STATUS: fail
TASK_ID: {TASK_ID}
AGENT_INSTANCE_ID: {AUDIT_AGENT_INSTANCE_ID}
ROLE: auditor
TASK: {TASK_ID}
SUMMARY:
Synthetic failed audit for correction routing regression.
READ_DOCS:
- agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json
READ_INPUTS:
- project-runtime/artifacts/accepted/{TASK_ID}/PACKAGE/manifest.json
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
- SOURCE_RESULT_REF: {RESULT_REF}
- CHANGED_FILES_SCOPE_STATUS: failed
SCOPE_VERIFICATION:
- TASK_PACKET_SCHEMA_STATUS: passed
FORBIDDEN_CHANGES_CHECK:
- FORBIDDEN_PATH_STATUS: passed
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
""",
        encoding="utf-8",
    )


class RealE2ELifecycleRegressionTests(unittest.TestCase):
    def test_real_e2e_lifecycle_routes_result_artifact_audit_fail_to_correction(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aso-p58-100-real-e2e-") as tmp_text:
            tmp = Path(tmp_text)
            workspace = tmp / "workspace"
            workspace_input = workspace / "project-input"
            workspace_input.mkdir(parents=True)
            shutil.copyfile(REAL_TZ_FIXTURE, workspace_input / "TZ.md")

            init_json = tmp / "state-init.json"
            intake_json = tmp / "intake.json"
            context_json = tmp / "context.json"
            initial_plan_json = tmp / "plan-initial.json"
            verify_after_result_json = tmp / "verify-after-result.json"
            plan_after_result_json = tmp / "plan-after-result.json"
            artifact_validate_json = tmp / "artifact-validate.json"
            artifact_accept_json = tmp / "artifact-accept.json"
            plan_after_terminate_json = tmp / "plan-after-terminate.json"
            plan_after_audit_fail_json = tmp / "plan-after-audit-fail.json"
            checkpoint_json = tmp / "checkpoint-preflight.json"

            require_success(
                run_aso(
                    workspace,
                    "state",
                    "init",
                    "--tz",
                    "project-input/TZ.md",
                    "--confirm-write",
                    "--json-out",
                    str(init_json),
                )
            )
            require_success(
                run_aso(
                    workspace,
                    "intake",
                    "bootstrap",
                    "--tz",
                    "project-input/TZ.md",
                    "--target-role",
                    "requirements_analyst",
                    "--confirm-write",
                    "--json-out",
                    str(intake_json),
                )
            )
            require_success(run_aso(workspace, "orchestrator", "context", "--format", "json", "--json-out", str(context_json)))
            require_success(run_aso(workspace, "plan-next", "--strict", "--json-out", str(initial_plan_json)))

            initial_plan = load_json(initial_plan_json)
            self.assertEqual(initial_plan["recommended_next_action"], "CREATE_AGENT")
            self.assertTrue(initial_plan["dispatchable"])
            self.assertEqual(initial_plan["target_role"], "requirements_analyst")
            self.assertEqual(initial_plan["task_id"], TASK_ID)
            self.assertEqual(initial_plan["task_packet"], TASK_PACKET)

            context_report = load_json(context_json)
            self.assertEqual(context_report["status"], "pass")
            self.assertEqual(context_report["context_mode"], "routine")
            self.assertEqual(context_report["runtime_contract"]["path"], "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json")
            self.assertIn("routine_context_policy", context_report["runtime_contract"]["required_sections"])
            self.assertIn("handoff_context_builder_contract", context_report["runtime_contract"]["required_sections"])
            handoff_context = context_report["handoff_context"]
            self.assertEqual(handoff_context["reference_docs"], [])
            routine_paths = {doc["path"] for doc in handoff_context["required_docs"]}
            self.assertIn("agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json", routine_paths)
            self.assertIn(TASK_PACKET, routine_paths)
            self.assertIn("agent-system/01_roles/REQUIREMENTS_ANALYST.md", routine_paths)
            self.assertIn("agent-system/03_templates/AGENT_RESULT_TEMPLATE.md", routine_paths)
            for routine_path in routine_paths:
                self.assertNotEqual(routine_path, "agent-system/GOVERNANCE_CHANGELOG.md")
                self.assertFalse(routine_path.startswith("agent-system/09_validators/"))
                self.assertFalse(routine_path.startswith("agent-system/11_release/"))

            write_requirements_result_and_manifest(workspace)
            require_success(
                run_aso(
                    workspace,
                    "lifecycle",
                    "receive-result",
                    "--from-result",
                    RESULT_REF,
                    "--confirm-write",
                )
            )

            verify_after_result = run_aso(workspace, "state", "verify", "--strict", "--json-out", str(verify_after_result_json))
            self.assertEqual(verify_after_result.returncode, 1, verify_after_result.stdout + verify_after_result.stderr)
            verify_report = load_json(verify_after_result_json)
            verify_rule_ids = {finding["rule_id"] for finding in verify_report["findings"]}
            self.assertIn("RUNTIME_NEXT_ACTION_STALE", verify_rule_ids)
            self.assertIn("RUNTIME_LIFECYCLE_RESULT_REGISTRY_STALE", verify_rule_ids)
            self.assertEqual(verify_report["reconciliation"]["current_state"], "RESULT_PENDING_ARTIFACT_ACCEPTANCE")
            self.assertEqual(
                verify_report["reconciliation"]["next_action"]["recommended_next_action"],
                "ACCEPT_ARTIFACT",
            )

            plan_after_result = run_aso(workspace, "plan-next", "--strict", "--json-out", str(plan_after_result_json))
            self.assertEqual(plan_after_result.returncode, 1, plan_after_result.stdout + plan_after_result.stderr)
            result_plan = load_json(plan_after_result_json)
            self.assertEqual(result_plan["recommended_next_action"], "ACCEPT_ARTIFACT")
            self.assertNotEqual(result_plan["recommended_next_action"], "CREATE_AGENT")
            self.assertEqual(result_plan["evidence"]["transition_engine"]["current_state"], "RESULT_PENDING_ARTIFACT_ACCEPTANCE")

            require_success(
                run_aso(
                    workspace,
                    "artifact",
                    "validate",
                    "--package",
                    MANIFEST_REF,
                    "--type",
                    "RESULT",
                    "--task-id",
                    TASK_ID,
                    "--role",
                    "requirements_analyst",
                    "--strict",
                    "--json-out",
                    str(artifact_validate_json),
                )
            )
            artifact_validate = load_json(artifact_validate_json)
            self.assertEqual(artifact_validate["status"], "pass")
            self.assertEqual(Path(str(artifact_validate["manifest"])).relative_to(workspace).as_posix(), MANIFEST_REF)

            require_success(
                run_aso(
                    workspace,
                    "artifact",
                    "accept",
                    "--package",
                    MANIFEST_REF,
                    "--confirm-write",
                    "--json-out",
                    str(artifact_accept_json),
                )
            )
            artifact_accept = load_json(artifact_accept_json)
            accepted_manifest = workspace / artifact_accept["receipt"]["artifact_ref"]
            self.assertEqual(artifact_accept["status"], "written")
            self.assertEqual(accepted_manifest.name, "manifest.json")
            self.assertTrue(accepted_manifest.is_file())
            self.assertFalse((accepted_manifest.parent / "artifact_package_manifest.json").exists())

            require_success(
                run_aso(
                    workspace,
                    "lifecycle",
                    "terminate-agent",
                    "--from-result",
                    RESULT_REF,
                    "--confirm-write",
                )
            )
            self.assertEqual(
                event_types(workspace),
                ["RESULT_RECEIVED", "ARTIFACT_ACCEPTED", "AGENT_TERMINATED", "AUDIT_ROUTE_READY"],
            )

            plan_after_terminate = run_aso(workspace, "plan-next", "--strict", "--json-out", str(plan_after_terminate_json))
            self.assertEqual(plan_after_terminate.returncode, 1, plan_after_terminate.stdout + plan_after_terminate.stderr)
            terminate_plan = load_json(plan_after_terminate_json)
            self.assertEqual(terminate_plan["recommended_next_action"], "WAIT_FOR_AUDIT_RESULT")
            self.assertEqual(terminate_plan["target_role"], "auditor")
            self.assertNotEqual(terminate_plan["recommended_next_action"], "CREATE_AGENT")
            self.assertEqual(terminate_plan["evidence"]["transition_engine"]["current_state"], "AUDIT_PENDING")

            write_failed_audit_result(workspace)
            require_success(
                run_aso(
                    workspace,
                    "lifecycle",
                    "receive-result",
                    "--from-result",
                    AUDIT_RESULT_REF,
                    "--confirm-write",
                )
            )
            plan_after_audit_fail = run_aso(
                workspace,
                "plan-next",
                "--strict",
                "--json-out",
                str(plan_after_audit_fail_json),
            )
            self.assertEqual(plan_after_audit_fail.returncode, 1, plan_after_audit_fail.stdout + plan_after_audit_fail.stderr)
            correction_plan = load_json(plan_after_audit_fail_json)
            self.assertEqual(correction_plan["recommended_next_action"], "CORRECTION_REQUIRED")
            self.assertEqual(correction_plan["evidence"]["transition_engine"]["current_state"], "CORRECTION_REQUIRED")
            self.assertEqual(correction_plan["correction_routing"]["route"], "CORRECTION_REQUIRED")
            self.assertTrue(correction_plan["correction_routing"]["checkpoint_preflight_blocked"])

            checkpoint = run_aso(
                workspace,
                "checkpoint-preflight",
                "--mode",
                "workspace",
                "--strict",
                "--json-out",
                str(checkpoint_json),
            )
            self.assertEqual(checkpoint.returncode, 1, checkpoint.stdout + checkpoint.stderr)
            checkpoint_report = load_json(checkpoint_json)
            self.assertFalse(checkpoint_report["eligible"])
            checkpoint_rule_ids = {rule["rule_id"] for rule in checkpoint_report["blocking_rules"]}
            self.assertIn("GOV-CHECKPOINT-AUDIT-GATE", checkpoint_rule_ids)
            state_verify_rule_ids = {
                finding["rule_id"]
                for finding in checkpoint_report["evidence"]["state_verify"]["findings"]
            }
            self.assertIn("RUNTIME_LIFECYCLE_CORRECTION_REGISTRY_STALE", state_verify_rule_ids)


if __name__ == "__main__":
    unittest.main()
