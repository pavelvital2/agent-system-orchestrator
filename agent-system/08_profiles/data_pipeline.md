# Project profile: data_pipeline

## When to use

Use this profile for batch, streaming, extract-transform-load, synchronization, enrichment, reporting, or scheduled data processing systems.

## Required gates and checks

- Verify source, transform, sink, schedule, freshness, retention, and replay expectations.
- Check data quality rules, schema evolution, idempotency, deduplication, and backfill behavior.
- Confirm failure handling, retry policy, partial-run recovery, and alerting expectations.
- Validate data volume, performance, privacy, and access control assumptions.
- Confirm lineage and evidence requirements for produced datasets or reports.

## Typical artifacts

- pipeline architecture or flow notes;
- source and sink schema documentation;
- transform logic;
- schedule or orchestration configuration;
- data quality checks;
- runbook, backfill notes, and smoke checklist.

## Test expectations

- Unit tests for transformations and validation rules.
- Fixture-based integration tests across representative source and sink data.
- Idempotency and duplicate-handling tests when writes are in scope.
- Backfill or replay tests when historical processing is in scope.
- Smoke checks for a minimal safe run.

## Setup considerations

- Document required runtimes, storage, compute, scheduler, queue, or service dependencies.
- Define configuration key names for sources, sinks, credentials, schedules, and limits without exposing values.
- Specify local fixture setup and safe sample execution commands.

## Launch considerations

- Confirm dry run or minimal safe run succeeds.
- Confirm data quality checks, alerting, retry behavior, and rollback or correction paths are defined.
- Confirm backfill, replay, and retention risks are accepted when applicable.
- Confirm launch does not depend on unreviewed production data mutation.

## Handover considerations

- Provide pipeline map, run commands, schedule notes, schema paths, data quality checks, backfill procedure, and failure recovery steps.
- Identify ownership boundaries for source and sink systems.
