from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


VALIDATOR = Path(__file__).resolve().parents[1] / "scripts" / "validate_task_packet.py"


def task_packet(role: str) -> str:
    return textwrap.dedent(
        f"""\
        # TASK PACKET

        ## TASK_ID
        ```text
        TASK_BOOTSTRAP_{role.upper()}_001
        ```

        ## TASK_STATUS
        ```text
        active
        ```

        ## TASK_KIND
        ```text
        bootstrap
        ```

        ## SUPERSEDES
        ```text
        NONE
        ```

        ## SUPERSEDED_BY
        ```text
        NONE
        ```

        ## CORRECTION_OF
        ```text
        NONE
        ```

        ## SOURCE_RESULT_REF
        ```text
        NONE
        ```

        ## ATTEMPT_NO
        ```text
        1
        ```

        ## FAILURE_TYPE
        ```text
        none
        ```

        ## TASK_TITLE
        ```text
        Bootstrap role alias validation
        ```

        ## TASK_TYPE
        ```text
        {role}
        ```

        ## TARGET_ROLE
        ```text
        {role}
        ```

        ## REASONING_LEVEL
        ```text
        VALUE: xhigh
        OVERRIDE_REASON: NONE
        ```

        ## DEPENDENCIES
        ```text
        NONE
        ```

        ## DEPENDENCY_STATUS
        ```text
        none
        ```

        ## REQUESTED_BY_ROLE
        ```text
        NONE
        ```

        ## REQUESTED_BY_TASK
        ```text
        NONE
        ```

        ## RESEARCH_QUESTION_ID
        ```text
        NONE
        ```

        ## RESEARCH_PURPOSE
        ```text
        NONE
        ```

        ## RESEARCH_QUESTIONS
        ```text
        NONE
        ```

        ## ALLOWED_SOURCES
        ```text
        NONE
        ```

        ## FORBIDDEN_SOURCES
        ```text
        NONE
        ```

        ## EXPECTED_EVIDENCE
        ```text
        NONE
        ```

        ## EXPECTED_OUTPUT
        ```text
        NONE
        ```

        ## RETURN_TO_REQUESTER_AFTER_AUDIT_PASS
        ```text
        no
        ```

        ## RETURN_TO_ROLE_AFTER_AUDIT_PASS
        ```text
        none
        ```

        ## RETURN_TASK_AFTER_AUDIT_PASS
        ```text
        NONE
        ```

        ## PURPOSE
        ```text
        Validate role alias behavior.
        ```

        ## SOURCE_OF_TRUTH
        ```text
        NONE
        ```

        ## SCOPE_IN
        ```text
        - Validate one role alias packet.
        ```

        ## SCOPE_OUT
        ```text
        - No repository changes.
        ```

        ## REQUIRED_DOCS
        ```text
        NONE
        ```

        ## INPUTS
        ```text
        NONE
        ```

        ## READ_INPUTS
        ```text
        NONE
        ```

        ## EXPECTED_OUTPUTS
        ```text
        - Validator result.
        ```

        ## ALLOWED_FILE_CHANGES
        ```text
        - NONE
        ```

        ## FORBIDDEN_FILE_CHANGES
        ```text
        - NONE
        ```

        ## ACCEPTANCE_CRITERIA
        ```text
        - Validator accepts the packet.
        ```

        ## EVIDENCE_REQUIREMENTS
        ```text
        NONE
        ```

        ## SETUP_HOOKS
        ```text
        NONE
        ```

        ## LAUNCH_HOOKS
        ```text
        NONE
        ```

        ## RESULT_PATH
        ```text
        project-runtime/results/worker/RESULT_TASK_BOOTSTRAP_{role.upper()}_001_ATTEMPT_001.md
        ```

        ## RISK_REQUIREMENTS
        ```text
        NONE
        ```

        ## MANDATORY_WORKFLOW
        ```text
        {role}(pass) -> auditor
        ```

        ## NEXT_ROLE_ON_PASS
        ```text
        auditor
        ```

        ## NEXT_ROLE_ON_FAIL
        ```text
        orchestrator
        ```

        ## NEXT_ROLE_ON_BLOCKED
        ```text
        orchestrator
        ```

        ## NEXT_ROLE_ON_GAP
        ```text
        orchestrator
        ```

        ## AUDIT_REQUIREMENTS
        ```text
        mandatory
        ```

        ## TESTING_REQUIREMENTS
        ```text
        none
        ```

        ## DOCUMENTATION_REQUIREMENTS
        ```text
        none
        ```

        ## FILESYSTEM_GOVERNANCE
        ```text
        - No file changes.
        ```

        ## RUNTIME_GOVERNANCE
        ```text
        - No runtime changes.
        ```

        ## RESULT_FORMAT
        ```text
        agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
        ```

        ## TERMINAL_CONDITIONS
        ```text
        NONE
        ```

        ## NOTES
        ```text
        NONE
        ```
        """
    )


def run_validator(root: Path, packet_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--mode",
            "dispatch",
            "--allow-first-bootstrap",
            str(packet_path),
        ],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )


class TaskPacketRoleAliasTests(unittest.TestCase):
    def test_legacy_designer_bootstrap_packet_validates_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_dir = root / "project-runtime" / "bootstrap"
            bootstrap_dir.mkdir(parents=True)
            packet_path = bootstrap_dir / "TASK_BOOTSTRAP_DESIGNER_001.md"
            packet_path.write_text(task_packet("designer"), encoding="utf-8")

            result = run_validator(root, packet_path)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VALID:", result.stdout)
            self.assertIn("WARNING: deprecated_role_alias", result.stdout)
            self.assertIn("canonical role is solution_architect", result.stdout)

    def test_solution_architect_bootstrap_packet_validates_without_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_dir = root / "project-runtime" / "bootstrap"
            bootstrap_dir.mkdir(parents=True)
            packet_path = bootstrap_dir / "TASK_BOOTSTRAP_SOLUTION_ARCHITECT_001.md"
            packet_path.write_text(task_packet("solution_architect"), encoding="utf-8")

            result = run_validator(root, packet_path)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VALID:", result.stdout)
            self.assertNotIn("WARNING:", result.stdout)

    def test_obsolete_bootstrap_marker_fails_with_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bootstrap_dir = root / "project-runtime" / "bootstrap"
            bootstrap_dir.mkdir(parents=True)
            packet_path = bootstrap_dir / "TASK_BOOTSTRAP_SOLUTION_ARCHITECT_001.md"
            packet_path.write_text(
                task_packet("solution_architect").replace("# TASK PACKET", "# BOOTSTRAP TASK PACKET", 1),
                encoding="utf-8",
            )

            result = run_validator(root, packet_path)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("obsolete # BOOTSTRAP TASK PACKET marker", result.stdout)
            self.assertIn("TASK_KIND: bootstrap", result.stdout)


if __name__ == "__main__":
    unittest.main()
