# CANONICAL_JSON_STATE

## Purpose

This document defines the Runtime State P2 canonical JSON state sidecar model.

Runtime State P2 adds the package-level JSON-first runtime state contract for
runtime schema `3.1.0`. It does not activate daemon, proposal/apply, live
dispatch, or checkpoint-executor commands, does not create active
`project-runtime/` files in the package repository, and does not give profile
agents authority to write runtime state.

## Runtime State P2 authority model

`project-runtime/state/*.json` sidecars are the canonical
machine-verifiable representation of Runtime Schema `3.2.0` runtime state.
Markdown runtime files remain supported as generated compatibility and
human-readable render views.

For Runtime Schema `3.2.0`:

```text
1. If a valid JSON sidecar and its Markdown view both exist, validators should
   use the JSON sidecar as the structured input and verify parity with the
   Markdown view for governed fields.
2. If a required JSON sidecar is missing, current Runtime Schema `3.2.0`
   validation must report the missing canonical state instead of treating the
   Markdown view as authoritative.
3. If JSON and Markdown conflict on governed fields, validators must fail
   instead of silently choosing one source.
4. A JSON sidecar cannot authorize a runtime mutation, checkpoint, commit,
   push, dispatch, or lifecycle transition by itself.
5. Profile agents must not write active `project-runtime/` state unless a
   separate bounded task explicitly grants that runtime ownership.
```

Older sidecars are compatibility inputs only. Validators must not silently
treat older `2.0.0` or `3.0.0` sidecars as current P2 state.

## Sidecar locations

The package schemas live under:

```text
agent-system/03_templates/state/
```

The expected P2 workspace paths are:

```text
project-runtime/state/PROJECT_STATE.json
project-runtime/state/CURRENT_GATE.json
project-runtime/state/NEXT_ACTION.json
project-runtime/state/TASK_REGISTRY.json
project-runtime/state/ACCEPTED_ARTIFACTS.json
project-runtime/state/WORKSPACE_IDENTITY.json
project-runtime/state/REPOSITORY_LOCK.json
project-runtime/state/CHECKPOINT_STATE.json
project-runtime/state/SCHEMA_MANIFEST.json
```

The matching Markdown compatibility views are:

```text
project-runtime/PROJECT_STATE.md
project-runtime/CURRENT_GATE.md
project-runtime/NEXT_ACTION.md
project-runtime/TASK_REGISTRY.md
project-runtime/ACCEPTED_ARTIFACTS.md
project-runtime/WORKSPACE_IDENTITY.md
project-runtime/REPOSITORY_LOCK.md
project-runtime/CHECKPOINT_STATE.md
project-runtime/SCHEMA_MANIFEST.md
```

Required minimum P2 sidecars are defined in
`RUNTIME_STATE_P2_CONTRACT.md`. Optional sidecars may be absent before the
matching governance stage, but validators must report readiness or migration
status instead of inferring missing state.
When present, every canonical sidecar receives a generated Markdown
compatibility view; the JSON sidecar remains authoritative.

## Common sidecar envelope

Each sidecar is one JSON object with a stable envelope:

```json
{
  "schema_version": "3.1.0",
  "sidecar_type": "PROJECT_STATE",
  "runtime_schema_version": "3.1.0",
  "markdown_source": "project-runtime/PROJECT_STATE.md",
  "state_revision": 1,
  "updated_at": "2026-01-01T00:00:00Z",
  "updated_by": "orchestrator",
  "content": {}
}
```

Envelope rules:

```text
- schema_version is required and must be `3.1.0` for current P2 sidecars.
- runtime_schema_version is required and must be `3.1.0` for current P2 sidecars.
- sidecar_type must match the sidecar file and Markdown source.
- markdown_source must point to the compatible Markdown runtime view.
- state_revision is a positive integer that increases when governed content changes.
- updated_at is an RFC 3339 UTC timestamp. Runtime commands write current UTC
  timestamps by default; fixed deterministic timestamps are only for explicit
  test or fixture modes.
- updated_by records the actor that produced the sidecar.
- content contains the state-specific object defined by the package template.
- large reports, task packet bodies, audit bodies, and secret values must not be embedded.
- references must be bounded workspace or package-relative paths, not copied payloads.
```

