# ASO Bootstrap TASK_REGISTRY Alignment P5.3 v3.7.3 Release Notes

## Version Tuple

```text
CURRENT_PACKAGE_VERSION: 3.7.3
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.3
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

## Summary

P5.3 aligns the active TASK_REGISTRY task-kind contract with governed
bootstrap routing. `bootstrap` is allowed for the first bootstrap route and
governed bootstrap correction/preparation tasks. Unknown `task_kind` values
remain forbidden.

## Changed

- Package and governance metadata advance to `3.7.3`.
- Runtime schema metadata advances to `3.1.1` for the TASK_REGISTRY
  task-kind contract alignment.
- TASK_REGISTRY template text explicitly allows `bootstrap` only for governed
  bootstrap routing and correction/preparation.
- Artifact Package Schema remains `1.1.0`.

## Not Included

- Artifact package storage semantic changes
- Runtime protocol expansion beyond task-kind contract alignment
- daemon
- live dispatch executor
- checkpoint executor
- ASO Studio
- product-intake engine
- distributed workers
- semantic raw-TZ interpretation
- automatic task execution
