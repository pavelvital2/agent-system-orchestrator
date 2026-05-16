# DESIGN_STAGE

## Purpose

Design converts accepted requirements into bounded project documentation and executable task packets.

## Main role

`agent-system/01_roles/DESIGNER.md`

## Inputs

- design task packet;
- TZ and requirements baseline, if listed in REQUIRED_DOCS;
- approved GAP resolutions;
- accepted architecture or project docs.

## Required work

- identify architecture and implementation boundaries;
- decompose work into bounded stages and tasks;
- define REQUIRED_DOCS for each task;
- define dependencies, audit gates, testing needs, and documentation needs;
- avoid giant documents and oversized task packets.

## Outputs

- bounded design docs;
- implementation task packets;
- audit packet requirements;
- testing and documentation routing notes;
- GAPs for unresolved design blockers.

## Exit criteria

Design exits with `STATUS: pass` only when the next bounded task can be dispatched without relying on stale context or hidden assumptions. Design pass must be followed by audit.
