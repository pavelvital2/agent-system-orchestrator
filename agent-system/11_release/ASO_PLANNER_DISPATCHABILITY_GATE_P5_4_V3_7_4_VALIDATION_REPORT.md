# ASO Planner Dispatchability Gate P5.4 v3.7.4 Validation Report

## Version Tuple

- Package version: 3.7.4
- Governance ruleset: 3.7.4
- Runtime schema: 3.1.1
- Artifact package schema: 1.1.0

## Branch

- Branch: correction/planner-dispatchability-gate-p5.4-v3.7.4
- Validation included uncommitted technical-writer edits in the bounded P5.4
  docs/version/release scope.

## Local Validation

- `PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py status
  --root . --mode package`: passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lint
  --root . --mode package --strict`: passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py doctor
  --root . --mode package --strict`: failed.
  - `DOCTOR_PKG_VERSION_003`: `pyproject.toml` remains `3.7.3` while
    `CURRENT_PACKAGE_VERSION` is `3.7.4`.
  - `DOCTOR_PKG_VERSION_004`: `agent_system_orchestrator_aso.__version__`
    remains `3.7.3` while `CURRENT_PACKAGE_VERSION` is `3.7.4`.
- `git diff --check`: passed.
- `git ls-files project-input project-runtime project-archive .venv`: passed;
  empty output.

The doctor failures are outside this task packet's editable file set. This
technical-writer task may update only the authorized documentation/version
boundary files and must not edit `pyproject.toml`, Python package version
constants, code, or tests.

## Boundary Evidence

- Active documentation tuple is `3.7.4 / 3.7.4 / 3.1.1`.
- Runtime schema remains `3.1.1`.
- Artifact Package Schema remains `1.1.0`.
- `agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/runtime_schema_contracts.py`
  still records `ACTIVE_RUNTIME_SCHEMA_VERSION = "3.1.1"` and
  `ACTIVE_ARTIFACT_PACKAGE_SCHEMA_VERSION = "1.1.0"`.
- `pyproject.toml` and `agent_system_orchestrator_aso.__version__` remain
  `3.7.3` because they are outside this task's allowed files.

## Result

- STATUS: local-validation-blocked-by-out-of-scope-package-metadata
- BLOCKERS: package doctor requires out-of-scope code/package metadata version
  updates to align with `CURRENT_PACKAGE_VERSION: 3.7.4`.
