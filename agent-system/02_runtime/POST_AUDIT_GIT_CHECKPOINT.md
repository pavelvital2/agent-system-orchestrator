# POST_AUDIT_GIT_CHECKPOINT

## Purpose

This document defines the universal post-audit Git checkpoint gate.

The gate is executed only by the orchestrator after a required auditor result
has passed. It records accepted package or project state in Git and then routes
the runtime to the next governed task.

## Authority

The orchestrator may run Git checkpoint commands only inside this gate and only
after all preconditions pass.

Profile agents never commit or push. Task packets cannot grant commit or push
authority to profile agents.

Research dependency results follow the same audit-pass checkpoint rule. If a
research dependency task requires checkpointing, requester continuation may be
marked ready only after the independent auditor passes and this checkpoint
completes successfully.

The orchestrator must not inspect, print, copy, modify, stage, commit, or push
credentials, secret values, token values, private keys, cookies, or local
environment files.

## Required preconditions

A post-audit Git checkpoint may start only when all conditions are true:

- the immediately preceding required audit exists;
- the immediately preceding required audit returned `STATUS: pass`;
- the audited task result is formally valid;
- the audited task result is accepted by the auditor;
- no audit `fail`, `blocked`, or `gap` result exists for the same accepted
  work without a later governed correction and audit pass;
- changed files match the task packet `ALLOWED_FILE_CHANGES`;
- changed files do not match the task packet `FORBIDDEN_FILE_CHANGES`;
- runtime state has no active blocker or GAP that blocks the accepted work;
- `GIT_CHECKPOINT_VALIDATION_RULES.md` passes.

## Forbidden conditions

The orchestrator must not stage, commit, or push after:

- profile-agent `STATUS: pass` without the required auditor `STATUS: pass`;
- auditor `STATUS: fail`;
- auditor `STATUS: blocked`;
- auditor `STATUS: gap`;
- formally invalid profile-agent RESULT;
- formally invalid auditor RESULT;
- pending correction for the same work;
- unaudited research dependency output or research audit fail/blocked/gap when
  requester continuation is waiting;
- suspected secret or credential risk in changed, staged, logged, or generated
  checkpoint material;
- out-of-scope changed files.

## Allowed checkpoint commands

The orchestrator may run only bounded Git commands needed for checkpointing,
for example:

```text
git status
git diff --name-only
git diff --cached --name-only
git add <accepted files only>
git commit -m <accepted task commit message>
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git push
```

The orchestrator must not run commands that print secret values or inspect
credential stores.

## Required checkpoint record

Every checkpoint attempt must create or update bounded records with:

```text
TASK_ID:
AUDIT_REF:
ACCEPTED_RESULT_REF:
ACCEPTED_FILES:
BRANCH:
COMMIT_HASH:
PUSH_STATUS: not_attempted | pushed | failed
CHECKPOINT_STATUS: passed | failed | blocked
FAILURE_REASON:
RECOVERY_ROUTE:
```

Successful checkpoint records must include:

- commit hash;
- branch name;
- push status;
- accepted files;
- accepted task id;
- audit reference.

Failed checkpoint records must not include secret values.

## Runtime updates after success

After a successful commit and push:

- set the task registry entry to `STATUS: checkpoint_done`;
- record `COMMIT_HASH`, `BRANCH`, `PUSH_STATUS`, and accepted files;
- update accepted artifact entries with the commit hash;
- append a `checkpoint` event with `STATUS: passed`;
- route only to the next task allowed by `STATE_TRANSITION_RULES.md`.

## Failure routing

Commit failure:

- do not push;
- log a `checkpoint` event with `STATUS: failed`;
- set `PUSH_STATUS: not_attempted`;
- route to governed correction or owner handling.

Push failure:

- keep the local commit record;
- log a `checkpoint` event with `STATUS: failed`;
- set `PUSH_STATUS: failed`;
- route to governed correction or owner handling.

Secret or credential risk:

- do not stage additional files;
- do not commit;
- do not push;
- log only a redacted secret-risk class and affected path or field;
- route to governed correction or owner handling.

Validation failure:

- do not stage additional files;
- do not commit;
- do not push;
- log validation failure without secret values;
- route according to `GIT_CHECKPOINT_VALIDATION_RULES.md`.
