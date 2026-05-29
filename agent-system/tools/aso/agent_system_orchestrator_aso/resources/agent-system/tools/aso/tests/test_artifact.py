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


class ArtifactCommandContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="aso-artifact-contract-"))
        self.root = self.tmpdir / "workspace"
        self.root.mkdir()
        self.package_root = self.root / "project-runtime/artifacts/candidates/TASK_DEMO"
        self.manifest = {
            "artifact_package_schema_version": "1.1.0",
            "artifact_type": "RESULT",
            "artifact_id": "RESULT_TASK_DEMO_ATTEMPT_001",
            "task_id": "TASK_DEMO",
            "role": "developer",
            "attempt_no": 1,
            "status": "pass",
            "main_document": "RESULT_TASK_DEMO_ATTEMPT_001.md",
            "structured_artifacts": "NONE",
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

    def _write_candidate(self) -> Path:
        self.package_root.mkdir(parents=True)
        (self.package_root / "RESULT_TASK_DEMO_ATTEMPT_001.md").write_text("RESULT:\nSTATUS: pass\n", encoding="utf-8")
        manifest_path = self.package_root / "manifest.json"
        manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8")
        return manifest_path

    def test_validate_accepts_manifest_path_and_package_directory(self) -> None:
        manifest_path = self._write_candidate()

        for package_arg in (str(manifest_path), str(self.package_root)):
            with self.subTest(package=package_arg):
                code, stdout, stderr = self._run(
                    [
                        "artifact",
                        "validate",
                        "--root",
                        str(self.root),
                        "--package",
                        package_arg,
                        "--format",
                        "json",
                    ]
                )

                self.assertEqual(code, 0, stderr)
                report = json.loads(stdout)
                self.assertEqual(report["status"], "pass")
                self.assertEqual(report["manifest"], str(manifest_path))
                self.assertEqual(report["requested_write_mode"], "read_only")
                self.assertEqual(report["actual_read_outcome"], "completed")
                self.assertEqual(report["actual_write_outcome"], "not_requested")
                self.assertFalse(report["mutations_performed"])

    def test_accept_dry_run_reports_requested_mode_blocker_and_outcomes(self) -> None:
        self._write_candidate()

        code, stdout, stderr = self._run(
            [
                "artifact",
                "accept",
                "--root",
                str(self.root),
                "--package",
                "project-runtime/artifacts/candidates/TASK_DEMO/manifest.json",
                "--format",
                "json",
            ]
        )

        self.assertEqual(code, 1, stderr)
        report = json.loads(stdout)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["requested_write_mode"], "dry_run")
        self.assertEqual(report["actual_read_outcome"], "completed")
        self.assertEqual(report["actual_write_outcome"], "not_requested")
        self.assertIn("--confirm-write is required", report["blocked_reason"])
        self.assertFalse(report["mutations_performed"])

    def test_accept_confirm_write_reports_actual_write_outcome(self) -> None:
        self._write_candidate()

        code, stdout, stderr = self._run(
            [
                "artifact",
                "accept",
                "--root",
                str(self.root),
                "--package",
                "project-runtime/artifacts/candidates/TASK_DEMO/manifest.json",
                "--confirm-write",
                "--format",
                "json",
            ]
        )

        self.assertEqual(code, 0, stderr)
        report = json.loads(stdout)
        self.assertEqual(report["status"], "written")
        self.assertEqual(report["requested_write_mode"], "confirmed_write")
        self.assertEqual(report["actual_read_outcome"], "completed")
        self.assertEqual(report["actual_write_outcome"], "completed")
        self.assertIsNone(report["blocked_reason"])
        self.assertTrue(report["mutations_performed"])
        self.assertTrue((self.root / "project-runtime/artifacts/accepted/TASK_DEMO/manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
