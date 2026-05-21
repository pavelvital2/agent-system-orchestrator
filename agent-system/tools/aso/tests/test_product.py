from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def workspace_files(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


class ProductCommandTests(unittest.TestCase):
    def test_help_declares_product_group_and_subcommands(self) -> None:
        group_help = run_aso("product", "--help")

        self.assertEqual(group_help.returncode, 0, group_help.stdout + group_help.stderr)
        for command in ("intake", "clarify", "spec", "capabilities", "plan"):
            self.assertIn(command, group_help.stdout)

        for command in ("intake", "clarify", "spec", "capabilities", "plan"):
            with self.subTest(command=command):
                result = run_aso("product", command, "--help")

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("--root", result.stdout)
                self.assertIn("--profile", result.stdout)
                self.assertIn("--readiness", result.stdout)
                self.assertIn("--dry-run", result.stdout)
                self.assertIn("--json-out", result.stdout)
                self.assertIn("--confirm-write", result.stdout)

    def test_intake_dry_run_json_out_writes_only_explicit_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            tz = root / "owner_tz.md"
            tz.write_text("Build a support bot. Needs TELEGRAM_BOT_TOKEN later.\n", encoding="utf-8")
            before = workspace_files(root)
            json_out = Path(tmp) / "product-intake.json"

            result = run_aso(
                "product",
                "intake",
                "--root",
                str(root),
                "--tz",
                str(tz),
                "--profile",
                "telegram_bot",
                "--readiness",
                "mvp",
                "--dry-run",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(before, workspace_files(root))
            artifact = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(artifact["artifact_type"], "PRODUCT_INTAKE")
            self.assertEqual(artifact["status"], "needs_clarification")
            self.assertEqual(artifact["profile"], "telegram_bot")
            self.assertEqual(artifact["required_secrets"][0]["name"], "TELEGRAM_BOT_TOKEN")
            self.assertEqual(artifact["required_secrets"][0]["value_status"], "not_collected")

    def test_workspace_json_out_requires_confirm_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            tz = root / "owner_tz.md"
            tz.write_text("Build a local planning app.\n", encoding="utf-8")
            product_dir = root / "project-runtime" / "product"
            product_dir.mkdir(parents=True)
            json_out = product_dir / "manual-product-intake.json"
            before = workspace_files(root)

            result = run_aso(
                "product",
                "intake",
                "--root",
                str(root),
                "--tz",
                str(tz),
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("--confirm-write is required", result.stderr)
            self.assertFalse(json_out.exists())
            self.assertEqual(before, workspace_files(root))

    def test_confirm_write_writes_only_under_project_runtime_product(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            tz = root / "owner_tz.md"
            tz.write_text("Build a deterministic planning helper.\n", encoding="utf-8")
            before = workspace_files(root)

            result = run_aso("product", "intake", "--root", str(root), "--tz", str(tz), "--confirm-write")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            added = workspace_files(root) - before
            self.assertEqual(len(added), 1, added)
            written = next(iter(added))
            self.assertTrue(written.startswith("project-runtime/product/"), written)
            self.assertTrue(written.endswith(".json"), written)
            artifact = json.loads((root / written).read_text(encoding="utf-8"))
            self.assertEqual(artifact["artifact_type"], "PRODUCT_INTAKE")


if __name__ == "__main__":
    unittest.main()
