# AGENT_LIFECYCLE_VALIDATION_RULES

## Purpose

This document defines validator rules for the mandatory one-profile-agent
lifecycle policy.

## Source documents

```text
agent-system/02_runtime/PROFILE_AGENT_LIFECYCLE.md
agent-system/02_runtime/AGENT_LIFECYCLE.md
agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
agent-system/09_validators/RESULT_VALIDATION_RULES.md
agent-system/09_validators/schemas/result.schema.json
```

## Validation points

Validators apply these rules:

```text
before_dispatch:
  reject dispatch to an existing profile-agent instance

after_agent_result:
  validate RESULT lifecycle fields
  validate agent result-received event when present
  require agent termination event before lifecycle completion

before_next_task_dispatch:
  require previous profile-agent instance termination for the completed task
```

## Required rules

### AGENT_LIFECYCLE_001: one agent, one task

Each `AGENT_INSTANCE_ID` must be associated with exactly one `TASK_ID`.

Invalid:

```text
same AGENT_INSTANCE_ID appears with multiple TASK_ID values
same AGENT_INSTANCE_ID is dispatched to a second task
same profile-agent context is used for correction after RESULT
```

Correction requires a new task packet where applicable and a new
`AGENT_INSTANCE_ID`.

### AGENT_LIFECYCLE_002: RESULT lifecycle fields

A profile-agent RESULT is invalid if it omits:

```text
TASK_ID
AGENT_INSTANCE_ID
SUMMARY
CHANGED_FILES
COMMANDS_RUN
TESTS_RUN
RISKS
LIMITATIONS
REUSE_ALLOWED
AGENT_TERMINATION_REQUIRED
```

`REUSE_ALLOWED` must be `false`.

`AGENT_TERMINATION_REQUIRED` must be `true`.

`TASK_ID` must match the dispatched task and must not contradict `TASK`.

### AGENT_LIFECYCLE_003: termination event required

After a RESULT exists for an `AGENT_INSTANCE_ID`, the lifecycle is incomplete
until `project-runtime/agents/instances.jsonl` contains:

```text
event: agent_instance_terminated
agent_instance_id: <same AGENT_INSTANCE_ID>
task_id: <same TASK_ID>
reuse_allowed: false
```

Inline prose such as "agent closed" is not a substitute for the machine-readable
termination event.

### AGENT_LIFECYCLE_004: result-received reuse flag

When the lifecycle log contains `agent_result_received`, that event must record:

```text
reuse_allowed: false
```

Missing, true, unknown, or non-false values are invalid.

### AGENT_LIFECYCLE_005: physical deletion is not required

Validators must not require a physical deletion primitive such as deleting a
chat, stopping a container, or killing a process.

Validators must require logical termination evidence:

```text
agent_instance_terminated event exists
agent is not sent another task
standardized RESULT remains the authoritative output
```

Physical deletion evidence may be recorded as supporting evidence, but it does
not replace logical termination.

## Lint mapping

`aso lint` implements the read-only filesystem checks for this policy:

```text
LINT_AGENT_001: RESULT does not forbid agent reuse
LINT_AGENT_002: RESULT does not require agent termination
LINT_AGENT_003: Agent termination event is missing after RESULT
LINT_AGENT_004: Agent result event allows reuse
LINT_AGENT_005: RESULT is missing lifecycle fields
LINT_AGENT_006: Agent instance is associated with multiple task ids
```

Future validators may add timestamp ordering checks, but lack of timestamp
ordering support must not weaken the required `agent_instance_terminated` event.
