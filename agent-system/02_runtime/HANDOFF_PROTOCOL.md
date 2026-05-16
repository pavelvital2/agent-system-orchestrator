# HANDOFF_PROTOCOL

This protocol defines how durable handoff records are created, consumed, superseded, and rejected.

## Source Template

All durable handoffs must use:

```text
agent-system/03_templates/HANDOFF_TEMPLATE.md
```

## Required Fields

Each handoff must include:

```text
STATUS
CREATED_AT
SOURCE_TASK
SOURCE_RESULT
TARGET_ROLE
PURPOSE
REQUIRED_DOCS
READ_INPUTS
SCOPE
DEPENDENCIES
EVIDENCE
CONSUMED_BY_RESULT
SUPERSEDED_BY
```

## Status Lifecycle

Allowed statuses:

```text
draft
active
consumed
superseded
cancelled
```

Allowed transitions:

```text
draft -> active
draft -> cancelled
active -> consumed
active -> superseded
active -> cancelled
```

Forbidden transitions:

```text
consumed -> active
superseded -> active
cancelled -> active
```

## Creation Rules

- A handoff must have a bounded purpose.
- A handoff must name one TARGET_ROLE or the orchestrator/owner when no profile role applies.
- A handoff must include REQUIRED_DOCS and READ_INPUTS, or `NONE`.
- A handoff must not expand task packet scope.
- A handoff must not introduce project-specific requirements into universal runtime rules.
- A handoff must not contain secrets or credentials.

## Consumption Rules

- A profile-agent RESULT consumes an active handoff only when the RESULT corresponds to the same bounded task or target action.
- When consumed, `STATUS` becomes `consumed`.
- `CONSUMED_BY_RESULT` must reference the consuming RESULT.
- A consumed handoff must not be dispatched again.

## Supersession Rules

- A stale or replaced handoff must be marked `superseded`.
- `SUPERSEDED_BY` must reference the replacement handoff.
- Supersession does not accept the underlying work; normal task, audit, testing, documentation, setup, launch, and checkpoint gates still apply.

## Validation Rules

Before dispatch, the orchestrator must verify:

- handoff `STATUS` is `active`;
- `CREATED_AT` exists;
- `TARGET_ROLE` matches the next bounded action;
- dependencies are ready;
- required docs are available and not deprecated;
- `CONSUMED_BY_RESULT` is `NONE`;
- `SUPERSEDED_BY` is `NONE`;
- scope and forbidden changes match the active task packet and governance.

Invalid handoffs must be rejected or corrected through governed recovery flow. A handoff cannot override governance authority, runtime state transition rules, role instructions, accepted-state locking, or filesystem governance.
