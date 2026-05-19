# STAGE2_STATE_CONTRACT_CORRECTION_VALIDATION_REPORT

## Status

```text
REPORT_STATUS: draft_pending_task_006_final_validation
OWNER_TASK: TASK_ASO_STAGE2_CORRECTION_006_FINAL_VALIDATION
PREPARATION_TASK: TASK_ASO_STAGE2_CORRECTION_005_DOCS_VERSION_RELEASE_CLEANUP
STAGE: 2-correction
PACKAGE_VERSION_MARKER: 3.0.2
GOVERNANCE_RULESET_VERSION_MARKER: 3.0.2
RUNTIME_SCHEMA_VERSION_MARKER: 3.0.0
VALIDATION_DATE: pending
PROFILE_AGENT_COMMIT_PUSH_AUTHORITY: none
CLEANUP_PERFORMED_BY_PROFILE_AGENT: no
```

This draft report is the handoff location for final validation of the Stage 2
state-contract correction. The correction resolves drift among state sidecars,
templates, schemas, fixtures, validator expectations, command examples, and
release evidence while preserving the read-only ASO helper boundary.

The original Stage 2 validation report remains historical evidence at
`agent-system/11_release/STAGE2_UPGRADE_VALIDATION_REPORT.md`, but it is
superseded for current acceptance by this correction report. Task 006 owns the
final command evidence and must replace the pending entries below with observed
results.

## Validation Scope

```text
BRANCH: upgrade/stage-2-state-contract-correction
BASE_HEAD_REQUIRED: 7840460ab70ba4f3b76a2c0dc173310bacb8f987
FORBIDDEN_PUBLICATION_ROOTS: project-input, project-runtime, project-archive
RAW_COMMAND_LOG_PUBLICATION: forbidden
ASO_BOUNDARY: read-only and dry-run only
```

ASO does not dispatch agents, mutate package or workspace state, perform
checkpoints, commit, or push.

## Draft Command Matrix

| Command or command group | Status | Evidence |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py --help` | pending_task_006 | Task 006 must record observed command output summary. |
| `PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py lint --root . --mode package --strict` | pending_task_006 | Task 006 must record observed package lint result. |
| `PYTHONDONTWRITEBYTECODE=1 python3 agent-system/tools/aso/aso.py doctor --root . --mode package --strict` | pending_task_006 | Task 006 must record observed package doctor result. |
| `git diff --check` | pending_task_006 | Task 006 must record whitespace validation result. |
| `git ls-files project-input project-runtime project-archive` | pending_task_006 | Expected tracked output is empty. |

## Acceptance Criteria

| Criterion | Draft Status | Required final evidence |
|---|---|---|
| Stage 2 correction is explained without using the original blocked/superseded report as final acceptance evidence. | prepared_pending_task_006 | Task 006 must confirm report status and docs after final validation. |
| Package version markers are coherent. | prepared_pending_task_006 | Task 006 must confirm `3.0.2 / 3.0.2 / 3.0.0` in package docs and installed metadata checks as required by its packet. |
| README examples use corrected valid fixture commands. | prepared_pending_task_006 | Task 006 must confirm examples use `agent-system/tests/fixtures/state/valid_workspace` for state command examples. |
| No raw command logs or local runtime files are published. | prepared_pending_task_006 | Task 006 must confirm no generated logs or forbidden roots are tracked. |

## Pending Finalization Notes

This Task 005 draft intentionally does not claim final validation pass/fail.
Task 006 must replace pending statuses with observed command evidence and record
any residual limitation, including external CI or cleanup follow-up if required.
