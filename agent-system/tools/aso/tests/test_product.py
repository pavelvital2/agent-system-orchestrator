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


def write_complete_answers(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "product_name": "Support Analytics Workbench",
                "product_summary": "A local parser and analytics review tool for support exports.",
                "target_users": ["Support analyst", "Operations owner"],
                "scope_in": ["Parse CSV logs", "Review dashboard metrics", "Export weekly reports"],
                "scope_out": ["Live external API calls", "Deployment execution"],
                "data_model_notes": ["Store normalized events from local sample files only."],
                "acceptance_summary": "Owner reviews parser output and dashboard metrics against sample files.",
                "acceptance_criteria": [
                    "Given a sample CSV, the parser produces normalized event rows for owner review."
                ],
            }
        ),
        encoding="utf-8",
    )


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

    def test_intake_accepts_parser_analytics_tz_without_external_calls_or_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            json_out = Path(tmp) / "analytics-intake.json"

            result = run_aso(
                "product",
                "intake",
                "--root",
                str(root),
                "--tz",
                str(FIXTURE_DIR / "analytics_parser_tz.md"),
                "--readiness",
                "business_ready",
                "--dry-run",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            artifact = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(artifact["artifact_type"], "PRODUCT_INTAKE")
            self.assertEqual(artifact["profile"], "analytics_tool")
            self.assertEqual(artifact["readiness_mode"], "business_ready")
            self.assertEqual(artifact["required_secrets"], [])
            self.assertEqual(artifact["external_integrations"], [])
            capability_names = {item["name"] for item in artifact["candidate_capabilities"]}
            self.assertIn("Reports and analytics", capability_names)
            self.assertIn("Data capture and storage", capability_names)
            constraints = " ".join(item["text"] for item in artifact["constraints"])
            self.assertIn("No network, LLM, or external API calls", constraints)

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

    def test_confirm_write_rejects_disallowed_json_out_without_partial_workspace_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            tz = root / "owner_tz.md"
            tz.write_text("Build a deterministic planning helper.\n", encoding="utf-8")
            blocked_dir = root / "project-runtime" / "state"
            blocked_dir.mkdir(parents=True)
            json_out = blocked_dir / "product-intake.json"
            before = workspace_files(root)

            result = run_aso(
                "product",
                "intake",
                "--root",
                str(root),
                "--tz",
                str(tz),
                "--confirm-write",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("ASO_OUTPUT_PATH_FORBIDDEN", result.stderr)
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

    def test_confirm_write_pipeline_writes_only_product_runtime_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            answers_path = Path(tmp) / "answers.json"
            write_complete_answers(answers_path)
            before = workspace_files(root)

            intake_result = run_aso(
                "product",
                "intake",
                "--root",
                str(root),
                "--tz",
                str(FIXTURE_DIR / "analytics_parser_tz.md"),
                "--confirm-write",
            )
            self.assertEqual(intake_result.returncode, 0, intake_result.stdout + intake_result.stderr)
            intake_added = workspace_files(root) - before
            self.assertEqual(len(intake_added), 1, intake_added)
            intake_path = root / next(iter(intake_added))

            clarify_result = run_aso(
                "product",
                "clarify",
                "--root",
                str(root),
                "--from-intake",
                str(intake_path),
                "--confirm-write",
            )
            self.assertEqual(clarify_result.returncode, 0, clarify_result.stdout + clarify_result.stderr)

            before_spec = workspace_files(root)
            spec_result = run_aso(
                "product",
                "spec",
                "--root",
                str(root),
                "--from-intake",
                str(intake_path),
                "--answers",
                str(answers_path),
                "--confirm-write",
            )
            self.assertEqual(spec_result.returncode, 0, spec_result.stdout + spec_result.stderr)
            spec_added = workspace_files(root) - before_spec
            self.assertEqual(len(spec_added), 1, spec_added)
            spec_path = root / next(iter(spec_added))

            before_matrix = workspace_files(root)
            matrix_result = run_aso(
                "product",
                "capabilities",
                "--root",
                str(root),
                "--from-spec",
                str(spec_path),
                "--confirm-write",
            )
            self.assertEqual(matrix_result.returncode, 0, matrix_result.stdout + matrix_result.stderr)
            matrix_added = workspace_files(root) - before_matrix
            self.assertEqual(len(matrix_added), 1, matrix_added)
            matrix_path = root / next(iter(matrix_added))

            plan_result = run_aso(
                "product",
                "plan",
                "--root",
                str(root),
                "--from-spec",
                str(spec_path),
                "--from-capabilities",
                str(matrix_path),
                "--confirm-write",
            )
            self.assertEqual(plan_result.returncode, 0, plan_result.stdout + plan_result.stderr)

            added = workspace_files(root) - before
            self.assertEqual(len(added), 5, added)
            for written in added:
                self.assertTrue(written.startswith("project-runtime/product/"), written)
                self.assertTrue(written.endswith(".json"), written)

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

    def test_incomplete_tz_produces_open_questions_without_product_readiness_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            intake_out = Path(tmp) / "incomplete-intake.json"
            questions_out = Path(tmp) / "incomplete-open-questions.json"

            intake_result = run_aso(
                "product",
                "intake",
                "--root",
                str(root),
                "--tz",
                str(FIXTURE_DIR / "incomplete_tz.md"),
                "--dry-run",
                "--json-out",
                str(intake_out),
            )
            self.assertEqual(intake_result.returncode, 0, intake_result.stdout + intake_result.stderr)
            intake = json.loads(intake_out.read_text(encoding="utf-8"))
            self.assertEqual(intake["status"], "needs_clarification")
            missing = " ".join(item["text"] for item in intake["missing_information"])
            self.assertIn("Target users", missing)
            self.assertIn("Acceptance criteria", missing)

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
            questions = json.loads(questions_out.read_text(encoding="utf-8"))
            self.assertEqual(questions["artifact_type"], "OPEN_QUESTIONS")
            self.assertEqual(questions["status"], "needs_clarification")
            blocking_categories = {
                question["category"]
                for question in questions["questions"]
                if question["blocks_implementation"]
            }
            self.assertIn("product", blocking_categories)
            self.assertIn("users", blocking_categories)
            self.assertIn("acceptance", blocking_categories)
            raw_questions = json.dumps(questions, sort_keys=True)
            self.assertNotIn("ready_to_build", raw_questions)
            self.assertNotIn("mvp_ready", raw_questions)

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

    def test_spec_from_intake_and_answers_generates_linked_artifacts_and_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            intake_out = Path(tmp) / "intake.json"
            answers_path = Path(tmp) / "answers.json"
            spec_out = Path(tmp) / "product-spec.json"
            answers_path.write_text(
                json.dumps(
                    {
                        "product_name": "Marketplace Support Bot",
                        "required_secrets": ["TELEGRAM_BOT_TOKEN", {"name": "MARKETPLACE_API_KEY"}],
                    }
                ),
                encoding="utf-8",
            )

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

            result = run_aso(
                "product",
                "spec",
                "--root",
                str(root),
                "--from-intake",
                str(intake_out),
                "--answers",
                str(answers_path),
                "--dry-run",
                "--json-out",
                str(spec_out),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            artifact = json.loads(spec_out.read_text(encoding="utf-8"))
            self.assertEqual(artifact["artifact_type"], "PRODUCT_SPEC")
            self.assertEqual(artifact["product_name"], "Marketplace Support Bot")
            self.assertEqual(artifact["status"], "needs_clarification")
            self.assertTrue(artifact["blocks_implementation_start"])
            self.assertIn("This artifact does not claim implementation readiness", artifact["readiness_summary"])
            self.assertEqual(artifact["user_stories_artifact"]["artifact_type"], "USER_STORIES")
            self.assertEqual(artifact["acceptance_criteria_artifact"]["artifact_type"], "ACCEPTANCE_CRITERIA")
            self.assertEqual(
                artifact["user_stories_artifact"]["source_refs"][0]["artifact_id"],
                artifact["artifact_id"],
            )
            self.assertEqual(
                artifact["acceptance_criteria_artifact"]["criteria"][0]["user_story_id"],
                artifact["user_stories_artifact"]["stories"][0]["user_story_id"],
            )
            gaps = " ".join(gap["text"] for gap in artifact["open_gaps"])
            self.assertIn("Critical answer missing: target users.", gaps)
            self.assertIn("Critical answer missing: data model notes.", gaps)
            self.assertIn("Critical answer missing: acceptance summary.", gaps)
            secret_names = {secret["name"] for secret in artifact["required_secrets"]}
            self.assertIn("TELEGRAM_BOT_TOKEN", secret_names)
            self.assertIn("MARKETPLACE_API_KEY", secret_names)
            raw_artifact = json.dumps(artifact, sort_keys=True)
            self.assertNotIn("secret_value", raw_artifact)

    def test_spec_malformed_answers_fail_closed_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            intake_out = Path(tmp) / "intake.json"
            answers_path = Path(tmp) / "answers.json"
            spec_out = Path(tmp) / "should-not-exist.json"
            answers_path.write_text(
                json.dumps({"product_name": "Demo", "target_users": "owner"}),
                encoding="utf-8",
            )

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

            result = run_aso(
                "product",
                "spec",
                "--root",
                str(root),
                "--from-intake",
                str(intake_out),
                "--answers",
                str(answers_path),
                "--dry-run",
                "--json-out",
                str(spec_out),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("target_users must be a list of non-empty strings", result.stderr)
            self.assertFalse(spec_out.exists())

    def test_spec_malformed_answer_shapes_fail_closed_without_writes(self) -> None:
        malformed_cases = [
            (
                "non_object_root",
                ["not", "an", "object"],
                "expected JSON object",
            ),
            (
                "answers_not_object",
                {"answers": []},
                "answers field must contain a JSON object",
            ),
            (
                "unsupported_field",
                {"product_name": "Demo", "launch_now": True},
                "unsupported fields: launch_now",
            ),
            (
                "secret_value_field",
                {"required_secrets": [{"name": "OPENAI_API_KEY", "value": "sk-testsecretvalue"}]},
                "secret names only",
            ),
        ]
        for name, payload, expected_error in malformed_cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "workspace"
                root.mkdir()
                intake_out = Path(tmp) / "intake.json"
                answers_path = Path(tmp) / f"{name}-answers.json"
                spec_out = Path(tmp) / "should-not-exist.json"
                answers_path.write_text(json.dumps(payload), encoding="utf-8")

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
                before = workspace_files(root)

                result = run_aso(
                    "product",
                    "spec",
                    "--root",
                    str(root),
                    "--from-intake",
                    str(intake_out),
                    "--answers",
                    str(answers_path),
                    "--dry-run",
                    "--json-out",
                    str(spec_out),
                )

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(expected_error, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertFalse(spec_out.exists())
                self.assertEqual(before, workspace_files(root))

    def test_spec_rejects_secret_values_in_answers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            intake_out = Path(tmp) / "intake.json"
            answers_path = Path(tmp) / "answers.json"
            spec_out = Path(tmp) / "should-not-exist.json"
            token_value = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
            answers_path.write_text(
                json.dumps({"product_name": "Demo", "product_summary": f"Telegram token is {token_value}"}),
                encoding="utf-8",
            )

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

            result = run_aso(
                "product",
                "spec",
                "--root",
                str(root),
                "--from-intake",
                str(intake_out),
                "--answers",
                str(answers_path),
                "--dry-run",
                "--json-out",
                str(spec_out),
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("appears to contain secret values", result.stderr)
            self.assertNotIn(token_value, result.stderr)
            self.assertFalse(spec_out.exists())

    def test_capabilities_from_spec_generates_traceable_contract_without_completion_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            spec_path = Path(tmp) / "product-spec.json"
            matrix_out = Path(tmp) / "capability-matrix.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "artifact_id": "PRODUCT_SPEC-test",
                        "artifact_type": "PRODUCT_SPEC",
                        "schema_version": "1.0.0",
                        "package_version": "3.6.0",
                        "runtime_schema_version": "3.1.0",
                        "created_at": "2026-05-21T00:00:00Z",
                        "created_by": "aso",
                        "target_root": "project-runtime/product/",
                        "profile": "telegram_bot",
                        "readiness_mode": "mvp",
                        "status": "proposed",
                        "source_refs": [
                            {
                                "source_ref_id": "SRC-owner-decision",
                                "source_type": "artifact",
                                "title": "Owner decision cards artifact",
                                "artifact_id": "OWNER_DECISION_CARDS-test",
                            }
                        ],
                        "human_summary": "Planning-only product spec.",
                        "problem_statement": "Shop operators need Telegram order review and catalog updates.",
                        "requirements": [
                            {
                                "requirement_id": "REQ-001",
                                "description": "The product must support Telegram order review.",
                                "priority": "must",
                                "source_ref_ids": ["SRC-owner-decision"],
                                "capability_ids": ["CAP-001"],
                            },
                            {
                                "requirement_id": "REQ-002",
                                "description": "The product must update marketplace catalog stock after approval.",
                                "priority": "must",
                                "source_ref_ids": ["SRC-owner-decision"],
                                "capability_ids": ["CAP-002"],
                            },
                        ],
                        "external_integrations": [
                            {
                                "id": "INTEGRATION-001",
                                "text": "Telegram integration scope is planning-only; no external call was made.",
                                "source_ref_ids": ["SRC-owner-decision"],
                            }
                        ],
                        "required_secrets": [
                            {
                                "secret_id": "SECRET-001",
                                "name": "TELEGRAM_BOT_TOKEN",
                                "value_status": "not_collected",
                                "purpose": "Telegram bot access token name only.",
                            }
                        ],
                        "dependencies": [],
                        "open_gaps": [],
                        "blocks_implementation_start": False,
                        "user_stories_artifact": {
                            "stories": [
                                {
                                    "user_story_id": "US-001",
                                    "requirement_id": "REQ-001",
                                    "persona": "Shop operator",
                                    "story": "As a shop operator, I want to review Telegram orders.",
                                    "value": "Orders can be reviewed before future fulfillment work.",
                                    "priority": "must",
                                    "capability_ids": ["CAP-001"],
                                }
                            ]
                        },
                        "acceptance_criteria_artifact": {
                            "criteria": [
                                {
                                    "acceptance_criterion_id": "AC-001",
                                    "user_story_id": "US-001",
                                    "capability_id": "CAP-001",
                                    "statement": "Owner can review Telegram order flow evidence.",
                                    "verification_method": "owner_review",
                                    "expected_evidence": "Future governed implementation evidence.",
                                    "status": "proposed",
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = run_aso(
                "product",
                "capabilities",
                "--root",
                str(root),
                "--from-spec",
                str(spec_path),
                "--dry-run",
                "--json-out",
                str(matrix_out),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            artifact = json.loads(matrix_out.read_text(encoding="utf-8"))
            self.assertEqual(artifact["artifact_type"], "CAPABILITY_MATRIX")
            self.assertIn("planning contract", artifact["proof_boundary"])
            self.assertEqual(len(artifact["capabilities"]), 2)
            first = artifact["capabilities"][0]
            self.assertEqual(first["capability_id"], "CAP-001")
            self.assertEqual(first["name"], "Support Telegram order review")
            self.assertEqual(first["source_requirement_refs"], ["REQ-001"])
            self.assertEqual(first["requirement_ids"], ["REQ-001"])
            self.assertEqual(first["user_story_ids"], ["US-001"])
            self.assertEqual(first["source_user_story_refs"], ["US-001"])
            self.assertEqual(first["acceptance_criteria_refs"], ["AC-001"])
            self.assertEqual(first["verification_method"], "owner_review")
            self.assertIn("FUTURE-EVIDENCE-CAP-001", first["expected_evidence_refs"])
            self.assertEqual(first["required_integrations"], ["Telegram"])
            self.assertEqual(first["required_secrets"], ["TELEGRAM_BOT_TOKEN"])
            self.assertEqual(first["owner_decision_refs"], ["SRC-owner-decision"])
            self.assertIn("mvp", first["readiness_relevance"])
            allowed_statuses = {"proposed", "needs_clarification", "out_of_scope", "blocked", "ready_for_review"}
            for capability in artifact["capabilities"]:
                self.assertIn(capability["status"], allowed_statuses)
                self.assertNotIn(capability["status"], {"implemented", "mvp_ready", "product_pass", "final_acceptance", "checkpoint_done"})

    def test_plan_from_spec_and_capabilities_generates_non_executable_plan_with_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            spec_path = Path(tmp) / "product-spec.json"
            matrix_path = Path(tmp) / "capability-matrix.json"
            plan_out = Path(tmp) / "product-plan.json"

            spec_path.write_text(
                json.dumps(
                    {
                        "artifact_id": "PRODUCT_SPEC-test",
                        "artifact_type": "PRODUCT_SPEC",
                        "profile": "telegram_bot",
                        "readiness_mode": "business_ready",
                        "status": "needs_clarification",
                        "product_summary": "Telegram order review and marketplace stock approval.",
                        "problem_statement": "Operators need approved Telegram and marketplace workflows.",
                        "dependencies": [
                            {
                                "id": "DEPENDENCY-001",
                                "text": "Marketplace sandbox access owner is not confirmed.",
                                "source_ref_ids": ["SRC-owner-answers"],
                            }
                        ],
                        "open_gaps": [
                            {
                                "id": "GAP-001",
                                "text": "Owner has not confirmed approval policy for stock updates.",
                                "source_ref_ids": ["SRC-owner-answers"],
                            }
                        ],
                        "acceptance_summary": "Acceptance evidence remains an explicit gap.",
                        "blocks_implementation_start": True,
                    }
                ),
                encoding="utf-8",
            )
            matrix_path.write_text(
                json.dumps(
                    {
                        "artifact_id": "CAPABILITY_MATRIX-test",
                        "artifact_type": "CAPABILITY_MATRIX",
                        "profile": "telegram_bot",
                        "readiness_mode": "business_ready",
                        "capabilities": [
                            {
                                "capability_id": "CAP-001",
                                "name": "Support Telegram order review",
                                "description": "The product must support Telegram order review.",
                                "acceptance_criterion_ids": ["AC-001"],
                                "acceptance_criteria_refs": ["AC-001"],
                                "required_integrations": ["Telegram", "Marketplace API"],
                                "required_secrets": ["TELEGRAM_BOT_TOKEN", "MARKETPLACE_API_KEY"],
                                "risks": ["External integration scope requires later verification."],
                                "status": "needs_clarification",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_aso(
                "product",
                "plan",
                "--root",
                str(root),
                "--from-spec",
                str(spec_path),
                "--from-capabilities",
                str(matrix_path),
                "--dry-run",
                "--json-out",
                str(plan_out),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            artifact = json.loads(plan_out.read_text(encoding="utf-8"))
            self.assertEqual(artifact["artifact_type"], "PRODUCT_PLAN")
            self.assertEqual(artifact["status"], "needs_clarification")
            self.assertIn("REQUIREMENTS", artifact["recommended_lifecycle_starting_point"])
            self.assertEqual(artifact["suggested_workstreams"][0]["capability_ids"], ["CAP-001"])
            self.assertEqual(artifact["planned_workstreams"], artifact["suggested_workstreams"])
            self.assertIn("requirements_analyst", {role["role"] for role in artifact["candidate_roles"]})
            self.assertFalse(artifact["candidate_task_groups"][0]["is_executable"])
            self.assertFalse(artifact["candidate_task_groups"][0]["creates_task_packet"])
            blockers = " ".join(item["text"] for item in artifact["blocking_open_questions"])
            self.assertIn("approval policy for stock updates", blockers)
            decisions = " ".join(item["text"] for item in artifact["required_owner_decisions"])
            self.assertIn("TELEGRAM_BOT_TOKEN", decisions)
            self.assertEqual(artifact["suggested_domain_pack_profile"]["profile"], "telegram_bot")
            self.assertTrue(all(gate["blocks_plan_to_build"] for gate in artifact["readiness_mode_gates"]))
            self.assertIn("product spec", artifact["next_safe_aso_action"])
            self.assertEqual(artifact["implementation_start_claim"], "not_claimed_blocked_by_open_questions")
            self.assertIn("no_checkpoint_requests_or_proposals", artifact["non_executable_constraints"])
            self.assertIn("no_app_generation", artifact["non_executable_constraints"])
            self.assertFalse(artifact["creates_task_packets"])
            self.assertFalse(artifact["queues_dispatches"])
            self.assertFalse(artifact["executes_checkpoints"])
            self.assertFalse(artifact["performs_commits"])
            self.assertFalse(artifact["performs_deployments"])

            raw_artifact = json.dumps(artifact, sort_keys=True)
            self.assertNotIn("ready_to_build", raw_artifact)
            self.assertNotIn("task_packet_id", raw_artifact)
            self.assertNotIn("secret_value", raw_artifact)

    def test_plan_output_content_is_deterministic_for_same_spec_and_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            spec_path = Path(tmp) / "product-spec.json"
            matrix_path = Path(tmp) / "capability-matrix.json"
            first_out = Path(tmp) / "first-plan.json"
            second_out = Path(tmp) / "second-plan.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "artifact_id": "PRODUCT_SPEC-test",
                        "artifact_type": "PRODUCT_SPEC",
                        "profile": "api_service",
                        "readiness_mode": "mvp",
                        "status": "ready_for_review",
                        "product_summary": "API service for approved report exports.",
                        "problem_statement": "Operators need exportable report data.",
                        "dependencies": [],
                        "open_gaps": [],
                        "acceptance_summary": "Owner review plus checklist evidence.",
                        "blocks_implementation_start": False,
                    }
                ),
                encoding="utf-8",
            )
            matrix_path.write_text(
                json.dumps(
                    {
                        "artifact_id": "CAPABILITY_MATRIX-test",
                        "artifact_type": "CAPABILITY_MATRIX",
                        "profile": "api_service",
                        "readiness_mode": "mvp",
                        "capabilities": [
                            {
                                "capability_id": "CAP-002",
                                "name": "Export reports",
                                "description": "The product must export approved reports.",
                                "acceptance_criterion_ids": ["AC-002"],
                                "required_integrations": [],
                                "required_secrets": [],
                                "risks": [],
                                "status": "proposed",
                            },
                            {
                                "capability_id": "CAP-001",
                                "name": "Review report data",
                                "description": "The product must let operators review report data.",
                                "acceptance_criterion_ids": ["AC-001"],
                                "required_integrations": [],
                                "required_secrets": [],
                                "risks": [],
                                "status": "proposed",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            for output in (first_out, second_out):
                result = run_aso(
                    "product",
                    "plan",
                    "--root",
                    str(root),
                    "--from-spec",
                    str(spec_path),
                    "--from-capabilities",
                    str(matrix_path),
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
            self.assertEqual(
                [stream["capability_ids"][0] for stream in first["planned_workstreams"]],
                ["CAP-001", "CAP-002"],
            )
            self.assertEqual(first["suggested_domain_pack_profile"]["profile"], "backend_api")

    def test_product_dry_run_pipeline_writes_no_workspace_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            tz = root / "owner_tz.md"
            tz.write_text((FIXTURE_DIR / "analytics_parser_tz.md").read_text(encoding="utf-8"), encoding="utf-8")
            answers_path = Path(tmp) / "answers.json"
            write_complete_answers(answers_path)
            intake_out = Path(tmp) / "intake.json"
            questions_out = Path(tmp) / "open-questions.json"
            spec_out = Path(tmp) / "product-spec.json"
            matrix_out = Path(tmp) / "capability-matrix.json"
            plan_out = Path(tmp) / "product-plan.json"
            before = workspace_files(root)

            commands = [
                (
                    "intake",
                    [
                        "product",
                        "intake",
                        "--root",
                        str(root),
                        "--tz",
                        str(tz),
                        "--dry-run",
                        "--json-out",
                        str(intake_out),
                    ],
                ),
                (
                    "clarify",
                    [
                        "product",
                        "clarify",
                        "--root",
                        str(root),
                        "--from-intake",
                        str(intake_out),
                        "--dry-run",
                        "--json-out",
                        str(questions_out),
                    ],
                ),
                (
                    "spec",
                    [
                        "product",
                        "spec",
                        "--root",
                        str(root),
                        "--from-intake",
                        str(intake_out),
                        "--answers",
                        str(answers_path),
                        "--dry-run",
                        "--json-out",
                        str(spec_out),
                    ],
                ),
                (
                    "capabilities",
                    [
                        "product",
                        "capabilities",
                        "--root",
                        str(root),
                        "--from-spec",
                        str(spec_out),
                        "--dry-run",
                        "--json-out",
                        str(matrix_out),
                    ],
                ),
                (
                    "plan",
                    [
                        "product",
                        "plan",
                        "--root",
                        str(root),
                        "--from-spec",
                        str(spec_out),
                        "--from-capabilities",
                        str(matrix_out),
                        "--dry-run",
                        "--json-out",
                        str(plan_out),
                    ],
                ),
            ]

            for command_name, args in commands:
                with self.subTest(command=command_name):
                    result = run_aso(*args)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(before, workspace_files(root))

            self.assertEqual(json.loads(intake_out.read_text(encoding="utf-8"))["artifact_type"], "PRODUCT_INTAKE")
            self.assertEqual(json.loads(questions_out.read_text(encoding="utf-8"))["artifact_type"], "OPEN_QUESTIONS")
            self.assertEqual(json.loads(spec_out.read_text(encoding="utf-8"))["artifact_type"], "PRODUCT_SPEC")
            self.assertEqual(json.loads(matrix_out.read_text(encoding="utf-8"))["artifact_type"], "CAPABILITY_MATRIX")
            self.assertEqual(json.loads(plan_out.read_text(encoding="utf-8"))["artifact_type"], "PRODUCT_PLAN")

    def test_owner_runtime_roots_are_not_tracked(self) -> None:
        result = subprocess.run(
            ["git", "ls-files", "project-input", "project-runtime", "project-archive", ".venv"],
            check=False,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
