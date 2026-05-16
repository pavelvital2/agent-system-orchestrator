# TASK_REGISTRY

## Purpose

Operational registry of task lifecycle state and traceability.

This file is updated by the orchestrator only.

It must not replace task packets, audit reports, RESULT reports, or project documentation.

## Task entries

```text
TASK_ID:
TASK_TITLE:
TASK_TYPE:
TASK_KIND: normal | research_dependency | design_continuation | task_continuation | correction | audit | testing | setup | launch | handover
OWNER_ROLE:
STATUS: pending | ready | running | audit_pending | audit_passed | checkpoint_done | blocked | failed | superseded | completed
TASK_PACKET:
DEPENDENCIES:
REQUESTED_BY_ROLE:
REQUESTED_BY_TASK:
RETURN_TO_REQUESTER_AFTER_AUDIT_PASS: yes | no
RETURN_TO_ROLE_AFTER_AUDIT_PASS:
RETURN_TASK_AFTER_AUDIT_PASS:
RESEARCH_QUESTION_ID:
RESULT_REFS:
AUDIT_REFS:
CORRECTION_LINKS:
COMMIT_HASH:
BRANCH:
PUSH_STATUS: not_required | not_attempted | pushed | failed
ACCEPTED_FILES:
CHECKPOINT_REF:
CREATED_AT:
UPDATED_AT:
```

If no tasks are registered:

```text
NONE
```

## Field rules

- `TASK_ID` must match the task packet identifier.
- `STATUS` must reflect the governed lifecycle state, not an agent recommendation alone.
- `DEPENDENCIES` must list prerequisite task ids or `NONE`.
- `TASK_KIND` must classify the task without adding a second execution role.
- Requester return metadata must be populated for `research_dependency`,
  `design_continuation`, and `task_continuation`; otherwise use `NONE` for
  role/task/question fields and `RETURN_TO_REQUESTER_AFTER_AUDIT_PASS: no`.
- `RETURN_TO_ROLE_AFTER_AUDIT_PASS` and `RETURN_TASK_AFTER_AUDIT_PASS` must not
  route to requester continuation until independent audit pass.
- `RESULT_REFS` must point to bounded RESULT records or `NONE`.
- `AUDIT_REFS` must point to bounded audit RESULT records or `NONE`.
- `CORRECTION_LINKS` must list correction task ids, correction result refs, or `NONE`.
- `COMMIT_HASH` is required after a successful post-audit Git checkpoint; before checkpoint it may be `NONE`.
- `BRANCH` is required after a post-audit Git checkpoint; before checkpoint it may be `NONE`.
- `PUSH_STATUS` must reflect the latest checkpoint push state.
- `ACCEPTED_FILES` must list only audited and accepted changed files or `NONE`.
- `CHECKPOINT_REF` must point to the checkpoint event or record after checkpoint attempt, otherwise `NONE`.
- Superseded tasks must keep their historical refs and set `STATUS: superseded`.

## Rules

- each dispatched task must have one registry entry;
- dependent work must not be marked `ready` until dependencies satisfy transition rules;
- audit pass alone does not imply checkpoint completion;
- `STATUS: checkpoint_done` requires commit hash, branch, pushed status, accepted files, and checkpoint reference;
- failed and blocked tasks must retain result and correction traceability;
- ordinary profile agents must not edit this file.
