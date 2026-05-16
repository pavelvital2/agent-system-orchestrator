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
- first task packet can be routed deterministically to the correct role;
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

The orchestrator may inspect source input only enough to choose this route. It
must not analyze project business logic, resolve ambiguity, invent requirements,
design architecture, or decompose implementation work.

## Outputs

- initialized project context;
- first requirements or design task packet;
- initial GAP if source inputs are insufficient;
- one valid `NEXT_ACTION` using v1.2.0 fields for either
  `TARGET_ROLE: requirements_analyst` or `TARGET_ROLE: designer`.

## Exit criteria

Bootstrap exits when the orchestrator has a valid next bounded task and enough source material to dispatch the next role.
