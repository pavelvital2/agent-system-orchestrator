# GIT_CHECKPOINT_VALIDATION_RULES

## Purpose

This document defines documentation-first validation rules for post-audit Git
checkpoint attempts.

Git checkpoint validation applies before staging, committing, or pushing.
It does not require a working CLI implementation.

## Source documents

```text
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
agent-system/04_state/TASK_REGISTRY_TEMPLATE.md
agent-system/04_state/ACCEPTED_ARTIFACTS_TEMPLATE.md
agent-system/06_logs/ORCHESTRATOR_EVENTS_LOG_TEMPLATE.md
```

## Checkpoint preconditions

A Git checkpoint is valid only when all conditions are true:

- the immediately preceding required audit returned `STATUS: pass`;
- the audited task result is within scope;
- no required audit failed for the same work;
- no correction is pending for the same work;
- changed files match the task packet `ALLOWED_FILE_CHANGES`;
- no changed file matches `FORBIDDEN_FILE_CHANGES`;
- no suspected secret or credential file is staged;
- runtime state does not contain active blockers or GAPs that block the
  checkpointed work.
- accepted files can be listed without reading or printing secret values.

## Forbidden checkpoint attempts

Checkpoint is forbidden after:

- profile-agent pass without required audit pass;
- audit fail;
- audit blocked;
- audit gap;
- invalid RESULT shape;
- invalid task packet;
- invalid runtime tuple;
- direct progress after audit fail;
- unverified correction result.

## Allowed and forbidden file checks

Before staging, compare changed paths against:

```text
ALLOWED_FILE_CHANGES
FORBIDDEN_FILE_CHANGES
FILESYSTEM_GOVERNANCE
```

Invalid checkpoint conditions:

- path outside task packet allowed scope;
- path inside task packet forbidden scope;
- ordinary project task changed `agent-system/`;
- profile agent changed `project-runtime/`;
- auditor changed files without explicit correction authority;
- archive/deprecated source modified as active work;
- accepted artifact modified outside a governed task.

## Secret-safety checks

Before staging or committing, the orchestrator must verify that the checkpoint
does not include:

- credential files;
- token files;
- private keys;
- cookies;
- `.env` values;
- command outputs containing secret values;
- unredacted secret material in RESULT, logs, docs, or runtime state.

Validators must not print suspected secret values. Evidence must identify only
the path, field, or redacted class of issue.

## Commit message checks

Commit message must be consistent with the accepted task and must not include:

- secret values;
- unrelated task IDs;
- project-specific credentials or environment data;
- claims of audit pass when audit did not pass.

## Push checks

Push is valid only after the local commit is valid.

Push must not proceed when:

- checkpoint preconditions fail;
- working tree contains out-of-scope staged changes;
- secret-safety checks fail;
- audit pass is missing;
- correction remains pending for the committed work.

## Required checkpoint outputs

Successful checkpoint validation must ensure the checkpoint records:

- accepted task id;
- accepted result reference;
- audit reference;
- accepted files;
- branch;
- commit hash;
- push status.

`PUSH_STATUS: pushed` requires a valid local commit hash and a completed push.

`STATUS: checkpoint_done` in the task registry is invalid unless commit hash,
branch, pushed status, accepted files, and checkpoint reference are recorded.

## Recovery

If checkpoint validation fails:

- do not stage additional files;
- do not commit;
- do not push;
- log the validation failure without secret values;
- route to correction or owner handling according to governance.

If commit fails:

- do not push;
- log a checkpoint failure with `PUSH_STATUS: not_attempted`;
- route to governed correction or owner handling.

If push fails:

- keep the local commit hash traceable if available;
- log a checkpoint failure with `PUSH_STATUS: failed`;
- route to governed correction or owner handling.

If secret or credential risk is detected:

- do not stage additional files;
- do not commit;
- do not push;
- log only a redacted risk class and affected path or field;
- route to governed correction or owner handling.
