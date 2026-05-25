# ASO Artifact Package Model P5 v3.7.0 Release Notes

## Status

Final local release validation for the P5 artifact package model package is
recorded in
`agent-system/11_release/ASO_ARTIFACT_PACKAGE_MODEL_P5_V3_7_0_VALIDATION_REPORT.md`.

## Active Tuple

```text
CURRENT_PACKAGE_VERSION: 3.7.0
CURRENT_GOVERNANCE_RULESET_VERSION: 3.7.0
CURRENT_RUNTIME_SCHEMA_VERSION: 3.1.0
ARTIFACT_PACKAGE_SCHEMA_VERSION: 1.0.0
DESIGN_GAP_GOVERNANCE_SCHEMA_VERSION: 1.0.0
```

## Summary

P5 defines the Artifact Package Model for governed profile-agent and auditor
outputs:

```text
agent writes candidate package
ASO validates form/schema
ASO accepts or rejects
auditor checks meaning after acceptance
ASO builds context pack for next agent
```

The release separates publishable package artifacts from workspace-local
owner-input, runtime, archive, and virtual-environment roots. Source-of-truth
artifact packages use a manifest plus typed markdown, structured JSON, and
evidence files; rendered views are derived outputs rather than authority.

## Release Scope

This release installs the P5 package boundary across documentation, schemas,
fixtures, validators, CLI commands, lifecycle records, and context pack
construction:

- artifact package schema version `1.0.0` and manifest contract;
- raw, candidate, accepted, and rejected artifact storage roots under
  workspace-local runtime state;
- `aso artifact validate`, `accept`, `reject`, and `render` command surfaces;
- strict pre-audit gating on accepted RESULT packages;
- accepted-package based context pack construction;
- lifecycle events and receipts that reference accepted artifact ids before
  audit route readiness;
- regression coverage for malformed result, status, manifest, task, role,
  hash, route, and accepted-package cases;
- Project Factory documentation alignment with P5 package/runtime boundaries.

## Runtime Schema Impact

Runtime Schema remains `3.1.0`. P5 adds artifact package schema metadata and
workspace-local package storage semantics. It does not migrate active
`project-runtime/` state or redefine the P2/P3 runtime sidecar envelope.

## Publication Boundary

No `project-input/`, `project-runtime/`, `project-archive/`, or `.venv/` files
are package publication artifacts. The P5 task package under
`project-input/aso_upgrade_artifact_package_model_p5_v3_7_0/` is local input
material and must be removed only after final audit pass, commit, push, and CI
success according to the P5 cleanup instructions.

## Non-Goals Preserved

This release does not add daemon mode, live dispatch, checkpoint execution,
product-intake automation, product generation, external workers, or secret
collection.
