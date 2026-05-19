from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "aso.py"
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "state"
DAG_VALID = FIXTURE_ROOT / "dag_valid"


def run_dag(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "dag", *extra, "--root", str(root)],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def copy_dag_valid(tmp: str) -> Path:
    root = Path(tmp) / "workspace"
    shutil.copytree(DAG_VALID, root)
    return root


def load_registry(root: Path) -> dict[str, object]:
    return json.loads((root / "project-runtime" / "state" / "TASK_REGISTRY.json").read_text(encoding="utf-8"))


def write_registry(root: Path, payload: dict[str, object]) -> None:
    (root / "project-runtime" / "state" / "TASK_REGISTRY.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def tasks(payload: dict[str, object]) -> list[dict[str, object]]:
    content = payload["content"]
    if not isinstance(content, dict):
        raise AssertionError("registry content must be a dictionary")
    registry_tasks = content["tasks"]
    if not isinstance(registry_tasks, list):
        raise AssertionError("registry tasks must be a list")
    return registry_tasks


class DagCommandTests(unittest.TestCase):
    def test_help_declares_dag_commands(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "dag", "--help"],
            check=False,
            text=True,
            capture_output=True,
            cwd=REPO_ROOT,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("verify", result.stdout)
        self.assertIn("render", result.stdout)

    def test_valid_fixture_passes_and_does_not_edit_state(self) -> None:
        tracked = [path for path in DAG_VALID.rglob("*") if path.is_file()]
        mtimes_before = {path: path.stat().st_mtime_ns for path in tracked}

        result = run_dag(DAG_VALID, "verify")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ASO dag verify: PASSED", result.stdout)
        self.assertIn("Tasks: 3", result.stdout)
        self.assertIn("Edges: 2", result.stdout)
        self.assertEqual(mtimes_before, {path: path.stat().st_mtime_ns for path in tracked})

    def test_negative_fixtures_fail_with_stable_rule_ids(self) -> None:
        cases = {
            "dag_invalid_cycle": "DAG_DEPENDENCY_CYCLE",
            "dag_invalid_missing_dependency": "DAG_DEPENDENCY_MISSING",
            "dag_invalid_blocked_ready": "DAG_READY_TASK_BLOCKED_BY_DEPENDENCY",
            "dag_invalid_audit_passed_dependency_ready": "DAG_DEPENDENCY_AUDIT_PASSED_WITHOUT_CHECKPOINT",
        }
        for fixture_name, rule_id in cases.items():
            with self.subTest(fixture_name=fixture_name):
                result = run_dag(FIXTURE_ROOT / fixture_name, "verify")

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("ASO dag verify: FAILED", result.stdout)
                self.assertIn(rule_id, result.stdout)

    def test_mermaid_render_writes_deterministic_tmp_output(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            out = Path(tmp) / "dag.mmd"

            first = run_dag(DAG_VALID, "render", "--format", "mermaid", "--out", str(out))
            first_text = out.read_text(encoding="utf-8")
            second = run_dag(DAG_VALID, "render", "--format", "mermaid", "--out", str(out))
            second_text = out.read_text(encoding="utf-8")

        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(first_text, second_text)
        self.assertTrue(first_text.startswith("flowchart TD\n"))
        self.assertIn('n0["TASK_DAG_LEAF\\nLeaf task\\nready"]', first_text)
        self.assertIn("n2 --> n1", first_text)

    def test_dot_render_prints_stdout(self) -> None:
        result = run_dag(DAG_VALID, "render", "--format", "dot")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("digraph TASK_DAG {\n"))
        self.assertIn("rankdir=LR;", result.stdout)
        self.assertIn("n2 -> n1;", result.stdout)

    def test_duplicate_task_id_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_dag_valid(tmp)
            payload = load_registry(root)
            registry_tasks = tasks(payload)
            duplicate = dict(registry_tasks[-1])
            duplicate["task_title"] = "Duplicate leaf"
            registry_tasks.append(duplicate)
            write_registry(root, payload)

            result = run_dag(root, "verify")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("DAG_TASK_ID_DUPLICATE", result.stdout)

    def test_checkpoint_done_dependency_requires_checkpoint_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_dag_valid(tmp)
            payload = load_registry(root)
            middle = tasks(payload)[1]
            middle["checkpoint_ref"] = "NONE"
            write_registry(root, payload)

            result = run_dag(root, "verify")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("DAG_DEPENDENCY_CHECKPOINT_EVIDENCE_INCOMPLETE", result.stdout)

    def test_requester_return_metadata_inconsistency_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_dag_valid(tmp)
            payload = load_registry(root)
            leaf = tasks(payload)[-1]
            leaf["return_to_requester_after_audit_pass"] = False
            leaf["return_to_role_after_audit_pass"] = "developer"
            write_registry(root, payload)

            result = run_dag(root, "verify")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("DAG_REQUESTER_RETURN_METADATA_INCONSISTENT", result.stdout)

    def test_render_sanitizes_untrusted_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_dag_valid(tmp)
            payload = load_registry(root)
            tasks(payload)[0]["task_title"] = 'bad"] --> injected["<script>'
            write_registry(root, payload)

            result = run_dag(root, "render", "--format", "mermaid")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("bad? --? injected?script?", result.stdout)
        self.assertNotIn("<script>", result.stdout)
        self.assertNotIn('"] --> injected["', result.stdout)

    def test_forbidden_runtime_output_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_dag_valid(tmp)
            out = root / "project-runtime" / "dag.mmd"

            result = run_dag(root, "render", "--format", "mermaid", "--out", str(out))

            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("forbidden output path", result.stderr)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
