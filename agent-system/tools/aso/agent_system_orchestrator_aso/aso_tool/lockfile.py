"""Project Factory aso.lock generation and validation helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import runtime_schema_contracts


LOCKFILE_NAME = "aso.lock"
LOCKFILE_VERSION = "1.0"
PACKAGE_NAME = "agent-system-orchestrator"
PACKAGE_VERSION = runtime_schema_contracts.ACTIVE_PACKAGE_VERSION
RUNTIME_SCHEMA_VERSION = runtime_schema_contracts.ACTIVE_RUNTIME_SCHEMA_VERSION
COMPATIBLE_ENGINE_VERSION_TUPLES = (
    (PACKAGE_VERSION, RUNTIME_SCHEMA_VERSION),
    ("3.7.3", "3.1.1"),
    ("3.7.2", "3.1.0"),
    ("3.7.1", "3.1.0"),
    ("3.6.1", "3.1.0"),
    ("3.6.0", "3.1.0"),
    ("3.5.0", "3.1.0"),
    ("3.4.0", "3.1.0"),
    ("3.3.0", "3.0.0"),
    ("3.2.0", "3.0.0"),
)
COMPATIBLE_PACKAGE_VERSIONS = tuple(
    dict.fromkeys(package_version for package_version, _runtime_schema in COMPATIBLE_ENGINE_VERSION_TUPLES)
)
COMPATIBLE_RUNTIME_SCHEMA_VERSIONS = tuple(
    dict.fromkeys(runtime_schema for _package_version, runtime_schema in COMPATIBLE_ENGINE_VERSION_TUPLES)
)
PACKAGE_SOURCE = "https://github.com/pavelvital2/agent-system-orchestrator"
SUPPORTED_ENGINE_MODES = ("vendored", "reference")
DEFAULT_ENGINE_MODE = "vendored"
DEFAULT_PROFILE = "generic"
DEFAULT_BRANCH = "main"
REQUIRED_PUBLICATION_ROOTS = (
    "project-input/",
    "project-runtime/",
    "project-archive/",
    ".venv/",
)

RULE_MISSING_FILE = "ASO_LOCK_001"
RULE_INVALID_JSON = "ASO_LOCK_002"
RULE_ROOT_OBJECT = "ASO_LOCK_003"
RULE_UNSUPPORTED_LOCKFILE_VERSION = "ASO_LOCK_004"
RULE_MISSING_OBJECT = "ASO_LOCK_005"
RULE_MISSING_FIELD = "ASO_LOCK_006"
RULE_INVALID_FIELD = "ASO_LOCK_007"
RULE_UNSUPPORTED_RUNTIME_SCHEMA = "ASO_LOCK_008"
RULE_UNSUPPORTED_ENGINE_MODE = "ASO_LOCK_009"
RULE_PUBLICATION_ROOT_MISSING = "ASO_LOCK_010"
RULE_UNSUPPORTED_PACKAGE_NAME = "ASO_LOCK_011"
RULE_UNSUPPORTED_PACKAGE_VERSION = "ASO_LOCK_012"


@dataclass(frozen=True)
class LockfileFinding:
    """Deterministic validation finding for aso.lock."""

    rule_id: str
    path: str
    message: str
    evidence: str

    def to_json(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "path": self.path,
            "message": self.message,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class LockfileValidationResult:
    """Validation result returned by lockfile helpers."""

    ok: bool
    findings: tuple[LockfileFinding, ...]

    @property
    def errors(self) -> tuple[LockfileFinding, ...]:
        return self.findings

    def to_json(self) -> dict[str, object]:
        return {
            "status": "pass" if self.ok else "fail",
            "findings": [finding.to_json() for finding in self.findings],
        }


def _finding(rule_id: str, path: str, message: str, evidence: object) -> LockfileFinding:
    return LockfileFinding(rule_id, path, message, str(evidence))


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def generate_lockfile(
    *,
    project_name: str,
    project_slug: str,
    profile: str = DEFAULT_PROFILE,
    repo_url: str | None = None,
    default_branch: str = DEFAULT_BRANCH,
    package_version: str = PACKAGE_VERSION,
    package_source: str = PACKAGE_SOURCE,
    runtime_schema: str = RUNTIME_SCHEMA_VERSION,
    engine_mode: str = DEFAULT_ENGINE_MODE,
    ignored_roots: tuple[str, ...] = REQUIRED_PUBLICATION_ROOTS,
    forbidden_tracked_roots: tuple[str, ...] = REQUIRED_PUBLICATION_ROOTS,
) -> dict[str, object]:
    """Build the canonical Project Factory lockfile dictionary."""

    return {
        "lockfile_version": LOCKFILE_VERSION,
        "aso_engine": {
            "package_name": PACKAGE_NAME,
            "version": package_version,
            "runtime_schema": runtime_schema,
            "source": package_source,
            "engine_mode": engine_mode,
        },
        "project": {
            "name": project_name,
            "slug": project_slug,
            "profile": profile,
            "repo_url": repo_url,
            "default_branch": default_branch,
        },
        "publication_boundary": {
            "ignored_roots": list(ignored_roots),
            "forbidden_tracked_roots": list(forbidden_tracked_roots),
        },
    }


def lockfile_json(lockfile: dict[str, object]) -> str:
    """Render an aso.lock document with stable formatting."""

    return json.dumps(lockfile, indent=2, sort_keys=False) + "\n"


def write_lockfile(path: Path, lockfile: dict[str, object]) -> None:
    """Write an aso.lock document with deterministic JSON formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(lockfile_json(lockfile), encoding="utf-8")


