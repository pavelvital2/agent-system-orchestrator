# ASO Bootstrap State Reconciliation P5.2 v3.7.2 Validation Report

## Version Tuple

- Package version: 3.7.2
- Governance ruleset: 3.7.2
- Runtime schema: 3.1.0
- Artifact package schema: 1.1.0

## Branch

- Branch: correction/bootstrap-state-reconciliation-p5.2-v3.7.2
- Local HEAD at validation: c5b4f5dbcf5d9cc8b1203ce2ec9b312dd727a46d
- Remote tracking HEAD at validation: c5b4f5dbcf5d9cc8b1203ce2ec9b312dd727a46d
- Validation included uncommitted correction edits in the owned files for the
  audit findings.

## Local Validation

- `git status --short --branch`: ran; branch
  `correction/bootstrap-state-reconciliation-p5.2-v3.7.2`; unrelated
  in-progress ASO command/test edits present in worktree
- `git diff --check`: passed
- `git diff --check -- agent-system/scripts/run_governance_smoke_tests.sh
  agent-system/tools/aso/agent_system_orchestrator_aso/aso_tool/commands/state_init.py
  agent-system/tools/aso/tests/test_state_init.py agent-system/GOVERNANCE_CHANGELOG.md
  agent-system/11_release/ASO_BOOTSTRAP_STATE_RECONCILIATION_P5_2_V3_7_2_VALIDATION_REPORT.md`:
  passed
- `PYTHONDONTWRITEBYTECODE=1 python -m pytest
  agent-system/tools/aso/tests/test_state_init.py`: passed; 7 tests
- standalone `/tmp` workspace `aso state init --confirm-write` followed by
  `aso state verify --strict`: passed; `project-input/TZ.md` was created
- `PYTHONDONTWRITEBYTECODE=1 make test`: passed; source hygiene passed, 331
  ASO tool tests passed, 6 agent-system tests passed
- `PYTHONDONTWRITEBYTECODE=1 make smoke`: passed; governance smoke reported
  18 assertions including active 3.7.2 / 3.7.2 / 3.1.0 coherence
- `PYTHONDONTWRITEBYTECODE=1 bash install.sh --venv /tmp/.../venv &&
  PYTHONDONTWRITEBYTECODE=1 make verify-install VENV=/tmp/.../venv`: passed;
  default repo `.venv` was intentionally not used
- focused version/schema unit tests: covered by `make test`
- package status/lint/doctor: passed for package mode strict checks
- package-layout verify: passed
- checkpoint-preflight: passed through `make smoke`
- regression fixtures: passed through `make test` and `make smoke`

## Required Regression Coverage

- invalid `TZ_PATH = Europe/Moscow` fails with an actionable semantic message:
  covered by state verify regression tests;
- active/open bootstrap plus terminal `stop_terminal` fails or routes to
  correction, not ready STOP;
- missing derived Markdown runtime views produce materialization or repair
  guidance;
- fresh workspace state initialization now creates `project-input/TZ.md` and
  passes immediate strict state verification;
- canonical bootstrap task packet validates through package test/smoke coverage.

## CI

- GitHub Actions run: not run locally; requires push/remote CI.
- Status: local validation passed.

## Publication Boundary

- `git ls-files project-input project-runtime project-archive .venv`: ran;
  empty output

## Result

- STATUS: passed-local-validation
- BLOCKERS: none for local correction validation; remote CI evidence remains an
  external publication step.
