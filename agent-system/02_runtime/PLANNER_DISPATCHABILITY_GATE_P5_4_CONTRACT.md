# PLANNER_DISPATCHABILITY_GATE_P5_4_CONTRACT

## Version Boundary

P5.4 is the planner dispatchability gate correction for the ASO package.

```text
PACKAGE_VERSION: 3.7.4
GOVERNANCE_RULESET_VERSION: 3.7.4
RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
```

Runtime Schema `3.1.1` and Artifact Package Schema `1.1.0` are preserved.
P5.4 changes the planner recommendation contract only; it does not redefine
runtime sidecar envelopes, artifact package manifests, RESULT packages, or
AUDIT_RESULT packages.

## Dispatchability Gate

`CREATE_AGENT` is a dispatch recommendation. `plan-next` may return it only
when `can_dispatch_agent()` proves the current action is dispatchable.

`can_dispatch_agent()` must require all of the following:

- `NEXT_ACTION.ACTION_TYPE` is dispatch-capable.
- `NEXT_ACTION.TARGET_ROLE` is a profile execution role.
- `NEXT_ACTION.TARGET_ROLE` is not a control or pseudo role such as
  `orchestrator`, `owner`, `project_owner`, or `none`.
- `NEXT_ACTION.TASK_ID` exists and is not `NONE`.
- `NEXT_ACTION.TASK_PACKET` exists and is not `NONE`.
- The referenced task packet file exists.
- The referenced task packet validates as a dispatchable task packet, not a
  task proposal or malformed document.
- The task registry entry is compatible with the target task and task kind.
- The current gate permits dispatch.
- Blocking rules do not prevent dispatch.
- Workspace identity, repository lock, baseline tracking, and runtime schema
  checks pass, unless an explicit first-bootstrap exception is documented by
  the active runtime contract.

## Required Failure Route

If `can_dispatch_agent()` fails, `plan-next` must not return `CREATE_AGENT`.
It must return a non-dispatch recommendation and machine-readable evidence for
the failed dispatchability checks.

Allowed non-dispatch recommendations include:

- `CORRECTION_REQUIRED`
- `UPDATE_STATE`
- `ASK_OWNER`
- `FREEZE`
- `BOOTSTRAP_PREP`
- `STOP`

The planner may use another documented non-dispatch recommendation when the
runtime transition contract explicitly permits it. The response status must
make the route non-dispatchable, for example `blocked` or
`correction_required`.

For this canonical invalid tuple:

```text
NEXT_ACTION.ACTION_TYPE: correction
NEXT_ACTION.TARGET_ROLE: orchestrator
NEXT_ACTION.TASK_ID: NONE
NEXT_ACTION.TASK_PACKET: NONE
```

`plan-next` must return a non-dispatch recommendation. It must not recommend
`CREATE_AGENT`.

## Non-Goals

P5.4 does not add a daemon, live dispatch executor, checkpoint executor, ASO
Studio, distributed workers, external queue infrastructure, product-intake
engine, product generator, semantic raw-TZ interpretation, or automatic task
execution.

P5.4 does not authorize the orchestrator to implement code, tests, schemas, or
profile-agent outputs directly. The orchestrator remains a conveyor over
validated runtime state, task packets, artifact packages, audit results,
receipts, and checkpoint/preflight evidence.

## Filesystem Boundary

The following roots remain forbidden as tracked package files:

```text
project-input/
project-runtime/
project-archive/
.venv/
```
