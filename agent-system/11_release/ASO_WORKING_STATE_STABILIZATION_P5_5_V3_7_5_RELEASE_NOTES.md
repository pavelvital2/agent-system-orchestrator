# ASO Working State Stabilization P5.5 v3.7.5 Release Notes

## Version Tuple

```text
CURRENT_PACKAGE_VERSION: 3.7.5
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.5
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.1
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

## Summary

P5.5 stabilizes active version metadata, cross-link readiness documentation,
and governance registry coverage around the accepted P5.4 planner
Dispatchability Gate. The active package and governance ruleset versions
advance to `3.7.5`; Runtime Schema remains `3.1.1`; Artifact Package Schema
remains `1.1.0`.

## Changed

- Package and governance metadata advance to `3.7.5`.
- Cross-link readiness checks now reference the active P5.5 tuple instead of
  stale v3.0.1 package/governance and v3.0.0 runtime constants.
- Governance registry includes a critical P5.4/P5.5 planner dispatchability
  gate rule.
- Governance changelog records the P5.5 stabilization as accepted.
- Final package verification evidence is recorded in
  `agent-system/11_release/ASO_WORKING_STATE_STABILIZATION_P5_5_V3_7_5_VALIDATION_REPORT.md`.

## Not Included

- Runtime schema migration
- Artifact package schema migration
- Planner implementation changes
- Artifact package storage semantic changes
- daemon
- live dispatch executor
- checkpoint executor
- ASO Studio
- product-intake engine
- distributed workers
- automatic task execution

## Validation

Local final validation evidence is recorded in
`agent-system/11_release/ASO_WORKING_STATE_STABILIZATION_P5_5_V3_7_5_VALIDATION_REPORT.md`.
Remote GitHub Actions evidence remains a post-push observation and is not
claimed by these uncommitted release evidence edits.
