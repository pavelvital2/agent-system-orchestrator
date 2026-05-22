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
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "design_gap"


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def copy_fixture(name: str, target: Path) -> Path:
    workspace = target / name
    shutil.copytree(FIXTURE_ROOT / "valid_workspace", workspace)
    return workspace


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def mark_question_presented(root: Path, *, legacy: bool = False) -> None:
    question_path = root / "project-docs" / "design" / "questions" / "Q-001.json"
    question = load_json(question_path)
    question["status"] = "presented_to_owner" if legacy else "presented"
    routing = question["routing"]
    assert isinstance(routing, dict)
    routing["presentation_state"] = "presented"
    write_json(question_path, question)


class DesignGovernanceCommandTests(unittest.TestCase):
    def test_design_help_exposes_required_commands(self) -> None:
        result = run_aso("design", "--help")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("verify", result.stdout)
        self.assertIn("questions", result.stdout)
        self.assertIn("decision", result.stdout)
        self.assertIn("gate", result.stdout)

    def test_valid_workspace_verifies_and_routes_next_question(self) -> None:
        root = FIXTURE_ROOT / "valid_workspace"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "question.json"

            verify = run_aso("design", "verify", "--root", str(root), "--strict")
            next_question = run_aso("design", "questions", "next", "--root", str(root), "--json-out", str(out))
            gate = run_aso("design", "gate", "verify", "--root", str(root), "--stage", "DESIGN", "--strict")

            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            self.assertIn("ASO design verify: PASSED", verify.stdout)
            self.assertEqual(next_question.returncode, 0, next_question.stdout + next_question.stderr)
            self.assertEqual(load_json(out)["question_id"], "Q-001")
            self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)

    def test_questions_next_does_not_route_when_question_is_already_presented(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture("already_presented", Path(tmp))
            mark_question_presented(root)
            out = Path(tmp) / "question.json"

            result = run_aso("design", "questions", "next", "--root", str(root), "--json-out", str(out))

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("DG4_ROUTING_003", result.stdout)
            self.assertEqual(load_json(out)["status"], "failed")
            self.assertEqual(load_json(root / "project-docs" / "design" / "questions" / "Q-001.json")["status"], "presented")

    def test_blocking_gate_fails_when_unanswered_gap_crosses_stage(self) -> None:
        root = FIXTURE_ROOT / "blocked_workspace"

        result = run_aso("design", "gate", "verify", "--root", str(root), "--stage", "IMPLEMENTATION", "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("DG4_GATE_002", result.stdout)
        self.assertIn("GAP-001", result.stdout)

    def test_fake_owner_answer_reference_fails_verify_and_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture("fake_answer_reference", Path(tmp))
            register_path = root / "project-docs" / "design" / "gap_register.json"
            register = load_json(register_path)
            register["gaps"][0]["owner_answer_record_id"] = "ANS-DOES-NOT-EXIST"  # type: ignore[index]
            write_json(register_path, register)

            verify = run_aso("design", "verify", "--root", str(root), "--strict")
            gate = run_aso("design", "gate", "verify", "--root", str(root), "--stage", "IMPLEMENTATION", "--strict")

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            self.assertIn("DG4_ANSWER_005", verify.stdout)
            self.assertEqual(gate.returncode, 1, gate.stdout + gate.stderr)
            self.assertIn("DG4_ANSWER_005", gate.stdout)
            self.assertIn("DG4_GATE_002", gate.stdout)

    def test_invalid_blocking_type_fails_verify_and_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture("invalid_blocking_type", Path(tmp))
            register_path = root / "project-docs" / "design" / "gap_register.json"
            register = load_json(register_path)
            register["gaps"][0]["blocking_type"] = "bogus"  # type: ignore[index]
            write_json(register_path, register)

            verify = run_aso("design", "verify", "--root", str(root), "--strict")
            gate = run_aso("design", "gate", "verify", "--root", str(root), "--stage", "IMPLEMENTATION", "--strict")

            self.assertEqual(verify.returncode, 1, verify.stdout + verify.stderr)
            self.assertIn("DG4_SCHEMA_GAP_009", verify.stdout)
            self.assertEqual(gate.returncode, 1, gate.stdout + gate.stderr)
            self.assertIn("DG4_SCHEMA_GAP_009", gate.stdout)

    def test_matching_owner_answer_unblocks_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture("answered_gap", Path(tmp))
            answers_dir = root / "project-runtime" / "owner-decisions"
            answers_dir.mkdir(parents=True)
            write_json(
                answers_dir / "ANS-001-A.json",
                {
                    "schema_version": "1.0.0",
                    "answer_record_id": "ANS-001-A",
                    "project_id": "fixture-project",
                    "question_id": "Q-001",
                    "gap_id": "GAP-001",
                    "question_ref": "project-docs/design/questions/Q-001.json",
                    "selected_option": "A",
                    "owner_answer_summary": "Owner selected option A for Q-001.",
                    "answered_by": "owner",
                    "answered_at": "2026-05-22T00:00:00Z",
                    "status": "received",
                    "design_update_required": True,
                    "design_update_ref": "NONE",
                    "accepted_source_of_truth_update": "PENDING",
                    "audit_refs": "NONE",
                },
            )

            result = run_aso("design", "gate", "verify", "--root", str(root), "--stage", "IMPLEMENTATION", "--strict")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("DG4_GATE_002", result.stdout)

    def test_decision_record_dry_run_ready_card_fails_without_writing(self) -> None:
        root = FIXTURE_ROOT / "valid_workspace"
        target = root / "project-runtime" / "owner-decisions" / "ANS-001-A.json"

        result = run_aso(
            "design",
            "decision",
            "record",
            "--root",
            str(root),
            "--question-id",
            "Q-001",
            "--answer",
            "A",
            "--dry-run",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("ASO design decision record: FAILED", result.stdout)
        self.assertIn("status ready_for_owner is not eligible", result.stdout)
        self.assertFalse(target.exists())

    def test_decision_record_dry_run_presented_card_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture("presented_dry_run", Path(tmp))
            mark_question_presented(root)
            target = root / "project-runtime" / "owner-decisions" / "ANS-001-A.json"

            result = run_aso(
                "design",
                "decision",
                "record",
                "--root",
                str(root),
                "--question-id",
                "Q-001",
                "--answer",
                "A",
                "--dry-run",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO design decision record: DRY_RUN", result.stdout)
            self.assertFalse(target.exists())

    def test_decision_record_confirm_write_writes_owner_decision_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture("confirm_write", Path(tmp))
            mark_question_presented(root)

            result = run_aso(
                "design",
                "decision",
                "record",
                "--root",
                str(root),
                "--question-id",
                "Q-001",
                "--answer",
                "A",
                "--confirm-write",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            written = root / "project-runtime" / "owner-decisions" / "ANS-001-A.json"
            self.assertTrue(written.exists())
            payload = load_json(written)
            self.assertEqual(payload["question_id"], "Q-001")
            self.assertEqual(payload["gap_id"], "GAP-001")

    def test_decision_record_accepts_legacy_presented_with_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture("legacy_presented", Path(tmp))
            mark_question_presented(root, legacy=True)

            result = run_aso(
                "design",
                "decision",
                "record",
                "--root",
                str(root),
                "--question-id",
                "Q-001",
                "--answer",
                "A",
                "--dry-run",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO design decision record: DRY_RUN", result.stdout)

    def test_decision_record_rejects_legacy_presented_without_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture("legacy_presented_without_evidence", Path(tmp))
            question_path = root / "project-docs" / "design" / "questions" / "Q-001.json"
            question = load_json(question_path)
            question["status"] = "presented_to_owner"
            write_json(question_path, question)

            result = run_aso(
                "design",
                "decision",
                "record",
                "--root",
                str(root),
                "--question-id",
                "Q-001",
                "--answer",
                "A",
                "--dry-run",
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("DG4_STATUS_002", result.stdout)

    def test_negative_question_cases_fail_with_expected_rules(self) -> None:
        cases = {
            "technical_question": ("question", "Should we use PostgreSQL or SQLite?", "DG4_QUESTION_008"),
            "missing_options": ("options", [], "DG4_QUESTION_002"),
            "missing_recommendation": ("recommended_option", "", "DG4_QUESTION_004"),
            "missing_reason": ("recommendation_reason", "", "DG4_QUESTION_006"),
            "missing_blocking_stage": ("blocking_stage", "not_applicable", "DG4_QUESTION_007"),
        }
        for name, (field, value, rule_id) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = copy_fixture(name, Path(tmp))
                question_path = root / "project-docs" / "design" / "questions" / "Q-001.json"
                question = load_json(question_path)
                question[field] = value
                write_json(question_path, question)

                result = run_aso("design", "verify", "--root", str(root), "--strict")

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(rule_id, result.stdout)

    def test_negative_linkage_and_audit_cases_fail_with_expected_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture("missing_question_link", Path(tmp))
            register_path = root / "project-docs" / "design" / "gap_register.json"
            register = load_json(register_path)
            register["gaps"][0]["question_card_id"] = "NONE"  # type: ignore[index]
            write_json(register_path, register)
            result = run_aso("design", "verify", "--root", str(root), "--strict")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("DG4_LINK_001", result.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture("question_missing_gap", Path(tmp))
            question_path = root / "project-docs" / "design" / "questions" / "Q-001.json"
            question = load_json(question_path)
            question["gap_id"] = "GAP-404"
            write_json(question_path, question)
            result = run_aso("design", "verify", "--root", str(root), "--strict")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("DG4_LINK_003", result.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            root = copy_fixture("missing_audit", Path(tmp))
            question_path = root / "project-docs" / "design" / "questions" / "Q-001.json"
            question = load_json(question_path)
            question["audit"] = {"status": "pending", "evidence_ref": "NONE"}
            write_json(question_path, question)
            result = run_aso("design", "verify", "--root", str(root), "--strict")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("DG4_AUDIT_001", result.stdout)

    def test_unknown_owner_answer_question_fails(self) -> None:
        result = run_aso(
            "design",
            "decision",
            "record",
            "--root",
            str(FIXTURE_ROOT / "valid_workspace"),
            "--question-id",
            "Q-404",
            "--answer",
            "A",
            "--dry-run",
        )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("unknown question_id: Q-404", result.stdout)


if __name__ == "__main__":
    unittest.main()
