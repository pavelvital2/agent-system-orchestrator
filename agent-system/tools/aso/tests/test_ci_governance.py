from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "stage1-governance.yml"
MAKEFILE = REPO_ROOT / "Makefile"


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
    "make ci",
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


if __name__ == "__main__":
    unittest.main()
