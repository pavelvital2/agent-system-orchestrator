# TESTING_STAGE

## Purpose

Testing verifies accepted implementation behavior against the testing task packet and acceptance criteria.

## Main role

`agent-system/01_roles/TESTER.md`

## Inputs

- testing task packet;
- accepted implementation RESULT;
- passed implementation audit RESULT;
- REQUIRED_DOCS listed in the testing task packet.

## Required work

- run only required acceptance, smoke, or runtime checks;
- record reproducible commands or manual steps;
- map each acceptance criterion to pass, fail, blocked, or not checked;
- report defects without fixing implementation.

## Outputs

- testing RESULT;
- acceptance evidence;
- fail list or blocker list when applicable;
- route to developer correction, documentation, setup, or orchestrator according to the task packet.

## Exit criteria

Testing exits with `STATUS: pass` only when all required acceptance criteria in scope have passed with reproducible evidence.
