# HANDOFF_TEMPLATE

Use this template when creating a durable handoff record between orchestrator, profile agents, auditors, testers, technical writers, or owner-decision flow.

```text
HANDOFF:
HANDOFF_ID:
<stable handoff id>

STATUS:
draft | active | consumed | superseded | cancelled

CREATED_AT:
<ISO-8601 timestamp>

CREATED_BY:
<orchestrator | role | owner>

SOURCE_TASK:
<TASK_ID | NONE>

SOURCE_RESULT:
<RESULT_REF | NONE>

TARGET_ROLE:
<designer | developer | auditor | tester | technical_writer | orchestrator | owner>

PURPOSE:
<bounded handoff purpose>

REQUIRED_DOCS:
- <path> | NONE

READ_INPUTS:
- <path or input ref> | NONE

SCOPE:
IN:
- <allowed item> | NONE
OUT:
- <forbidden item> | NONE

DEPENDENCIES:
- <TASK_ID | RESULT_REF | runtime gate | NONE>

EVIDENCE:
- <evidence ref> | NONE

CONSUMED_BY_RESULT:
<RESULT_REF | NONE>

SUPERSEDES:
<HANDOFF_ID | NONE>

SUPERSEDED_BY:
<HANDOFF_ID | NONE>
```

## Status Lifecycle

- `draft`: created but not dispatchable.
- `active`: current source for the next bounded action.
- `consumed`: completed by the referenced `CONSUMED_BY_RESULT`.
- `superseded`: replaced by `SUPERSEDED_BY`.
- `cancelled`: closed without dispatch by governed orchestrator action.

## Rules

- Only one active handoff may represent the same bounded next action.
- `CREATED_AT` is required for every handoff.
- `CONSUMED_BY_RESULT` must remain `NONE` until a valid RESULT consumes the handoff.
- `SUPERSEDED_BY` must remain `NONE` unless another handoff replaces this one.
- Superseded or cancelled handoffs must not be dispatched.
- A handoff cannot override role instructions, task packet scope, runtime state, or governance.
