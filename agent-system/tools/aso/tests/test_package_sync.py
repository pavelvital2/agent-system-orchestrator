from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_sync_fixture(root: Path) -> None:
    source = root / "agent-system" / "tools" / "aso"
    bundled = root / "agent_system_orchestrator_aso" / "aso_tool"
    for base in (source, bundled):
        _write(base / "aso.py", "print('aso')\n")
        _write(base / "commands" / "__init__.py", "\n")
        _write(base / "commands" / "status.py", "STATUS = 'ok'\n")
        _write(base / "models" / "__init__.py", "\n")


def _run_package_sync(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "package-sync",
            "verify",
            "--root",
            str(root),
            "--strict",
            "--json",
        ],
        check=False,
        text=True,
        capture_output=True,
    )


class PackageSyncTests(unittest.TestCase):
    def test_matching_fixture_passes_and_ignores_generated_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_sync_fixture(root)
            _write(
                root / "agent-system" / "tools" / "aso" / "__pycache__" / "aso.cpython-312.pyc",
                "source cache",
            )
            _write(
                root
                / "agent_system_orchestrator_aso"
                / "aso_tool"
                / "__pycache__"
                / "aso.cpython-312.pyc",
                "bundled cache",
            )

            result = _run_package_sync(root)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["mismatches"], [])
        self.assertEqual(report["summary"]["mismatches"], 0)
        self.assertIn("tests/", report["summary"]["excluded_paths"])

    def test_stale_bundled_file_fails_with_stable_rule_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_sync_fixture(root)
            _write(
                root / "agent_system_orchestrator_aso" / "aso_tool" / "commands" / "status.py",
                "STATUS = 'stale'\n",
            )

            result = _run_package_sync(root)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["mismatches"][0]["rule_id"], "PACKAGE_SYNC_002")
        self.assertEqual(report["mismatches"][0]["path"], "commands/status.py")

    def test_missing_bundled_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_sync_fixture(root)
            (root / "agent_system_orchestrator_aso" / "aso_tool" / "models" / "__init__.py").unlink()

            result = _run_package_sync(root)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(report["mismatches"][0]["rule_id"], "PACKAGE_SYNC_001")
        self.assertEqual(report["mismatches"][0]["path"], "models/__init__.py")

    def test_bundled_only_command_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_sync_fixture(root)
            _write(
                root / "agent_system_orchestrator_aso" / "aso_tool" / "commands" / "extra.py",
                "EXTRA = True\n",
            )

            result = _run_package_sync(root)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(report["mismatches"][0]["rule_id"], "PACKAGE_SYNC_003")
        self.assertEqual(report["mismatches"][0]["path"], "commands/extra.py")

    def test_tests_are_explicitly_excluded_from_bundled_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_sync_fixture(root)
            _write(
                root / "agent-system" / "tools" / "aso" / "tests" / "test_direct_only.py",
                "REPO_ROOT = 'repository-specific test fixture'\n",
            )

            result = _run_package_sync(root)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["mismatches"], [])
        self.assertIn("tests/", report["summary"]["excluded_paths"])


if __name__ == "__main__":
    unittest.main()
