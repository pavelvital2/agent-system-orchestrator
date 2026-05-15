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
OWNER_ROLE:
STATUS: pending | ready | running | audit_pending | audit_passed | checkpoint_done | blocked | failed | superseded | completed
TASK_PACKET:
DEPENDENCIES:
RESULT_REFS:
AUDIT_REFS:
CORRECTION_LINKS:
COMMIT_HASH:
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
- `RESULT_REFS` must point to bounded RESULT records or `NONE`.
- `AUDIT_REFS` must point to bounded audit RESULT records or `NONE`.
- `CORRECTION_LINKS` must list correction task ids, correction result refs, or `NONE`.
- `COMMIT_HASH` is required after a post-audit Git checkpoint; before checkpoint it may be `NONE`.
- Superseded tasks must keep their historical refs and set `STATUS: superseded`.

## Rules

- each dispatched task must have one registry entry;
- dependent work must not be marked `ready` until dependencies satisfy transition rules;
- audit pass alone does not imply checkpoint completion;
- failed and blocked tasks must retain result and correction traceability;
- ordinary profile agents must not edit this file.
