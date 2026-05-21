from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "product_intake"


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
            self.assertEqual(artifact["product_goal"], artifact["goal"])
            self.assertEqual(artifact["required_secrets"][0]["name"], "TELEGRAM_BOT_TOKEN")
            self.assertEqual(artifact["required_secrets"][0]["value_status"], "not_collected")

    def test_intake_detects_profile_capabilities_integrations_risks_and_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            json_out = Path(tmp) / "intake.json"

            result = run_aso(
                "product",
                "intake",
                "--root",
                str(root),
                "--tz",
                str(FIXTURE_DIR / "telegram_marketplace_tz.md"),
                "--readiness",
                "mvp",
                "--dry-run",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            artifact = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(artifact["profile"], "telegram_bot")
            self.assertIn("source path:", artifact["source_summary"].casefold())
            self.assertIn("source type: markdown_tz", artifact["source_summary"])
            capability_names = {item["name"] for item in artifact["candidate_capabilities"]}
            self.assertIn("Telegram bot conversation", capability_names)
            self.assertIn("Admin dashboard", capability_names)
            self.assertIn("Catalog and marketplace sync", capability_names)
            integrations = " ".join(item["text"] for item in artifact["external_integrations"])
            self.assertIn("Telegram integration", integrations)
            self.assertIn("Marketplace API integration", integrations)
            secret_names = {item["name"] for item in artifact["required_secrets"]}
            self.assertIn("TELEGRAM_BOT_TOKEN", secret_names)
            self.assertIn("MARKETPLACE_API_KEY", secret_names)
            risks = " ".join(item["text"] for item in artifact["high_risk_business_actions"])
            self.assertIn("Marketplace price, stock, or promotion changes", risks)
            self.assertIn("owner approval policy", artifact["recommended_next_action"])
            self.assertTrue(artifact["constraints"])
            self.assertTrue(artifact["missing_information"])

    def test_intake_empty_tz_fails_closed_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            tz = root / "empty_tz.md"
            tz.write_text("\n\t\n", encoding="utf-8")
            json_out = Path(tmp) / "should-not-exist.json"
            before = workspace_files(root)

            result = run_aso(
                "product",
                "intake",
                "--root",
                str(root),
                "--tz",
                str(tz),
                "--dry-run",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("empty TZ input", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertFalse(json_out.exists())
            self.assertEqual(before, workspace_files(root))

    def test_intake_missing_tz_fails_closed_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            json_out = Path(tmp) / "should-not-exist.json"
            before = workspace_files(root)

            result = run_aso(
                "product",
                "intake",
                "--root",
                str(root),
                "--tz",
                str(root / "missing_tz.md"),
                "--dry-run",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("failed to read", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertFalse(json_out.exists())
            self.assertEqual(before, workspace_files(root))

    def test_intake_redacts_secret_like_values_from_stdout_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            secret_value = "MY" + "SECRET" + "KEY" + "VALUE"
            tz = root / "owner_tz.md"
            tz.write_text(
                f"Build a Telegram bot. TELEGRAM_BOT_TOKEN={secret_value}\n",
                encoding="utf-8",
            )

            result = run_aso("product", "intake", "--root", str(root), "--tz", str(tz), "--dry-run")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn(secret_value, result.stdout)
            self.assertNotIn(secret_value, result.stderr)
            artifact = json.loads(result.stdout)
            raw_artifact = json.dumps(artifact, sort_keys=True)
            self.assertNotIn(secret_value, raw_artifact)
            self.assertIn("[REDACTED_SECRET_VALUE]", raw_artifact)
            secret_names = {item["name"] for item in artifact["required_secrets"]}
            self.assertIn("TELEGRAM_BOT_TOKEN", secret_names)
            self.assertNotIn(secret_value, secret_names)
            self.assertNotIn("REDACTED_SECRET_VALUE", secret_names)
            for secret in artifact["required_secrets"]:
                self.assertNotIn("value", secret)

    def test_intake_redacts_telegram_token_phrase_everywhere(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            token_value = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
            tz = root / "owner_tz.md"
            tz.write_text(
                f"The bot token is {token_value}. Build a Telegram support bot.\n",
                encoding="utf-8",
            )

            result = run_aso("product", "intake", "--root", str(root), "--tz", str(tz), "--dry-run")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn(token_value, result.stdout)
            self.assertNotIn(token_value, result.stderr)
            artifact = json.loads(result.stdout)
            for value in (
                artifact["goal"],
                artifact["product_goal"],
                artifact["source_summary"],
                json.dumps(artifact.get("assumptions", []), sort_keys=True),
                json.dumps(artifact.get("missing_information", []), sort_keys=True),
            ):
                self.assertNotIn(token_value, value)
            secret_names = {item["name"] for item in artifact["required_secrets"]}
            self.assertIn("TELEGRAM_BOT_TOKEN", secret_names)
            self.assertNotIn(token_value, secret_names)
            self.assertNotIn("REDACTED_SECRET_VALUE", secret_names)

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

    def test_clarify_from_intake_generates_grouped_questions_and_owner_decision_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            intake_out = Path(tmp) / "intake.json"
            questions_out = Path(tmp) / "open-questions.json"

            intake_result = run_aso(
                "product",
                "intake",
                "--root",
                str(root),
                "--tz",
                str(FIXTURE_DIR / "telegram_marketplace_tz.md"),
                "--readiness",
                "mvp",
                "--dry-run",
                "--json-out",
                str(intake_out),
            )
            self.assertEqual(intake_result.returncode, 0, intake_result.stdout + intake_result.stderr)

            clarify_result = run_aso(
                "product",
                "clarify",
                "--root",
                str(root),
                "--from-intake",
                str(intake_out),
                "--dry-run",
                "--json-out",
                str(questions_out),
            )

            self.assertEqual(clarify_result.returncode, 0, clarify_result.stdout + clarify_result.stderr)
            self.assertEqual(clarify_result.stdout, "")
            artifact = json.loads(questions_out.read_text(encoding="utf-8"))
            self.assertEqual(artifact["artifact_type"], "OPEN_QUESTIONS")
            self.assertIn("owner_decision_cards", artifact)
            expected_categories = {
                "product",
                "users",
                "data",
                "integrations",
                "deployment",
                "security",
                "operations",
                "business risks",
                "acceptance",
            }
            self.assertEqual({group["category"] for group in artifact["question_groups"]}, expected_categories)
            self.assertEqual({question["category"] for question in artifact["questions"]}, expected_categories)

            for question in artifact["questions"]:
                self.assertIn(question["priority"], {"must", "should", "could"})
                self.assertIn(question["severity"], {"critical", "high", "medium", "low"})
                self.assertTrue(question["why_it_matters"])
                self.assertTrue(question["options"])
                self.assertIn("blocks_implementation", question)
                self.assertNotIn("RBAC", question["question"])

            cards = artifact["owner_decision_cards"]
            self.assertGreaterEqual(len(cards), 1)
            for card in cards:
                self.assertTrue(card["options"])
                self.assertTrue(card["recommendation"])
                self.assertTrue(card["impact"])
                self.assertTrue(card["tradeoffs"])
                self.assertTrue(card["risk"])
                self.assertTrue(card["required_owner_action"])

            raw_artifact = json.dumps(artifact, sort_keys=True)
            self.assertIn("do not paste secret values", raw_artifact)
            self.assertIn("secret owner", raw_artifact)
            self.assertNotIn("secret_value", raw_artifact)
            self.assertNotIn("api key value", raw_artifact.casefold())

    def test_clarify_output_content_is_deterministic_for_same_intake(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            intake_out = Path(tmp) / "intake.json"
            first_out = Path(tmp) / "first-open-questions.json"
            second_out = Path(tmp) / "second-open-questions.json"

            intake_result = run_aso(
                "product",
                "intake",
                "--root",
                str(root),
                "--tz",
                str(FIXTURE_DIR / "telegram_marketplace_tz.md"),
                "--dry-run",
                "--json-out",
                str(intake_out),
            )
            self.assertEqual(intake_result.returncode, 0, intake_result.stdout + intake_result.stderr)

            for output in (first_out, second_out):
                result = run_aso(
                    "product",
                    "clarify",
                    "--root",
                    str(root),
                    "--from-intake",
                    str(intake_out),
                    "--dry-run",
                    "--json-out",
                    str(output),
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            first = json.loads(first_out.read_text(encoding="utf-8"))
            second = json.loads(second_out.read_text(encoding="utf-8"))
            for artifact in (first, second):
                artifact["artifact_id"] = "<generated>"
                artifact["created_at"] = "<generated>"
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
