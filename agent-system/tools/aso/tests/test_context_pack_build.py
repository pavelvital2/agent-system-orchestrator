from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
TASK_FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "task_packets"


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


class ContextPackBuildCommandTests(unittest.TestCase):
    def test_valid_task_packet_builds_valid_context_pack(self) -> None:
        task_packet = TASK_FIXTURE_ROOT / "valid_context_pack_builder_task.md"

        result = run_aso("context-pack", "build", "--task-packet", str(task_packet), "--root", str(REPO_ROOT), "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        proposal = json.loads(result.stdout)
        self.assertEqual(proposal["task_id"], "TASK_FIXTURE_CONTEXT_PACK_BUILD_VALID")
        self.assertTrue(proposal["read_only"])
        self.assertEqual(proposal["proposal_mode"], "dry_run")
        self.assertIn("required_docs_reason", proposal)
        self.assertIn("section_hints", proposal)
        self.assertGreaterEqual(proposal["context_budget"]["max_docs"], len(proposal["required_docs"]))
        self.assertTrue(all("sha256" in doc for doc in proposal["required_docs"]))

        with tempfile.TemporaryDirectory() as tmp:
            context_pack = Path(tmp) / "context-pack.json"
            context_pack.write_text(json.dumps(proposal), encoding="utf-8")
            validation = run_aso("validate-context-pack", str(context_pack), "--root", str(REPO_ROOT), "--strict")

        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
        self.assertIn("ASO validate-context-pack: PASSED", validation.stdout)

    def test_json_out_writes_only_explicit_proposal_path(self) -> None:
        task_packet = TASK_FIXTURE_ROOT / "valid_context_pack_builder_task.md"
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "proposal.json"

            result = run_aso(
                "context-pack",
                "build",
                "--task-packet",
                str(task_packet),
                "--root",
                str(REPO_ROOT),
                "--strict",
                "--json-out",
                str(json_out),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")
            proposal = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(proposal["task_id"], "TASK_FIXTURE_CONTEXT_PACK_BUILD_VALID")

    def test_forbidden_root_task_packet_fails(self) -> None:
        task_packet = TASK_FIXTURE_ROOT / "bad_context_pack_builder_forbidden_root.md"

        result = run_aso("context-pack", "build", "--task-packet", str(task_packet), "--root", str(REPO_ROOT), "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        report = json.loads(result.stderr)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["findings"][0]["rule_id"], "CPB-BUILD-002")

    def test_whole_project_task_packet_fails(self) -> None:
        task_packet = TASK_FIXTURE_ROOT / "bad_context_pack_builder_whole_project.md"

        result = run_aso("context-pack", "build", "--task-packet", str(task_packet), "--root", str(REPO_ROOT), "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        report = json.loads(result.stderr)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["findings"][0]["rule_id"], "CPB-BUILD-003")

    def test_missing_required_doc_fails_under_strict(self) -> None:
        task_packet = TASK_FIXTURE_ROOT / "bad_context_pack_builder_missing_doc.md"

        result = run_aso("context-pack", "build", "--task-packet", str(task_packet), "--root", str(REPO_ROOT), "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        report = json.loads(result.stderr)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["findings"][0]["rule_id"], "CPB-BUILD-005")

    def test_read_inputs_add_only_accepted_packages_and_rendered_views(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            doc = root / "docs/source.md"
            accepted = root / "project-runtime/artifacts/accepted/TASK_DEMO/manifest.json"
            rendered = root / "project-runtime/rendered/TASK_DEMO/context.md"
            doc.parent.mkdir(parents=True)
            accepted.parent.mkdir(parents=True)
            rendered.parent.mkdir(parents=True)
            doc.write_text("# Source\n", encoding="utf-8")
            accepted.write_text('{"status":"accepted"}\n', encoding="utf-8")
            rendered.write_text("# Rendered context\n", encoding="utf-8")
            task_packet = root / "TASK_DEMO.md"
            task_packet.write_text(
                """# TASK PACKET

```text
TASK_ID: TASK_DEMO
```

## Required docs

- `docs/source.md`

## Read inputs

- `project-runtime/artifacts/accepted/TASK_DEMO/manifest.json`
- `project-runtime/rendered/TASK_DEMO/context.md`

## Forbidden write paths

```text
project-runtime/**
```
""",
                encoding="utf-8",
            )

            result = run_aso("context-pack", "build", "--task-packet", str(task_packet), "--root", str(root), "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        proposal = json.loads(result.stdout)
        paths = {doc["path"] for doc in proposal["required_docs"]}
        self.assertIn("project-runtime/artifacts/accepted/TASK_DEMO/manifest.json", paths)
        self.assertIn("project-runtime/rendered/TASK_DEMO/context.md", paths)
        self.assertEqual(
            proposal["accepted_artifact_packages"],
            ["project-runtime/artifacts/accepted/TASK_DEMO/manifest.json"],
        )
        self.assertEqual(proposal["rendered_views"], ["project-runtime/rendered/TASK_DEMO/context.md"])

    def test_read_inputs_reject_candidate_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            doc = root / "docs/source.md"
            candidate = root / "project-runtime/artifacts/candidates/TASK_DEMO/manifest.json"
            doc.parent.mkdir(parents=True)
            candidate.parent.mkdir(parents=True)
            doc.write_text("# Source\n", encoding="utf-8")
            candidate.write_text('{"status":"candidate"}\n', encoding="utf-8")
            task_packet = root / "TASK_DEMO.md"
            task_packet.write_text(
                """# TASK PACKET

```text
TASK_ID: TASK_DEMO
```

## Required docs

- `docs/source.md`

## Read inputs

- `project-runtime/artifacts/candidates/TASK_DEMO/manifest.json`
""",
                encoding="utf-8",
            )

            result = run_aso("context-pack", "build", "--task-packet", str(task_packet), "--root", str(root), "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stderr)
        self.assertEqual(report["status"], "failed")
        self.assertIn("CPB-BUILD-008", {finding["rule_id"] for finding in report["findings"]})

    def test_read_inputs_reject_explicitly_forbidden_accepted_and_rendered_paths(self) -> None:
        cases = (
            (
                "project-runtime/artifacts/accepted/TASK_DEMO/manifest.json",
                "project-runtime/artifacts/accepted/",
            ),
            (
                "project-runtime/rendered/TASK_DEMO/context.md",
                "project-runtime/rendered/",
            ),
        )
        for runtime_path, forbidden_path in cases:
            with self.subTest(runtime_path=runtime_path), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "workspace"
                doc = root / "docs/source.md"
                runtime_doc = root / runtime_path
                doc.parent.mkdir(parents=True)
                runtime_doc.parent.mkdir(parents=True)
                doc.write_text("# Source\n", encoding="utf-8")
                runtime_doc.write_text("# Runtime context\n", encoding="utf-8")
                task_packet = root / "TASK_DEMO.md"
                task_packet.write_text(
                    f"""# TASK PACKET

```text
TASK_ID: TASK_DEMO
```

## Required docs

- `docs/source.md`

## Read inputs

- `{runtime_path}`

## Forbidden write paths

```text
project-runtime/**
{forbidden_path}
```
""",
                    encoding="utf-8",
                )

                result = run_aso(
                    "context-pack",
                    "build",
                    "--task-packet",
                    str(task_packet),
                    "--root",
                    str(root),
                    "--strict",
                )

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertEqual(result.stdout, "")
                report = json.loads(result.stderr)
                self.assertEqual(report["status"], "failed")
                self.assertIn("CPB-BUILD-002", {finding["rule_id"] for finding in report["findings"]})


if __name__ == "__main__":
    unittest.main()
