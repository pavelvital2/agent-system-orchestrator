# ORCHESTRATOR_CONVEYOR_PROTOCOL

## Purpose

The normal orchestrator loop should operate as a conveyor over current ASO
state summaries, receipts, validation reports, and explicit task packets. It
must not reread broad governance documents for every routine step when the same
decision can be made from current JSON sidecars and receipts.

## Normal Context Set

For ordinary operation, the maximum expected context is:

```text
agent-system/00_start/ORCHESTRATOR_START.md
agent-system/02_runtime/ORCHESTRATOR_CONVEYOR_PROTOCOL.md
ASO status/next summaries
current task packet
latest RESULT or AUDIT_RESULT package
latest validation, acceptance, rejection, and audit receipts
```

The preferred summary commands are:

```bash
aso orchestrator status --root . --json-out project-runtime/reports/orchestrator_status.json
aso orchestrator next --root . --json-out project-runtime/reports/orchestrator_next.json
```

Equivalent direct reads of `project-runtime/state/*.json`,
`project-runtime/receipts/**/*.json`, and `project-runtime/reports/**/*.json`
are allowed when the CLI is unavailable.

## Debug And Recovery

Full governance documents remain authoritative for debug, audit, recovery,
schema migration, changelog review, and correction work. When a summary is
missing, malformed, stale, or contradicts a governance document, the
orchestrator must stop normal conveyor flow and enter explicit recovery or
correction routing.

## Non-Execution Boundary

The conveyor protocol is read-only. It does not add live dispatch, daemon
behavior, checkpoint execution, distributed workers, or automatic acceptance.
