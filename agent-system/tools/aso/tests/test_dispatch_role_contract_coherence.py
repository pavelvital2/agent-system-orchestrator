from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - optional test dependency
    Draft202012Validator = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[4]
ASO_TOOL_ROOT = REPO_ROOT / "agent-system" / "tools" / "aso"
RESOURCE_ROOT = ASO_TOOL_ROOT / "agent_system_orchestrator_aso" / "resources"
PACKAGED_ASO_TOOL_ROOT = RESOURCE_ROOT / "agent-system" / "tools" / "aso"
SCHEMA_DIR = REPO_ROOT / "agent-system" / "09_validators" / "schemas"
PACKAGED_SCHEMA_DIR = RESOURCE_ROOT / "agent-system" / "09_validators" / "schemas"
DISPATCHABLE_ROLES = (
    "requirements_analyst",
    "solution_architect",
    "developer",
    "tester",
    "auditor",
    "technical_writer",
)
FORBIDDEN_DISPATCH_ROLES = ("designer", "devops_setup_engineer", "release_manager")

sys.path.insert(0, str(ASO_TOOL_ROOT))

from agent_system_orchestrator_aso.aso_tool import aso  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import dispatch_receipts  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import result_parser  # noqa: E402
from agent_system_orchestrator_aso.aso_tool import role_registry  # noqa: E402
from agent_system_orchestrator_aso.aso_tool.commands import record_result  # noqa: E402


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return payload


def _dispatchability_report(role: str) -> dict[str, object]:
    check_ids = _load_json(SCHEMA_DIR / "dispatchability_gate.schema.json")["$defs"]["check"]["properties"]["check_id"]["enum"]  # type: ignore[index]
    return {
        "contract_id": "ASO_PLANNER_DISPATCHABILITY_GATE_P5_4",
        "contract_version": "1.0.0",
        "dispatchable": True,
        "verdict": "dispatchable",
        "recommended_next_action": "CREATE_AGENT",
        "status": "ready",
        "target_role": role,
        "role_class": "profile_execution",
        "action_type": "create_agent",
        "action_class": "dispatch",
        "task_id": "TASK_DEMO_001",
        "task_packet": "project-runtime/tasks/active/TASK_DEMO_001.md",
        "checks": [
            {
                "check_id": check_id,
                "passed": True,
                "severity": "info",
                "reason_code": "none",
                "evidence": f"{check_id}=passed",
            }
            for check_id in check_ids
        ],
        "reasons": [],
        "live_dispatch_performed": False,
    }


def _dispatch_receipt(role: str) -> dict[str, object]:
    return dispatch_receipts.build_dispatch_receipt(
        agent_instance_id="agent_TASK_DEMO_001_attempt_001",
        task_id="TASK_DEMO_001",
        role=role,
        runner="external_codex_cli",
        model="UNKNOWN",
        reasoning_effort="high",
        prompt_ref="project-runtime/handoffs/TASK_DEMO_001.prompt.md",
        handoff_ref="project-runtime/handoffs/TASK_DEMO_001.json",
        started_at="2026-05-25T00:00:00Z",
    )


def _handoff_payload(role: str) -> dict[str, object]:
    return {
        "handoff_type": "ORCHESTRATOR_HANDOFF",
        "schema_version": "1.0.0",
        "task_id": "TASK_DEMO_001",
        "role": role,
        "resolved_reasoning_level": "high",
        "context_mode": "routine",
        "handoff_ref": "project-runtime/handoffs/TASK_DEMO_001.json",
        "prompt_ref": "project-runtime/handoffs/TASK_DEMO_001.prompt.md",
        "required_docs": [
            {
                "path": "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json",
                "sections": ["Runtime contract"],
                "why_needed": "Required for role contract validation.",
                "source": "runtime_contract",
            }
        ],
        "required_doc_tokens": ["runtime_contract"],
        "forbidden_docs": ["agent-system/09_validators/"],
        "reference_docs": [],
        "governance_corpus_included": False,
        "expected_result_path": "project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md",
        "expected_artifact_package_path": "project-runtime/artifacts/candidates/TASK_DEMO_001/manifest.json",
        "lifecycle_policy": "one_agent_one_task_delete_after_result",
        "expected_receipt_ref_template": "project-runtime/agents/dispatches/<AGENT_INSTANCE_ID>.json",
        "external_runner_contract": {
            "runner": "external_codex_cli",
            "runner_semantics": "ASO records external runner dispatch evidence and does not execute the runner.",
            "external_runner_command_template": (
                'codex exec -C <WORKSPACE_ROOT> -m <MODEL> '
                '-c model_reasoning_effort="<REASONING_EFFORT>" - < <PROMPT_REF>'
            ),
            "receipt_writer_command_template": "python3 agent-system/tools/aso/aso.py dispatch receipt",
            "live_dispatch_performed_by_aso": False,
        },
        "result_contract_ref": "agent-system/03_templates/AGENT_RESULT_TEMPLATE.md",
        "lifecycle_policy_enforcement": {
            "reuse_allowed": False,
            "agent_termination_required": True,
        },
    }


