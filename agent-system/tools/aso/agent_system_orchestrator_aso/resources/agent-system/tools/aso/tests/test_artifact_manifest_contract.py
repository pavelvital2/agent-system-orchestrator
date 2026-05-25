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
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool.aso import main  # noqa: E402


class ArtifactManifestContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="aso-artifact-manifest-contract-"))
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

    def _write_candidate(self, manifest_filename: str = "manifest.json") -> Path:
        package_root = self.root / "project-runtime/artifacts/candidates/TASK_DEMO/PACKAGE"
        if package_root.exists():
            shutil.rmtree(package_root)
        package_root.mkdir(parents=True)
        (package_root / "RESULT_TASK_DEMO_ATTEMPT_001.md").write_text("RESULT:\nSTATUS: pass\n", encoding="utf-8")
        structured = package_root / "structured"
        structured.mkdir()
        (structured / "result_package.json").write_text('{"package_id":"RESULT_PACKAGE_TASK_DEMO_ATTEMPT_001"}\n', encoding="utf-8")
        manifest_path = package_root / manifest_filename
        manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8")
        return manifest_path

    def test_runtime_contract_declares_canonical_manifest_and_legacy_alias(self) -> None:
        contract = json.loads((REPO_ROOT / "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json").read_text(encoding="utf-8"))

        artifact_contracts = contract["artifact_contracts"]
        self.assertEqual(artifact_contracts["candidate_manifest_canonical"], "manifest.json")
        self.assertEqual(artifact_contracts["accepted_manifest_canonical"], "manifest.json")
        self.assertIn("artifact_package_manifest.json", artifact_contracts["candidate_manifest_legacy_aliases"])

    def test_legacy_manifest_validates_with_compatibility_warning(self) -> None:
        legacy_manifest = self._write_candidate("artifact_package_manifest.json")

        code, stdout, stderr = self._run(
            [
                "artifact",
                "validate",
                "--root",
                str(self.root),
                "--package",
                str(legacy_manifest),
                "--format",
                "json",
            ]
        )

        self.assertEqual(code, 0, stderr)
        report = json.loads(stdout)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"], {"errors": 0, "warnings": 1})
        self.assertEqual(report["manifest"], str(legacy_manifest))
        self.assertEqual(report["findings"][0]["severity"], "warning")
        self.assertEqual(report["findings"][0]["rule_id"], "ARTIFACT_MANIFEST_COMPAT_001")
        self.assertIn("manifest.json", report["findings"][0]["details"])

    def test_accepting_legacy_manifest_materializes_canonical_accepted_manifest(self) -> None:
        legacy_manifest = self._write_candidate("artifact_package_manifest.json")
        out = self.tmpdir / "accept.json"

        code, _stdout, stderr = self._run(
            [
                "artifact",
                "accept",
                "--root",
                str(self.root),
                "--package",
                str(legacy_manifest),
                "--confirm-write",
                "--json-out",
                str(out),
            ]
        )

        self.assertEqual(code, 0, stderr)
        report = json.loads(out.read_text(encoding="utf-8"))
        accepted_root = self.root / "project-runtime/artifacts/accepted/TASK_DEMO/PACKAGE"
        self.assertTrue((accepted_root / "manifest.json").is_file())
        self.assertFalse((accepted_root / "artifact_package_manifest.json").exists())
        self.assertEqual(json.loads((accepted_root / "manifest.json").read_text(encoding="utf-8")), self.manifest)
        self.assertEqual(report["status"], "written")
        self.assertEqual(report["summary"], {"errors": 0, "warnings": 1})
        self.assertEqual(report["actual_write_outcome"], "completed")
        self.assertEqual(report["receipt"]["artifact_ref"], "project-runtime/artifacts/accepted/TASK_DEMO/PACKAGE/manifest.json")
        self.assertEqual(report["event"]["artifact_ref"], "project-runtime/artifacts/accepted/TASK_DEMO/PACKAGE/manifest.json")

    def test_accepting_explicit_legacy_manifest_replaces_invalid_canonical_manifest(self) -> None:
        legacy_manifest = self._write_candidate("artifact_package_manifest.json")
        invalid_canonical = dict(self.manifest)
        invalid_canonical["artifact_id"] = "invalid-canonical"
        invalid_canonical["task_id"] = "TASK_CANONICAL_BAD"
        invalid_canonical["role"] = "auditor"
        invalid_canonical["producer"] = {
            "agent_instance_id": "auditor_TASK_CANONICAL_BAD_attempt_001",
            "role": "auditor",
        }
        (legacy_manifest.parent / "manifest.json").write_text(json.dumps(invalid_canonical, indent=2) + "\n", encoding="utf-8")
        out = self.tmpdir / "accept-dual.json"

        code, _stdout, stderr = self._run(
            [
                "artifact",
                "accept",
                "--root",
                str(self.root),
                "--package",
                str(legacy_manifest),
                "--confirm-write",
                "--json-out",
                str(out),
            ]
        )

        self.assertEqual(code, 0, stderr)
        report = json.loads(out.read_text(encoding="utf-8"))
        accepted_root = self.root / "project-runtime/artifacts/accepted/TASK_DEMO/PACKAGE"
        accepted_manifest = json.loads((accepted_root / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(accepted_manifest, self.manifest)
        self.assertFalse((accepted_root / "artifact_package_manifest.json").exists())
        self.assertEqual(report["summary"], {"errors": 0, "warnings": 1})
        self.assertEqual(report["receipt"]["artifact_id"], self.manifest["artifact_id"])
        self.assertEqual(report["receipt"]["task_id"], self.manifest["task_id"])
        self.assertEqual(report["receipt"]["role"], self.manifest["role"])
        self.assertEqual(report["event"]["artifact_id"], self.manifest["artifact_id"])
        self.assertEqual(report["event"]["task_id"], self.manifest["task_id"])
        self.assertEqual(report["event"]["role"], self.manifest["role"])
        self.assertNotEqual(report["receipt"]["artifact_id"], invalid_canonical["artifact_id"])
        self.assertNotEqual(report["event"]["task_id"], invalid_canonical["task_id"])


if __name__ == "__main__":
    unittest.main()
