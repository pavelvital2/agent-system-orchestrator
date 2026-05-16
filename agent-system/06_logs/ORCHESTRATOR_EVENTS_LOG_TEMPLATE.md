# ORCHESTRATOR_EVENTS_LOG

## Purpose

Append-only operational event log for orchestrator actions and routing decisions.

This file is updated by the orchestrator only.

It must not replace runtime state files, task packets, RESULT reports, or audit reports.

## Event entries

```text
DATE:
EVENT_TYPE: bootstrap | owner_pause | validator_result | checkpoint | manual_intervention | task_dispatch | result_route | audit_route | correction_route | state_update | violation_recovery
ACTOR: orchestrator | project_owner | validator | system
TASK_ID:
GATE_ID:
ACTION_ID:
STATUS:
SUMMARY:
INPUT_REFS:
OUTPUT_REFS:
COMMIT_HASH:
BRANCH:
PUSH_STATUS: not_required | not_attempted | pushed | failed
ACCEPTED_FILES:
FAILURE_REASON:
NEXT_ACTION_REF:
```

If no events are logged:

```text
NONE
```

## Required event coverage

The log must be able to record:

- `bootstrap` for package or project runtime initialization;
- `owner_pause` for an owner-requested or owner-blocked pause;
- `validator_result` for validation pass, fail, blocked, gap, or violation findings;
- `checkpoint` for post-audit Git checkpoint attempts and results;
- `manual_intervention` for owner or operator actions outside the normal agent loop.

## Field rules

- `TASK_ID`, `GATE_ID`, and `ACTION_ID` may be `NONE` only when the event is not tied to that object.
- `INPUT_REFS` and `OUTPUT_REFS` must use bounded references and must not include large copied reports.
- `COMMIT_HASH` is required for successful checkpoint events; otherwise use `NONE`.
- `BRANCH`, `PUSH_STATUS`, and `ACCEPTED_FILES` are required for checkpoint events.
- `FAILURE_REASON` must be populated for failed checkpoint, validator, or recovery events and must not include secret values.
- `NEXT_ACTION_REF` should point to the runtime next-action file or `NONE`.

## Rules

- append one entry for every material orchestrator action;
- log validator and checkpoint failures before recovery routing;
- log checkpoint commit failures with `PUSH_STATUS: not_attempted`;
- log checkpoint push failures with `PUSH_STATUS: failed`;
- log suspected secret or credential risk as a redacted class and affected path or field only;
- log manual intervention without inferring unstated owner intent;
- ordinary profile agents must not edit this file.