def read_lockfile(path: Path) -> object:
    """Read and decode an aso.lock JSON document."""

    return json.loads(path.read_text(encoding="utf-8"))


def validate_lockfile_path(path: Path) -> LockfileValidationResult:
    """Validate an aso.lock file from disk."""

    if not path.is_file():
        return LockfileValidationResult(
            False,
            (
                _finding(
                    RULE_MISSING_FILE,
                    str(path),
                    "aso.lock is missing.",
                    path,
                ),
            ),
        )

    try:
        lockfile = read_lockfile(path)
    except json.JSONDecodeError as exc:
        return LockfileValidationResult(
            False,
            (
                _finding(
                    RULE_INVALID_JSON,
                    str(path),
                    "aso.lock is not valid JSON.",
                    f"line {exc.lineno}, column {exc.colno}: {exc.msg}",
                ),
            ),
        )

    return validate_lockfile(lockfile)


def validate_lockfile(lockfile: object) -> LockfileValidationResult:
    """Validate a decoded aso.lock object against the Project Factory contract."""

    findings: list[LockfileFinding] = []

    if not isinstance(lockfile, dict):
        return LockfileValidationResult(
            False,
            (
                _finding(
                    RULE_ROOT_OBJECT,
                    "$",
                    "aso.lock root must be a JSON object.",
                    type(lockfile).__name__,
                ),
            ),
        )

    if lockfile.get("lockfile_version") != LOCKFILE_VERSION:
        findings.append(
            _finding(
                RULE_UNSUPPORTED_LOCKFILE_VERSION,
                "$.lockfile_version",
                "lockfile_version must be 1.0.",
                lockfile.get("lockfile_version"),
            )
        )

    aso_engine = _required_object(lockfile, "aso_engine", "$.aso_engine", findings)
    project = _required_object(lockfile, "project", "$.project", findings)
    publication_boundary = _required_object(
        lockfile,
        "publication_boundary",
        "$.publication_boundary",
        findings,
    )

    if aso_engine is not None:
        _validate_aso_engine(aso_engine, findings)
    if project is not None:
        _validate_project(project, findings)
    if publication_boundary is not None:
        _validate_publication_boundary(publication_boundary, findings)

    return LockfileValidationResult(not findings, tuple(findings))


def _required_object(
    parent: dict[str, object],
    key: str,
    path: str,
    findings: list[LockfileFinding],
) -> dict[str, object] | None:
    value = parent.get(key)
    if key not in parent:
        findings.append(
            _finding(
                RULE_MISSING_OBJECT,
                path,
                f"Required object {key!r} is missing.",
                "missing",
            )
        )
        return None
    if not isinstance(value, dict):
        findings.append(
            _finding(
                RULE_INVALID_FIELD,
                path,
                f"Required object {key!r} must be a JSON object.",
                type(value).__name__,
            )
        )
        return None
    return value


def _required_field(
    parent: dict[str, object],
    key: str,
    path: str,
    findings: list[LockfileFinding],
    *,
    allow_null: bool = False,
) -> object | None:
    if key not in parent:
        findings.append(
            _finding(
                RULE_MISSING_FIELD,
                path,
                f"Required field {key!r} is missing.",
                "missing",
            )
        )
        return None
    if parent[key] is None and not allow_null:
        findings.append(
            _finding(
                RULE_INVALID_FIELD,
                path,
                f"Required field {key!r} must not be null.",
                "null",
            )
        )
        return None
    return parent[key]


