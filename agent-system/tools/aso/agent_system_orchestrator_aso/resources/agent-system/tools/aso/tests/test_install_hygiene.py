from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from current_source_snapshot import create_current_source_snapshot


REPO_ROOT = Path(__file__).resolve().parents[4]
INSTALL_SH = REPO_ROOT / "install.sh"
INSTALL_PS1 = REPO_ROOT / "install.ps1"
INSTALL_SCRIPT = REPO_ROOT / "agent-system" / "scripts" / "install_aso_clean.sh"
INSTALLED_CLI_SMOKE_SCRIPT = REPO_ROOT / "agent-system" / "scripts" / "installed_cli_smoke.sh"
SOURCE_HYGIENE_SCRIPT = REPO_ROOT / "agent-system" / "scripts" / "source_hygiene.sh"
INSTALLED_RESOURCE_TEST = REPO_ROOT / "agent-system" / "tools" / "aso" / "tests" / "test_installed_resource_lookup.py"


class CleanInstallHygieneTests(unittest.TestCase):
    def _create_source_hygiene_fixture(self, repo: Path) -> None:
        script_copy = repo / "agent-system" / "scripts" / "source_hygiene.sh"
        script_copy.parent.mkdir(parents=True)
        shutil.copy2(SOURCE_HYGIENE_SCRIPT, script_copy)

        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "aso-test@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "ASO Test"], cwd=repo, check=True)
        subprocess.run(["git", "add", "agent-system/scripts/source_hygiene.sh"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=repo, check=True, stdout=subprocess.DEVNULL)

    def _run_source_hygiene(self, repo: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "agent-system/scripts/source_hygiene.sh"],
            cwd=repo,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def _write_source_hygiene_expanded_artifacts(self, repo: Path) -> list[str]:
        artifact_paths = [
            "agent-system/tools/aso/tests/.pytest_cache/CACHEDIR.TAG",
            "agent-system/tools/aso/.mypy_cache/meta.json",
            "agent-system/tools/aso/.ruff_cache/0.12/cache",
            "agent-system/tools/aso/.coverage",
            "agent-system/tools/aso/htmlcov/index.html",
            "agent-system/tools/aso/coverage.xml",
        ]
        for artifact_path in artifact_paths:
            path = repo / artifact_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("generated artifact\n", encoding="utf-8")
        return artifact_paths

    def _fake_python_for_venv_creation(self, directory: Path) -> Path:
        fake_python = directory / "fake-python"
        fake_python.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ge 3 ] && [ "$1" = "-m" ] && [ "$2" = "venv" ]; then
  venv_dir="$3"
  mkdir -p "$venv_dir/bin"
  cat >"$venv_dir/bin/python" <<'PYEOF'
#!/usr/bin/env bash
exit 0
PYEOF
  cat >"$venv_dir/bin/pip" <<'PIPEOF'
#!/usr/bin/env bash
exit 0
PIPEOF
  chmod +x "$venv_dir/bin/python" "$venv_dir/bin/pip"
  exit 0
