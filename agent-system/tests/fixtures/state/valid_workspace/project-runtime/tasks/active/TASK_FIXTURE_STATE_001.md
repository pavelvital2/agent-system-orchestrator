# TASK PACKET

```text
TASK_ID: TASK_FIXTURE_STATE_001
TASK_STATUS: active
TASK_KIND: normal
TASK_TYPE: developer
TARGET_ROLE: developer
```

## Purpose

Fixture task packet used by ASO plan-next dispatchability tests.

## Scope In

- Validate that a profile developer dispatch can be recommended when runtime state is ready.

## Scope Out

- Live dispatch execution.

## Expected Outputs

- Dry-run CREATE_AGENT recommendation only.

## Allowed File Changes

- NONE

## Acceptance Criteria

- plan-next reports dispatchable true for this task packet.