def _validate_aso_engine(aso_engine: dict[str, object], findings: list[LockfileFinding]) -> None:
    package_name = _required_field(aso_engine, "package_name", "$.aso_engine.package_name", findings)
    version = _required_field(aso_engine, "version", "$.aso_engine.version", findings)
    runtime_schema = _required_field(
        aso_engine,
        "runtime_schema",
        "$.aso_engine.runtime_schema",
        findings,
    )
    source = _required_field(aso_engine, "source", "$.aso_engine.source", findings)
    engine_mode = _required_field(aso_engine, "engine_mode", "$.aso_engine.engine_mode", findings)

    if package_name is not None and package_name != PACKAGE_NAME:
        findings.append(
            _finding(
                RULE_UNSUPPORTED_PACKAGE_NAME,
                "$.aso_engine.package_name",
                f"aso_engine.package_name must be {PACKAGE_NAME}.",
                package_name,
            )
        )
    if version is not None and version not in COMPATIBLE_PACKAGE_VERSIONS:
        findings.append(
            _finding(
                RULE_UNSUPPORTED_PACKAGE_VERSION,
                "$.aso_engine.version",
                f"aso_engine.version must be one of {', '.join(COMPATIBLE_PACKAGE_VERSIONS)}.",
                version,
            )
        )
    if runtime_schema is not None and runtime_schema not in COMPATIBLE_RUNTIME_SCHEMA_VERSIONS:
        findings.append(
            _finding(
                RULE_UNSUPPORTED_RUNTIME_SCHEMA,
                "$.aso_engine.runtime_schema",
                "aso_engine.runtime_schema must be one of "
                f"{', '.join(COMPATIBLE_RUNTIME_SCHEMA_VERSIONS)}.",
                runtime_schema,
            )
        )
    if (
        version is not None
        and runtime_schema is not None
        and version in COMPATIBLE_PACKAGE_VERSIONS
        and runtime_schema in COMPATIBLE_RUNTIME_SCHEMA_VERSIONS
        and (version, runtime_schema) not in COMPATIBLE_ENGINE_VERSION_TUPLES
    ):
        accepted_tuples = ", ".join(
            f"{package_version}/{runtime_schema_version}"
            for package_version, runtime_schema_version in COMPATIBLE_ENGINE_VERSION_TUPLES
        )
        findings.append(
            _finding(
                RULE_UNSUPPORTED_PACKAGE_VERSION,
                "$.aso_engine",
                f"aso_engine version/runtime_schema tuple must be one of {accepted_tuples}.",
                f"{version}/{runtime_schema}",
            )
        )
    if source is not None and not _is_non_empty_string(source):
        findings.append(
            _finding(
                RULE_INVALID_FIELD,
                "$.aso_engine.source",
                "aso_engine.source must be a non-empty string.",
                source,
            )
        )
    if engine_mode is not None and engine_mode not in SUPPORTED_ENGINE_MODES:
        findings.append(
            _finding(
                RULE_UNSUPPORTED_ENGINE_MODE,
                "$.aso_engine.engine_mode",
                f"aso_engine.engine_mode must be one of {', '.join(SUPPORTED_ENGINE_MODES)}.",
                engine_mode,
            )
        )


def _validate_project(project: dict[str, object], findings: list[LockfileFinding]) -> None:
    for key in ("name", "slug", "profile", "default_branch"):
        value = _required_field(project, key, f"$.project.{key}", findings)
        if value is not None and not _is_non_empty_string(value):
            findings.append(
                _finding(
                    RULE_INVALID_FIELD,
                    f"$.project.{key}",
                    f"project.{key} must be a non-empty string.",
                    value,
                )
            )

    repo_url = _required_field(project, "repo_url", "$.project.repo_url", findings, allow_null=True)
    if repo_url is not None and not isinstance(repo_url, str):
        findings.append(
            _finding(
                RULE_INVALID_FIELD,
                "$.project.repo_url",
                "project.repo_url must be a string or null.",
                type(repo_url).__name__,
            )
        )


def _validate_publication_boundary(
    publication_boundary: dict[str, object],
    findings: list[LockfileFinding],
) -> None:
    for key in ("ignored_roots", "forbidden_tracked_roots"):
        value = _required_field(
            publication_boundary,
            key,
            f"$.publication_boundary.{key}",
            findings,
        )
        if value is None:
            continue
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            findings.append(
                _finding(
                    RULE_INVALID_FIELD,
                    f"$.publication_boundary.{key}",
                    f"publication_boundary.{key} must be an array of strings.",
                    type(value).__name__,
                )
            )
            continue

        present = set(value)
        for required_root in REQUIRED_PUBLICATION_ROOTS:
            if required_root not in present:
                findings.append(
                    _finding(
                        RULE_PUBLICATION_ROOT_MISSING,
                        f"$.publication_boundary.{key}",
                        f"publication_boundary.{key} must include {required_root}.",
                        required_root,
                    )
                )
