# ACCEPTED_ARTIFACTS

## Purpose

Operational registry of artifact acceptance state.

This file records bounded references to artifacts and their acceptance status.
It must not store full artifact contents.

This file is updated by the orchestrator only.

## Artifact entries

```text
ARTIFACT_ID:
ARTIFACT_TYPE:
ARTIFACT_REF:
STATUS: draft | accepted | failed | superseded
SOURCE_TASK:
SOURCE_RESULT_REF:
AUDIT_REF:
SUPERSEDES:
SUPERSEDED_BY:
COMMIT_HASH:
BRANCH:
PUSH_STATUS: not_required | not_attempted | pushed | failed
CHECKPOINT_REF:
ACCEPTED_AT:
UPDATED_AT:
NOTES:
```

If no artifacts are registered:

```text
NONE
```

## Status rules

- `draft` means produced but not yet accepted through the required gate.
- `accepted` means the artifact passed required validation or audit and is part of accepted state.
- `failed` means the artifact or its producing result failed validation or audit and is not accepted state.
- `superseded` means a newer accepted or governed replacement has replaced the artifact.

## Traceability rules

- `ARTIFACT_REF` must be a bounded file path, report path, or stable reference.
- `SOURCE_TASK` must identify the producing task or `NONE`.
- `SOURCE_RESULT_REF` must point to the producing RESULT or `NONE`.
- `AUDIT_REF` is required for artifacts accepted through an audit gate; otherwise use `NONE`.
- `SUPERSEDES` and `SUPERSEDED_BY` must use artifact ids or `NONE`.
- `COMMIT_HASH` is required after a successful post-audit Git checkpoint; before checkpoint it may be `NONE`.
- `BRANCH` is required after a post-audit Git checkpoint; before checkpoint it may be `NONE`.
- `PUSH_STATUS` must reflect whether the accepted artifact has been pushed after checkpoint.
- `CHECKPOINT_REF` must point to the checkpoint event or record after checkpoint attempt, otherwise `NONE`.

## Rules

- failed artifacts must remain distinguishable from draft artifacts;
- superseded artifacts must remain traceable and must not be deleted from the registry;
- accepted-state locking rules apply to `STATUS: accepted`;
- audit-accepted artifacts are not fully checkpointed until commit hash, branch, pushed status, and checkpoint reference are recorded;
- ordinary profile agents must not edit this file.
