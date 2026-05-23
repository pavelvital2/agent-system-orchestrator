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


class ArtifactCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="aso-artifact-cli-"))
        self.root = self.tmpdir / "workspace"
        self.root.mkdir()
        self.manifest = {
            "artifact_package_schema_version": "1.1.0",
            "artifact_type": "RESULT",
            "artifact_id": "RESULT_TASK_DEMO_ATTEMPT_001",
            "task_id": "TASK_DEMO",
            "role": "developer",
            "attempt_no": 1,
            "status": "pass",
            "main_document": "RESULT_TASK_DEMO_ATTEMPT_001.md",
            "structured_artifacts": [
                "structured/result_package.json",
            ],
            "evidence_refs": "NONE",
            "created_at": "2026-05-22T00:00:00Z",
            "producer": {
                "agent_instance_id": "developer_TASK_DEMO_attempt_001",
                "role": "developer",
            },
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def _write_candidate(self, relpath: str = "project-runtime/artifacts/candidates/TASK_DEMO/PACKAGE") -> Path:
        path = self.root / relpath
        package_root = path.parent if path.name == "manifest.json" else path
        if package_root.exists():
            shutil.rmtree(package_root)
        package_root.mkdir(parents=True, exist_ok=True)
        (package_root / "RESULT_TASK_DEMO_ATTEMPT_001.md").write_text("RESULT:\nSTATUS: pass\n", encoding="utf-8")
        structured_dir = package_root / "structured"
        structured_dir.mkdir()
        (structured_dir / "result_package.json").write_text(
            '{"package_id":"RESULT_PACKAGE_TASK_DEMO_ATTEMPT_001"}\n',
            encoding="utf-8",
        )
        (package_root / "evidence").mkdir()
        manifest_path = package_root / "manifest.json"
        manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8")
        return manifest_path

    def _validate_candidate(self, candidate: Path, *extra: str) -> dict[str, object]:
        code, stdout, _stderr = self._run(
            [
                "artifact",
                "validate",
                "--root",
                str(self.root),
                "--artifact",
                str(candidate),
                "--format",
                "json",
                *extra,
            ]
        )
        self.assertEqual(code, 1)
        return json.loads(stdout)

    def _runtime_snapshot(self) -> dict[str, str]:
        runtime = self.root / "project-runtime"
        if not runtime.exists():
            return {}
        return {
            path.relative_to(runtime).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted(runtime.rglob("*"))
            if path.is_file()
        }

    def test_artifact_validate_accepts_valid_manifest(self) -> None:
        candidate = self._write_candidate()

        code, stdout, stderr = self._run(
            [
                "artifact",
                "validate",
                "--root",
                str(self.root),
                "--artifact",
                str(candidate),
                "--format",
                "json",
            ]
        )

        self.assertEqual(code, 0, stderr)
        report = json.loads(stdout)
        self.assertEqual(report["status"], "pass")
        self.assertFalse(report["mutations_performed"])

    def test_artifact_validate_negative_manifest_fixture_cases_are_blocked(self) -> None:
        cases = (
            (
                "malformed manifest JSON",
                lambda candidate: candidate.write_text('{"artifact_type": "RESULT",', encoding="utf-8"),
                (),
                "ARTIFACT_VALIDATE_JSON_001",
            ),
            (
                "wrong artifact_type",
                lambda candidate: candidate.write_text(
                    json.dumps({**self.manifest, "artifact_type": "TASK_PACKET"}), encoding="utf-8"
                ),
                ("--type", "RESULT"),
                "ARTIFACT_VALIDATE_TYPE_001",
            ),
            (
                "wrong task_id",
                lambda candidate: candidate.write_text(
                    json.dumps({**self.manifest, "task_id": "TASK_OTHER"}), encoding="utf-8"
                ),
                ("--task-id", "TASK_DEMO"),
                "ARTIFACT_VALIDATE_TASK_001",
            ),
            (
                "wrong role",
                lambda candidate: candidate.write_text(
                    json.dumps({**self.manifest, "role": "tester"}), encoding="utf-8"
                ),
                ("--role", "developer"),
                "ARTIFACT_VALIDATE_ROLE_001",
            ),
            (
                "invalid status",
                lambda candidate: candidate.write_text(
                    json.dumps({**self.manifest, "status": "accepted"}), encoding="utf-8"
                ),
                (),
                "ARTIFACT_VALIDATE_SCHEMA_009",
            ),
            (
                "missing main document",
                lambda candidate: candidate.write_text(
                    json.dumps({**self.manifest, "main_document": "package/MISSING.md"}), encoding="utf-8"
                ),
                (),
                "ARTIFACT_VALIDATE_PATH_001",
            ),
            (
                "malformed structured JSON",
                lambda candidate: (
                    (candidate.parent / "structured" / "result_package.json").write_text('{"package_id":', encoding="utf-8"),
                    candidate.write_text(json.dumps(self.manifest), encoding="utf-8"),
                ),
                (),
                "ARTIFACT_VALIDATE_JSON_003",
            ),
            (
                "evidence path escape",
                lambda candidate: candidate.write_text(
                    json.dumps({**self.manifest, "evidence_refs": ["package/../secret.txt"]}), encoding="utf-8"
                ),
                (),
                "ARTIFACT_VALIDATE_PATH_002",
            ),
        )
        for _label, mutate, extra, rule_id in cases:
            with self.subTest(case=_label):
                candidate = self._write_candidate()
                mutate(candidate)
                report = self._validate_candidate(candidate, *extra)
                self.assertEqual(report["status"], "blocked")
                self.assertIn(rule_id, {finding["rule_id"] for finding in report["findings"]})

    def test_artifact_validate_missing_manifest_is_blocked(self) -> None:
        missing = self.root / "project-runtime/artifacts/candidates/TASK_DEMO/manifest.json"

        report = self._validate_candidate(missing)

        self.assertEqual(report["status"], "blocked")
        self.assertIn("ARTIFACT_VALIDATE_READ_001", {finding["rule_id"] for finding in report["findings"]})

    def test_artifact_validate_spec_form_writes_json_out_without_runtime_mutation(self) -> None:
        candidate = self._write_candidate()
        before = self._runtime_snapshot()
        out = self.tmpdir / "validation.json"

        code, stdout, stderr = self._run(
            [
                "artifact",
                "validate",
                "--root",
                str(self.root),
                "--package",
                str(candidate),
                "--type",
                "RESULT",
                "--strict",
                "--json-out",
                str(out),
            ]
        )

        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, "")
        self.assertEqual(before, self._runtime_snapshot())
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["strict"])
        self.assertTrue(report["read_only"])
        self.assertFalse(report["mutations_performed"])

    def test_artifact_validate_json_out_may_write_explicit_runtime_report_only(self) -> None:
        candidate = self._write_candidate()
        out = self.root / "project-runtime/reports/validation.json"

        code, _stdout, stderr = self._run(
            [
                "artifact",
                "validate",
                "--root",
                str(self.root),
                "--package",
                str(candidate),
                "--json-out",
                str(out),
            ]
        )

        self.assertEqual(code, 0, stderr)
        self.assertTrue(out.exists())
        runtime_files = sorted(self._runtime_snapshot())
        self.assertEqual(
            runtime_files,
            [
                "artifacts/candidates/TASK_DEMO/PACKAGE/RESULT_TASK_DEMO_ATTEMPT_001.md",
                "artifacts/candidates/TASK_DEMO/PACKAGE/manifest.json",
                "artifacts/candidates/TASK_DEMO/PACKAGE/structured/result_package.json",
                "reports/validation.json",
            ],
        )

    def test_artifact_validate_rejects_workspace_local_package_paths(self) -> None:
        candidate = self._write_candidate()
        bad_manifest = dict(self.manifest)
        bad_manifest["main_document"] = "project-runtime/results/worker/RESULT_TASK_BAD.md"
        candidate.write_text(json.dumps(bad_manifest), encoding="utf-8")

        code, stdout, _stderr = self._run(
            [
                "artifact",
                "validate",
                "--root",
                str(self.root),
                "--artifact",
                str(candidate),
                "--format",
                "json",
            ]
        )

        self.assertEqual(code, 1)
        report = json.loads(stdout)
        messages = "\n".join(finding["details"] for finding in report["findings"])
        self.assertIn("project-runtime", messages)

    def test_artifact_accept_requires_confirm_write_and_defaults_to_blocked_dry_run(self) -> None:
        self._write_candidate()

        code, stdout, _stderr = self._run(
            [
                "artifact",
                "accept",
                "--root",
                str(self.root),
                "--artifact",
                "project-runtime/artifacts/candidates/TASK_DEMO/PACKAGE",
                "--format",
                "json",
            ]
        )

        self.assertEqual(code, 1)
        report = json.loads(stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["dry_run"])
        self.assertFalse((self.root / "project-runtime/artifacts/accepted/TASK_DEMO/PACKAGE").exists())

    def test_artifact_accept_confirm_write_copies_candidate_without_deleting_source(self) -> None:
        candidate = self._write_candidate()
        out = self.tmpdir / "accept-report.json"

        code, stdout, stderr = self._run(
            [
                "artifact",
                "accept",
                "--root",
                str(self.root),
                "--package",
                "project-runtime/artifacts/candidates/TASK_DEMO/PACKAGE/manifest.json",
                "--confirm-write",
                "--json-out",
                str(out),
            ]
        )

        self.assertEqual(code, 0, stderr)
        self.assertIn("ASO artifact accept: WRITTEN", stdout)
        report = json.loads(out.read_text(encoding="utf-8"))
        accepted = self.root / "project-runtime/artifacts/accepted/TASK_DEMO/PACKAGE/manifest.json"
        self.assertEqual(report["status"], "written")
        self.assertTrue(candidate.exists())
        self.assertEqual(json.loads(accepted.read_text(encoding="utf-8")), self.manifest)
        self.assertTrue((accepted.parent / "RESULT_TASK_DEMO_ATTEMPT_001.md").exists())
        self.assertTrue((accepted.parent / "structured" / "result_package.json").exists())
        self.assertGreaterEqual(len(report["receipt"]["inventory"]), 3)
        self.assertEqual(report["receipt"]["artifact_id"], "RESULT_TASK_DEMO_ATTEMPT_001")
        self.assertEqual(report["receipt_ref"], "project-runtime/receipts/artifacts/TASK_DEMO/RESULT_TASK_DEMO_ATTEMPT_001.acceptance.json")
        self.assertTrue((self.root / report["receipt_ref"]).exists())
        events = [
            json.loads(line)
            for line in (self.root / "project-runtime/agents/instances.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(events[0]["event_type"], "ARTIFACT_ACCEPTED")
        self.assertEqual(events[0]["artifact_id"], "RESULT_TASK_DEMO_ATTEMPT_001")
        self.assertEqual(events[0]["receipt_ref"], report["receipt_ref"])

    def test_artifact_reject_spec_form_uses_rejected_bucket(self) -> None:
        self._write_candidate()
        out = self.tmpdir / "reject-report.json"

        code, stdout, stderr = self._run(
            [
                "artifact",
                "reject",
                "--root",
                str(self.root),
                "--package",
                "project-runtime/artifacts/candidates/TASK_DEMO/PACKAGE",
                "--reason",
                "audit failed",
                "--confirm-write",
                "--json-out",
                str(out),
            ]
        )

        self.assertEqual(code, 0, stderr)
        self.assertIn("ASO artifact reject: WRITTEN", stdout)
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["target"], "project-runtime/artifacts/rejected/TASK_DEMO/PACKAGE")
        self.assertEqual(report["reason"], "audit failed")
        self.assertTrue((self.root / "project-runtime/artifacts/rejected/TASK_DEMO/PACKAGE/manifest.json").exists())
        self.assertTrue((self.root / report["rejection_report_ref"]).exists())

    def test_artifact_list_and_render_are_read_only(self) -> None:
        self._write_candidate()

        list_code, list_stdout, list_stderr = self._run(
            ["artifact", "list", "--root", str(self.root), "--format", "json"]
        )
        render_code, render_stdout, render_stderr = self._run(
            ["artifact", "render", "--root", str(self.root), "--format", "markdown"]
        )

        self.assertEqual(list_code, 0, list_stderr)
        self.assertEqual(render_code, 0, render_stderr)
        self.assertEqual(json.loads(list_stdout)["summary"]["count"], 3)
        self.assertIn("ASO Artifact Storage Report", render_stdout)

    def test_artifact_render_spec_form_writes_out_without_confirm_write(self) -> None:
        self._write_candidate()
        out = self.tmpdir / "artifacts.md"

        code, stdout, stderr = self._run(
            [
                "artifact",
                "render",
                "--root",
                str(self.root),
                "--package",
                "project-runtime/artifacts/candidates/TASK_DEMO/PACKAGE",
                "--format",
                "markdown",
                "--out",
                str(out),
            ]
        )

        self.assertEqual(code, 0, stderr)
        self.assertIn("ASO artifact render written:", stdout)
        self.assertIn("project-runtime/artifacts/candidates/TASK_DEMO/PACKAGE", out.read_text(encoding="utf-8"))

    def test_artifact_list_spec_form_filters_state(self) -> None:
        self._write_candidate()
        accepted = self.root / "project-runtime/artifacts/accepted/TASK_DEMO/PACKAGE"
        shutil.copytree(self.root / "project-runtime/artifacts/candidates/TASK_DEMO/PACKAGE", accepted)

        code, stdout, stderr = self._run(
            [
                "artifact",
                "list",
                "--root",
                str(self.root),
                "--state",
                "candidates",
            ]
        )

        self.assertEqual(code, 0, stderr)
        self.assertIn("project-runtime/artifacts/candidates/TASK_DEMO/PACKAGE/manifest.json", stdout)
        self.assertNotIn("project-runtime/artifacts/accepted/TASK_DEMO/PACKAGE/manifest.json", stdout)


if __name__ == "__main__":
    unittest.main()
