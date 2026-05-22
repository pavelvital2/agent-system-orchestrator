from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "context_pack"


NEGATIVE_FIXTURES = {
    "bad_context_pack_archive_doc.json": "CPP-002",
    "bad_context_pack_broad_directory.json": "CPP-006",
    "bad_context_pack_deprecated_doc.json": "CPP-003",
    "bad_context_pack_forbidden_doc.json": "CPP-004",
    "bad_context_pack_missing_required_fields.json": "CPS-002",
    "bad_context_pack_budget_overflow.json": "CPB-001",
    "bad_context_pack_path_escape.json": "CPP-001",
}


def run_validate_context_pack(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "validate-context-pack", *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


class ValidateContextPackCommandTests(unittest.TestCase):
    def test_valid_context_pack_fixture_passes_strict(self) -> None:
        fixture = FIXTURE_ROOT / "valid_context_pack.json"
        mtime_before = fixture.stat().st_mtime_ns

        result = run_validate_context_pack(str(fixture), "--root", str(REPO_ROOT), "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ASO validate-context-pack: PASSED", result.stdout)
        self.assertEqual(fixture.stat().st_mtime_ns, mtime_before)

    def test_negative_context_pack_fixtures_fail_with_expected_rule_ids(self) -> None:
        for filename, rule_id in NEGATIVE_FIXTURES.items():
            with self.subTest(filename=filename):
                fixture = FIXTURE_ROOT / filename
                result = run_validate_context_pack(str(fixture), "--root", str(REPO_ROOT), "--strict")

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("ASO validate-context-pack: FAILED", result.stdout)
                self.assertIn(rule_id, result.stdout)

    def test_agent_system_directory_context_fails_strict_validation(self) -> None:
        fixture = FIXTURE_ROOT / "bad_context_pack_broad_directory.json"

        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "broad-directory-report.json"
            result = run_validate_context_pack(
                str(fixture),
                "--root",
                str(REPO_ROOT),
                "--strict",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("ASO validate-context-pack: FAILED", result.stdout)
            payload = json.loads(json_out.read_text(encoding="utf-8"))

        rule_ids = {finding["rule_id"] for finding in payload["findings"]}
        fields = {finding["field"] for finding in payload["findings"] if finding["rule_id"] == "CPP-006"}
        self.assertIn("CPP-006", rule_ids)
        self.assertIn("required_docs[0].path", fields)
        self.assertIn("source_of_truth[0]", fields)

    def test_bounded_fixture_directory_context_passes_strict_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context_pack = Path(tmp) / "bounded-directory-context.json"
            context_pack.write_text(
                json.dumps(
                    {
                        "task_id": "TASK_ASO_STAGE3_003A_BOUNDED_DIRECTORY",
                        "required_docs": [
                            {
                                "path": "agent-system/tests/fixtures/context_pack/",
                                "sections": ["Fixture coverage"],
                                "why_needed": "Small fixture directory for validator regression coverage.",
                            }
                        ],
                        "forbidden_docs": ["project-archive/", "project-input/", "project-runtime/"],
                        "source_of_truth": ["agent-system/tests/fixtures/context_pack/"],
                        "context_budget": {
                            "max_docs": 1,
                            "max_sections_per_doc": 2,
                            "max_chars_total": 1000,
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = run_validate_context_pack(str(context_pack), "--root", str(REPO_ROOT), "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ASO validate-context-pack: PASSED", result.stdout)

    def test_accepted_packages_and_rendered_views_are_consumable_runtime_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            accepted = root / "project-runtime/artifacts/accepted/TASK_DEMO/manifest.json"
            rendered = root / "project-runtime/rendered/TASK_DEMO/context.md"
            accepted.parent.mkdir(parents=True)
            rendered.parent.mkdir(parents=True)
            accepted.write_text('{"status":"accepted"}\n', encoding="utf-8")
            rendered.write_text("# Rendered context\n", encoding="utf-8")
            context_pack = Path(tmp) / "runtime-context.json"
            context_pack.write_text(
                json.dumps(
                    {
                        "task_id": "TASK_DEMO",
                        "required_docs": [
                            {
                                "path": "project-runtime/artifacts/accepted/TASK_DEMO/manifest.json",
                                "sections": ["Accepted package"],
                                "why_needed": "Accepted package evidence for downstream work.",
                            },
                            {
                                "path": "project-runtime/rendered/TASK_DEMO/context.md",
                                "sections": ["Rendered context"],
                                "why_needed": "Rendered view for bounded downstream context.",
                            },
                        ],
                        "forbidden_docs": ["project-runtime/"],
                        "source_of_truth": [
                            "project-runtime/artifacts/accepted/TASK_DEMO/manifest.json",
                            "project-runtime/rendered/TASK_DEMO/context.md",
                        ],
                        "accepted_artifact_packages": [
                            "project-runtime/artifacts/accepted/TASK_DEMO/manifest.json"
                        ],
                        "rendered_views": ["project-runtime/rendered/TASK_DEMO/context.md"],
                        "context_budget": {
                            "max_docs": 2,
                            "max_sections_per_doc": 1,
                            "max_chars_total": 2000,
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = run_validate_context_pack(str(context_pack), "--root", str(root), "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ASO validate-context-pack: PASSED", result.stdout)

    def test_candidate_packages_are_not_consumable_runtime_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            candidate = root / "project-runtime/artifacts/candidates/TASK_DEMO/manifest.json"
            candidate.parent.mkdir(parents=True)
            candidate.write_text('{"status":"candidate"}\n', encoding="utf-8")
            context_pack = Path(tmp) / "candidate-context.json"
            context_pack.write_text(
                json.dumps(
                    {
                        "task_id": "TASK_DEMO",
                        "required_docs": [
                            {
                                "path": "project-runtime/artifacts/candidates/TASK_DEMO/manifest.json",
                                "sections": ["Candidate package"],
                                "why_needed": "Candidate package should not be consumable.",
                            }
                        ],
                        "forbidden_docs": ["project-runtime/"],
                        "source_of_truth": ["project-runtime/artifacts/candidates/TASK_DEMO/manifest.json"],
                        "accepted_artifact_packages": [
                            "project-runtime/artifacts/candidates/TASK_DEMO/manifest.json"
                        ],
                        "context_budget": {
                            "max_docs": 1,
                            "max_sections_per_doc": 1,
                            "max_chars_total": 2000,
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = run_validate_context_pack(str(context_pack), "--root", str(root), "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("CPP-007", result.stdout)

    def test_rejected_packages_are_not_consumable_runtime_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            rejected = root / "project-runtime/artifacts/rejected/TASK_DEMO/manifest.json"
            rejected.parent.mkdir(parents=True)
            rejected.write_text('{"status":"rejected"}\n', encoding="utf-8")
            context_pack = Path(tmp) / "rejected-context.json"
            context_pack.write_text(
                json.dumps(
                    {
                        "task_id": "TASK_DEMO",
                        "required_docs": [
                            {
                                "path": "project-runtime/artifacts/rejected/TASK_DEMO/manifest.json",
                                "sections": ["Rejected package"],
                                "why_needed": "Rejected package should not be consumable.",
                            }
                        ],
                        "forbidden_docs": ["project-runtime/"],
                        "source_of_truth": ["project-runtime/artifacts/rejected/TASK_DEMO/manifest.json"],
                        "accepted_artifact_packages": [
                            "project-runtime/artifacts/rejected/TASK_DEMO/manifest.json"
                        ],
                        "context_budget": {
                            "max_docs": 1,
                            "max_sections_per_doc": 1,
                            "max_chars_total": 2000,
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = run_validate_context_pack(str(context_pack), "--root", str(root), "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("CPP-007", result.stdout)

    def test_explicitly_forbidden_accepted_and_rendered_paths_fail_validation(self) -> None:
        cases = (
            (
                "project-runtime/artifacts/accepted/TASK_DEMO/manifest.json",
                "project-runtime/artifacts/accepted/",
                "accepted_artifact_packages",
            ),
            (
                "project-runtime/rendered/TASK_DEMO/context.md",
                "project-runtime/rendered/",
                "rendered_views",
            ),
        )
        for runtime_path, forbidden_path, runtime_field in cases:
            with self.subTest(runtime_path=runtime_path), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "workspace"
                runtime_doc = root / runtime_path
                runtime_doc.parent.mkdir(parents=True)
                runtime_doc.write_text("# Runtime context\n", encoding="utf-8")
                context_pack = Path(tmp) / "explicit-runtime-forbidden.json"
                payload = {
                    "task_id": "TASK_DEMO",
                    "required_docs": [
                        {
                            "path": runtime_path,
                            "sections": ["Runtime context"],
                            "why_needed": "Runtime context explicitly forbidden by this pack.",
                        }
                    ],
                    "forbidden_docs": ["project-runtime/", forbidden_path],
                    "source_of_truth": [runtime_path],
                    runtime_field: [runtime_path],
                    "context_budget": {
                        "max_docs": 1,
                        "max_sections_per_doc": 1,
                        "max_chars_total": 2000,
                    },
                }
                context_pack.write_text(json.dumps(payload, indent=2), encoding="utf-8")

                result = run_validate_context_pack(str(context_pack), "--root", str(root), "--strict")

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("ASO validate-context-pack: FAILED", result.stdout)
                self.assertIn("CPP-004", result.stdout)

    def test_explicitly_forbidden_runtime_fields_fail_even_when_required_docs_are_allowed(self) -> None:
        cases = (
            (
                "project-runtime/artifacts/accepted/TASK_DEMO/manifest.json",
                "project-runtime/artifacts/accepted/TASK_DEMO/",
                "accepted_artifact_packages",
            ),
            (
                "project-runtime/rendered/TASK_DEMO/context.md",
                "project-runtime/rendered/TASK_DEMO/",
                "rendered_views",
            ),
        )
        for runtime_path, forbidden_path, runtime_field in cases:
            with self.subTest(runtime_field=runtime_field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "workspace"
                runtime_doc = root / runtime_path
                source_doc = root / "docs/source.md"
                runtime_doc.parent.mkdir(parents=True)
                source_doc.parent.mkdir(parents=True)
                runtime_doc.write_text("# Runtime context\n", encoding="utf-8")
                source_doc.write_text("# Source context\n", encoding="utf-8")
                context_pack = Path(tmp) / "runtime-field-forbidden.json"
                payload = {
                    "task_id": "TASK_DEMO",
                    "required_docs": [
                        {
                            "path": "docs/source.md",
                            "sections": ["Source context"],
                            "why_needed": "Allowed source context for this task.",
                        }
                    ],
                    "forbidden_docs": ["project-runtime/", forbidden_path],
                    "source_of_truth": ["docs/source.md"],
                    runtime_field: [runtime_path],
                    "context_budget": {
                        "max_docs": 1,
                        "max_sections_per_doc": 1,
                        "max_chars_total": 2000,
                    },
                }
                context_pack.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                json_out = Path(tmp) / "runtime-field-forbidden-report.json"

                result = run_validate_context_pack(
                    str(context_pack),
                    "--root",
                    str(root),
                    "--strict",
                    "--json-out",
                    str(json_out),
                )
                report = json.loads(json_out.read_text(encoding="utf-8"))

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("ASO validate-context-pack: FAILED", result.stdout)
                self.assertIn("CPP-004", result.stdout)
                self.assertEqual(report["findings"][0]["field"], f"{runtime_field}[0]")

    def test_json_output_is_parseable_and_deterministic(self) -> None:
        fixture = FIXTURE_ROOT / "bad_context_pack_forbidden_doc.json"
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "validate-context-pack.json"

            first = run_validate_context_pack(
                str(fixture),
                "--root",
                str(REPO_ROOT),
                "--strict",
                "--json-out",
                str(json_out),
            )
            self.assertEqual(first.returncode, 1, first.stdout + first.stderr)
            payload = json.loads(json_out.read_text(encoding="utf-8"))

            second_json = Path(tmp) / "validate-context-pack-second.json"
            second = run_validate_context_pack(
                str(fixture),
                "--root",
                str(REPO_ROOT),
                "--strict",
                "--json-out",
                str(second_json),
            )
            self.assertEqual(second.returncode, 1, second.stdout + second.stderr)

            self.assertEqual(payload, json.loads(second_json.read_text(encoding="utf-8")))
            self.assertEqual(payload["command"], "validate-context-pack")
            self.assertEqual(payload["status"], "failed")
            self.assertEqual(payload["summary"]["errors"], 2)
            self.assertEqual(payload["findings"][0]["rule_id"], "CPP-004")
            self.assertTrue(payload["read_only"])


if __name__ == "__main__":
    unittest.main()
