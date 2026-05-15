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

- start the project using documented commands;
- run required smoke checks;
- record command output or reproducible manual evidence;
- identify runtime blockers, missing configuration, or portability issues;
- avoid changing behavior outside the task packet.

## Outputs

- run readiness result;
- smoke evidence;
- runtime blocker or GAP list;
- route to launch readiness only when required checks pass.

## Exit criteria

Run exits with `STATUS: pass` only when the project starts as required and all required smoke checks pass.
