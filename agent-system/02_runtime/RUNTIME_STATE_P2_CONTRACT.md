# RUNTIME_STATE_P2_CONTRACT

## Purpose

Runtime State P2 defines the package-level JSON-first runtime state boundary
for ASO package version `3.4.0`, governance ruleset version `3.4.0`, and
runtime schema version `3.1.0`.

The filesystem remains the governed boundary. The canonical P2 runtime state
root for a target workspace is:

```text
project-runtime/state/
```

The package repository must not publish active owner runtime files from
`project-runtime/`.

## Canonical P2 Sidecars

The P2 contract recognizes these sidecars:

```text
PROJECT_STATE.json
TASK_REGISTRY.json
NEXT_ACTION.json
CURRENT_GATE.json
WORKSPACE_IDENTITY.json
REPOSITORY_LOCK.json
ACCEPTED_ARTIFACTS.json
CHECKPOINT_STATE.json
SCHEMA_MANIFEST.json
```

Required minimum sidecars for a current P2 workspace are:

```text
PROJECT_STATE.json
TASK_REGISTRY.json
NEXT_ACTION.json
CURRENT_GATE.json
WORKSPACE_IDENTITY.json
SCHEMA_MANIFEST.json
```

`REPOSITORY_LOCK.json`, `ACCEPTED_ARTIFACTS.json`, and
`CHECKPOINT_STATE.json` may be absent when the workspace has not reached the
matching governance stage, but validators must report their compatibility or
readiness status instead of inferring missing state.

## Sidecar Envelope

Every current P2 sidecar uses runtime schema `3.1.0` and must include:

```text
schema_version
sidecar_type
runtime_schema_version
state_revision
updated_at
updated_by
content
```

Recommended optional envelope fields are:

```text
markdown_source
source_hash
previous_revision_hash
migration_source_schema
```

For current P2 sidecars, `schema_version` and `runtime_schema_version` both
record `3.1.0`. Validators must not silently treat older `2.0.0` or `3.0.0`
sidecars as current P2 state. Compatible older state may receive migration or
compatibility diagnostics until a later bounded migration task converts it.

## JSON And Markdown Authority

For P2 and later, JSON sidecars are the canonical machine-readable runtime
state. Markdown files remain compatibility and human-readable render views.
Generated Markdown views must be verifiable from JSON and must not override
canonical JSON state.

## Explicit Non-Goals

Runtime State P2 does not implement:

```text
runtime daemon
live agent dispatch
proposal/apply mutation layer
checkpoint executor
distributed workers
external queue or database infrastructure
web control panel
```

P2 also does not weaken publication-boundary, audit, checkpoint, or
Project Factory P1 safety rules. Any later daemon, proposal/apply, dispatch,
or checkpoint executor work requires a separate bounded package task and audit.