## Sidecar content contracts

### PROJECT_STATE

`PROJECT_STATE` records the project-level runtime tuple needed before dispatch
and checkpoint decisions.

Required governed fields include:

```text
project_slug
workspace_type
current_phase
project_status
active_doc_root
package_version
governance_ruleset_version
runtime_schema_version
workspace_identity_ref
repository_lock_ref
expected_git_remote
actual_git_remote
expected_branch
actual_branch
push_allowed
identity_validation_status
identity_validation_error
repository_lock_status
checkpoint_eligibility
checkpoint_blocked_by
active_blockers
active_branches
```

### CURRENT_GATE

`CURRENT_GATE` records the active gate and its dispatch/checkpoint blockers.

Required governed fields include:

```text
gate_id
gate_type
status
owner_role
task_id
task_packet
action_semantic
workspace_identity_status
repository_lock_status
checkpoint_eligibility
checkpoint_blocked_by
evidence_refs
```

### NEXT_ACTION

`NEXT_ACTION.json` is a rendered compatibility/cache view of the next routing
action. Dispatch and checkpoint decisions must derive the expected action from
the canonical inputs: `TASK_REGISTRY`, lifecycle events in
`project-runtime/agents/instances.jsonl`, artifact receipts and accepted
artifact records, audit results, `CURRENT_GATE`, correction records, and
`ORCHESTRATOR_RUNTIME_CONTRACT.json`.

`state verify --strict` must compare the stored `NEXT_ACTION.json` cache with
the derived action and fail on mismatch. `state render --confirm-write` may
refresh a structurally valid stale `NEXT_ACTION.json` cache before rendering
Markdown compatibility views.

Required governed fields include:

```text
action_id
action_type
target_role
task_id
task_packet
dependency_status
action_semantic
workspace_identity_required
repository_lock_required
checkpoint_policy
requester_return_context
blocked_by
summary
```

### TASK_REGISTRY

`TASK_REGISTRY` records task lifecycle metadata used for routing, audit, and
checkpoint eligibility.

Required governed fields include:

```text
registry_revision
tasks
```

Each task entry must identify the task, task packet, role, status, audit
requirements, checkpoint requirements, requester return metadata, blockers,
worker result references, and audit references.

Task entries may also carry correction-resolution metadata:

```text
correction_of
resolved_by
superseded_by
effective_audit_ref
raw_status
resolution_status
effective_status
```

`raw_status` preserves the historical task state. `effective_status` is the
computed state used by checkpoint and terminal eligibility. Failed, blocked, or
audit-pending raw states stop blocking only when a valid resolution record or
passing audit receipt explicitly resolves the failed audit reference.

### ACCEPTED_ARTIFACTS

`ACCEPTED_ARTIFACTS` records bounded accepted output references, not artifact
bodies.

Required governed fields include:

```text
artifacts
```

Each artifact entry must identify the artifact, path, producing task, accepted
result reference, audit reference, status, commit hash, and notes.

### WORKSPACE_IDENTITY

`WORKSPACE_IDENTITY` records the validated workspace and repository identity
needed before dispatch and checkpoint decisions.

Required governed fields include:

```text
workspace_id
project_slug
workspace_type
expected_git_remote
actual_git_remote
expected_branch
actual_branch
identity_validation_status
repository_lock_status
push_allowed
validated_at
validation_errors
```

## Migration compatibility

Runtime Schema `3.2.0` validators should prefer JSON sidecars for structured
checks and treat missing required sidecars as missing canonical runtime state.
Historical workspaces without sidecars require governed migration or
compatibility handling before current strict validation can pass.

Sidecar adoption is not permission to delete Markdown views. Markdown remains
the readable compatibility surface generated from canonical JSON state.
