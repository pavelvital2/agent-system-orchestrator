from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "stage1-governance.yml"
MAKEFILE = REPO_ROOT / "Makefile"
TASK_PACKET_TEMPLATE = REPO_ROOT / "agent-system" / "03_templates" / "TASK_PACKET_TEMPLATE.md"
BOOTSTRAP_TASK_PACKET_TEMPLATE = REPO_ROOT / "agent-system" / "03_templates" / "BOOTSTRAP_TASK_PACKET_TEMPLATE.md"
HANDOFF_TEMPLATE = REPO_ROOT / "agent-system" / "03_templates" / "ORCHESTRATOR_TASK_HANDOFF_TEMPLATE.md"
TASK_PACKET_SCHEMA_RULES = REPO_ROOT / "agent-system" / "09_validators" / "TASK_PACKET_SCHEMA_VALIDATION_RULES.md"
TASK_PACKET_SCHEMA = REPO_ROOT / "agent-system" / "09_validators" / "schemas" / "task_packet.schema.json"
REASONING_RULES = REPO_ROOT / "agent-system" / "09_validators" / "REASONING_LEVEL_VALIDATION_RULES.md"
LIFECYCLE_DOC = REPO_ROOT / "agent-system" / "02_runtime" / "PROFILE_AGENT_LIFECYCLE.md"
CONVEYOR_DOC = REPO_ROOT / "agent-system" / "02_runtime" / "ORCHESTRATOR_CONVEYOR_PROTOCOL.md"


FORBIDDEN_WORKFLOW_PATTERNS = (
    r"\bsecrets\.",
    r"\bgit\s+push\b",
    r"\bgit\s+remote\s+(add|set-url|rename|remove|prune|update)\b",
    r"\bgh\s+(auth|release|repo|workflow|run|api)\b",
    r"\btwine\s+upload\b",
    r"\bnpm\s+publish\b",
    r"\bdocker\s+push\b",
    r"\bdeploy\b",
)

REQUIRED_WORKFLOW_COMMANDS = (
    "actions/setup-python",
    'python-version: ${{ matrix.python-version }}',
    "- \"3.10\"",
    "install_aso_clean.sh",
    "--venv \"$RUNNER_TEMP/aso-ci-test-venv\"",
    "--with-test",
    "--skip-verify",
    'make ci PYTHON="$RUNNER_TEMP/aso-ci-test-venv/bin/python"',
)

REQUIRED_MAKEFILE_COMMANDS = (
    "unittest discover -s agent-system/tools/aso/tests",
    "unittest discover -s agent-system/tests",
    "status --root . --mode package",
    "lint --root . --mode package --strict",
    "doctor --root . --mode package --strict",
    "validate-design agent-system/tests/fixtures/design/valid_design.md --root . --strict",
    "validate-context-pack agent-system/tests/fixtures/context_pack/valid_context_pack.json --root . --strict",
    "validate-rules --root . --strict",
    "state verify --root agent-system/tests/fixtures/state/valid_workspace --strict",
    "state verify --root agent-system/tests/fixtures/state/p2_valid_workspace --strict",
    "state render --root agent-system/tests/fixtures/state/p2_valid_workspace --format json --out /tmp/aso-p2-state-render-smoke.json",
    "plan-next --root agent-system/tests/fixtures/state/valid_workspace --strict",
    "dashboard --root agent-system/tests/fixtures/state/valid_workspace --out /tmp/aso-stage2-dashboard-smoke.html",
    "checkpoint-preflight --root . --mode package --strict",
    "./agent-system/scripts/run_governance_smoke_tests.sh",
    "install_aso_clean.sh --source . --venv",
    "bin/aso\" --help >/dev/null",
    "bin/aso\" status --root . --mode package",
    "bin/aso\" package-layout verify --root . --mode package --strict",
    "agent_system_orchestrator_aso.cli",
    "git diff --check",
)


class Stage2CIGovernanceTests(unittest.TestCase):
    def test_governance_workflow_runs_on_upgrade_branches_with_read_only_checkout(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("- upgrade/**", workflow)
        self.assertNotIn("- upgrade/stage-1-executable-controls", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("uses: actions/checkout@v5", workflow)
        self.assertNotIn("uses: actions/checkout@v4", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn('python -m pip install -e ".[test]"', workflow)
        for command in REQUIRED_WORKFLOW_COMMANDS:
            with self.subTest(command=command):
                self.assertIn(command, workflow)

        for pattern in FORBIDDEN_WORKFLOW_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, workflow, flags=re.IGNORECASE))

    def test_makefile_ci_target_runs_offline_governance_surface(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")

        self.assertRegex(makefile, r"(?m)^ci:\s+test\s+smoke\s+doctor\s+lint\s+install-smoke$")
        self.assertRegex(makefile, r"(?m)^test:")
        self.assertRegex(makefile, r"(?m)^smoke:")
        self.assertRegex(makefile, r"(?m)^doctor:")
        self.assertRegex(makefile, r"(?m)^lint:")
        self.assertRegex(makefile, r"(?m)^install-smoke:")
        self.assertNotIn("pytest", makefile)
        for command in REQUIRED_MAKEFILE_COMMANDS:
            with self.subTest(command=command):
                self.assertIn(command, makefile)

    def test_agent_governance_fields_stay_in_active_templates_and_rules(self) -> None:
        required_fields = (
            "TASK_COMPLEXITY",
            "REASONING_LEVEL_REQUIRED",
            "AGENT_LIFECYCLE_POLICY",
            "one_agent_one_task_delete_after_result",
        )
        required_docs = (
            TASK_PACKET_TEMPLATE,
            BOOTSTRAP_TASK_PACKET_TEMPLATE,
            HANDOFF_TEMPLATE,
            TASK_PACKET_SCHEMA_RULES,
            TASK_PACKET_SCHEMA,
        )

        for path in required_docs:
            text = path.read_text(encoding="utf-8")
            for field in required_fields:
                with self.subTest(path=path.name, field=field):
                    self.assertIn(field, text)

        reasoning_rules = REASONING_RULES.read_text(encoding="utf-8")
        self.assertRegex(reasoning_rules, r"tester(?:.|\n)*high")
        self.assertRegex(reasoning_rules, r"auditor(?:.|\n)*xhigh")
        self.assertIn("above medium", reasoning_rules)

        lifecycle_doc = LIFECYCLE_DOC.read_text(encoding="utf-8")
        self.assertIn("one agent = one task = one RESULT", lifecycle_doc)
        self.assertRegex(lifecycle_doc, r"deleted(?:.|\n)*rendered(?:.|\n)*inaccessible")

        conveyor_doc = CONVEYOR_DOC.read_text(encoding="utf-8")
        self.assertIn("orchestrator does not write", conveyor_doc)
        self.assertRegex(conveyor_doc, r"does not check(?:.|\n)*changes semantically")


if __name__ == "__main__":
    unittest.main()
