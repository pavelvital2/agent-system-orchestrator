# REQUIREMENTS_STAGE

## Purpose

Requirements turns the TZ and approved owner decisions into a traceable requirements baseline.

## Main role

`agent-system/01_roles/REQUIREMENTS_ANALYST.md`

## Inputs

- requirements task packet;
- TZ or equivalent source brief;
- approved GAP resolutions;
- owner decision records;
- existing accepted requirements docs, if any.

## Required work

- extract explicit requirements;
- classify functional, non-functional, operational, documentation, and acceptance requirements;
- identify contradictions and missing decisions;
- record unresolved items as GAPs;
- preserve source traceability.

## Outputs

- bounded requirements baseline;
- GAP records for unresolved owner decisions;
- acceptance signal summary when supported by inputs;
- route to design only when requirements are sufficient for bounded design.

## Exit criteria

Requirements exits with `STATUS: pass` only when enough requirements exist for the designer to create bounded design docs and task packets without inventing scope.
