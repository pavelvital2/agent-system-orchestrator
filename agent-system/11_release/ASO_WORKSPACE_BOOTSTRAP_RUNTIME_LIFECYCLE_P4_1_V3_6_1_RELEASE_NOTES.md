# ASO Workspace Bootstrap / Runtime Materialization / Lifecycle P4.1 v3.6.1 Release Notes

## Status

Placeholder release notes for the P4.1 hotfix. Final validation evidence is
recorded by the final validation/cleanup task after all bounded hotfix tasks
and audits complete.

## Active Tuple

```text
CURRENT_PACKAGE_VERSION: 3.6.1
CURRENT_GOVERNANCE_RULESET_VERSION: 3.6.1
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

## Summary

P4.1 is a bounded hotfix to corrected P4. It fixes workspace/package mode guard
handling, materialized runtime Markdown compatibility views derived from JSON
sidecars, and the missing lifecycle termination event after RESULT before
audit routing.

ASO remains a deterministic governance/control conveyor. It does not
semantically read raw TZ, replace project designer or requirements analyst
reasoning, generate product questions from TZ, install product-intake code or a
product-intake engine, run a daemon, dispatch live agents, execute
checkpoints, generate products, collect secrets, or run external workers.

## Runtime Schema Impact

Runtime Schema remains `3.1.0`. This hotfix does not redefine the P2/P3
runtime sidecar envelope and does not migrate active runtime state.

## Superseded Work

The branch `upgrade/product-intake-capability-p4-v3.6.0` remains superseded
and non-authoritative. It must stay untouched and must not be merged as the
authoritative P4.1 line.
