# ASO Planner Dispatchability Gate P5.4 v3.7.4 Release Notes

## Version Tuple

```text
CURRENT_PACKAGE_VERSION: 3.7.4
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.4
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

## Summary

P5.4 defines the planner Dispatchability Gate. `plan-next` may recommend
`CREATE_AGENT` only after proving the current next action is dispatchable as a
profile-agent task with a valid target role, task id, task packet, task
registry entry, gate state, blocking-rule status, workspace identity,
repository lock, baseline, and runtime schema evidence.

The canonical invalid route is:

```text
NEXT_ACTION.ACTION_TYPE: correction
NEXT_ACTION.TARGET_ROLE: orchestrator
NEXT_ACTION.TASK_ID: NONE
NEXT_ACTION.TASK_PACKET: NONE
```

For that route, `plan-next` must return a non-dispatch recommendation such as
`CORRECTION_REQUIRED` or `UPDATE_STATE` with machine-readable evidence. It
must not return `CREATE_AGENT`.

## Root Cause

The planner mapped `ACTION_TYPE: correction` to `CREATE_AGENT` through the
action-type recommendation path without first proving that the current action
could dispatch a profile agent. That allowed a control-role correction with no
task packet to look dispatchable.

## Correction

P5.4 centralizes the dispatchability boundary. `CREATE_AGENT` is valid only
when the dispatchability gate proves all required dispatch evidence is present:
dispatch-capable action type, profile execution role, non-`NONE` task id,
non-`NONE` task packet, existing and valid task packet file, compatible task
registry entry, current gate permission, no blocking rules, workspace identity,
repository lock, baseline, and runtime schema compatibility.

When any dispatchability requirement fails, `plan-next` must return a
documented non-dispatch route such as `CORRECTION_REQUIRED`, `UPDATE_STATE`,
`ASK_OWNER`, `FREEZE`, `BOOTSTRAP_PREP`, or `STOP` with machine-readable
reasons.

## Observed Regression

The regression route was:

```text
ACTION_TYPE: correction
TARGET_ROLE: orchestrator
TASK_ID: NONE
TASK_PACKET: NONE
```

This route is not dispatchable because `orchestrator` is a control role and no
task packet exists. It must not produce `CREATE_AGENT`.

## Changed

- Package and governance metadata advance to `3.7.4`.
- Runtime Schema remains `3.1.1`.
- Artifact Package Schema remains `1.1.0`.
- The P5.4 contract defines the dispatchability checks required before
  `CREATE_AGENT` can be recommended.
- The P5.4 contract documents non-dispatch fallback recommendations when
  dispatchability fails.

## Not Included

- Runtime schema migration
- Artifact package schema migration
- Artifact package storage semantic changes
- daemon
- live dispatch executor
- checkpoint executor
- ASO Studio
- product-intake engine
- distributed workers
- semantic raw-TZ interpretation
- automatic task execution

## Validation And CI

Local validation evidence is recorded in
`agent-system/11_release/ASO_PLANNER_DISPATCHABILITY_GATE_P5_4_V3_7_4_VALIDATION_REPORT.md`.
The final remote CI run for the documentation report commit remains an
orchestrator-owned post-audit checkpoint after commit and push; these release
notes do not claim final CI for an unpushed report commit.
