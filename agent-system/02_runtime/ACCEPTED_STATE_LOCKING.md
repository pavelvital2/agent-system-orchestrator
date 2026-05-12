# ACCEPTED_STATE_LOCKING

## Purpose

This document defines when outputs become accepted and how accepted artifacts may be changed without corrupting deterministic orchestration.

## Accepted state rules

1. Designer output is accepted only after design audit pass.
2. Developer output is accepted only after implementation audit pass.
3. Tested behavior is accepted only after tester pass when testing is required.
4. Documentation output is accepted only when it documents verified implementation and passes its governed path.
5. Profile-agent `STATUS: pass` alone does not create accepted state if mandatory audit/testing remains.

## Lock rule

After acceptance, an artifact is locked as source-of-truth for downstream tasks. It cannot be modified in place by unrelated tasks.

Changing accepted artifacts requires:

```text
new bounded task
explicit scope
required docs
allowed file changes
mandatory audit if design/implementation/source contract changes
runtime state update after accepted result
```

## Superseded task handling

Task packets should include:

```text
TASK_STATUS: active | completed | superseded | deprecated
SUPERSEDES: <TASK_ID | NONE>
SUPERSEDED_BY: <TASK_ID | NONE>
```

Rules:

- Superseded task receives a new replacing TASK_ID.
- Old and new task packets cannot both be active.
- Superseded task packet cannot be used in NEXT_ACTION.
- Superseded docs cannot be source-of-truth for new work.

## Correction handling

Correction task packets should include:

```text
CORRECTION_OF:
SOURCE_RESULT_REF:
ATTEMPT_NO:
FAILURE_TYPE:
```

Rules:

- failed result is not accepted;
- correction uses fresh agent context;
- correction follows mandatory audit path;
- repeated same failure escalates to designer/owner routing.

## Accepted artifact violation

If an accepted artifact is modified outside a governed task, the orchestrator treats it as workflow violation and enters correction.
