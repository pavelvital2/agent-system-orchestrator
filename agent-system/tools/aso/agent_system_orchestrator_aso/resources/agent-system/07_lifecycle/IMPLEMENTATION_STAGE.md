# IMPLEMENTATION_STAGE

## Purpose

Implementation performs one bounded task exactly as described by the task packet.

## Main role

`agent-system/01_roles/DEVELOPER.md`

## Inputs

- implementation task packet;
- REQUIRED_DOCS listed in that task packet;
- accepted prior results only when listed as required inputs.

## Required work

- modify only files allowed by the task packet;
- implement only scope IN;
- avoid scope OUT and unrelated refactoring;
- run focused verification commands when appropriate;
- report changed files, risks, blockers, and GAPs.

## Outputs

- scoped implementation result;
- command evidence;
- changed file list;
- risks and limitations;
- route to implementation audit.

## Exit criteria

Implementation exits with `STATUS: pass` only when the bounded change is ready for independent audit. It does not proceed directly to testing, setup, documentation, or launch.

## Audit gate

Implementation pass requires an auditor before any downstream stage accepts the work.
