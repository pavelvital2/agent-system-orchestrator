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
- verify owner-facing instructions for starting, using, operating, or accepting the delivered project;
- verify known limitations, unresolved non-blocking risks, and owner decisions are documented;
- confirm rollback or recovery notes when required;
- confirm final audit requirements are present and not bypassed;
- identify unresolved launch blockers;
- avoid performing deployment unless explicitly assigned.

## Required launch readiness checks

Launch readiness cannot pass until the RESULT records evidence for each applicable check:

- accepted implementation, audit, testing, setup, run, and documentation evidence required by the task packet exists;
- owner-facing instructions are complete enough for the owner or operator to use the accepted deliverable;
- known limitations, open risks, deferred items, and non-blocking findings are listed or explicitly marked `NONE`;
- rollback, recovery, restore, disablement, or contingency notes are present when release risk requires them;
- final audit or final review requirement is identified for orchestrator routing;
- production deployment is not performed unless a dedicated task explicitly authorizes it.

## Outputs

- launch readiness RESULT;
- blocker and risk list;
- evidence map from launch criteria to accepted artifacts;
- owner-facing instruction readiness notes;
- known limitations and rollback or recovery readiness notes;
- final audit routing recommendation;
- route to orchestrator-controlled launch, documentation, or handover.

## Exit criteria

Launch exits with `STATUS: pass` only when all required launch criteria are satisfied, owner-facing instructions and rollback or recovery notes are covered where applicable, final audit routing is explicit, and unresolved blockers are absent.
