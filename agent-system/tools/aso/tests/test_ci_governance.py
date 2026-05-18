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
    "python3 agent-system/tools/aso/aso.py status --root . --mode package",
    "python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict",
    "python3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict",
    "python3 agent-system/tools/aso/aso.py validate-design agent-system/tests/fixtures/design/valid_design.md --root . --strict",
    "python3 agent-system/tools/aso/aso.py validate-context-pack agent-system/tests/fixtures/context_pack/valid_context_pack.json --root . --strict",
    "python3 -m unittest discover -s agent-system/tools/aso/tests",
    "python3 -m unittest discover -s agent-system/tests",
    "./agent-system/scripts/run_governance_smoke_tests.sh",
    "make test",
    "make smoke",
    "make doctor",
    "make lint",
    "git diff --check",
)


class Stage1CIGovernanceTests(unittest.TestCase):
    def test_stage1_governance_workflow_uses_local_secretless_checks(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("persist-credentials: false", workflow)
        for command in REQUIRED_WORKFLOW_COMMANDS:
            with self.subTest(command=command):
                self.assertIn(command, workflow)

        for pattern in FORBIDDEN_WORKFLOW_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, workflow, flags=re.IGNORECASE))

    def test_makefile_targets_run_stage1_governance_surface(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")

        self.assertRegex(makefile, r"(?m)^test:")
        self.assertRegex(makefile, r"(?m)^smoke:")
        self.assertRegex(makefile, r"(?m)^doctor:")
        self.assertRegex(makefile, r"(?m)^lint:")
        self.assertIn("unittest discover -s agent-system/tools/aso/tests", makefile)
        self.assertIn("unittest discover -s agent-system/tests", makefile)
        self.assertIn("status --root . --mode package", makefile)
        self.assertIn("lint --root . --mode package --strict", makefile)
        self.assertIn("doctor --root . --mode package --strict", makefile)
        self.assertIn("validate-design agent-system/tests/fixtures/design/valid_design.md --root . --strict", makefile)
        self.assertIn("validate-context-pack agent-system/tests/fixtures/context_pack/valid_context_pack.json --root . --strict", makefile)
        self.assertIn("./agent-system/scripts/run_governance_smoke_tests.sh", makefile)


if __name__ == "__main__":
    unittest.main()
