from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ASO_DIR = Path(__file__).resolve().parents[1]
if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool.aso import main  # noqa: E402


class OrchestratorContextMinimizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="aso-orchestrator-context-"))
        self.root = self.tmpdir / "workspace"
        state = self.root / "project-runtime" / "state"
        task_dir = self.root / "project-runtime" / "tasks" / "active"
        state.mkdir(parents=True)
        task_dir.mkdir(parents=True)
        (task_dir / "TASK_020.md").write_text("# TASK PACKET\n\nTASK_ID: TASK_020\n", encoding="utf-8")
        (state / "PROJECT_STATE.json").write_text(
            json.dumps({"content": {"current_phase": "implementation", "project_status": "active"}}),
            encoding="utf-8",
        )
        (state / "CURRENT_GATE.json").write_text(
            json.dumps({"content": {"gate_type": "implementation", "gate_status": "open"}}),
            encoding="utf-8",
        )
        (state / "NEXT_ACTION.json").write_text(
            json.dumps(
                {
                    "content": {
                        "action_type": "create_agent",
                        "target_role": "developer",
                        "task_id": "TASK_020",
                        "task_packet": "project-runtime/tasks/active/TASK_020.md",
                        "requester_return_context": "NONE",
                    }
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def _context_report(self, *extra_args: str) -> tuple[int, dict[str, object], str]:
        code, stdout, stderr = self._run(
            ["orchestrator", "context", "--root", str(self.root), "--format", "json", *extra_args]
        )
        return code, json.loads(stdout), stderr

    def _handoff_paths(self, report: dict[str, object]) -> set[str]:
        handoff_context = report["handoff_context"]
        self.assertIsInstance(handoff_context, dict)
        paths: set[str] = set()
        for field in ("required_docs", "reference_docs"):
            docs = handoff_context[field]
            self.assertIsInstance(docs, list)
            for doc in docs:
                self.assertIsInstance(doc, dict)
                paths.add(str(doc["path"]))
        return paths

    def test_routine_context_uses_compact_machine_readable_inputs(self) -> None:
        code, report, stderr = self._context_report()

        self.assertEqual(code, 0, stderr)
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["read_only"])
        self.assertFalse(report["mutations_performed"])
        self.assertEqual(report["context_mode"], "routine")
        self.assertEqual(report["target_role"], "developer")
        self.assertEqual(report["task_packet"], "project-runtime/tasks/active/TASK_020.md")
        self.assertEqual(report["handoff_context"]["reference_docs"], [])
        allowed_sources = report["allowed_sources"]
        self.assertEqual(allowed_sources["allowed_sources_ref"], "project-runtime/handoffs/TASK_020.allowed_sources.json")
        self.assertEqual(allowed_sources["own_handoff_ref"], "project-runtime/handoffs/TASK_020.json")
        self.assertEqual(allowed_sources["own_prompt_ref"], "project-runtime/handoffs/TASK_020.prompt.md")
        self.assertIn("SB3_BLOCKING", allowed_sources["severity_interpretation"]["correction_task_created_only_for"])
        allowed_refs = {entry["ref"] for entry in allowed_sources["allowed_refs"]}
        self.assertIn("project-runtime/tasks/active/TASK_020.md", allowed_refs)
        self.assertIn("project-runtime/handoffs/TASK_020.json", allowed_refs)

        runtime_contract = report["runtime_contract"]
        self.assertIsInstance(runtime_contract, dict)
        self.assertEqual(runtime_contract["path"], "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json")
        self.assertIn("routine_context_policy", runtime_contract["required_sections"])
        self.assertIn("handoff_context_builder_contract", runtime_contract["required_sections"])
        self.assertIn("source_boundary_contract", runtime_contract["required_sections"])
        self.assertEqual(report["context_budget"]["max_routine_files"], 6)
        self.assertEqual(report["context_budget"]["max_lines_per_file"], 160)
        self.assertFalse(report["context_budget"]["full_diff_or_report_in_stdout_by_default"])

        state_refs = report["current_state"]["state_refs"]
        state_paths = {ref["path"] for ref in state_refs}
        self.assertIn("project-runtime/state/NEXT_ACTION.json", state_paths)
        self.assertIn("project-runtime/agents/instances.jsonl", state_paths)

        paths = self._handoff_paths(report)
        self.assertIn("agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json", paths)
        self.assertIn("project-runtime/tasks/active/TASK_020.md", paths)
        self.assertNotIn("agent-system/01_roles/DEVELOPER.md", paths)
        self.assertNotIn("agent-system/03_templates/AGENT_RESULT_TEMPLATE.md", paths)
        self.assertNotIn("agent-system/01_roles/", paths)
        self.assertNotIn("agent-system/04_roles/", paths)
        self.assertNotIn("agent-system/03_templates/", paths)
        self.assertNotIn("agent-system/GOVERNANCE_CHANGELOG.md", paths)
        self.assertNotIn("agent-system/11_release/", paths)
        self.assertNotIn("agent-system/09_validators/", paths)
        self.assertTrue(
            all(doc["line_limit"] <= report["context_budget"]["max_lines_per_file"] for doc in report["handoff_context"]["required_docs"])
        )
        self.assertEqual(report["handoff_context"]["role_contract_summary"]["role"], "developer")
        self.assertEqual(report["handoff_context"]["role_contract_summary"]["role_reasoning_floor"], "high")
        self.assertEqual(report["handoff_context"]["result_contract_summary"]["result_kind"], "worker_result")

    def test_routine_context_rejects_broad_reference_corpus(self) -> None:
        broad_paths = (
            "agent-system/01_roles/",
            "agent-system/01_roles/DEVELOPER.md",
            "agent-system/04_roles/DEVELOPER.md",
            "agent-system/03_templates/",
            "agent-system/03_templates/AGENT_RESULT_TEMPLATE.md",
            "agent-system/GOVERNANCE_CHANGELOG.md",
            "agent-system/11_release/",
            "agent-system/11_release/ASO_P58_REAL_E2E_LIFECYCLE_HARDENING_V3_7_9_VALIDATION_REPORT.md",
            "agent-system/09_validators/",
            "agent-system/09_validators/schemas/orchestrator_handoff.schema.json",
        )
        for broad_path in broad_paths:
            with self.subTest(broad_path=broad_path):
                code, report, stderr = self._context_report("--reference-doc", broad_path)

                self.assertEqual(code, 1, stderr)
                self.assertEqual(report["status"], "fail")
                rule_ids = {finding["rule_id"] for finding in report["findings"]}
                self.assertIn("OCM-001", rule_ids)
                self.assertIn("OCM-004", rule_ids)

    def test_debug_reference_docs_require_authorization(self) -> None:
        code, report, stderr = self._context_report(
            "--context-mode",
            "debug",
            "--reference-doc",
            "agent-system/09_validators/",
        )

        self.assertEqual(code, 1, stderr)
        self.assertEqual(report["status"], "fail")
        self.assertIn("OCM-003", {finding["rule_id"] for finding in report["findings"]})

        code, report, stderr = self._context_report(
            "--context-mode",
            "debug",
            "--reference-doc",
            "agent-system/09_validators/schemas/orchestrator_handoff.schema.json",
            "--reference-reason",
            "specific validator reference requested",
        )

        self.assertEqual(code, 0, stderr)
        self.assertEqual(report["status"], "pass")
        reference_docs = report["handoff_context"]["reference_docs"]
        self.assertEqual(reference_docs[0]["path"], "agent-system/09_validators/schemas/orchestrator_handoff.schema.json")
        self.assertEqual(reference_docs[0]["authorization"], "explicit_reference_reason")

    def test_explain_mode_does_not_allow_reference_docs(self) -> None:
        code, report, stderr = self._context_report(
            "--context-mode",
            "explain",
            "--reference-doc",
            "agent-system/09_validators/schemas/orchestrator_handoff.schema.json",
            "--reference-reason",
            "explain request",
        )

        self.assertEqual(code, 1, stderr)
        self.assertEqual(report["status"], "fail")
        self.assertIn("OCM-005", {finding["rule_id"] for finding in report["findings"]})

    def test_explain_validator_required_does_not_authorize_template_reference(self) -> None:
        code, report, stderr = self._context_report(
            "--context-mode",
            "explain",
            "--reference-doc",
            "agent-system/03_templates/AGENT_RESULT_TEMPLATE.md",
            "--validator-required",
        )

        self.assertEqual(code, 1, stderr)
        self.assertEqual(report["status"], "fail")
        rule_ids = {finding["rule_id"] for finding in report["findings"]}
        self.assertIn("OCM-005", rule_ids)
        self.assertIn("OCM-007", rule_ids)
        self.assertEqual(report["handoff_context"]["reference_docs"], [])
        allowed_refs = {entry["ref"] for entry in report["allowed_sources"]["allowed_refs"]}
        self.assertNotIn("agent-system/03_templates/AGENT_RESULT_TEMPLATE.md", allowed_refs)

    def test_explain_validator_required_rejects_parent_segment_validator_escape(self) -> None:
        escaped_ref = "agent-system/09_validators/../03_templates/AGENT_RESULT_TEMPLATE.md"

        code, report, stderr = self._context_report(
            "--context-mode",
            "explain",
            "--reference-doc",
            escaped_ref,
            "--validator-required",
        )

        self.assertEqual(code, 1, stderr)
        self.assertEqual(report["status"], "fail")
        rule_ids = {finding["rule_id"] for finding in report["findings"]}
        self.assertIn("OCM-005", rule_ids)
        self.assertIn("OCM-007", rule_ids)
        self.assertEqual(report["handoff_context"]["reference_docs"], [])
        allowed_refs = {entry["ref"] for entry in report["allowed_sources"]["allowed_refs"]}
        self.assertNotIn(escaped_ref, allowed_refs)
        self.assertNotIn("agent-system/03_templates/AGENT_RESULT_TEMPLATE.md", allowed_refs)

    def test_explain_validator_required_allows_concrete_validator_reference(self) -> None:
        validator_ref = "agent-system/09_validators/schemas/orchestrator_handoff.schema.json"

        code, report, stderr = self._context_report(
            "--context-mode",
            "explain",
            "--reference-doc",
            validator_ref,
            "--validator-required",
        )

        self.assertEqual(code, 0, stderr)
        self.assertEqual(report["status"], "pass")
        reference_docs = report["handoff_context"]["reference_docs"]
        self.assertEqual(reference_docs[0]["path"], validator_ref)
        self.assertEqual(reference_docs[0]["authorization"], "validator_required")
        allowed_refs = {entry["ref"] for entry in report["allowed_sources"]["allowed_refs"]}
        self.assertIn(validator_ref, allowed_refs)

    def test_target_role_receives_only_its_compact_role_summary(self) -> None:
        code, report, stderr = self._context_report("--target-role", "auditor")

        self.assertEqual(code, 0, stderr)
        self.assertEqual(report["target_role"], "auditor")
        paths = self._handoff_paths(report)
        self.assertNotIn("agent-system/01_roles/AUDITOR.md", paths)
        self.assertNotIn("agent-system/01_roles/DEVELOPER.md", paths)
        self.assertNotIn("agent-system/01_roles/", paths)
        self.assertEqual(report["handoff_context"]["role_contract_summary"]["role"], "auditor")
        self.assertEqual(report["handoff_context"]["role_contract_summary"]["role_reasoning_floor"], "xhigh")
        self.assertEqual(report["handoff_context"]["result_contract_summary"]["result_kind"], "audit_result")


if __name__ == "__main__":
    unittest.main()
