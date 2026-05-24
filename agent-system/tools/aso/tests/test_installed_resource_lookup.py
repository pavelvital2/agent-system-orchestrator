from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
DIRECT_CLI = REPO_ROOT / "agent-system" / "tools" / "aso" / "aso.py"


def _run(command: list[str], *, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(command, cwd=cwd, check=False, text=True, capture_output=True, env=env)


class InstalledResourceLookupTests(unittest.TestCase):
    def test_installed_plan_next_uses_packaged_governance_resources_for_external_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aso-resource-lookup-") as tmp:
            tmp_path = Path(tmp)
            workspace = tmp_path / "workspace"
            venv = tmp_path / "venv"
            direct_json = tmp_path / "direct-plan-next.json"
            installed_json = tmp_path / "installed-plan-next.json"
            workspace.mkdir()

            create_venv = _run([sys.executable, "-m", "venv", str(venv)])
            self.assertEqual(create_venv.returncode, 0, create_venv.stderr)

            pip = venv / "bin" / "python"
            install = _run([str(pip), "-m", "pip", "install", f"{REPO_ROOT}[test]"])
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)

            installed_aso = venv / "bin" / "aso"
            init = _run(
                [
                    str(installed_aso),
                    "state",
                    "init",
                    "--root",
                    str(workspace),
                    "--confirm-write",
                    "--json-out",
                    str(tmp_path / "state-init.json"),
                ]
            )
            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)

            direct = _run(
                [
                    sys.executable,
                    str(DIRECT_CLI),
                    "plan-next",
                    "--root",
                    str(workspace),
                    "--strict",
                    "--json-out",
                    str(direct_json),
                ]
            )
            installed = _run(
                [
                    str(installed_aso),
                    "plan-next",
                    "--root",
                    str(workspace),
                    "--strict",
                    "--json-out",
                    str(installed_json),
                ]
            )

            self.assertEqual(installed.returncode, direct.returncode, installed.stdout + installed.stderr)
            direct_report = json.loads(direct_json.read_text(encoding="utf-8"))
            installed_report = json.loads(installed_json.read_text(encoding="utf-8"))

            self.assertEqual(installed_report["status"], direct_report["status"])
            self.assertEqual(installed_report["recommended_next_action"], direct_report["recommended_next_action"])
            installed_rules = installed_report["evidence"]["governance_rules"]
            direct_rules = direct_report["evidence"]["governance_rules"]
            self.assertEqual(
                installed_rules["registry_id"],
                direct_rules["registry_id"],
            )
            self.assertEqual(
                installed_rules["rule_count"],
                direct_rules["rule_count"],
            )
            self.assertEqual(installed_rules["load_error"], "")
            self.assertIn("agent_system_orchestrator_aso.resources", installed_rules["origin"])
            self.assertNotIn("venv/agent-system/09_validators", json.dumps(installed_report))
            self.assertFalse((venv / "agent-system").exists())


if __name__ == "__main__":
    unittest.main()
