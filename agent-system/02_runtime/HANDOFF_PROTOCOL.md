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

## Routine Context Builder Contract

Routine orchestrator handoff context is compact and machine-readable. It is
defined by `agent-system/02_runtime/ORCHESTRATOR_RUNTIME_CONTRACT.json` field
`handoff_context_builder_contract`.

Routine handoffs include only:

- required runtime contract sections;
- current runtime state refs;
- current event, RESULT/AUDIT_RESULT, artifact manifest, or receipt refs;
- current task packet;
- the specific target role doc;
- doc tokens required by the target role.

Routine handoffs must not include the full governance corpus, all role docs,
all templates, full changelog, release notes, or all validator docs. Reference
docs are allowed only in `debug`, `explain`, or `violation_recovery` mode with
an explicit reason, or when a validator marks them required.

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
- A corrected P4 project-design handoff must target the runtime role
  `requirements_analyst` and state in `PURPOSE` or `SCOPE` that the agent is
  performing the `PROJECT_DESIGNER` responsibility profile.
- A project-design handoff must include
  `agent-system/01_roles/PROJECT_DESIGNER.md` in REQUIRED_DOCS and must include
  the source TZ, owner decision records, accepted design context, and applicable
  template references only when those inputs are explicitly authorized.
- A project-design handoff must forbid ASO semantic TZ interpretation,
  product-intake automation, live dispatch, runtime mutation, checkpoint
  execution, product generation, external workers, secret collection, and
  technical owner questions.
- A handoff to `project_owner` for a design gap must reference one audited
  owner question card only. Bulk gap lists may remain internal evidence, but
  owner-facing handoff is sequential.

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
- project-design handoffs use the runtime role `requirements_analyst`, not a
  new runtime role value, unless a later audited schema revision explicitly
  changes the runtime schema.
- owner-facing design-gap handoffs contain no framework, library, database,
  queue, ORM, transport, deployment, hosting, cache, worker, scheduler, or API
  mechanism question.

Invalid handoffs must be rejected or corrected through governed recovery flow. A handoff cannot override governance authority, runtime state transition rules, role instructions, accepted-state locking, or filesystem governance.
