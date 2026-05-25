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

- verify dependency prerequisites, supported versions, package managers, external services, and required local tools;
- verify configuration templates or example config files are present when the project needs configuration;
- identify required environment variable names, purpose, required/optional status, and safe example placeholders without exposing secret values;
- verify migrations, seed commands, setup scripts, build scripts, or initialization scripts required before first run;
- verify local run instructions are documented well enough for a fresh agent or owner to reproduce setup;
- document setup risks and blockers;
- prepare evidence for run readiness.

## Required setup gate checks

Setup cannot pass until the RESULT records evidence for each applicable check:

- dependencies are listed with installation commands or documented prerequisites;
- configuration files are documented by template, sample, or creation instruction;
- environment variables are listed without values, tokens, credentials, cookies, private keys, or host-specific secrets;
- migrations, setup scripts, data initialization, build steps, or equivalent preparation commands are documented and verified when applicable;
- local run instructions identify the working directory, command sequence, and expected successful readiness signal;
- missing prerequisites are reported as `STATUS: blocked` or `STATUS: gap` instead of being guessed.

## Outputs

- verified setup commands;
- environment variable inventory without values;
- configuration template readiness notes;
- migration, setup script, build, or initialization readiness notes;
- local run instruction readiness notes;
- setup readiness result;
- blocker list when setup cannot be completed.

## Exit criteria

Setup exits with `STATUS: pass` only when required setup steps are reproducible from documented inputs, dependencies and local run preparation are covered, and no secret values have been exposed.
