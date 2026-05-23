# ASO Bootstrap State Reconciliation P5.2 v3.7.2 Release Notes

## Version Tuple

```text
CURRENT_PACKAGE_VERSION: 3.7.2
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.2
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

## Summary

P5.2 corrects bootstrap state and planner contradictions discovered during
generated workspace testing after P5.1. It preserves Runtime Schema `3.1.0`
and Artifact Package Schema `1.1.0`.

## Fixed

- Non-terminal active/open bootstrap state no longer qualifies as ready
  terminal STOP when mandatory bootstrap inputs exist.
- `PROJECT_STATE.TZ_PATH` is documented as a project TZ file path, not an IANA
  timezone string.
- Missing derived Markdown runtime views are documented as materialization or
  repair blockers for strict workspace checks.
- `plan-next` and normal conveyor routing must prefer bootstrap preparation or
  governed correction over misleading terminal readiness.
- Project Factory/state initialization expectations are aligned with
  deterministic bootstrap-ready state when mandatory inputs exist.

## Not Included

- daemon
- live dispatch executor
- checkpoint executor
- ASO Studio
- product-intake engine
- distributed workers
- semantic raw-TZ interpretation
- automatic task execution
