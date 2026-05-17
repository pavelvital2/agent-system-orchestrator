# TRANSACTIONAL_CHECKPOINT_SPEC

## Purpose

This document specifies the future transactional behavior for `aso checkpoint`.
It is a contract for a later mutation implementation. It does not authorize
profile agents, validators, or lint commands to commit, push, or mutate runtime
state.

## Authority boundary

`aso checkpoint` is orchestrator-owned. It may run only after the required audit
has passed and deterministic checkpoint preflight has returned eligible.

Until a separate implementation task is approved, this specification is
documentation-only. Existing read-only commands, including `aso lint`, must not
perform checkpoint mutation.

## Transaction sequence

A successful checkpoint transaction must apply these steps in order:

```text
1. preflight passed
2. commit created
3. push completed
4. receipt written
5. PROJECT_STATE updated
6. CURRENT_GATE closed
7. TASK_REGISTRY updated
8. NEXT_ACTION recalculated
9. ACCEPTED_ARTIFACTS updated
10. event written
11. post-check verification
```

The sequence is intentionally ordered so Git evidence exists before accepted
runtime state claims checkpoint success, and post-check verification validates
the completed state tuple after all writes.

## Step contracts

### 1. Preflight passed

Preflight must pass the rules in
`agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md` before any
staging, commit, or push. Failed preflight forbids commit, push, receipt success
claims, and runtime success claims.

### 2. Commit created

The commit must include only the accepted files for the audited work. The commit
hash and branch must be captured from Git after commit creation.

### 3. Push completed

For `commit_and_push` checkpoints, the push must complete and the pushed target
must match the governed remote and branch. Local-only checkpoints must record
`PUSH_STATUS: not_required` and must not push.

### 4. Receipt written

The checkpoint receipt must be written after commit and required push evidence
exist. It must record at least:

```text
TASK_ID
AUDIT_REF
ACCEPTED_RESULT_REF
ACCEPTED_FILES
COMMIT_STATUS
COMMIT_HASH
BRANCH
PUSH_STATUS
PUSH_REMOTE
PUSH_BRANCH
LAST_PUSH_TARGET_STATUS
PROJECT_CHECKPOINT_STATUS
CHECKPOINT_RECEIPT_REF
```

`CHECKPOINT_RECEIPT_REF` must not be `NONE` for a passed checkpoint.

### 5. PROJECT_STATE updated

`PROJECT_STATE.md` may set `PROJECT_CHECKPOINT_STATUS: passed` only after the
receipt exists and the commit/push policy is satisfied. It must also reference
the checkpoint receipt and commit evidence.

### 6. CURRENT_GATE closed

After `PROJECT_CHECKPOINT_STATUS: passed`, `CURRENT_GATE.md` must not remain
active. Valid post-checkpoint gate statuses are closed terminal or inactive
states such as:

```text
passed
skipped
closed
completed
inactive
```

### 7. TASK_REGISTRY updated

The checkpointed task entry must move to `STATUS: checkpoint_done` and record
commit hash, branch, accepted files, audit reference, and checkpoint reference.

### 8. NEXT_ACTION recalculated

`NEXT_ACTION.md` must be recalculated from the updated runtime tuple. After a
passed checkpoint it must not continue to point at the same checkpoint attempt.
In particular, a stale `NEXT_ACTION` is invalid when it still carries a
checkpoint policy for the just-checkpointed task or reuses the same checkpoint
receipt as the completed checkpoint.

### 9. ACCEPTED_ARTIFACTS updated

Accepted artifact records for checkpointed work must reference the commit or
checkpoint record. Artifact updates must not precede a successful commit and
required push.

### 10. Event written

The orchestrator events log must append a `checkpoint` event with
`STATUS: passed`, the checkpoint receipt reference, and the Git evidence needed
for traceability. Event text must not contain secrets.

### 11. Post-check verification

After all transaction writes, the orchestrator must run post-check verification
over the new runtime tuple. At minimum, post-check verification must enforce:

```text
CURRENT_GATE must not remain active
NEXT_ACTION must not point to the same checkpoint
CHECKPOINT_RECEIPT_REF must not be NONE
```

`aso lint` is the read-only validator for these invariants. It may report
findings, but it must not repair runtime state.

## Failure behavior

If any step fails, later steps in the sequence must not claim success. Failure
routing follows `POST_AUDIT_GIT_CHECKPOINT.md` and
`GIT_CHECKPOINT_VALIDATION_RULES.md`.

Commit failure forbids push. Push failure forbids passed checkpoint state.
Receipt write failure forbids `PROJECT_CHECKPOINT_STATUS: passed`. Runtime
update failure must route to governed correction or owner handling without
inventing a successful checkpoint record.
