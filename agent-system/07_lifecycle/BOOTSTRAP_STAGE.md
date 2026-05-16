# BOOTSTRAP_STAGE

## Purpose

Bootstrap prepares the project for deterministic orchestration before requirements or design work starts.

## Inputs

- TZ or equivalent source brief;
- universal agent-system package;
- initial project workspace;
- owner-provided constraints;
- runtime state templates.

## Required checks

- source inputs are present and identifiable;
- no secret values are copied into package or task docs;
- project runtime state can be created by the orchestrator;
- required role and template package files exist for both requirements and
  design routing;
- first bootstrap task packet can be created and routed deterministically to
  the correct role;
- known constraints are recorded without inventing requirements.

## Routing rule

Bootstrap must choose exactly one first profile-agent route:

```text
if source input is sufficiently structured for design:
  route to designer
else:
  route to requirements_analyst
```

Source input is sufficiently structured for direct design only when it contains
enough explicit information for architecture and task planning without guessing:
project purpose, scope boundaries, target deliverables, major constraints,
acceptance or success criteria, runtime/setup expectations when relevant, and
known dependencies when relevant.

If the input is incomplete, ambiguous, or the orchestrator is unsure, bootstrap
routes to `requirements_analyst`.

Before that route may be dispatched, the orchestrator must create or reference a
valid bootstrap task packet using:

```text
agent-system/03_templates/BOOTSTRAP_TASK_PACKET_TEMPLATE.md
```

Canonical bootstrap task packet path convention:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md
```

Concrete first-route paths:

```text
project-runtime/bootstrap/TASK_BOOTSTRAP_REQUIREMENTS_ANALYST_001.md
project-runtime/bootstrap/TASK_BOOTSTRAP_DESIGNER_001.md
```

The bootstrap task packet is an orchestrator-created runtime input. Profile
agents may read it but must not edit it. The first profile-agent `NEXT_ACTION`
must reference this packet in `TASK_PACKET`; `TASK_PACKET: NONE` is forbidden
for first profile-agent dispatch. A handoff file is not a task packet
substitute.

The orchestrator may inspect source input only enough to choose this route. It
must not analyze project business logic, resolve ambiguity, invent requirements,
design architecture, or decompose implementation work.

## Outputs

- initialized project context;
- first requirements or design bootstrap task packet under
  `project-runtime/bootstrap/`;
- initial GAP if source inputs are insufficient;
- one valid `NEXT_ACTION` using the current `NEXT_ACTION_TEMPLATE.md` and
  active runtime schema for either `TARGET_ROLE: requirements_analyst` or
  `TARGET_ROLE: designer`.

Bootstrap `NEXT_ACTION` output must include:

```text
ACTION_ID
ACTION_TYPE
TARGET_ROLE
TASK_ID
TASK_PACKET
DEPENDENCY_STATUS
BLOCKED_BY
ACTION_SEMANTIC
REQUESTER_RETURN_CONTEXT
BLOCKING_OR_RESUME_CONTEXT
REQUIRED_UNIVERSAL_DOCS
REQUIRED_PROJECT_DOCS
EXPECTED_RESULT
INSTRUCTION_FOR_ORCHESTRATOR
```

For ordinary first bootstrap dispatch:

```text
ACTION_SEMANTIC: normal
REQUESTER_RETURN_CONTEXT: NONE
BLOCKING_OR_RESUME_CONTEXT: NONE
```

## Exit criteria

Bootstrap exits when the orchestrator has a valid next bounded task packet and
enough source material to dispatch the next role.
