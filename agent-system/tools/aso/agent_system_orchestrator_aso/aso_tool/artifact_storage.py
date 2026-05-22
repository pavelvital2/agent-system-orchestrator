"""P5 artifact storage path helpers.

The helpers in this module are intentionally narrow: they validate and build
workspace-relative paths for governed artifact storage. They do not create
directories, write files, accept/reject artifacts, or integrate with lifecycle
state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath


ARTIFACT_STORAGE_ROOT = PurePosixPath("project-runtime/artifacts")
ARTIFACT_STORAGE_BUCKETS = ("raw", "candidates", "accepted", "rejected")
IMMUTABLE_STORAGE_BUCKETS = ARTIFACT_STORAGE_BUCKETS
ARTIFACT_STORAGE_TRANSITIONS = {
    "raw": ("candidates",),
    "candidates": ("accepted", "rejected"),
    "accepted": (),
    "rejected": (),
}

RAW_ARTIFACT_ROOT = ARTIFACT_STORAGE_ROOT / "raw"
CANDIDATE_ARTIFACT_ROOT = ARTIFACT_STORAGE_ROOT / "candidates"
ACCEPTED_ARTIFACT_ROOT = ARTIFACT_STORAGE_ROOT / "accepted"
REJECTED_ARTIFACT_ROOT = ARTIFACT_STORAGE_ROOT / "rejected"

_BUCKET_ROOTS = {
    "raw": RAW_ARTIFACT_ROOT,
    "candidates": CANDIDATE_ARTIFACT_ROOT,
    "accepted": ACCEPTED_ARTIFACT_ROOT,
    "rejected": REJECTED_ARTIFACT_ROOT,
}


class ArtifactPathError(ValueError):
    """Raised when an artifact storage path is not workspace-local and safe."""


@dataclass(frozen=True)
class ArtifactStorageLocation:
    """A validated workspace-relative artifact storage location."""

    bucket: str
    relative_path: str


def artifact_storage_roots() -> dict[str, str]:
    """Return canonical workspace-relative roots for P5 artifact storage."""

    return {bucket: root.as_posix() for bucket, root in _BUCKET_ROOTS.items()}


def is_immutable_bucket(bucket: str) -> bool:
    """Return whether a storage bucket is immutable after materialization."""

    _bucket_root(bucket)
    return bucket in IMMUTABLE_STORAGE_BUCKETS


def allowed_successor_buckets(bucket: str) -> tuple[str, ...]:
    """Return valid next buckets for the append-only storage classification flow."""

    _bucket_root(bucket)
    return ARTIFACT_STORAGE_TRANSITIONS[bucket]


def is_allowed_storage_transition(source_bucket: str, target_bucket: str) -> bool:
    """Return whether a source bucket may classify into a target bucket."""

    _bucket_root(target_bucket)
    return target_bucket in allowed_successor_buckets(source_bucket)


def safe_artifact_path(bucket: str, *parts: str) -> ArtifactStorageLocation:
    """Build a safe workspace-relative artifact path for a storage bucket.

    Every part must be a relative POSIX segment or subpath. Absolute paths,
    backslash-separated paths, empty segments, current-directory segments, and
    parent traversal are rejected before the path is joined under the governed
    bucket root.
    """

    root = _bucket_root(bucket)
    normalized_parts = _normalize_parts(parts)
    if not normalized_parts:
        raise ArtifactPathError("artifact path must include at least one member path")
    relative_path = (root / PurePosixPath(*normalized_parts)).as_posix()
    return ArtifactStorageLocation(bucket=bucket, relative_path=relative_path)


def safe_raw_path(*parts: str) -> ArtifactStorageLocation:
    """Build a safe path under project-runtime/artifacts/raw."""

    return safe_artifact_path("raw", *parts)


def safe_candidate_path(*parts: str) -> ArtifactStorageLocation:
    """Build a safe path under project-runtime/artifacts/candidates."""

    return safe_artifact_path("candidates", *parts)


def safe_accepted_path(*parts: str) -> ArtifactStorageLocation:
    """Build a safe path under project-runtime/artifacts/accepted."""

    return safe_artifact_path("accepted", *parts)


def safe_rejected_path(*parts: str) -> ArtifactStorageLocation:
    """Build a safe path under project-runtime/artifacts/rejected."""

    return safe_artifact_path("rejected", *parts)


def _bucket_root(bucket: str) -> PurePosixPath:
    if bucket not in _BUCKET_ROOTS:
        allowed = ", ".join(ARTIFACT_STORAGE_BUCKETS)
        raise ArtifactPathError(f"artifact storage bucket must be one of: {allowed}")
    return _BUCKET_ROOTS[bucket]


def _normalize_parts(parts: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw_part in parts:
        if not isinstance(raw_part, str):
            raise ArtifactPathError("artifact path parts must be strings")
        if "\x00" in raw_part:
            raise ArtifactPathError("artifact path must not contain NUL bytes")
        if "\\" in raw_part:
            raise ArtifactPathError("artifact path must use POSIX separators")
        if not raw_part.strip():
            raise ArtifactPathError("artifact path parts must be non-empty")

        for segment in raw_part.split("/"):
            if segment in ("", "."):
                raise ArtifactPathError("artifact path must not contain empty or current-directory segments")

        path = PurePosixPath(raw_part)
        if path.is_absolute():
            raise ArtifactPathError("artifact path must be relative")

        for segment in path.parts:
            if segment == "..":
                raise ArtifactPathError("artifact path must not contain parent traversal")
            normalized.append(segment)

    return tuple(normalized)
