from __future__ import annotations

import unittest
from pathlib import Path

import sys


ASO_DIR = Path(__file__).resolve().parents[1]
if str(ASO_DIR) not in sys.path:
    sys.path.insert(0, str(ASO_DIR))

from agent_system_orchestrator_aso.aso_tool import artifact_storage  # noqa: E402


class ArtifactStoragePathTests(unittest.TestCase):
    def test_storage_roots_are_workspace_local_runtime_artifact_paths(self) -> None:
        self.assertEqual(
            artifact_storage.artifact_storage_roots(),
            {
                "raw": "project-runtime/artifacts/raw",
                "candidates": "project-runtime/artifacts/candidates",
                "accepted": "project-runtime/artifacts/accepted",
                "rejected": "project-runtime/artifacts/rejected",
            },
        )

    def test_safe_artifact_path_builds_canonical_posix_path(self) -> None:
        location = artifact_storage.safe_candidate_path(
            "TASK_ASO_APM5_030",
            "candidate-001.json",
        )

        self.assertEqual(location.bucket, "candidates")
        self.assertEqual(
            location.relative_path,
            "project-runtime/artifacts/candidates/TASK_ASO_APM5_030/candidate-001.json",
        )

    def test_safe_artifact_path_rejects_escape_and_ambiguous_paths(self) -> None:
        invalid_paths = (
            ("raw", "../escape.md"),
            ("raw", "/absolute.md"),
            ("accepted", "TASK/../../escape.md"),
            ("rejected", "TASK\\windows.md"),
            ("candidates", ""),
            ("candidates", "."),
            ("candidates", "a//b"),
            ("candidates", "a/./b"),
            ("candidates", "./b"),
            ("candidates", "a/."),
            ("candidates", "a//"),
            ("candidates", "a/"),
            ("raw", "TASK", "..", "escape.md"),
        )

        for bucket, *parts in invalid_paths:
            with self.subTest(bucket=bucket, parts=parts):
                with self.assertRaises(artifact_storage.ArtifactPathError):
                    artifact_storage.safe_artifact_path(bucket, *parts)

    def test_safe_artifact_path_rejects_unknown_bucket(self) -> None:
        with self.assertRaises(artifact_storage.ArtifactPathError):
            artifact_storage.safe_artifact_path("quarantine", "artifact.md")

    def test_all_p5_storage_buckets_are_immutable_after_materialization(self) -> None:
        for bucket in artifact_storage.ARTIFACT_STORAGE_BUCKETS:
            with self.subTest(bucket=bucket):
                self.assertTrue(artifact_storage.is_immutable_bucket(bucket))

    def test_storage_flow_is_raw_to_candidate_to_terminal_classification(self) -> None:
        self.assertEqual(artifact_storage.allowed_successor_buckets("raw"), ("candidates",))
        self.assertEqual(
            artifact_storage.allowed_successor_buckets("candidates"),
            ("accepted", "rejected"),
        )
        self.assertEqual(artifact_storage.allowed_successor_buckets("accepted"), ())
        self.assertEqual(artifact_storage.allowed_successor_buckets("rejected"), ())
        self.assertTrue(artifact_storage.is_allowed_storage_transition("raw", "candidates"))
        self.assertTrue(artifact_storage.is_allowed_storage_transition("candidates", "accepted"))
        self.assertTrue(artifact_storage.is_allowed_storage_transition("candidates", "rejected"))
        self.assertFalse(artifact_storage.is_allowed_storage_transition("raw", "accepted"))
        self.assertFalse(artifact_storage.is_allowed_storage_transition("accepted", "rejected"))


if __name__ == "__main__":
    unittest.main()
