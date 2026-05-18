"""Read-only diagnostic doctor command."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from commands import lint, package_checks


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_IO_ERROR = 3

VERSION_FIELDS = (
    "CURRENT_PACKAGE_VERSION",
    "CURRENT_GOVERNANCE_RULESET_VERSION",
    "CURRENT_RUNTIME_SCHEMA_VERSION",
)
PYPROJECT_REQUIRED_MARKERS = (
    "[build-system]",
    "[project]",
    "[project.scripts]",
    'aso = "agent_system_orchestrator_aso.cli:main"',
)
PACKAGE_REQUIRED_PATHS = (
    "agent-system",
    "agent-system/tools/aso",
    "agent-system/tools/aso/aso.py",
    "agent-system/tools/aso/commands",
    "agent-system/tools/aso/commands/status.py",
    "agent-system/tools/aso/commands/lint.py",
    "agent-system/tools/aso/commands/archive_verify.py",
    "agent-system/tools/aso/commands/doctor.py",
    "agent-system/tools/aso/commands/validate_context_pack.py",
    "agent-system/tools/aso/tests",
    "agent_system_orchestrator_aso",
    "agent_system_orchestrator_aso/cli.py",
    "pyproject.toml",
    "Makefile",
)
MAKE_TARGETS = ("test", "smoke", "doctor", "lint")
NONE_VALUES = {"", "NONE", "none", "null", "UNKNOWN"}


@dataclass(frozen=True)
class Diagnostic:
    check_id: str
    severity: str
    title: str
    details: str
    files: list[str]
    recommendation: str

    def to_json(self, mode: str) -> dict[str, object]:
        return {
            "rule_id": self.check_id,
            "severity": self.severity,
            "message": self.details,
            "path": self.files[0] if self.files else "",
            "title": self.title,
            "details": self.details,
            "files": self.files,
            "recommendation": self.recommendation,
            "mode": mode,
        }


def _is_none(value: str | None) -> bool:
    return value is None or value.strip() in NONE_VALUES


def _read_text(path: Path) -> tuple[str, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return "", str(exc)


def _summary(findings: Iterable[Diagnostic]) -> dict[str, int]:
    finding_list = list(findings)
    return {
        "errors": sum(1 for finding in finding_list if finding.severity == "error"),
        "warnings": sum(1 for finding in finding_list if finding.severity == "warning"),
        "info": sum(1 for finding in finding_list if finding.severity == "info"),
    }


def _status(summary: dict[str, int], strict: bool, *, io_error: bool = False) -> tuple[str, int]:
    if io_error:
        return "io_error", EXIT_IO_ERROR
    if summary["errors"] > 0 or (strict and summary["warnings"] > 0):
        return "failed", EXIT_FINDINGS
    if summary["warnings"] > 0:
        return "warning", EXIT_OK
    return "passed", EXIT_OK


def _from_package_finding(finding: package_checks.Finding) -> Diagnostic:
    return Diagnostic(
        finding.rule_id,
        finding.severity,
        finding.title,
        finding.details,
        finding.files,
        finding.recommendation,
    )


def _from_lint_finding(finding: dict[str, object]) -> Diagnostic:
    files = finding.get("files", [])
    if not isinstance(files, list):
        files = []
    return Diagnostic(
        str(finding.get("rule_id", "DOCTOR_LINT_UNKNOWN")),
        str(finding.get("severity", "error")),
        str(finding.get("title", "Lint finding")),
        str(finding.get("details", finding.get("message", ""))),
        [str(item) for item in files],
        str(finding.get("recommendation", "Resolve the reported lint finding.")),
    )


def _active_version_tuple(root: Path) -> tuple[dict[str, str], list[Diagnostic]]:
    path = root / "agent-system" / "PACKAGE_VERSIONING.md"
    text, error = _read_text(path)
    if error:
        return {}, [
            Diagnostic(
                "DOCTOR_PKG_VERSION_001",
                "error",
                "Package versioning file is unreadable",
                f"agent-system/PACKAGE_VERSIONING.md: {error}",
                ["agent-system/PACKAGE_VERSIONING.md"],
                "Restore PACKAGE_VERSIONING.md with active version constants.",
            )
        ]

    active_section = re.search(
        r"^## Active version constants\s*(?P<body>.*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    source = active_section.group("body") if active_section else text
    versions = {
        field: match.group(1).strip() if (match := re.search(rf"^{field}:\s*(\S+)\s*$", source, re.MULTILINE)) else ""
        for field in VERSION_FIELDS
    }
    findings: list[Diagnostic] = []
    missing = [field for field, value in versions.items() if not value]
    if missing:
        findings.append(
            Diagnostic(
                "DOCTOR_PKG_VERSION_002",
                "error",
                "Active version tuple is incomplete",
                f"Missing active constants: {', '.join(missing)}.",
                ["agent-system/PACKAGE_VERSIONING.md"],
                "Define CURRENT_PACKAGE_VERSION, CURRENT_GOVERNANCE_RULESET_VERSION, and CURRENT_RUNTIME_SCHEMA_VERSION.",
            )
        )
    return versions, findings


def _pyproject_version(root: Path) -> str:
    path = root / "pyproject.toml"
    text, error = _read_text(path)
    if error:
        return ""
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _init_version(root: Path) -> str:
    path = root / "agent_system_orchestrator_aso" / "__init__.py"
    text, error = _read_text(path)
    if error:
        return ""
    match = re.search(r'^__version__\s*=\s*"([^"]+)"\s*$', text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _check_package_paths(root: Path) -> list[Diagnostic]:
    findings: list[Diagnostic] = []
    for relpath in PACKAGE_REQUIRED_PATHS:
        path = root / relpath
        if path.exists():
            continue
        findings.append(
            Diagnostic(
                "DOCTOR_PKG_LAYOUT_001",
                "error",
                "Required package path is missing",
                f"{relpath} is required for the Stage 1 ASO command surface.",
                [relpath],
                "Restore the missing package path before publishing or installing the package.",
            )
        )
    return findings


def _check_package_versions(root: Path) -> tuple[dict[str, str], list[Diagnostic]]:
    versions, findings = _active_version_tuple(root)
    package_version = versions.get("CURRENT_PACKAGE_VERSION", "")
    pyproject_version = _pyproject_version(root)
    init_version = _init_version(root)

    if package_version and pyproject_version and package_version != pyproject_version:
        findings.append(
            Diagnostic(
                "DOCTOR_PKG_VERSION_003",
                "error",
                "pyproject version differs from active package version",
                f"pyproject.toml version={pyproject_version}; CURRENT_PACKAGE_VERSION={package_version}.",
                ["pyproject.toml", "agent-system/PACKAGE_VERSIONING.md"],
                "Keep pyproject.toml aligned with CURRENT_PACKAGE_VERSION.",
            )
        )
    if package_version and init_version and package_version != init_version:
        findings.append(
            Diagnostic(
                "DOCTOR_PKG_VERSION_004",
                "error",
                "Installed wrapper version differs from active package version",
                f"agent_system_orchestrator_aso.__version__={init_version}; CURRENT_PACKAGE_VERSION={package_version}.",
                ["agent_system_orchestrator_aso/__init__.py", "agent-system/PACKAGE_VERSIONING.md"],
                "Keep the wrapper package __version__ aligned with CURRENT_PACKAGE_VERSION.",
            )
        )
    return {
        **versions,
        "PYPROJECT_VERSION": pyproject_version,
        "WRAPPER_VERSION": init_version,
    }, findings


def _check_pyproject(root: Path) -> list[Diagnostic]:
    path = root / "pyproject.toml"
    text, error = _read_text(path)
    if error:
        return [
            Diagnostic(
                "DOCTOR_PKG_INSTALL_001",
                "error",
                "pyproject.toml is unreadable",
                f"pyproject.toml: {error}",
                ["pyproject.toml"],
                "Restore pyproject.toml package metadata.",
            )
        ]
    missing = [marker for marker in PYPROJECT_REQUIRED_MARKERS if marker not in text]
    if not missing:
        return []
    return [
        Diagnostic(
            "DOCTOR_PKG_INSTALL_002",
            "error",
            "pyproject installability signals are incomplete",
            f"pyproject.toml is missing: {', '.join(missing)}.",
            ["pyproject.toml"],
            "Define build metadata, project metadata, and the aso console script entry point.",
        )
    ]


def _check_command_registration(root: Path) -> list[Diagnostic]:
    path = root / "agent-system" / "tools" / "aso" / "aso.py"
    text, error = _read_text(path)
    if error:
        return [
            Diagnostic(
                "DOCTOR_PKG_COMMAND_001",
                "error",
                "ASO command parser is unreadable",
                f"agent-system/tools/aso/aso.py: {error}",
                ["agent-system/tools/aso/aso.py"],
                "Restore the ASO command parser.",
            )
        ]
    required_terms = ('"doctor"', "handler=doctor.run", "from commands import")
    missing = [term for term in required_terms if term not in text]
    if not missing:
        return []
    return [
        Diagnostic(
            "DOCTOR_PKG_COMMAND_002",
            "error",
            "doctor command is not registered",
            f"agent-system/tools/aso/aso.py is missing registration marker(s): {', '.join(missing)}.",
            ["agent-system/tools/aso/aso.py"],
            "Register doctor in the top-level ASO parser.",
        )
    ]


def _make_targets(text: str) -> set[str]:
    targets: set[str] = set()
    for line in text.splitlines():
        if not line or line.startswith(("\t", " ")):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:", line)
        if match:
            targets.add(match.group(1))
    return targets


def _check_tests_and_smoke(root: Path) -> list[Diagnostic]:
    findings: list[Diagnostic] = []
    tests_dir = root / "agent-system" / "tools" / "aso" / "tests"
    test_files = sorted(tests_dir.glob("test_*.py")) if tests_dir.is_dir() else []
    if not test_files:
        findings.append(
            Diagnostic(
                "DOCTOR_PKG_TEST_001",
                "error",
                "ASO tests are missing",
                "agent-system/tools/aso/tests has no test_*.py files.",
                ["agent-system/tools/aso/tests"],
                "Add focused ASO unit tests before relying on the command surface.",
            )
        )

    makefile = root / "Makefile"
    text, error = _read_text(makefile)
    if error:
        findings.append(
            Diagnostic(
                "DOCTOR_PKG_TEST_002",
                "error",
                "Makefile is unreadable",
                f"Makefile: {error}",
                ["Makefile"],
                "Restore repeatable test, smoke, doctor, and lint targets.",
            )
        )
        return findings

    targets = _make_targets(text)
    missing_targets = [target for target in MAKE_TARGETS if target not in targets]
    if missing_targets:
        findings.append(
            Diagnostic(
                "DOCTOR_PKG_TEST_003",
                "error",
                "Repeatable command targets are missing",
                f"Makefile is missing target(s): {', '.join(missing_targets)}.",
                ["Makefile"],
                "Add repeatable test, smoke, doctor, and lint targets.",
            )
        )
    return findings


def _check_ci_presence(root: Path) -> list[Diagnostic]:
    workflows = root / ".github" / "workflows"
    workflow_files = sorted(workflows.glob("*.yml")) + sorted(workflows.glob("*.yaml")) if workflows.is_dir() else []
    if workflow_files:
        return []
    return [
        Diagnostic(
            "DOCTOR_PKG_CI_001",
            "info",
            "CI workflow is not present yet",
            "No .github/workflows/*.yml or *.yaml file was found.",
            [".github/workflows"],
            "Add CI in the bounded Stage 1 CI/governance task.",
        )
    ]


def _package_report(root: Path, strict: bool) -> tuple[dict[str, object], int]:
    inspection = package_checks.inspect_package(root)
    findings = [_from_package_finding(finding) for finding in inspection.findings]
    findings.extend(_check_package_paths(root))
    versions, version_findings = _check_package_versions(root)
    findings.extend(version_findings)
    findings.extend(_check_pyproject(root))
    findings.extend(_check_command_registration(root))
    findings.extend(_check_tests_and_smoke(root))
    findings.extend(_check_ci_presence(root))

    summary = _summary(findings)
    io_error = any(finding.check_id == "PACKAGE_IO_001" for finding in findings)
    status, exit_code = _status(summary, strict, io_error=io_error)
    return {
        "tool": "aso",
        "command": "doctor",
        "mode": "package",
        "status": status,
        "root": str(root),
        "strict": strict,
        "summary": summary,
        "findings": [finding.to_json("package") for finding in findings],
        "package": {
            "package_consistency": package_checks.consistency(inspection.findings),
            "generated_roots": inspection.generated_roots,
            "readmes": inspection.readmes,
            "git_tracked_generated_files": inspection.git_tracked_generated_files,
            "versions": versions,
        },
    }, exit_code


def _git_value(root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _runtime_files(root: Path) -> dict[str, lint.RuntimeFile]:
    return {name: lint._read_runtime_file(root, name) for name in lint.REQUIRED_RUNTIME_FILES}


def _runtime_field(files: dict[str, lint.RuntimeFile], name: str, *keys: str) -> str:
    runtime_file = files.get(name)
    if runtime_file is None:
        return ""
    for key in keys:
        value = runtime_file.fields.get(key, "").strip()
        if value:
            return value
    return ""


def _generated_root_states(root: Path) -> dict[str, str]:
    states: dict[str, str] = {}
    for name in package_checks.GENERATED_ROOTS:
        path = root / name
        if not path.exists():
            states[name] = "absent"
        elif path.is_dir():
            states[name] = "present"
        else:
            states[name] = "present-not-directory"
    return states


def _check_workspace_roots(root: Path, states: dict[str, str]) -> list[Diagnostic]:
    findings: list[Diagnostic] = []
    if states.get("project-runtime") != "present":
        findings.append(
            Diagnostic(
                "DOCTOR_WS_ROOT_001",
                "error",
                "project-runtime is missing",
                "Workspace mode requires generated runtime state under project-runtime/.",
                ["project-runtime"],
                "Run workspace mode against an initialized ASO workspace or initialize runtime state first.",
            )
        )
    for name, state in states.items():
        if state == "present-not-directory":
            findings.append(
                Diagnostic(
                    "DOCTOR_WS_ROOT_002",
                    "error",
                    "Generated root is not a directory",
                    f"{name} exists but is not a directory.",
                    [name],
                    f"Repair {name} so it is either absent or a generated workspace directory.",
                )
            )
    return findings


def _check_workspace_identity(files: dict[str, lint.RuntimeFile]) -> list[Diagnostic]:
    identity = files.get("WORKSPACE_IDENTITY.md")
    if identity is None or not identity.exists:
        return []
    missing = [
        label
        for label, value in {
            "PROJECT_SLUG or PROJECT_NAME": _runtime_field(files, "WORKSPACE_IDENTITY.md", "PROJECT_SLUG", "PROJECT_NAME"),
            "WORKSPACE_TYPE": _runtime_field(files, "WORKSPACE_IDENTITY.md", "WORKSPACE_TYPE"),
        }.items()
        if _is_none(value)
    ]
    if not missing:
        return []
    return [
        Diagnostic(
            "DOCTOR_WS_IDENTITY_001",
            "warning",
            "Workspace identity is incomplete",
            f"WORKSPACE_IDENTITY.md is missing: {', '.join(missing)}.",
            ["project-runtime/WORKSPACE_IDENTITY.md"],
            "Record explicit workspace identity fields; do not infer identity from folder name or Git metadata.",
        )
    ]


def _check_repository_lock(files: dict[str, lint.RuntimeFile]) -> list[Diagnostic]:
    lock = files.get("REPOSITORY_LOCK.md")
    if lock is None or not lock.exists:
        return []
    status = _runtime_field(files, "REPOSITORY_LOCK.md", "REPOSITORY_LOCK_STATUS", "LOCK_STATUS")
    push_allowed = _runtime_field(files, "REPOSITORY_LOCK.md", "PUSH_ALLOWED")
    expected_branch = _runtime_field(files, "REPOSITORY_LOCK.md", "EXPECTED_BRANCH")
    actual_branch = _runtime_field(files, "REPOSITORY_LOCK.md", "ACTUAL_BRANCH", "ACTUAL_BRANCH_AT_LOCK")
    expected_remote = _runtime_field(files, "REPOSITORY_LOCK.md", "EXPECTED_GIT_REMOTE", "EXPECTED_REMOTE")
    actual_remote = _runtime_field(files, "REPOSITORY_LOCK.md", "ACTUAL_GIT_REMOTE", "ACTUAL_REMOTE")

    findings: list[Diagnostic] = []
    if _is_none(status):
        findings.append(
            Diagnostic(
                "DOCTOR_WS_LOCK_001",
                "warning",
                "Repository lock status is missing",
                "REPOSITORY_LOCK.md does not declare REPOSITORY_LOCK_STATUS or LOCK_STATUS.",
                ["project-runtime/REPOSITORY_LOCK.md"],
                "Record an explicit accepted repository lock status before checkpoint or push decisions.",
            )
        )
    if not _is_none(expected_branch) and not _is_none(actual_branch) and expected_branch != actual_branch:
        findings.append(
            Diagnostic(
                "DOCTOR_WS_LOCK_002",
                "error",
                "Repository lock branch mismatch",
                f"EXPECTED_BRANCH={expected_branch}; ACTUAL_BRANCH={actual_branch}.",
                ["project-runtime/REPOSITORY_LOCK.md"],
                "Reconcile the repository lock before checkpoint or push decisions.",
            )
        )
    if not _is_none(expected_remote) and not _is_none(actual_remote) and expected_remote != actual_remote:
        findings.append(
            Diagnostic(
                "DOCTOR_WS_LOCK_003",
                "error",
                "Repository lock remote mismatch",
                f"EXPECTED_GIT_REMOTE={expected_remote}; ACTUAL_GIT_REMOTE={actual_remote}.",
                ["project-runtime/REPOSITORY_LOCK.md"],
                "Reconcile the repository lock before checkpoint or push decisions.",
            )
        )
    if push_allowed.lower() == "true" and status.lower() not in {"accepted", "passed", "valid", "locked"}:
        findings.append(
            Diagnostic(
                "DOCTOR_WS_LOCK_004",
                "error",
                "Push is allowed without an accepted repository lock",
                f"PUSH_ALLOWED={push_allowed}; REPOSITORY_LOCK_STATUS={status or 'MISSING'}.",
                ["project-runtime/REPOSITORY_LOCK.md"],
                "Set PUSH_ALLOWED false or record an accepted repository lock before push is permitted.",
            )
        )
    return findings


def _check_branch_remote(root: Path, files: dict[str, lint.RuntimeFile]) -> list[Diagnostic]:
    findings: list[Diagnostic] = []
    expected_branch = (
        _runtime_field(files, "PROJECT_STATE.md", "EXPECTED_BRANCH")
        or _runtime_field(files, "WORKSPACE_IDENTITY.md", "EXPECTED_BRANCH")
        or _runtime_field(files, "REPOSITORY_LOCK.md", "EXPECTED_BRANCH")
    )
    actual_branch = (
        _runtime_field(files, "PROJECT_STATE.md", "ACTUAL_BRANCH")
        or _runtime_field(files, "WORKSPACE_IDENTITY.md", "ACTUAL_BRANCH")
        or _runtime_field(files, "REPOSITORY_LOCK.md", "ACTUAL_BRANCH", "ACTUAL_BRANCH_AT_LOCK")
    )
    git_branch = _git_value(root, ["branch", "--show-current"])
    branch_seen = git_branch or actual_branch
    if not _is_none(expected_branch) and not _is_none(branch_seen) and expected_branch != branch_seen:
        findings.append(
            Diagnostic(
                "DOCTOR_WS_GIT_001",
                "error",
                "Workspace branch differs from expected branch",
                f"EXPECTED_BRANCH={expected_branch}; observed branch={branch_seen}.",
                ["project-runtime/PROJECT_STATE.md", "project-runtime/WORKSPACE_IDENTITY.md", "project-runtime/REPOSITORY_LOCK.md"],
                "Use the expected branch or update workspace identity and repository lock through governed setup.",
            )
        )

    expected_remote = (
        _runtime_field(files, "PROJECT_STATE.md", "EXPECTED_GIT_REMOTE")
        or _runtime_field(files, "WORKSPACE_IDENTITY.md", "EXPECTED_GIT_REMOTE")
        or _runtime_field(files, "REPOSITORY_LOCK.md", "EXPECTED_GIT_REMOTE", "EXPECTED_REMOTE")
    )
    actual_remote = (
        _git_value(root, ["remote", "get-url", "origin"])
        or _runtime_field(files, "PROJECT_STATE.md", "ACTUAL_GIT_REMOTE")
        or _runtime_field(files, "WORKSPACE_IDENTITY.md", "ACTUAL_GIT_REMOTE")
        or _runtime_field(files, "REPOSITORY_LOCK.md", "ACTUAL_GIT_REMOTE", "ACTUAL_REMOTE")
    )
    if not _is_none(expected_remote) and not _is_none(actual_remote) and expected_remote != actual_remote:
        findings.append(
            Diagnostic(
                "DOCTOR_WS_GIT_002",
                "error",
                "Workspace remote differs from expected remote",
                f"EXPECTED_GIT_REMOTE={expected_remote}; observed remote={actual_remote}.",
                ["project-runtime/PROJECT_STATE.md", "project-runtime/WORKSPACE_IDENTITY.md", "project-runtime/REPOSITORY_LOCK.md"],
                "Use the expected remote or update workspace identity and repository lock through governed setup.",
            )
        )
    return findings


def _check_checkpoint_readiness(files: dict[str, lint.RuntimeFile]) -> list[Diagnostic]:
    eligibility = _runtime_field(files, "PROJECT_STATE.md", "CHECKPOINT_ELIGIBILITY", "CHECKPOINT_ELIGIBILITY_STATUS")
    blocked_by = _runtime_field(files, "PROJECT_STATE.md", "CHECKPOINT_BLOCKED_BY")
    checkpoint_status = _runtime_field(files, "PROJECT_STATE.md", "PROJECT_CHECKPOINT_STATUS")
    if checkpoint_status == "passed":
        return []
    if _is_none(eligibility) or eligibility in {"pending", "not_checked", "unknown"}:
        return [
            Diagnostic(
                "DOCTOR_WS_CHECKPOINT_001",
                "info",
                "Checkpoint eligibility is not ready",
                f"CHECKPOINT_ELIGIBILITY={eligibility or 'MISSING'}; CHECKPOINT_BLOCKED_BY={blocked_by or 'NONE'}.",
                ["project-runtime/PROJECT_STATE.md"],
                "Run the governed checkpoint preflight only after an auditor pass and before commit or push.",
            )
        ]
    if eligibility in {"blocked", "failed", "ineligible"}:
        return [
            Diagnostic(
                "DOCTOR_WS_CHECKPOINT_002",
                "warning",
                "Checkpoint eligibility is blocked",
                f"CHECKPOINT_ELIGIBILITY={eligibility}; CHECKPOINT_BLOCKED_BY={blocked_by or 'MISSING'}.",
                ["project-runtime/PROJECT_STATE.md"],
                "Resolve checkpoint blockers before staging, commit, or push.",
            )
        ]
    return []


def _workspace_report(root: Path, strict: bool) -> tuple[dict[str, object], int]:
    states = _generated_root_states(root)
    findings: list[Diagnostic] = []
    if not root.exists() or not root.is_dir():
        findings.append(
            Diagnostic(
                "DOCTOR_WS_IO_001",
                "error",
                "Workspace root is unreadable",
                f"{root} is not an existing readable directory.",
                [str(root)],
                "Pass --root pointing at an initialized ASO workspace.",
            )
        )
        summary = _summary(findings)
        status, exit_code = _status(summary, strict, io_error=True)
        return {
            "tool": "aso",
            "command": "doctor",
            "mode": "workspace",
            "status": status,
            "root": str(root),
            "strict": strict,
            "summary": summary,
            "findings": [finding.to_json("workspace") for finding in findings],
            "workspace": {"generated_roots": states},
        }, exit_code

    findings.extend(_check_workspace_roots(root, states))
    lint_report, _lint_exit = lint._report(root, strict=False)
    lint_findings = lint_report.get("findings", [])
    if isinstance(lint_findings, list):
        findings.extend(_from_lint_finding(finding) for finding in lint_findings if isinstance(finding, dict))

    files = _runtime_files(root) if states.get("project-runtime") == "present" else {}
    if files:
        findings.extend(_check_workspace_identity(files))
        findings.extend(_check_repository_lock(files))
        findings.extend(_check_branch_remote(root, files))
        findings.extend(_check_checkpoint_readiness(files))

    summary = _summary(findings)
    io_error = any(finding.check_id.startswith(("DOCTOR_WS_IO_", "LINT_IO_")) for finding in findings)
    status, exit_code = _status(summary, strict, io_error=io_error)
    return {
        "tool": "aso",
        "command": "doctor",
        "mode": "workspace",
        "status": status,
        "root": str(root),
        "strict": strict,
        "summary": summary,
        "findings": [finding.to_json("workspace") for finding in findings],
        "workspace": {
            "generated_roots": states,
            "branch": _git_value(root, ["branch", "--show-current"]),
            "remote": _git_value(root, ["remote", "get-url", "origin"]),
        },
    }, exit_code


def _print_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    if not isinstance(summary, dict):
        raise TypeError("internal doctor report summary must be a dictionary")

    print(f"ASO doctor: {str(report['status']).upper()}")
    print(f"Root: {report['root']}")
    print(f"Mode: {report['mode']}")
    print(f"Strict: {report['strict']}")
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Info: {summary['info']}")
    print(f"Findings: {len(report['findings'])}")
    for finding in report["findings"]:
        if not isinstance(finding, dict):
            continue
        print(f"- {finding['severity']} {finding['rule_id']}: {finding['title']}")


def _write_json(path_text: str, report: dict[str, object]) -> bool:
    path = Path(path_text).expanduser()
    if not path.parent.exists():
        print(f"aso doctor: json-out parent does not exist: {path.parent}", file=sys.stderr)
        return False
    try:
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"aso doctor: failed to write json-out: {exc}", file=sys.stderr)
        return False
    return True


def run(args: argparse.Namespace) -> int:
    """Run the doctor command."""
    if args.mode == "package":
        report, exit_code = _package_report(args.root, args.strict)
    else:
        report, exit_code = _workspace_report(args.root, args.strict)
    _print_text(report)
    if args.json_out and not _write_json(args.json_out, report):
        return EXIT_IO_ERROR
    return exit_code
