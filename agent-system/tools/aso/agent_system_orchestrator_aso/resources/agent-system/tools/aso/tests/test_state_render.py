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
P2_VALID_WORKSPACE = REPO_ROOT / "agent-system" / "tests" / "fixtures" / "state" / "p2_valid_workspace"
sys.path.insert(0, str(CLI.parent))

from agent_system_orchestrator_aso.aso_tool.commands import state_init, state_render  # noqa: E402


def load_sidecar(root: Path, name: str) -> dict[str, object]:
    return json.loads((root / "project-runtime" / "state" / name).read_text(encoding="utf-8"))


def write_sidecar(root: Path, name: str, payload: dict[str, object]) -> None:
    (root / "project-runtime" / "state" / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def fixture_task(task_id: str, status: str, task_packet: str) -> dict[str, object]:
    return {
        "accepted_files": [],
        "audit_refs": [],
        "branch": "NONE",
        "checkpoint_ref": "NONE",
        "commit_hash": "NONE",
        "correction_links": [],
        "created_at": "2026-05-21T00:00:00Z",
        "dependencies": [],
        "owner_role": "developer",
        "push_status": "not_required",
        "requested_by_role": "NONE",
        "requested_by_task": "NONE",
        "research_question_id": "NONE",
        "result_refs": [],
        "return_task_after_audit_pass": "NONE",
        "return_to_requester_after_audit_pass": False,
        "return_to_role_after_audit_pass": "none",
        "status": status,
        "task_id": task_id,
        "task_kind": "normal",
        "task_packet": task_packet,
        "task_title": "State render fixture task",
        "task_type": "developer",
        "updated_at": "2026-05-21T00:00:00Z",
    }


def run_aso(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def write_tz_file(root: Path) -> None:
    tz_path = root / "project-input" / "TZ.md"
    tz_path.parent.mkdir(parents=True, exist_ok=True)
    tz_path.write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")


class StateRenderCommandTests(unittest.TestCase):
    def test_materialized_view_types_cover_state_init_sidecars(self) -> None:
        init_sidecar_types = {filename.removesuffix(".json") for filename in state_init.SIDECAR_FILENAMES}

        self.assertEqual(len(init_sidecar_types), 9)
        self.assertEqual(set(state_render.MATERIALIZED_VIEW_TYPES), init_sidecar_types)
        self.assertIn("CHECKPOINT_STATE", state_render.MATERIALIZED_VIEW_TYPES)
        self.assertIn("SCHEMA_MANIFEST", state_render.MATERIALIZED_VIEW_TYPES)

    def test_help_declares_state_render(self) -> None:
        result = run_aso("state", "render", "--help")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("--format", result.stdout)
        self.assertIn("--out", result.stdout)
        self.assertIn("--confirm-write", result.stdout)

    def test_initialized_workspace_renders_deterministic_markdown_to_tmp(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz_file(root)
            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Render Test",
                "--project-slug",
                "render-test",
                "--tz",
                "project-input/TZ.md",
                "--confirm-write",
            )
            out = Path(tmp) / "state-report.md"

            first = run_aso("state", "render", "--root", str(root), "--format", "markdown", "--out", str(out))
            first_text = out.read_text(encoding="utf-8")
            second = run_aso("state", "render", "--root", str(root), "--format", "markdown", "--out", str(out))
            second_text = out.read_text(encoding="utf-8")

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(first_text, second_text)
        self.assertTrue(first_text.startswith("# ASO Runtime State Report\n"))
        self.assertIn("Runtime schema: 3.2.0", first_text)

    def test_json_render_reports_schema_health(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz_file(root)
            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-slug",
                "json-render",
                "--tz",
                "project-input/TZ.md",
                "--confirm-write",
            )
            out = root / "project-runtime" / "rendered" / "state-report.json"

            result = run_aso("state", "render", "--root", str(root), "--format", "json", "--out", str(out))
            report = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["command"], "state render")
        self.assertTrue(report["read_only"])
        self.assertEqual(report["runtime_schema"]["active_version"], "3.2.0")
        self.assertEqual(report["runtime_schema"]["required_sidecars_missing"], [])
        self.assertIn("SCHEMA_MANIFEST", report["sidecars"])

    def test_p2_fixture_render_reports_current_schema_without_mutating_state(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "p2-workspace"
            shutil.copytree(P2_VALID_WORKSPACE, root)
            for sidecar in (root / "project-runtime" / "state").glob("*.json"):
                sidecar_payload = json.loads(sidecar.read_text(encoding="utf-8"))
                sidecar_payload["schema_version"] = "3.2.0"
                sidecar_payload["runtime_schema_version"] = "3.2.0"
                content = sidecar_payload.get("content")
                if isinstance(content, dict) and "runtime_schema_version" in content:
                    content["runtime_schema_version"] = "3.2.0"
                sidecar.write_text(json.dumps(sidecar_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            (root / "project-input").mkdir(exist_ok=True)
            (root / "project-input" / "TZ.md").write_text("# TZ\n\nTIMEZONE: Europe/Moscow\n", encoding="utf-8")
            project_state = root / "project-runtime" / "state" / "PROJECT_STATE.json"
            payload = json.loads(project_state.read_text(encoding="utf-8"))
            content = payload["content"]
            self.assertIsInstance(content, dict)
            content["tz_path"] = "project-input/TZ.md"
            project_state.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            next_action = root / "project-runtime" / "state" / "NEXT_ACTION.json"
            next_payload = json.loads(next_action.read_text(encoding="utf-8"))
            next_content = next_payload["content"]
            self.assertIsInstance(next_content, dict)
            next_content["action_type"] = "correction"
            next_content["action_semantic"] = "normal"
            next_content["dependency_status"] = "ready"
            next_action.write_text(json.dumps(next_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            tracked = [path for path in root.rglob("*") if path.is_file()]
            mtimes_before = {path: path.stat().st_mtime_ns for path in tracked}
            out = Path(tmp) / "p2-state-report.json"

            result = run_aso(
                "state",
                "render",
                "--root",
                str(root),
                "--format",
                "json",
                "--out",
                str(out),
            )
            report = json.loads(out.read_text(encoding="utf-8"))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(report["runtime_schema"]["current_p2_state"])
            self.assertEqual(report["runtime_schema"]["migration_available_sidecars"], [])
            self.assertEqual(report["runtime_schema"]["unsupported_sidecars"], [])
            self.assertEqual(mtimes_before, {path: path.stat().st_mtime_ns for path in tracked})

    def test_forbidden_output_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz_file(root)
            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-slug",
                "bad-out",
                "--tz",
                "project-input/TZ.md",
                "--confirm-write",
            )
            out = root / "project-runtime" / "state-report.md"

            result = run_aso("state", "render", "--root", str(root), "--out", str(out))

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("ASO_OUTPUT_PATH_FORBIDDEN", result.stderr)

    def test_confirm_write_materializes_markdown_views_from_json_sidecars(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz_file(root)
            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-name",
                "Materialize Test",
                "--project-slug",
                "materialize-test",
                "--tz",
                "project-input/TZ.md",
                "--confirm-write",
            )
            lint_json = Path(tmp) / "lint-before.json"
            before_lint = run_aso(
                "lint",
                "--root",
                str(root),
                "--mode",
                "workspace",
                "--strict",
                "--json-out",
                str(lint_json),
            )
            before_lint_report = json.loads(lint_json.read_text(encoding="utf-8"))
            first = run_aso("state", "render", "--root", str(root), "--confirm-write")
            first_report = json.loads(first.stdout)
            sidecar_names = sorted(path.stem for path in (root / "project-runtime" / "state").glob("*.json"))
            project_state = root / "project-runtime" / "PROJECT_STATE.md"
            first_text = project_state.read_text(encoding="utf-8")
            materialized_view_texts = {
                path.stem: path.read_text(encoding="utf-8")
                for path in (root / "project-runtime").glob("*.md")
                if (root / "project-runtime" / "state" / f"{path.stem}.json").is_file()
            }
            second = run_aso("state", "render", "--root", str(root), "--confirm-write")
            second_text = project_state.read_text(encoding="utf-8")
            after_status = run_aso("status", "--root", str(root), "--mode", "workspace")
            after_lint = run_aso("lint", "--root", str(root), "--mode", "workspace", "--strict")
            after_doctor = run_aso("doctor", "--root", str(root), "--mode", "workspace", "--strict")

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(before_lint.returncode, 3, before_lint.stdout + before_lint.stderr)
        self.assertIn("LINT_IO_004", before_lint.stdout)
        self.assertIn("aso state render --root WORKSPACE --confirm-write", before_lint.stdout)
        self.assertIn(
            "aso state render --root WORKSPACE --confirm-write",
            before_lint_report["findings"][0]["recommendation"],
        )
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(first_report["status"], "written")
        self.assertEqual(len(sidecar_names), 9)
        self.assertEqual(first_report["summary"]["views_written"], 9)
        self.assertEqual(sorted(item["sidecar_type"] for item in first_report["writes"]), sidecar_names)
        self.assertEqual(sorted(materialized_view_texts), sidecar_names)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(first_text, second_text)
        self.assertTrue(first_text.startswith("DERIVED VIEW.\n"))
        self.assertIn("Source: project-runtime/state/PROJECT_STATE.json", first_text)
        self.assertIn("Do not edit this file directly.", first_text)
        self.assertIn("Canonical state is JSON sidecar.", first_text)
        self.assertIn("PROJECT_SLUG: materialize-test", first_text)
        for sidecar_name, view_text in materialized_view_texts.items():
            self.assertTrue(view_text.startswith("DERIVED VIEW.\n"), sidecar_name)
            self.assertIn(f"Source: project-runtime/state/{sidecar_name}.json", view_text)
            self.assertIn("Canonical state is JSON sidecar.", view_text)
        self.assertIn("CHECKPOINT_STATUS: not_required", materialized_view_texts["CHECKPOINT_STATE"])
        self.assertIn("STATE_ROOT: project-runtime/state", materialized_view_texts["SCHEMA_MANIFEST"])
        self.assertEqual(after_status.returncode, 0, after_status.stdout + after_status.stderr)
        self.assertEqual(after_lint.returncode, 0, after_lint.stdout + after_lint.stderr)
        self.assertEqual(after_doctor.returncode, 0, after_doctor.stdout + after_doctor.stderr)

    def test_confirm_write_refreshes_stale_checkpoint_next_action_from_active_running_task(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "p2-workspace"
            shutil.copytree(P2_VALID_WORKSPACE, root)
            write_tz_file(root)
            active_task_id = "TASK_ACTIVE_LIFECYCLE"
            old_task_id = "TASK_OLD_CHECKPOINT_DONE"
            active_packet = f"project-runtime/tasks/active/{active_task_id}.md"
            old_packet = f"project-runtime/tasks/active/{old_task_id}.md"

            registry = load_sidecar(root, "TASK_REGISTRY.json")
            registry["content"]["tasks"] = [
                fixture_task(old_task_id, "checkpoint_done", old_packet),
                fixture_task(active_task_id, "running", active_packet),
            ]
            registry["content"]["tasks"][0]["audit_refs"] = ["project-runtime/results/audit/AUDIT_RESULT_OLD_ATTEMPT_001.md"]
            write_sidecar(root, "TASK_REGISTRY.json", registry)

            accepted = load_sidecar(root, "ACCEPTED_ARTIFACTS.json")
            accepted["content"]["artifacts"] = []
            write_sidecar(root, "ACCEPTED_ARTIFACTS.json", accepted)

            project_state = load_sidecar(root, "PROJECT_STATE.json")
            project_state["content"].update(
                {
                    "tz_path": "project-input/TZ.md",
                    "current_phase": "implementation",
                    "project_status": "active",
                    "active_branches": [],
                    "active_blockers": [],
                    "checkpoint_blocked_by": [],
                    "checkpoint_eligibility": "not_applicable",
                    "checkpoint_eligibility_status": "not_checked",
                    "project_checkpoint_status": "not_required",
                }
            )
            write_sidecar(root, "PROJECT_STATE.json", project_state)

            current_gate = load_sidecar(root, "CURRENT_GATE.json")
            current_gate["content"].update(
                {
                    "status": "open",
                    "task_id": "NONE",
                    "task_packet": "NONE",
                    "required_next_role": "none",
                    "checkpoint_eligibility": "not_applicable",
                    "checkpoint_eligibility_status": "not_checked",
                    "project_checkpoint_status": "not_required",
                }
            )
            write_sidecar(root, "CURRENT_GATE.json", current_gate)

            next_action = load_sidecar(root, "NEXT_ACTION.json")
            next_action["content"].update(
                {
                    "action_type": "update_state",
                    "target_role": "orchestrator",
                    "task_id": old_task_id,
                    "task_packet": old_packet,
                    "dependency_status": "ready",
                    "blocked_by": [],
                    "action_semantic": "normal",
                    "checkpoint_policy": "local_only",
                    "checkpoint_preflight_required": True,
                    "checkpoint_receipt_required": True,
                }
            )
            write_sidecar(root, "NEXT_ACTION.json", next_action)

            render = run_aso("state", "render", "--root", str(root), "--confirm-write")
            refreshed = load_sidecar(root, "NEXT_ACTION.json")["content"]
            plan_json = Path(tmp) / "plan-next.json"
            plan = run_aso("plan-next", "--root", str(root), "--strict", "--json-out", str(plan_json))
            verify = run_aso("state", "verify", "--root", str(root), "--strict")

            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            self.assertEqual(refreshed["task_id"], active_task_id)
            self.assertEqual(refreshed["action_type"], "route_result")
            self.assertEqual(refreshed["checkpoint_policy"], "no_checkpoint")
            self.assertFalse(refreshed["checkpoint_preflight_required"])
            plan_report = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan_report["task_id"], active_task_id)
            self.assertEqual(plan_report["recommended_next_action"], "WAIT_FOR_RESULT")
            self.assertNotEqual(plan_report["recommended_next_action"], "CHECKPOINT_PREFLIGHT")
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)

    def test_confirm_write_rejects_report_out_combination(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            write_tz_file(root)
            init = run_aso(
                "state",
                "init",
                "--root",
                str(root),
                "--project-slug",
                "bad-combo",
                "--tz",
                "project-input/TZ.md",
                "--confirm-write",
            )
            result = run_aso(
                "state",
                "render",
                "--root",
                str(root),
                "--confirm-write",
                "--out",
                str(Path(tmp) / "report.md"),
            )

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("--confirm-write cannot be combined with --out", result.stderr)


if __name__ == "__main__":
    unittest.main()
