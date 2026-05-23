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

## Bootstrap Reconciliation

During bootstrap, the conveyor must treat ASO summaries as inconsistent when
they report terminal STOP for an active/open workspace that still has mandatory
bootstrap inputs and has not completed first profile-agent dispatch. In that
case normal conveyor flow stops and the next route is bootstrap preparation or
governed correction, not terminal completion.

The reconciled bootstrap signals are:

```text
CURRENT_PHASE: bootstrap
PROJECT_STATUS: active
CURRENT_GATE.STATUS: open
NEXT_ACTION.ACTION_SEMANTIC: stop_terminal
```

That tuple is invalid unless a separate documented terminal bootstrap
invariant is present. Missing derived Markdown runtime views are repairable
materialization blockers, and `PROJECT_STATE.TZ_PATH` must reference a project
TZ file such as `project-input/TZ.md`; an IANA timezone string is not a valid
path value.

## Debug And Recovery

Full governance documents remain authoritative for debug, audit, recovery,
schema migration, changelog review, and correction work. When a summary is
missing, malformed, stale, or contradicts a governance document, the
orchestrator must stop normal conveyor flow and enter explicit recovery or
correction routing.

## Non-Execution Boundary

The conveyor protocol is read-only. It does not add live dispatch, daemon
behavior, checkpoint execution, distributed workers, or automatic acceptance.
