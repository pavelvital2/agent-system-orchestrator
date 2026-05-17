from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
COMMIT_A = "0123456789abcdef0123456789abcdef01234567"
COMMIT_B = "fedcba9876543210fedcba9876543210fedcba98"


RUNTIME_CONTENT = {
    "PROJECT_STATE.md": f"""# PROJECT_STATE

PROJECT_SLUG: demo-project
PROJECT_STATUS: active
LAST_COMMIT_HASH: {COMMIT_A}
""",
    "ACCEPTED_ARTIFACTS.md": f"""# ACCEPTED_ARTIFACTS

ARTIFACT_ID: ART_CODE_001
ARTIFACT_TYPE: code
ARTIFACT_REF: src/app.py
STATUS: accepted
SOURCE_TASK: TASK_DEMO_001
SOURCE_RESULT_REF: project-runtime/results/RESULT_TASK_DEMO_001_ATTEMPT_001.md
AUDIT_REF: NONE
SUPERSEDES: NONE
SUPERSEDED_BY: NONE
COMMIT_HASH: {COMMIT_A}
BRANCH: main
PUSH_STATUS: not_attempted
CHECKPOINT_REF: NONE
ACCEPTED_AT: 2026-05-17
UPDATED_AT: 2026-05-17
NOTES: NONE
""",
    "TASK_REGISTRY.md": f"""# TASK_REGISTRY

TASK_ID: TASK_DEMO_001
STATUS: checkpoint_done
COMMIT_HASH: {COMMIT_A}
ACCEPTED_FILES: src/app.py
""",
}


def write_workspace(root: Path) -> list[Path]:
    paths: list[Path] = []
    for relpath, text in {
        "project-input/README.md": "# Input\n",
        "project-docs/README.md": "# Docs\n",
        "src/app.py": "print('demo')\n",
    }.items():
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        paths.append(path)

    runtime = root / "project-runtime"
    runtime.mkdir(exist_ok=True)
    for name, text in RUNTIME_CONTENT.items():
        path = runtime / name
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths


def manifest(
    commit_hash: str = COMMIT_A,
    exclusions: list[dict[str, str]] | None = None,
    files: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "generated_at": "2026-05-17T00:00:00Z",
            "commit_hash": commit_hash,
            "files": files
            if files is not None
            else ["project-runtime/ACCEPTED_ARTIFACTS.md", "project-docs/README.md", "src/app.py"],
            "excluded_paths": exclusions or [],
        }
    )


def archive_members(
    *,
    include_manifest: bool = True,
    include_src: bool = True,
    include_app: bool = True,
    commit_hash: str = COMMIT_A,
    exclusions: list[dict[str, str]] | None = None,
    manifest_files: list[str] | None = None,
) -> dict[str, str]:
    members = {
        "project-runtime/ACCEPTED_ARTIFACTS.md": RUNTIME_CONTENT["ACCEPTED_ARTIFACTS.md"],
        "project-runtime/PROJECT_STATE.md": RUNTIME_CONTENT["PROJECT_STATE.md"],
        "project-runtime/TASK_REGISTRY.md": RUNTIME_CONTENT["TASK_REGISTRY.md"],
        "project-docs/README.md": "# Docs\n",
        "project-input/README.md": "# Input\n",
    }
    if include_manifest:
        members["manifest.json"] = manifest(commit_hash, exclusions, manifest_files)
    if include_src:
        members["src/README.md"] = "# Source\n"
    if include_app:
        members["src/app.py"] = "print('demo')\n"
    return members


def write_archive(path: Path, members: dict[str, str]) -> None:
    if path.name.endswith(".zip"):
        with zipfile.ZipFile(path, "w") as archive:
            for relpath, text in members.items():
                archive.writestr(relpath, text)
        return

    mode = "w:gz" if path.name.endswith((".tgz", ".tar.gz")) else "w"
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        for relpath, text in members.items():
            staged = staging / relpath
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text(text, encoding="utf-8")
        with tarfile.open(path, mode) as archive:
            for staged in sorted(staging.rglob("*")):
                if staged.is_file():
                    archive.add(staged, arcname=staged.relative_to(staging).as_posix())


def run_archive_verify(root: Path, archive: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "archive", "verify", "--root", str(root), "--archive", str(archive), *extra],
        check=False,
        text=True,
        capture_output=True,
    )


class ArchiveVerifyCommandTests(unittest.TestCase):
    def test_archive_verify_passes_supported_formats_and_writes_json_only_to_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace_paths = write_workspace(root)
            mtimes_before = {path: path.stat().st_mtime_ns for path in workspace_paths}

            for suffix in (".zip", ".tgz", ".tar.gz", ".tar"):
                archive_path = root / f"package{suffix}"
                write_archive(archive_path, archive_members())
                json_out = root / f"archive_verify{suffix.replace('.', '_')}.json"

                result = run_archive_verify(root, archive_path, "--json-out", str(json_out))

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("ASO archive verify: PASSED", result.stdout)
                report = json.loads(json_out.read_text(encoding="utf-8"))
                self.assertEqual(report["tool"], "aso")
                self.assertEqual(report["command"], "archive verify")
                self.assertEqual(report["status"], "passed")
                self.assertEqual(report["summary"], {"errors": 0, "warnings": 0, "info": 0})
                self.assertEqual(report["findings"], [])

            self.assertEqual(mtimes_before, {path: path.stat().st_mtime_ns for path in workspace_paths})

    def test_archive_verify_distinguishes_manifest_missing_and_packaging_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workspace(root)
            archive_path = root / "package.zip"
            write_archive(archive_path, archive_members(include_manifest=False, include_src=False, include_app=False))

            result = run_archive_verify(root, archive_path)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("manifest_missing", result.stdout)
            self.assertIn("packaging_error", result.stdout)
            self.assertNotIn("NOT_IMPLEMENTED", result.stdout)

    def test_archive_verify_reports_accepted_artifact_missing_when_parent_folder_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workspace(root)
            archive_path = root / "package.tar"
            write_archive(
                archive_path,
                archive_members(
                    include_src=True,
                    include_app=False,
                    manifest_files=["project-runtime/ACCEPTED_ARTIFACTS.md", "project-docs/README.md"],
                ),
            )

            result = run_archive_verify(root, archive_path)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("accepted_artifact_missing", result.stdout)

    def test_archive_verify_accepts_manifest_exclusion_with_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workspace(root)
            archive_path = root / "package.tgz"
            write_archive(
                archive_path,
                archive_members(
                    include_src=False,
                    include_app=False,
                    exclusions=[{"path": "src/app.py", "reason": "large generated artifact stored externally"}],
                ),
            )

            result = run_archive_verify(root, archive_path)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ASO archive verify: PASSED", result.stdout)

    def test_archive_verify_reports_commit_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_workspace(root)
            archive_path = root / "package.zip"
            write_archive(archive_path, archive_members(commit_hash=COMMIT_B))

            result = run_archive_verify(root, archive_path)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("commit_mismatch", result.stdout)


if __name__ == "__main__":
    unittest.main()
