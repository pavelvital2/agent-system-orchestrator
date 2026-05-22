# ASO Workspace Bootstrap / Runtime Materialization / Lifecycle P4.1 v3.6.1 Release Notes

## Status

Final local release validation completed for the P4.1 hotfix package on
2026-05-22. The validation report is recorded in
`agent-system/11_release/ASO_WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_V3_6_1_VALIDATION_REPORT.md`.

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

## Release Scope

This hotfix finalizes the corrected workspace bootstrap/runtime lifecycle
surface:

- package/workspace mode detection rejects workspace roots requested as package
  roots with an actionable workspace-mode recommendation;
- `aso state render --root WORKSPACE --confirm-write` materializes derived
  `project-runtime/*.md` compatibility views from canonical JSON sidecars;
- strict workspace lint/doctor report missing derived views with the render
  repair command;
- `aso lifecycle terminate-agent --root WORKSPACE --from-result RESULT --confirm-write`
  records the required termination event after RESULT and before audit route;
- Project Factory local generated projects document and exercise workspace-mode
  checks rather than package-mode checks;
- positive and negative fixtures cover the three reported incidents.

The corrected bootstrap sequence is summarized in
`agent-system/02_runtime/CORRECTED_BOOTSTRAP_SEQUENCE_P4_1.md`. Incident replay
coverage is summarized in
`agent-system/11_release/ASO_WORKSPACE_BOOTSTRAP_RUNTIME_LIFECYCLE_P4_1_V3_6_1_INCIDENT_REPLAY_NOTES.md`.

## Validation Summary

Final local validation passed for unit tests, smoke tests, editable install,
installed CLI verification, strict package status/lint/doctor/package-layout,
checkpoint preflight, whitespace checks, incident fixture coverage, and
forbidden-root tracked-file checks.

The final validation report records exact commands and outcomes. The required
`bash install.sh` validation created local untracked `.venv/`; final cleanup
removed `.venv/`, bytecode caches, egg-info directories, and the local P4.1
`project-input/` hotfix package before commit/push.

## Publication Boundary

No `project-input/`, `project-runtime/`, `project-archive/`, or `.venv/` files
are tracked for publication. The local P4.1 hotfix package under
`project-input/aso_hotfix_workspace_bootstrap_runtime_lifecycle_p4_1_v3_6_1/`
is input material only and must be removed during final cleanup, not shipped as
package state.

## Non-Goals Preserved

This release does not add semantic TZ parsing, product-intake automation,
daemon mode, live dispatch, checkpoint execution, external workers, product
generation, or secret collection.
