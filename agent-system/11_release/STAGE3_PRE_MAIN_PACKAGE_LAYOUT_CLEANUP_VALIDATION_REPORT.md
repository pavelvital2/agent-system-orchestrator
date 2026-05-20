# Stage 3 Pre-Main Package Layout Cleanup Validation Report

```text
REPORT_ID: STAGE3_PRE_MAIN_PACKAGE_LAYOUT_CLEANUP_VALIDATION_REPORT
TASK_ID: TASK_ASO_PRE_MAIN_005_DOCS_VERSION_CHANGELOG
DATE: 2026-05-20
BRANCH: upgrade/stage-3-pre-main-package-layout-cleanup
VALIDATION_COMMAND_HEAD: 0e8468431c67faf8d6cf4ba1dddc6869be94f7b5
FINAL_COMMIT_PENDING: yes
REMOTE_HEAD_VERIFICATION_REQUIRED_AFTER_PUSH: yes
MAIN_MERGE_CLAIMED: no
PACKAGE_VERSION: 3.1.2
GOVERNANCE_RULESET_VERSION: 3.1.2
RUNTIME_SCHEMA_VERSION: 3.0.0
CANONICAL_PACKAGE_SOURCE: agent-system/tools/aso/agent_system_orchestrator_aso/
ROOT_DUPLICATE_PACKAGE_TRACKED: no
VALIDATION_STATUS: passed
BLOCKER: none
```

## Package Layout

The canonical installable ASO package source is:

```text
agent-system/tools/aso/agent_system_orchestrator_aso/
```

The removed duplicate root package path is:

```text
agent_system_orchestrator_aso/
```

Package discovery is configured through `pyproject.toml` with:

```text
[tool.setuptools.packages.find]
where = ["agent-system/tools/aso"]
include = ["agent_system_orchestrator_aso*"]
```

## Installation And Verification

User install from repository root:

```text
bash install.sh
source .venv/bin/activate
make verify-install
```

Manual editable install:

```text
python3 -m pip install -e .
aso --help
aso package-layout verify --root . --strict
```

Direct compatibility check:

```text
python3 agent-system/tools/aso/aso.py --help
python3 agent-system/tools/aso/aso.py package-layout verify --root . --strict
```

## Command Evidence

```text
COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py --help
EXIT_CODE: 0
OUTCOME: passed; help output lists package-layout and deprecated package-sync alias.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
EXIT_CODE: 0
OUTCOME: passed; ASO lint reported Errors: 0, Warnings: 0, Findings: 0.

COMMAND: PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py package-layout verify --root . --strict
EXIT_CODE: 0
OUTCOME: passed; canonical package is agent-system/tools/aso/agent_system_orchestrator_aso, root duplicate package path is agent_system_orchestrator_aso, Findings: 0.

COMMAND: git diff --check
EXIT_CODE: 0
OUTCOME: passed; no whitespace errors reported.

COMMAND: git ls-files project-input project-runtime project-archive agent_system_orchestrator_aso
EXIT_CODE: 0
OUTCOME: passed; output empty.

COMMAND: git diff --cached --name-only
EXIT_CODE: 0
OUTCOME: passed; output empty.

COMMAND: grep -R 'CURRENT_PACKAGE_VERSION: 3.1.2' agent-system/PACKAGE_VERSIONING.md
EXIT_CODE: 0
OUTCOME: passed; two matching lines reported.

COMMAND: grep -R 'version = "3.1.2"' pyproject.toml
EXIT_CODE: 0
OUTCOME: passed; one matching line reported.

COMMAND: PYTHONDONTWRITEBYTECODE=1 ./agent-system/scripts/run_governance_smoke_tests.sh
EXIT_CODE: 0
OUTCOME: passed; SMOKE_RESULT: passed (18 assertions), including version_changelog_coherence for 3.1.2 / 3.1.2 / 3.0.0 and GOV-2026-05-20-001 STATUS: proposed.
```

## Merge Readiness

This report does not claim merge readiness by itself and does not claim a merge
to `main`. Merge readiness must follow
`09_MAIN_MERGE_READINESS_PROCEDURE.md` or accepted package merge-readiness docs,
with independent audit, orchestrator-owned checkpoint, push, remote CI evidence,
and post-push remote HEAD verification.