fi
exit 1
""",
            encoding="utf-8",
        )
        fake_python.chmod(0o755)
        return fake_python

    def _run_clean_installer(
        self,
        temp_dir: Path,
        venv: Path,
        *extra_args: str,
    ) -> subprocess.CompletedProcess[str]:
        fake_python = self._fake_python_for_venv_creation(temp_dir)
        source_snapshot = create_current_source_snapshot(REPO_ROOT, temp_dir / f"source-snapshot-{uuid.uuid4().hex}")
        return subprocess.run(
            [
                "bash",
                str(INSTALL_SCRIPT),
                "--source",
                str(source_snapshot),
                "--venv",
                str(venv),
                "--python",
                str(fake_python),
                "--skip-verify",
                *extra_args,
            ],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

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
        self.assertIn("source worktree is dirty; refusing to archive HEAD", script)

    def test_clean_installer_rejects_dirty_source_before_archiving_head(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            source = temp_dir / "source"
            source.mkdir()
            (source / "agent-system" / "tools" / "aso").mkdir(parents=True)
            (source / "pyproject.toml").write_text("[project]\nname = \"fixture\"\n", encoding="utf-8")
            (source / "agent-system" / "tools" / "aso" / "aso.py").write_text("print('fixture')\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=source, check=True)
            subprocess.run(["git", "config", "user.email", "aso-test@example.invalid"], cwd=source, check=True)
            subprocess.run(["git", "config", "user.name", "ASO Test"], cwd=source, check=True)
            subprocess.run(["git", "add", "."], cwd=source, check=True)
            subprocess.run(["git", "commit", "-m", "fixture"], cwd=source, check=True, stdout=subprocess.DEVNULL)
            (source / "pyproject.toml").write_text("[project]\nname = \"dirty-fixture\"\n", encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(INSTALL_SCRIPT),
                    "--source",
                    str(source),
                    "--venv",
                    str(temp_dir / "venv"),
                    "--python",
                    str(self._fake_python_for_venv_creation(temp_dir)),
                    "--skip-verify",
                ],
                cwd=REPO_ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("source worktree is dirty; refusing to archive HEAD", result.stderr)
            self.assertIn("pyproject.toml", result.stderr)
            self.assertFalse((temp_dir / "venv").exists())

    def test_clean_installer_requires_explicit_existing_venv_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            venv = temp_dir / "venv"

            absent_result = self._run_clean_installer(temp_dir, venv)
            self.assertEqual(absent_result.returncode, 0, absent_result.stderr)
            self.assertTrue((venv / "bin" / "python").exists())

            default_result = self._run_clean_installer(temp_dir, venv)
            self.assertNotEqual(default_result.returncode, 0, default_result.stdout)
            self.assertIn("--venv already exists and is non-empty", default_result.stderr)
            self.assertIn("--fresh", default_result.stderr)
            self.assertIn("--reuse-venv", default_result.stderr)

            marker = venv / "reuse-marker"
            marker.write_text("existing venv state\n", encoding="utf-8")
            fresh_result = self._run_clean_installer(temp_dir, venv, "--fresh")
            self.assertEqual(fresh_result.returncode, 0, fresh_result.stderr)
            self.assertFalse(marker.exists())
            self.assertTrue((venv / "bin" / "python").exists())

            reuse_marker = venv / "explicit-reuse-marker"
            reuse_marker.write_text("intentional reuse state\n", encoding="utf-8")
            reuse_result = self._run_clean_installer(temp_dir, venv, "--reuse-venv")
            self.assertEqual(reuse_result.returncode, 0, reuse_result.stderr)
            self.assertTrue(reuse_marker.exists())

    def test_clean_installer_verifies_installed_console_command(self) -> None:
        script = INSTALL_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("\"$venv_aso\" --help", script)
        self.assertIn("\"$venv_aso\" status --root \"$source_root\" --mode package", script)
        self.assertIn("\"$venv_aso\" project create --local --target", script)
        self.assertIn("\"$venv_aso\" project verify-clean --root", script)
        self.assertIn("\"$venv_aso\" state init --root \"$runtime_smoke\"", script)
        self.assertIn("\"$venv_aso\" intake bootstrap --root \"$runtime_smoke\"", script)
        self.assertIn("\"$venv_aso\" state verify --root \"$runtime_smoke\" --strict", script)
        self.assertIn("\"$venv_aso\" plan-next --root \"$runtime_smoke\" --strict", script)

    def test_editable_installers_verify_stage1_command_surface(self) -> None:
        shell_script = INSTALL_SH.read_text(encoding="utf-8")
        ps_script = INSTALL_PS1.read_text(encoding="utf-8")

        for script in (shell_script, ps_script):
            self.assertIn("project create --local", script)
            self.assertIn("project verify-clean", script)
            self.assertIn("state init", script)
            self.assertIn("intake bootstrap", script)
            self.assertIn("state verify", script)
            self.assertIn("plan-next", script)

    def test_installed_cli_smoke_covers_package_factory_and_state_paths(self) -> None:
        script = INSTALLED_CLI_SMOKE_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("status --root \"$package_root\" --mode package", script)
        self.assertIn("doctor --root \"$package_root\" --mode package --strict", script)
        self.assertIn("package-layout verify --root \"$package_root\" --mode package --strict", script)
        self.assertIn("--engine-mode reference", script)
        self.assertIn("--engine-mode vendored", script)
        self.assertIn("state init", script)
        self.assertIn("intake bootstrap", script)
        self.assertIn("state verify", script)
        self.assertIn("plan-next", script)
        self.assertIn("agent-system/00_start/ORCHESTRATOR_START.md", script)
        self.assertIn("agent-system/ORCHESTRATOR_RUNTIME_CONTRACT.json", script)
        self.assertIn("agent-system/tools/aso/aso.py", script)
        self.assertIn("site-packages", script)
        self.assertIn("build dist", script)

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
            self._create_source_hygiene_fixture(repo)

            project_input_file = repo / "project-input" / "owner-note.md"
            project_input_file.parent.mkdir()
            project_input_file.write_text("owner workflow input\n", encoding="utf-8")
            clean_result = self._run_source_hygiene(repo)
            self.assertEqual(clean_result.returncode, 0, clean_result.stderr)

            forbidden_cache = repo / "agent-system" / "tools" / "aso" / "tests" / "__pycache__"
            forbidden_cache.mkdir(parents=True)
            (forbidden_cache / "bad.cpython-311.pyc").write_bytes(b"pyc")
            dirty_result = self._run_source_hygiene(repo)

            self.assertNotEqual(dirty_result.returncode, 0, dirty_result.stdout)
            self.assertIn(
                "Python/tooling cache, build, and coverage artifacts contaminate source checkout",
                dirty_result.stderr,
            )
            self.assertIn("agent-system/tools/aso/tests/__pycache__", dirty_result.stderr)

    def test_source_hygiene_catches_tracked_tooling_cache_and_coverage_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            self._create_source_hygiene_fixture(repo)
            artifact_paths = self._write_source_hygiene_expanded_artifacts(repo)
            subprocess.run(["git", "add", *artifact_paths], cwd=repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "tracked artifacts"],
                cwd=repo,
                check=True,
                stdout=subprocess.DEVNULL,
            )

            dirty_result = self._run_source_hygiene(repo)

            self.assertNotEqual(dirty_result.returncode, 0, dirty_result.stdout)
            self.assertIn(
                "tracked Python/tooling cache and coverage artifacts are not publishable",
                dirty_result.stderr,
            )
            for artifact_path in artifact_paths:
                self.assertIn(artifact_path, dirty_result.stderr)

    def test_source_hygiene_catches_staged_tooling_cache_and_coverage_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            self._create_source_hygiene_fixture(repo)
            artifact_paths = self._write_source_hygiene_expanded_artifacts(repo)
            subprocess.run(["git", "add", *artifact_paths], cwd=repo, check=True)

            dirty_result = self._run_source_hygiene(repo)

            self.assertNotEqual(dirty_result.returncode, 0, dirty_result.stdout)
            self.assertIn(
                "staged Python/tooling cache and coverage artifacts are not publishable",
                dirty_result.stderr,
            )
            for artifact_path in artifact_paths:
                self.assertIn(artifact_path, dirty_result.stderr)

    def test_source_hygiene_catches_untracked_tooling_cache_and_coverage_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            self._create_source_hygiene_fixture(repo)
            artifact_paths = self._write_source_hygiene_expanded_artifacts(repo)

            dirty_result = self._run_source_hygiene(repo)

            self.assertNotEqual(dirty_result.returncode, 0, dirty_result.stdout)
            self.assertIn(
                "untracked Python/tooling cache, build, and coverage artifacts contaminate source checkout",
                dirty_result.stderr,
            )
            for artifact_path in artifact_paths:
                self.assertIn(artifact_path, dirty_result.stderr)

    def test_source_hygiene_catches_ignored_tooling_cache_and_coverage_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            self._create_source_hygiene_fixture(repo)
            gitignore = repo / ".gitignore"
            gitignore.write_text(
                "\n".join(
                    [
                        ".pytest_cache/",
                        ".mypy_cache/",
                        ".ruff_cache/",
                        ".coverage",
                        "htmlcov/",
                        "coverage.xml",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            subprocess.run(["git", "add", ".gitignore"], cwd=repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "ignore artifacts"],
                cwd=repo,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            self._write_source_hygiene_expanded_artifacts(repo)

            dirty_result = self._run_source_hygiene(repo)

            self.assertNotEqual(dirty_result.returncode, 0, dirty_result.stdout)
            self.assertIn(
                "filesystem Python/tooling cache, build, and coverage artifacts contaminate source checkout",
                dirty_result.stderr,
            )
            for artifact_path in [
                "agent-system/tools/aso/tests/.pytest_cache",
                "agent-system/tools/aso/.mypy_cache",
                "agent-system/tools/aso/.ruff_cache",
                "agent-system/tools/aso/.coverage",
                "agent-system/tools/aso/htmlcov",
                "agent-system/tools/aso/coverage.xml",
            ]:
                self.assertIn(artifact_path, dirty_result.stderr)

    def test_source_hygiene_allows_documentation_mentions_of_cache_and_coverage_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            self._create_source_hygiene_fixture(repo)
            docs = repo / "agent-system" / "docs" / "source-hygiene-notes.md"
            docs.parent.mkdir(parents=True)
            docs.write_text(
                "Mention .pytest_cache, .mypy_cache, .ruff_cache, .coverage, htmlcov, and coverage.xml as text.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "agent-system/docs/source-hygiene-notes.md"], cwd=repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "document names"],
                cwd=repo,
                check=True,
                stdout=subprocess.DEVNULL,
            )

            clean_result = self._run_source_hygiene(repo)

            self.assertEqual(clean_result.returncode, 0, clean_result.stderr)


if __name__ == "__main__":
    unittest.main()
