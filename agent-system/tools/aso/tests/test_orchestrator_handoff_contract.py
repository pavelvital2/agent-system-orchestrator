from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - optional test dependency
    Draft202012Validator = None  # type: ignore[assignment]


ASO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "state"
if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool import handoff_artifacts  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import transition_engine  # noqa: E402
from agent_system_orchestrator_aso.aso_tool.aso import main  # noqa: E402


class OrchestratorHandoffContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="aso-orchestrator-handoff-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_plan_next_emits_machine_readable_handoff_for_dispatchable_action(self) -> None:
        root = self.tmpdir / "valid-workspace"
        shutil.copytree(FIXTURE_ROOT / "valid_workspace", root)
        out = self.tmpdir / "plan-next.json"

        code, _, stderr = self._run(["plan-next", "--root", str(root), "--strict", "--json-out", str(out)])

        self.assertEqual(code, 0, stderr)
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(report["dispatchable"])
        self.assertEqual(report["recommended_next_action"], "CREATE_AGENT")

        handoff = report["handoff_artifact"]
        self.assertTrue(handoff["required"])
        self.assertTrue(handoff["machine_readable"])
        self.assertEqual(handoff["schema_ref"], handoff_artifacts.SCHEMA_RELATIVE_PATH)
        self.assertEqual(handoff["template_ref"], handoff_artifacts.TEMPLATE_RELATIVE_PATH)
        self.assertEqual(handoff["validation"]["status"], "passed")
        self.assertEqual(handoff["validation"]["errors"], [])

        payload = handoff["payload"]
        self.assertEqual(payload["handoff_type"], "ORCHESTRATOR_HANDOFF")
        self.assertEqual(payload["task_id"], "TASK_FIXTURE_STATE_001")
        self.assertEqual(payload["role"], "developer")
        self.assertEqual(payload["resolved_reasoning_level"], "high")
        self.assertEqual(payload["context_mode"], "routine")
        self.assertEqual(payload["prompt_ref"], "project-runtime/handoffs/TASK_FIXTURE_STATE_001.prompt.md")
        self.assertEqual(payload["handoff_ref"], "project-runtime/handoffs/TASK_FIXTURE_STATE_001.json")
        self.assertEqual(
            payload["allowed_sources_ref"],
            "project-runtime/handoffs/TASK_FIXTURE_STATE_001.allowed_sources.json",
        )
        self.assertEqual(
            payload["expected_result_path"],
            "project-runtime/results/worker/RESULT_TASK_FIXTURE_STATE_001_ATTEMPT_001.md",
        )
        self.assertEqual(
            payload["expected_artifact_package_path"],
            "project-runtime/artifacts/candidates/TASK_FIXTURE_STATE_001/manifest.json",
        )
        self.assertEqual(payload["lifecycle_policy"], "one_agent_one_task_delete_after_result")
        self.assertFalse(payload["governance_corpus_included"])
        self.assertEqual(payload["reference_docs"], [])
        self.assertFalse(payload["external_runner_contract"]["live_dispatch_performed_by_aso"])
        self.assertIn("codex exec", payload["external_runner_contract"]["external_runner_command_template"])

        required_paths = {doc["path"] for doc in payload["required_docs"]}
        allowed_source_refs = {entry["ref"] for entry in payload["allowed_sources"]["allowed_refs"]}
        self.assertIn("agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json", required_paths)
        self.assertIn("project-runtime/tasks/active/TASK_FIXTURE_STATE_001.md", required_paths)
        self.assertIn("agent-system/01_roles/DEVELOPER.md", required_paths)
        self.assertIn("agent-system/03_templates/AGENT_RESULT_TEMPLATE.md", required_paths)
        self.assertIn("project-runtime/handoffs/TASK_FIXTURE_STATE_001.json", allowed_source_refs)
        self.assertIn("project-runtime/handoffs/TASK_FIXTURE_STATE_001.prompt.md", allowed_source_refs)
        self.assertEqual(
            payload["allowed_sources"]["severity_interpretation"]["correction_task_created_only_for"],
            ["SB3_BLOCKING", "SB4_INVALIDATING"],
        )
        self.assertIn("agent-system/09_validators/", payload["forbidden_docs"])
        self.assertTrue(handoff_artifacts.validate_handoff_artifact(payload).passed)

    def test_non_dispatchable_plan_does_not_emit_profile_handoff_payload(self) -> None:
        root = self.tmpdir / "blocked-workspace"
        shutil.copytree(FIXTURE_ROOT / "p2_valid_workspace", root)
        out = self.tmpdir / "plan-next-blocked.json"

        code, _, stderr = self._run(["plan-next", "--root", str(root), "--strict", "--json-out", str(out)])

        self.assertEqual(code, 0, stderr)
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["route_status"], "ready")
        self.assertFalse(report["dispatchable"])
        handoff = report["handoff_artifact"]
        self.assertFalse(handoff["required"])
        self.assertEqual(handoff["payload"], {})
        self.assertEqual(handoff["validation"]["status"], "not_required")
        self.assertEqual(handoff["validation"]["errors"], [])

    def test_routine_handoff_rejects_broad_governance_corpus_reference(self) -> None:
        contract = transition_engine.load_runtime_contract()
        payload = handoff_artifacts.build_handoff_artifact(
            contract=contract,
            task_id="TASK_DEMO_001",
            role="developer",
            resolved_reasoning_level="high",
            task_packet="project-runtime/tasks/active/TASK_DEMO_001.md",
            reference_docs=["agent-system/09_validators/"],
        )

        validation = handoff_artifacts.validate_handoff_artifact(payload)

        self.assertFalse(validation.passed)
        joined = "\n".join(validation.errors)
        self.assertIn("routine handoff must not include reference_docs", joined)
        self.assertIn("broad governance corpus path: agent-system/09_validators/", joined)

    @unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
    def test_handoff_schema_accepts_planner_payload(self) -> None:
        root = self.tmpdir / "valid-workspace-schema"
        shutil.copytree(FIXTURE_ROOT / "valid_workspace", root)
        out = self.tmpdir / "plan-next-schema.json"

        code, _, stderr = self._run(["plan-next", "--root", str(root), "--strict", "--json-out", str(out)])

        self.assertEqual(code, 0, stderr)
        report = json.loads(out.read_text(encoding="utf-8"))
        payload = report["handoff_artifact"]["payload"]
        schema = json.loads(
            (REPO_ROOT / "agent-system/09_validators/schemas/orchestrator_handoff.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda error: list(error.path))

        self.assertEqual(errors, [], "\n".join(error.message for error in errors))


if __name__ == "__main__":
    unittest.main()
