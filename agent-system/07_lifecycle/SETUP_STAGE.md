# SETUP_STAGE

## Purpose

Setup verifies that the project can be installed, configured, built, migrated, or prepared according to accepted project instructions.

## Main role

`agent-system/01_roles/DEVOPS_SETUP_ENGINEER.md`

## Inputs

- setup task packet;
- accepted implementation and audit results;
- setup or runtime docs;
- owner-approved operational constraints;
- required environment variable names and purposes.

## Required work

- verify setup commands;
- identify required configuration without exposing secret values;
- confirm dependency and version prerequisites when required;
- document setup risks and blockers;
- prepare evidence for run readiness.

## Outputs

- verified setup commands;
- environment variable inventory without values;
- setup readiness result;
- blocker list when setup cannot be completed.

## Exit criteria

Setup exits with `STATUS: pass` only when required setup steps are reproducible from documented inputs and no secret values have been exposed.
