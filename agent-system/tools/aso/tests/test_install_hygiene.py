from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
INSTALL_SCRIPT = REPO_ROOT / "agent-system" / "scripts" / "install_aso_clean.sh"
SOURCE_HYGIENE_SCRIPT = REPO_ROOT / "agent-system" / "scripts" / "source_hygiene.sh"
INSTALLED_RESOURCE_TEST = REPO_ROOT / "agent-system" / "tools" / "aso" / "tests" / "test_installed_resource_lookup.py"


class CleanInstallHygieneTests(unittest.TestCase):
    def test_clean_installer_uses_isolated_git_archive_source(self) -> None:
        script = INSTALL_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("git -C \"$source_root\" archive --format=tar HEAD", script)
        self.assertIn("tar -x -C \"$source_copy\"", script)
        self.assertIn("install_spec=\"$source_copy[test]\"", script)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1 \"$venv_pip\" install \"$install_spec\"", script)

    def test_clean_installer_rejects_repo_local_venv_and_checks_status(self) -> None:
        script = INSTALL_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("--venv must be outside the source repository", script)
        self.assertIn("git -C \"$source_root\" status --short --branch >\"$status_before\"", script)
        self.assertIn("git -C \"$source_root\" status --short --branch >\"$status_after\"", script)
        self.assertIn("diff -u \"$status_before\" \"$status_after\"", script)

    def test_clean_installer_verifies_installed_console_command(self) -> None:
        script = INSTALL_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("\"$venv_aso\" --help", script)
        self.assertIn("\"$venv_aso\" status --root \"$source_root\" --mode package", script)

    def test_installed_resource_lookup_does_not_install_from_live_checkout(self) -> None:
        test_source = INSTALLED_RESOURCE_TEST.read_text(encoding="utf-8")
        repo_root_tokens = r"(?:REPO_ROOT|\{REPO_ROOT\}|str\(REPO_ROOT\)|f[\"'][^\"']*REPO_ROOT)"
        direct_checkout_installs = [
            re.compile(r"pip[^\n]*install[^\n]*" + repo_root_tokens),
            re.compile(r"-m[\"'],\s*[\"']pip[\"'][^\n]*[\"']install[\"'][^\n]*" + repo_root_tokens),
        ]

        self.assertIn("install_aso_clean.sh", test_source)
        self.assertIn("--source", test_source)
        self.assertIn("--venv", test_source)
        self.assertIn("--with-test", test_source)
        for direct_checkout_install in direct_checkout_installs:
            self.assertNotRegex(test_source, direct_checkout_install)

    def test_source_hygiene_catches_untracked_python_build_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            script_copy = repo / "agent-system" / "scripts" / "source_hygiene.sh"
            script_copy.parent.mkdir(parents=True)
            shutil.copy2(SOURCE_HYGIENE_SCRIPT, script_copy)

            subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "config", "user.email", "aso-test@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "ASO Test"], cwd=repo, check=True)
            subprocess.run(["git", "add", "agent-system/scripts/source_hygiene.sh"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "fixture"], cwd=repo, check=True, stdout=subprocess.DEVNULL)

            project_input_file = repo / "project-input" / "owner-note.md"
            project_input_file.parent.mkdir()
            project_input_file.write_text("owner workflow input\n", encoding="utf-8")
            clean_result = subprocess.run(
                ["bash", "agent-system/scripts/source_hygiene.sh"],
                cwd=repo,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(clean_result.returncode, 0, clean_result.stderr)

            forbidden_cache = repo / "agent-system" / "tools" / "aso" / "tests" / "__pycache__"
            forbidden_cache.mkdir(parents=True)
            (forbidden_cache / "bad.cpython-311.pyc").write_bytes(b"pyc")
            dirty_result = subprocess.run(
                ["bash", "agent-system/scripts/source_hygiene.sh"],
                cwd=repo,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertNotEqual(dirty_result.returncode, 0, dirty_result.stdout)
            self.assertIn("Python build artifacts contaminate source checkout", dirty_result.stderr)
            self.assertIn("agent-system/tools/aso/tests/__pycache__", dirty_result.stderr)


if __name__ == "__main__":
    unittest.main()
