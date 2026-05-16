# RUN_STAGE

## Purpose

Run verifies that the accepted project can start and complete required smoke checks in the intended local or controlled runtime context.

## Main roles

- `agent-system/01_roles/DEVOPS_SETUP_ENGINEER.md`
- `agent-system/01_roles/TESTER.md`

## Inputs

- run or smoke task packet;
- setup readiness evidence;
- accepted implementation and audit results;
- runtime commands from accepted docs.

## Required work

- start the application or service using documented commands;
- run the required smoke command or documented smoke checklist;
- inspect logs, command output, health endpoints, or equivalent runtime signals required by the task packet;
- confirm absence of critical startup errors, unhandled exceptions, failed required services, or crash loops;
- record command output or reproducible manual evidence;
- identify runtime blockers, missing configuration, or portability issues;
- avoid changing behavior outside the task packet.

## Required run gate checks

Run cannot pass until the RESULT records evidence for each applicable check:

- application start command was executed or the task packet explains why a manual start is required;
- expected startup success signal is observed, such as listening port, ready log line, completed command, health check, or UI availability;
- smoke command or smoke checklist was executed with a pass result;
- logs or equivalent runtime output were inspected for critical errors;
- no critical errors remain unresolved;
- runtime blockers are reported as `STATUS: blocked` or `STATUS: fail` according to whether verification was impossible or checks explicitly failed.

## Outputs

- run readiness result;
- smoke evidence;
- startup evidence;
- log or runtime-output review evidence;
- runtime blocker or GAP list;
- route to launch readiness only when required checks pass.

## Exit criteria

Run exits with `STATUS: pass` only when the project starts as required, all required smoke checks pass, logs or equivalent runtime output show no unresolved critical errors, and evidence is reproducible from documented commands.