def _write_downstream_task_packet(root: Path, role: str) -> str:
    relpath = f"project-runtime/tasks/active/TASK_DEMO_{role.upper()}.md"
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# TASK PACKET",
                "",
                "TASK_ID: TASK_DEMO_001",
                "TASK_KIND: implementation",
                "TASK_TYPE: implementation",
                f"TARGET_ROLE: {role}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return relpath


def _role_enum(schema: dict[str, object], field: str) -> tuple[str, ...]:
    properties = schema["properties"]  # type: ignore[index]
    return tuple(properties[field]["enum"])  # type: ignore[index]


def _dispatchability_target_role_enum(schema: dict[str, object]) -> tuple[str, ...]:
    for rule in schema["allOf"]:  # type: ignore[index]
        if_props = rule.get("if", {}).get("properties", {})  # type: ignore[union-attr]
        action = if_props.get("recommended_next_action", {}).get("const")
        if action == "CREATE_AGENT":
            return tuple(rule["then"]["properties"]["target_role"]["enum"])  # type: ignore[index]
    raise AssertionError("CREATE_AGENT dispatchability rule was not found")


class RecordResultDownstreamDispatchabilityTests(unittest.TestCase):
    def test_source_record_result_accepts_only_dispatchable_downstream_task_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)

            for role in DISPATCHABLE_ROLES:
                with self.subTest(role=role):
                    relpath = _write_downstream_task_packet(root, role)
                    dispatchable, detail = record_result._dispatchable_downstream_packet(root, relpath)
                    self.assertTrue(dispatchable, detail)

            for role in FORBIDDEN_DISPATCH_ROLES:
                with self.subTest(role=role):
                    relpath = _write_downstream_task_packet(root, role)
                    dispatchable, detail = record_result._dispatchable_downstream_packet(root, relpath)
                    self.assertFalse(dispatchable, detail)
                    self.assertIn("is not dispatchable", detail)

    def test_packaged_record_result_accepts_only_dispatchable_downstream_task_roles(self) -> None:
        code = r'''
import json
import tempfile
from pathlib import Path
from agent_system_orchestrator_aso.aso_tool.commands import record_result

dispatchable_roles = (
    "requirements_analyst",
    "solution_architect",
    "developer",
    "tester",
    "auditor",
    "technical_writer",
)
forbidden_roles = ("designer", "devops_setup_engineer", "release_manager")

def write_packet(root, role):
    relpath = f"project-runtime/tasks/active/TASK_DEMO_{role.upper()}.md"
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# TASK PACKET",
                "",
                "TASK_ID: TASK_DEMO_001",
                "TASK_KIND: implementation",
                "TASK_TYPE: implementation",
                f"TARGET_ROLE: {role}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return relpath

with tempfile.TemporaryDirectory() as tempdir:
    root = Path(tempdir)
    payload = {"accepted": {}, "forbidden": {}}
    for role in dispatchable_roles:
        relpath = write_packet(root, role)
        payload["accepted"][role] = record_result._dispatchable_downstream_packet(root, relpath)[0]
    for role in forbidden_roles:
        relpath = write_packet(root, role)
        allowed, detail = record_result._dispatchable_downstream_packet(root, relpath)
        payload["forbidden"][role] = {"allowed": allowed, "detail": detail}
print(json.dumps(payload, sort_keys=True))
'''
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(PACKAGED_ASO_TOOL_ROOT)
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload["accepted"].values()), {True})
        for role, detail in payload["forbidden"].items():
            with self.subTest(role=role):
                self.assertFalse(detail["allowed"])
                self.assertIn("is not dispatchable", detail["detail"])

    def test_source_and_packaged_profile_result_role_allowances_exclude_forbidden_roles(self) -> None:
        expected_profile_roles = tuple(role for role in DISPATCHABLE_ROLES if role != "auditor")

        self.assertEqual(tuple(sorted(result_parser.PROFILE_ROLES)), tuple(sorted(expected_profile_roles)))
        self.assertEqual(tuple(sorted(record_result.PROFILE_ROLES)), tuple(sorted(expected_profile_roles)))
        for role in FORBIDDEN_DISPATCH_ROLES:
            self.assertNotIn(role, result_parser.PROFILE_ROLES)
            self.assertNotIn(role, record_result.PROFILE_ROLES)

        code = r'''
import json
from agent_system_orchestrator_aso.aso_tool import result_parser, role_registry
from agent_system_orchestrator_aso.aso_tool.commands import record_result

payload = {
    "dispatchable_roles": list(role_registry.dispatchable_roles()),
    "result_parser_profile_roles": sorted(result_parser.PROFILE_ROLES),
    "record_result_profile_roles": sorted(record_result.PROFILE_ROLES),
}
print(json.dumps(payload, sort_keys=True))
'''
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(PACKAGED_ASO_TOOL_ROOT)
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(tuple(payload["dispatchable_roles"]), DISPATCHABLE_ROLES)
        self.assertEqual(tuple(payload["result_parser_profile_roles"]), tuple(sorted(expected_profile_roles)))
        self.assertEqual(tuple(payload["record_result_profile_roles"]), tuple(sorted(expected_profile_roles)))
        for role in FORBIDDEN_DISPATCH_ROLES:
            self.assertNotIn(role, payload["result_parser_profile_roles"])
            self.assertNotIn(role, payload["record_result_profile_roles"])


