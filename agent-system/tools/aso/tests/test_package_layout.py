from __future__ import annotations

import hashlib
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


def _readme_text() -> str:
    return (
        "ASO CLI path: agent-system/tools/aso/aso.py\n"
        "Use --mode package for package mode and --mode workspace for workspace mode.\n"
        "The status command and lint command are read-only.\n"
        "The helper does not provide mutation, dispatch, or checkpoint authority.\n"
    )


def _direct_wrapper_text() -> str:
    return (
        "import sys\n"
        "from agent_system_orchestrator_aso.aso_tool.aso import build_parser, main\n"
        'if __name__ == "__main__":\n'
        "    sys.exit(main())\n"
    )


def _pyproject(where: str = "agent-system/tools/aso") -> str:
    return (
        "[project]\n"
        'name = "aso-fixture"\n'
        'version = "0.0.0"\n'
        "\n"
        "[project.scripts]\n"
        'aso = "agent_system_orchestrator_aso.cli:main"\n'
        "\n"
        "[tool.setuptools.packages.find]\n"
        f'where = ["{where}"]\n'
        'include = ["agent_system_orchestrator_aso*"]\n'
        "\n"
        "[tool.setuptools.package-data]\n"
        '"agent_system_orchestrator_aso.resources" = [\n'
        '    "RESOURCE_MANIFEST.json",\n'
        '    "agent-system/**/*",\n'
        "]\n"
    )


def _resource_manifest(files: dict[str, bytes]) -> str:
    return json.dumps(
        {
            "schema": "aso_resource_manifest_v1",
            "resource_root": "agent-system",
            "required_file_sentinels": [
                "agent-system/00_start/ORCHESTRATOR_START.md",
                "agent-system/ORCHESTRATOR_RUNTIME_CONTRACT.json",
                "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json",
                "agent-system/tools/aso/aso.py",
            ],
            "required_directory_sentinels": ["agent-system/09_validators"],
            "files": {
                relpath: {
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size": len(data),
                }
                for relpath, data in sorted(files.items())
            },
        },
        indent=2,
        sort_keys=True,
    ) + "\n"


def _minimal_layout_fixture(root: Path) -> None:
    aso_root = root / "agent-system" / "tools" / "aso"
    package = aso_root / "agent_system_orchestrator_aso"
    _write(
        aso_root / "aso.py",
        _direct_wrapper_text(),
    )
    _write(package / "__init__.py", "\n")
    _write(package / "cli.py", "from .aso_tool.aso import main\n")
    _write(package / "resources" / "__init__.py", "\n")
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
    _write(root / "pyproject.toml", _pyproject())
    _write(root / "README.md", _readme_text())
    _write(root / "agent-system" / "README.md", _readme_text())
    _write(root / ".gitignore", "/project-runtime/\n/project-input/\n/project-archive/\n")
    _write(
        root / "MANIFEST.in",
        (
            "graft agent-system/tools/aso/agent_system_orchestrator_aso/resources\n"
            "prune agent-system/tools/aso/agent_system_orchestrator_aso/resources/agent-system/tools/aso/agent_system_orchestrator_aso/resources/agent-system\n"
        ),
    )
    resource_files = {
        "agent-system/00_start/ORCHESTRATOR_START.md": b"# Start\n",
        "agent-system/ORCHESTRATOR_RUNTIME_CONTRACT.json": b"{}\n",
        "agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json": b"{}\n",
        "agent-system/09_validators/VALIDATOR_SPEC.md": b"# Validators\n",
        "agent-system/09_validators/rules/governance_rules.json": b"{}\n",
        "agent-system/tools/aso/aso.py": _direct_wrapper_text().encode("utf-8"),
    }
    resources_root = package / "resources"
    for relpath, data in resource_files.items():
        target = resources_root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if relpath != "agent-system/ORCHESTRATOR_RUNTIME_CONTRACT.json":
            source_target = root / relpath
            source_target.parent.mkdir(parents=True, exist_ok=True)
            source_target.write_bytes(data)
    _write(resources_root / "RESOURCE_MANIFEST.json", _resource_manifest(resource_files))
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


def _run_package_layout(root: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "package-layout",
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


def _init_git(root: Path) -> None:
    result = subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=False, capture_output=True)
    if result.returncode != 0:
        subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "checkout", "-b", "main"], check=True, capture_output=True)


class PackageLayoutTests(unittest.TestCase):
    def test_valid_layout_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_layout_fixture(root)

            result = _run_package_layout(root)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["summary"]["errors"], 0)

    def test_root_duplicate_reintroduction_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_layout_fixture(root)
            _write(root / "agent_system_orchestrator_aso" / "__init__.py", "\n")

            result = _run_package_layout(root)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("PACKAGE_LAYOUT_004", {finding["rule_id"] for finding in report["findings"]})

    def test_legacy_top_level_python_trees_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_layout_fixture(root)
            _write(root / "agent-system" / "tools" / "aso" / "commands" / "__init__.py", "\n")
            _write(root / "agent-system" / "tools" / "aso" / "rules" / "__init__.py", "\n")

            result = _run_package_layout(root)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("PACKAGE_LAYOUT_009", {finding["rule_id"] for finding in report["findings"]})

    def test_wrong_pyproject_where_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_layout_fixture(root)
            _write(root / "pyproject.toml", _pyproject(where="."))

            result = _run_package_layout(root)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("PACKAGE_LAYOUT_006", {finding["rule_id"] for finding in report["findings"]})

    def test_tracked_cache_patterns_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_layout_fixture(root)
            _init_git(root)
            cache_file = root / "agent-system" / "tools" / "aso" / "__pycache__" / "aso.cpython-312.pyc"
            _write(cache_file, "tracked cache")
            subprocess.run(["git", "-C", str(root), "add", str(cache_file.relative_to(root))], check=True)

            result = _run_package_layout(root)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("LINT_PKG_006", {finding["rule_id"] for finding in report["findings"]})

    def test_packaged_resource_root_source_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_layout_fixture(root)
            _write(root / "agent-system" / "02_runtime" / "ORCHESTRATOR_RUNTIME_CONTRACT.json", '{"drift": true}\n')

            result = _run_package_layout(root)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("PACKAGE_RESOURCES_005", {finding["rule_id"] for finding in report["findings"]})


if __name__ == "__main__":
    unittest.main()
