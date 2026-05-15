# HANDOVER_STAGE

## Purpose

Handover transfers accepted project knowledge, artifacts, commands, limitations, and open risks into a durable final package.

## Main roles

- `agent-system/01_roles/RELEASE_MANAGER.md`
- `agent-system/01_roles/TECHNICAL_WRITER.md`

## Inputs

- handover task packet;
- accepted requirements, design, implementation, audit, testing, setup, run, and launch evidence;
- verified user and operational documentation;
- owner decisions relevant to final acceptance.

## Required work

- list accepted artifacts and their source evidence;
- include verified setup and run commands;
- include final documentation index, user-facing docs, operational docs, and runbook references required by the task packet;
- include known limitations and open risks;
- include maintenance notes for routine operation, updates, troubleshooting, and ownership boundaries when applicable;
- include support, rollback, or recovery notes when required;
- confirm documentation reflects verified behavior only;
- prepare final acceptance evidence for orchestrator routing.

## Required handover checks

Handover cannot pass until the RESULT records evidence for each applicable check:

- accepted artifacts are listed with paths, owners or responsible roles, and source evidence;
- documentation and runbook references are complete enough for future operation or maintenance;
- verified setup, run, smoke, recovery, and rollback commands are included or explicitly marked not applicable;
- maintenance notes cover recurring tasks, update constraints, monitoring or log review expectations, and known ownership boundaries when applicable;
- known limitations, open risks, deferred work, and accepted exceptions are listed or explicitly marked `NONE`;
- handover does not mark final project completion directly; it recommends orchestrator-controlled final acceptance.

## Outputs

- handover summary;
- accepted artifact list;
- verified command list;
- documentation and runbook index;
- maintenance notes;
- known limitations and risks;
- final acceptance readiness statement.

## Exit criteria

Handover exits with `STATUS: pass` only when all required accepted artifacts, documentation, runbook references, maintenance notes, and verified operational instructions are present. Final acceptance remains orchestrator-controlled.