@unittest.skipIf(Draft202012Validator is None, "jsonschema is not installed")
class DispatchRoleContractCoherenceTests(unittest.TestCase):
    def test_dispatchable_role_registry_is_exactly_the_six_worker_roles(self) -> None:
        self.assertEqual(role_registry.dispatchable_roles(), DISPATCHABLE_ROLES)
        self.assertEqual(dispatch_receipts.PROFILE_ROLES, DISPATCHABLE_ROLES)

        parser = aso.build_parser()
        command_action = next(action for action in parser._actions if action.dest == "command")
        dispatch_parser = command_action.choices["dispatch"]
        dispatch_action = next(action for action in dispatch_parser._actions if action.dest == "dispatch_command")
        receipt_parser = dispatch_action.choices["receipt"]
        role_action = next(action for action in receipt_parser._actions if action.dest == "role")

        self.assertEqual(tuple(role_action.choices), DISPATCHABLE_ROLES)

    def test_source_and_packaged_schema_role_enums_match_dispatchable_roles(self) -> None:
        schema_fields = (
            ("dispatch_receipt.schema.json", "role"),
            ("orchestrator_handoff.schema.json", "role"),
        )

        for filename, field in schema_fields:
            with self.subTest(filename=filename):
                source_schema = _load_json(SCHEMA_DIR / filename)
                packaged_schema = _load_json(PACKAGED_SCHEMA_DIR / filename)

                self.assertEqual(source_schema, packaged_schema)
                self.assertEqual(_role_enum(source_schema, field), DISPATCHABLE_ROLES)

        source_dispatchability = _load_json(SCHEMA_DIR / "dispatchability_gate.schema.json")
        packaged_dispatchability = _load_json(PACKAGED_SCHEMA_DIR / "dispatchability_gate.schema.json")
        self.assertEqual(source_dispatchability, packaged_dispatchability)
        self.assertEqual(_dispatchability_target_role_enum(source_dispatchability), DISPATCHABLE_ROLES)

    def test_dispatchability_gate_schema_rejects_forbidden_dispatch_roles(self) -> None:
        for schema_root in (SCHEMA_DIR, PACKAGED_SCHEMA_DIR):
            schema = _load_json(schema_root / "dispatchability_gate.schema.json")
            validator = Draft202012Validator(schema)
            with self.subTest(schema_root=schema_root):
                for role in DISPATCHABLE_ROLES:
                    self.assertEqual(list(validator.iter_errors(_dispatchability_report(role))), [])
                for role in FORBIDDEN_DISPATCH_ROLES:
                    errors = list(validator.iter_errors(_dispatchability_report(role)))
                    self.assertTrue(errors)

    def test_dispatch_receipt_schema_rejects_forbidden_dispatch_roles(self) -> None:
        for schema_root in (SCHEMA_DIR, PACKAGED_SCHEMA_DIR):
            schema = _load_json(schema_root / "dispatch_receipt.schema.json")
            validator = Draft202012Validator(schema)
            with self.subTest(schema_root=schema_root):
                for role in DISPATCHABLE_ROLES:
                    self.assertEqual(list(validator.iter_errors(_dispatch_receipt(role))), [])
                for role in FORBIDDEN_DISPATCH_ROLES:
                    errors = list(validator.iter_errors(_dispatch_receipt(role)))
                    self.assertTrue(errors)

    def test_orchestrator_handoff_schema_rejects_forbidden_dispatch_roles(self) -> None:
        for schema_root in (SCHEMA_DIR, PACKAGED_SCHEMA_DIR):
            schema = _load_json(schema_root / "orchestrator_handoff.schema.json")
            validator = Draft202012Validator(schema)
            with self.subTest(schema_root=schema_root):
                for role in DISPATCHABLE_ROLES:
                    self.assertEqual(list(validator.iter_errors(_handoff_payload(role))), [])
                for role in FORBIDDEN_DISPATCH_ROLES:
                    errors = list(validator.iter_errors(_handoff_payload(role)))
                    self.assertTrue(errors)

    def test_source_and_packaged_dispatch_receipt_validation_match(self) -> None:
        for role in DISPATCHABLE_ROLES:
            with self.subTest(role=role):
                self.assertTrue(dispatch_receipts.validate_dispatch_receipt(_dispatch_receipt(role)).passed)

        for role in FORBIDDEN_DISPATCH_ROLES:
            with self.subTest(role=role):
                self.assertFalse(dispatch_receipts.validate_dispatch_receipt(_dispatch_receipt(role)).passed)

        code = """
import json
from agent_system_orchestrator_aso.aso_tool import aso, dispatch_receipts, role_registry, transition_engine
from agent_system_orchestrator_aso.aso_tool.commands import plan_next

def receipt(role):
    return dispatch_receipts.build_dispatch_receipt(
        agent_instance_id="agent_TASK_DEMO_001_attempt_001",
        task_id="TASK_DEMO_001",
        role=role,
        runner="external_codex_cli",
        model="UNKNOWN",
        reasoning_effort="high",
        prompt_ref="project-runtime/handoffs/TASK_DEMO_001.prompt.md",
        handoff_ref="project-runtime/handoffs/TASK_DEMO_001.json",
        started_at="2026-05-25T00:00:00Z",
    )

parser = aso.build_parser()
command_action = next(action for action in parser._actions if action.dest == "command")
dispatch_parser = command_action.choices["dispatch"]
dispatch_action = next(action for action in dispatch_parser._actions if action.dest == "dispatch_command")
receipt_parser = dispatch_action.choices["receipt"]
role_action = next(action for action in receipt_parser._actions if action.dest == "role")
contract = transition_engine.load_runtime_contract()
def stored_next_action(role):
    return {
        "NEXT_ACTION": {
            "content": {
                "action_type": "create_agent",
                "target_role": role,
                "task_id": "TASK_DEMO_001",
                "task_packet": "project-runtime/tasks/active/TASK_DEMO_001.md",
            }
        }
    }

payload = {
    "roles": list(role_registry.dispatchable_roles()),
    "plan_next_profile_roles": sorted(plan_next.PROFILE_EXECUTION_ROLES),
    "choices": list(role_action.choices),
    "accepted": {
        role: dispatch_receipts.validate_dispatch_receipt(receipt(role)).passed
        for role in role_registry.dispatchable_roles()
    },
    "forbidden": {
        role: dispatch_receipts.validate_dispatch_receipt(receipt(role)).passed
        for role in ("designer", "devops_setup_engineer", "release_manager")
    },
    "transition_accepted": {
        role: transition_engine.derive_transition(
            contract,
            "TASK_READY",
            "CREATE_AGENT_DISPATCHED",
            target_role=role,
            task_id="TASK_DEMO_001",
        ).allowed
        for role in role_registry.dispatchable_roles()
    },
    "transition_forbidden": {
        role: transition_engine.derive_transition(
            contract,
            "TASK_READY",
            "CREATE_AGENT_DISPATCHED",
            target_role=role,
            task_id="TASK_DEMO_001",
        ).allowed
        for role in ("designer", "devops_setup_engineer", "release_manager")
    },
    "stored_next_action_forbidden": {
        role: transition_engine.explain_next_action_from_sidecars(
            contract,
            stored_next_action(role),
        ).allowed
        for role in ("designer", "devops_setup_engineer", "release_manager")
    },
}
print(json.dumps(payload, sort_keys=True))
"""
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(PACKAGED_ASO_TOOL_ROOT)
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(tuple(payload["roles"]), DISPATCHABLE_ROLES)
        self.assertEqual(set(payload["plan_next_profile_roles"]), set(DISPATCHABLE_ROLES))
        self.assertEqual(tuple(payload["choices"]), DISPATCHABLE_ROLES)
        self.assertEqual(set(payload["accepted"].values()), {True})
        self.assertEqual(set(payload["forbidden"].values()), {False})
        self.assertEqual(set(payload["transition_accepted"].values()), {True})
        self.assertEqual(set(payload["transition_forbidden"].values()), {False})
        self.assertEqual(set(payload["stored_next_action_forbidden"].values()), {False})


if __name__ == "__main__":
    unittest.main()
