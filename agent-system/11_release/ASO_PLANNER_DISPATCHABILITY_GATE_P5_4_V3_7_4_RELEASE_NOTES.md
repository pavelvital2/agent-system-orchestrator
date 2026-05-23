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
