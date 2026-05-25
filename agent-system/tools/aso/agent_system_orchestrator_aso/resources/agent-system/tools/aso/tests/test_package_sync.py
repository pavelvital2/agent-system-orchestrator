from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_layout_fixture(root: Path) -> None:
    aso_root = root / "agent-system" / "tools" / "aso"
    package = aso_root / "agent_system_orchestrator_aso"
    _write(
        aso_root / "aso.py",
        (
            "import sys\n"
            "from agent_system_orchestrator_aso.aso_tool.aso import build_parser, main\n"
            'if __name__ == "__main__":\n'
            "    sys.exit(main())\n"
        ),
    )
    _write(package / "__init__.py", "\n")
    _write(package / "cli.py", "from .aso_tool.aso import main\n")
    _write(package / "aso_tool" / "__init__.py", "\n")
    _write(
        package / "aso_tool" / "aso.py",
        (
            "import argparse\n"
            "def build_parser():\n"
            "    return argparse.ArgumentParser(prog='aso')\n"
            "def main(argv=None):\n"
            "    build_parser().parse_args(argv)\n"
            "    return 0\n"
        ),
    )
    _write(
        root / "pyproject.toml",
        (
            "[project]\n"
            'name = "aso-fixture"\n'
            'version = "0.0.0"\n'
            "\n"
            "[project.scripts]\n"
            'aso = "agent_system_orchestrator_aso.cli:main"\n'
            "\n"
            "[tool.setuptools.packages.find]\n"
            'where = ["agent-system/tools/aso"]\n'
            'include = ["agent_system_orchestrator_aso*"]\n'
        ),
    )
    readme = (
        "ASO CLI path: agent-system/tools/aso/aso.py\n"
        "Use --mode package for package mode and --mode workspace for workspace mode.\n"
        "The status command and lint command are read-only.\n"
        "The helper does not provide mutation, dispatch, or checkpoint authority.\n"
    )
    _write(root / "README.md", readme)
    _write(root / "agent-system" / "README.md", readme)
    _write(root / ".gitignore", "/project-runtime/\n/project-input/\n/project-archive/\n")
    _write(
        root / ".github" / "workflows" / "governance.yml",
        (
            "name: governance\n"
            "on:\n"
            "  push:\n"
            "    branches:\n"
            "      - main\n"
            "      - upgrade/**\n"
            "      - merge-preparation/**\n"
        ),
    )


def _run_package_sync(root: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
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
        env=env,
    )


class PackageSyncAliasTests(unittest.TestCase):
    def test_package_sync_verify_delegates_to_package_layout_without_copy_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_layout_fixture(root)

            result = _run_package_sync(root)
            report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["command"], "package-sync verify")
            self.assertNotIn("mismatches", report)
            self.assertTrue(root.exists())
            self.assertFalse((root / "agent_system_orchestrator_aso").exists())


if __name__ == "__main__":
    unittest.main()
