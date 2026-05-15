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
- first task packet can be routed to the correct role;
- known constraints are recorded without inventing requirements.

## Outputs

- initialized project context;
- first requirements or design task packet;
- initial GAP if source inputs are insufficient;
- route to requirements analyst or designer, depending on available input quality.

## Exit criteria

Bootstrap exits when the orchestrator has a valid next bounded task and enough source material to dispatch the next role.
