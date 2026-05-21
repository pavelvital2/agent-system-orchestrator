# RUNTIME_STATE_P2_CONTRACT

## Purpose

Runtime State P2 defines the package-level JSON-first runtime state boundary
for ASO package version `3.5.0`, governance ruleset version `3.5.0`, and
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

The machine-readable package contract is:

```text
agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json
```

Companion sidecar schemas for newly formalized P2 sidecars are:

```text
agent-system/09_validators/schemas/repository_lock.schema.json
agent-system/09_validators/schemas/checkpoint_state.schema.json
agent-system/09_validators/schemas/schema_manifest.schema.json
```

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

## Allowed Runtime Values

Lifecycle values:

```text
bootstrap
requirements
design
design_audit
implementation
implementation_audit
audit
testing
setup
run
launch
documentation
handover
correction
blocked
finalization
final_acceptance
completed
```

Checkpoint status values:

```text
not_required
not_run
pending
eligible
ineligible
passed
failed
blocked
```

Action status values:

```text
ready
blocked
completed
not_applicable
```

Action type values:

```text
create_agent
route_result
update_state
wait_for_owner
correction
finalize
stop
```

Action semantic values:

```text
normal
wait_for_owner
pause
stop_terminal
completed_state_transition
```

Compatibility status values:

```text
current
compatible_migration_available
compatible_legacy_read_only
unsupported
malformed
```

## Validation Rules

Runtime Schema `3.1.0` validation is dependency-free and uses Python stdlib
JSON parsing plus explicit contract checks. The contract does not require an
external `jsonschema` runtime dependency.

Validators must fail closed for malformed JSON, non-object sidecar roots,
missing required envelope fields, unknown sidecar types, invalid sidecar type
or filename mismatches, invalid timestamps, invalid state revisions, and
mismatched `schema_version` / `runtime_schema_version` for current P2
sidecars.

Cross-sidecar validation must check that `NEXT_ACTION.task_id`,
`CURRENT_GATE.task_id`, `PROJECT_STATE.active_branches[].current_task`, and
`ACCEPTED_ARTIFACTS.artifacts[].source_task` resolve through
`TASK_REGISTRY.tasks[]` unless the value is explicitly `NONE` or equivalent
empty state. When `WORKSPACE_IDENTITY`, `REPOSITORY_LOCK`, and
`PROJECT_STATE` contain comparable repository identity fields, the values must
agree. Checkpoint-capable actions must not be considered ready without
audit-pass evidence.

## Migration Compatibility

Existing `schema_version` `2.0.0` and `3.0.0` sidecars are compatible legacy
inputs for diagnostics and deterministic migration planning only. Their
compatibility status is `compatible_migration_available`.

Legacy sidecars must not be silently treated as current Runtime Schema `3.1.0`
state. A later bounded migration command must add the `runtime_schema_version`
envelope field, set `migration_source_schema`, preserve valid revisions and
content values, and write deterministic JSON. Malformed, ambiguous, or
unsupported source state has compatibility status `malformed` or
`unsupported` and must fail closed.

## Fixture Expectations

Current P2 fixtures must include all required sidecars, use
`schema_version: 3.1.0` and `runtime_schema_version: 3.1.0`, resolve all task
references through `TASK_REGISTRY`, and include a `SCHEMA_MANIFEST` that points
to the packaged contract document.

Legacy Stage 2 fixtures using `schema_version: 2.0.0` remain compatibility
fixtures. They are useful for migration diagnostics, but they are not current
P2 fixtures.

Negative fixtures should cover malformed JSON, missing required envelope
fields, unknown sidecar types, mismatched schema/runtime schema versions,
missing task references, and workspace identity or repository lock mismatches.

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
