# LAUNCH_STAGE

## Purpose

Launch verifies readiness to release or expose the accepted project according to the task packet.

## Main role

`agent-system/01_roles/RELEASE_MANAGER.md`

## Inputs

- launch task packet;
- passed audit results;
- passed testing results;
- setup and run readiness evidence;
- documentation readiness evidence;
- approved owner decisions required for launch.

## Required work

- confirm all required gates have passed;
- verify launch criteria from the task packet;
- confirm rollback or recovery notes when required;
- identify unresolved launch blockers;
- avoid performing deployment unless explicitly assigned.

## Outputs

- launch readiness RESULT;
- blocker and risk list;
- evidence map from launch criteria to accepted artifacts;
- route to orchestrator-controlled launch, documentation, or handover.

## Exit criteria

Launch exits with `STATUS: pass` only when all required launch criteria are satisfied and unresolved blockers are absent.
