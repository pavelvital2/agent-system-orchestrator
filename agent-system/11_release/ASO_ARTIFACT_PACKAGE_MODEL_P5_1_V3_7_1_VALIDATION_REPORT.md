# ASO Artifact Package Model P5.1 v3.7.1 Validation Report

## Scope

BRANCH: correction/artifact-package-model-p5.1-v3.7.1
PACKAGE_VERSION: 3.7.1
GOVERNANCE_RULESET_VERSION: 3.7.1
RUNTIME_SCHEMA_VERSION: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0

## Regression Evidence

Bootstrap marker:

- canonical bootstrap packet with `# TASK PACKET` and `TASK_KIND: bootstrap`
  passes dispatch validation;
- obsolete `# BOOTSTRAP TASK PACKET` fails with an actionable error.

Artifact package:

- self-contained package directories validate from either package root or
  `manifest.json`;
- parent traversal and workspace-root-prefixed manifest refs fail;
- accept copies the full package directory and writes inventory hashes;
- reject copies the full package directory and writes a rejection report.

Governance and conveyor:

- active P5 changelog entries are superseded by accepted P5.1 entry
  `GOV-2026-05-23-001`;
- `aso orchestrator status` and `aso orchestrator next` provide read-only
  JSON summaries for normal conveyor flow.

## Validation Commands

```text
PYTHONDONTWRITEBYTECODE=1 make test
RESULT: passed; 323 ASO tool tests and 6 package tests.

PYTHONDONTWRITEBYTECODE=1 make smoke
RESULT: passed; governance smoke passed 18 assertions.

git diff --check
RESULT: passed.

PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py status --root . --mode package
RESULT: passed.

PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict
RESULT: passed.

PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict
RESULT: passed.

PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py package-layout verify --root . --strict
RESULT: passed.

PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py checkpoint-preflight --root . --mode package --strict
RESULT: eligible.

bash install.sh && make verify-install
RESULT: passed; editable install reports agent-system-orchestrator 3.7.1.

git ls-files project-input project-runtime project-archive .venv
RESULT: empty output.
```

## Cleanup

Forbidden roots remain untracked. The local corrective input package remains
outside tracked package scope and can be removed after owner/CI confirmation.
