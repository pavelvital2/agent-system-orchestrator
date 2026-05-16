# STATUS_SUMMARY

## Purpose

Compact operational summary for the current project state.

This file is updated by the orchestrator only.

It must summarize state by reference and must not replace source runtime files or full reports.

## Current summary

```text
PROJECT_STATUS: active | blocked | completed | archived
CURRENT_PHASE:
CURRENT_GATE:
GATE_STATUS: open | passed | failed | blocked | skipped
LAST_ACCEPTED_RESULT:
LAST_FAILED_RESULT:
ACTIVE_BLOCKERS:
ACTIVE_GAPS:
NEXT_ACTION:
LAUNCH_READINESS: not_started | not_ready | blocked | ready | launched | not_applicable
UPDATED_AT:
```

## Detail references

```text
PROJECT_STATE_REF:
CURRENT_GATE_REF:
NEXT_ACTION_REF:
TASK_REGISTRY_REF:
ACCEPTED_ARTIFACTS_REF:
AGENT_RESULTS_LOG_REF:
ORCHESTRATOR_EVENTS_LOG_REF:
```

## Field rules

- `PROJECT_STATUS` must match `PROJECT_STATE.md`.
- `CURRENT_GATE` and `GATE_STATUS` must match `CURRENT_GATE.md`.
- `LAST_ACCEPTED_RESULT` must reference the latest accepted result or `NONE`.
- `LAST_FAILED_RESULT` must reference the latest failed result or `NONE`.
- `ACTIVE_BLOCKERS` must list blocker ids or `NONE`.
- `ACTIVE_GAPS` must list GAP ids or `NONE`.
- `NEXT_ACTION` must summarize exactly one next action and reference `NEXT_ACTION.md`.
- `LAUNCH_READINESS` must reflect the current launch gate state when applicable; otherwise use `not_applicable`.

## Rules

- keep this file compact;
- prefer ids and refs over copied content;
- update after material task, audit, checkpoint, blocker, GAP, or launch-readiness changes;
- ordinary profile agents must not edit this file.
