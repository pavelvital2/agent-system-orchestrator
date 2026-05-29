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


class ArtifactManifestMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="aso-artifact-manifest-migration-"))
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
            "structured_artifacts": ["structured/result_package.json"],
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

    def _write_candidate(self, manifest_filename: str = "manifest.json", manifest: dict[str, object] | None = None) -> Path:
        if self.package_root.exists():
            shutil.rmtree(self.package_root)
        self.package_root.mkdir(parents=True)
        (self.package_root / "RESULT_TASK_DEMO_ATTEMPT_001.md").write_text("RESULT:\nSTATUS: pass\n", encoding="utf-8")
        structured = self.package_root / "structured"
        structured.mkdir()
        (structured / "result_package.json").write_text('{"package_id":"RESULT_PACKAGE_TASK_DEMO_ATTEMPT_001"}\n', encoding="utf-8")
        manifest_path = self.package_root / manifest_filename
        manifest_path.write_text(json.dumps(manifest or self.manifest, indent=2) + "\n", encoding="utf-8")
        return manifest_path

    def test_canonical_manifest_accepts_to_canonical_accepted_manifest(self) -> None:
        manifest_path = self._write_candidate("manifest.json")
        out = self.tmpdir / "accept-canonical.json"

        code, stdout, stderr = self._run(
            [
                "artifact",
                "accept",
                "--root",
                str(self.root),
                "--candidate",
                str(manifest_path),
                "--confirm-write",
                "--json-out",
                str(out),
            ]
        )

        self.assertEqual(code, 0, stderr)
        self.assertIn("ASO artifact accept: WRITTEN", stdout)
        report = json.loads(out.read_text(encoding="utf-8"))
        accepted_manifest = self.root / "project-runtime/artifacts/accepted/TASK_DEMO/manifest.json"
        self.assertEqual(report["status"], "written")
        self.assertEqual(report["summary"], {"errors": 0, "warnings": 0})
        self.assertTrue(accepted_manifest.is_file())
        self.assertEqual(json.loads(accepted_manifest.read_text(encoding="utf-8")), self.manifest)
        self.assertEqual(report["receipt"]["artifact_ref"], "project-runtime/artifacts/accepted/TASK_DEMO/manifest.json")

    def test_legacy_alias_accepts_with_warning_and_normalizes_storage(self) -> None:
        # Legacy coverage is limited to the pre-migration manifest filename alias.
        legacy_manifest = self._write_candidate("artifact_package_manifest.json")
        out = self.tmpdir / "accept-legacy.json"

        code, _stdout, stderr = self._run(
            [
                "artifact",
                "accept",
                "--root",
                str(self.root),
                "--candidate",
                str(legacy_manifest),
                "--confirm-write",
                "--json-out",
                str(out),
            ]
        )

        self.assertEqual(code, 0, stderr)
        report = json.loads(out.read_text(encoding="utf-8"))
        accepted_root = self.root / "project-runtime/artifacts/accepted/TASK_DEMO"
        self.assertEqual(report["status"], "written")
        self.assertEqual(report["summary"], {"errors": 0, "warnings": 1})
        self.assertEqual(report["findings"][0]["rule_id"], "ARTIFACT_MANIFEST_COMPAT_001")
        self.assertTrue((accepted_root / "manifest.json").is_file())
        self.assertFalse((accepted_root / "artifact_package_manifest.json").exists())
        self.assertEqual(json.loads((accepted_root / "manifest.json").read_text(encoding="utf-8")), self.manifest)

    def test_invalid_manifest_reject_writes_rejection_receipt(self) -> None:
        manifest_path = self._write_candidate("manifest.json")
        manifest_path.write_text('{"artifact_type": "RESULT",', encoding="utf-8")
        out = self.tmpdir / "reject-invalid.json"

        code, _stdout, stderr = self._run(
            [
                "artifact",
                "reject",
                "--root",
                str(self.root),
                "--candidate",
                str(self.package_root),
                "--reason",
                "invalid_manifest",
                "--confirm-write",
                "--json-out",
                str(out),
            ]
        )

        self.assertEqual(code, 0, stderr)
        report = json.loads(out.read_text(encoding="utf-8"))
        rejected_root = self.root / "project-runtime/artifacts/rejected/TASK_DEMO"
        self.assertEqual(report["status"], "written")
        self.assertTrue(report["invalid_manifest_rejection"])
        self.assertEqual(report["actual_read_outcome"], "completed")
        self.assertEqual(report["actual_write_outcome"], "completed")
        self.assertEqual(report["summary"]["nonblocking_manifest_errors"], 1)
        self.assertEqual(report["summary"]["blocking_errors"], 0)
        self.assertEqual(report["findings"][0]["rule_id"], "ARTIFACT_VALIDATE_JSON_001")
        self.assertTrue((rejected_root / "manifest.json").is_file())
        self.assertEqual((rejected_root / "manifest.json").read_text(encoding="utf-8"), '{"artifact_type": "RESULT",')
        self.assertEqual(report["rejection_report"]["reason"], "invalid_manifest")
        self.assertEqual(report["rejection_report"]["candidate_ref"], "project-runtime/artifacts/candidates/TASK_DEMO")
        self.assertTrue((self.root / report["rejection_report_ref"]).is_file())

    def test_accepted_package_does_not_keep_duplicate_manifest_alias(self) -> None:
        canonical_manifest = self._write_candidate("manifest.json")
        (self.package_root / "artifact_package_manifest.json").write_text(
            canonical_manifest.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        out = self.tmpdir / "accept-no-duplicates.json"

        code, _stdout, stderr = self._run(
            [
                "artifact",
                "accept",
                "--root",
                str(self.root),
                "--candidate",
                str(self.package_root),
                "--confirm-write",
                "--json-out",
                str(out),
            ]
        )

        self.assertEqual(code, 0, stderr)
        accepted_root = self.root / "project-runtime/artifacts/accepted/TASK_DEMO"
        manifest_names = sorted(path.name for path in accepted_root.glob("*manifest*.json"))
        self.assertEqual(manifest_names, ["manifest.json"])
        report = json.loads(out.read_text(encoding="utf-8"))
        inventory_paths = {item["path"] for item in report["receipt"]["inventory"]}
        self.assertIn("manifest.json", inventory_paths)
        self.assertNotIn("artifact_package_manifest.json", inventory_paths)


if __name__ == "__main__":
    unittest.main()
