# STATE_SIDECAR_VALIDATION_RULES

## Purpose

This document defines Stage 2 validation rules for canonical JSON state
sidecars. The rules are documentation-first and do not implement an
`aso state verify` command.

Related runtime semantics are defined in:

```text
agent-system/02_runtime/CANONICAL_JSON_STATE.md
agent-system/02_runtime/CANONICAL_JSON_STATE_PREPARATION.md
agent-system/02_runtime/RUNTIME_FILE_TAXONOMY.md
agent-system/02_runtime/ACTION_STATE_SEMANTICS.md
agent-system/02_runtime/STATE_TRANSITION_RULES.md
```

## Sidecars in scope

Stage 2 sidecar validation covers these optional workspace files:

```text
project-runtime/state/PROJECT_STATE.json
project-runtime/state/CURRENT_GATE.json
project-runtime/state/NEXT_ACTION.json
project-runtime/state/TASK_REGISTRY.json
project-runtime/state/ACCEPTED_ARTIFACTS.json
project-runtime/state/WORKSPACE_IDENTITY.json
```

The package templates for those files are:

```text
agent-system/03_templates/state/project_state.schema.json
agent-system/03_templates/state/current_gate.schema.json
agent-system/03_templates/state/next_action.schema.json
agent-system/03_templates/state/task_registry.schema.json
agent-system/03_templates/state/accepted_artifacts.schema.json
agent-system/03_templates/state/workspace_identity.schema.json
```

## Hard-fail rules

A validator must fail a sidecar workspace when any rule below is violated:

```text
SIDECAR_JSON_PARSE_ERROR
  A sidecar file is not valid JSON.

SIDECAR_TOP_LEVEL_NOT_OBJECT
  The parsed sidecar root is not a JSON object.

SIDECAR_SCHEMA_VERSION_MISSING_OR_INVALID
  schema_version is missing or is not the stable value required by the package
  template.

SIDECAR_TYPE_MISMATCH
  sidecar_type is missing, unknown, or does not match the sidecar file.

SIDECAR_MARKDOWN_SOURCE_MISMATCH
  markdown_source is missing or does not point to the expected Markdown
  compatibility file.

SIDECAR_REQUIRED_FIELD_MISSING
  Any required envelope or content field from the package template is missing.

SIDECAR_REQUIRED_FIELD_EMPTY
  A required string field is empty unless the package template explicitly
  allows an empty string.

SIDECAR_TYPE_INVALID
  A field has a JSON type that does not match the package template.

SIDECAR_UNKNOWN_GOVERNED_FIELD
  A sidecar contains unknown top-level fields or unknown governed content
  fields where the template sets additionalProperties to false.

SIDECAR_STATE_REVISION_INVALID
  state_revision is not a positive integer.

SIDECAR_TIMESTAMP_INVALID
  updated_at or another governed timestamp is not an RFC 3339 UTC timestamp
  when a timestamp is required.

SIDECAR_MARKDOWN_COMPATIBILITY_VIEW_MISSING
  A workspace sidecar is present but the matching Markdown runtime view is
  missing during the Stage 2 Markdown-compatible migration window.

SIDECAR_MARKDOWN_DRIFT
  A governed value in a valid sidecar conflicts with the matching governed
  value parsed from the Markdown compatibility view.

SIDECAR_SECRET_OR_CREDENTIAL_VALUE
  A sidecar embeds a secret, credential, token, private key, or unapproved
  remote credential value.

SIDECAR_FORBIDDEN_PAYLOAD_EMBEDDED
  A sidecar embeds large reports, task packet bodies, audit bodies, owner input
  payloads, or runtime logs instead of bounded references.

SIDECAR_TRANSITION_SEMANTICS_INVALID
  The combined sidecar tuple violates STATE_TRANSITION_RULES.md or
  ACTION_STATE_SEMANTICS.md.

SIDECAR_WORKSPACE_IDENTITY_INVALID
  workspace identity or repository lock fields conflict across PROJECT_STATE,
  CURRENT_GATE, NEXT_ACTION, and WORKSPACE_IDENTITY.

SIDECAR_CHECKPOINT_POLICY_INVALID
  checkpoint fields imply commit, push, or post-audit checkpoint eligibility
  before the required audit, workspace identity, and repository lock checks
  pass.
```

## Warning rules

A validator should warn, but not fail, for these Stage 2 migration conditions:

```text
SIDECAR_MISSING_MARKDOWN_FALLBACK_USED
  A sidecar is absent and the validator falls back to the Markdown runtime file.

SIDECAR_OPTIONAL_FIELD_MISSING
  A future-compatible optional field is absent.

SIDECAR_MARKDOWN_EXTRA_UNSTRUCTURED_TEXT
  The Markdown compatibility view contains extra prose that cannot be mapped to
  a governed sidecar field but does not conflict with governed values.

SIDECAR_STATE_REVISION_GAP
  state_revision values are valid but contain unexplained jumps.

SIDECAR_UPDATED_BY_NON_ORCHESTRATOR
  updated_by is not orchestrator in a fixture or future test workspace where
  non-orchestrator authorship is explicitly allowed for test data.

SIDECAR_LEGACY_RUNTIME_LAYOUT
  The workspace uses a legacy runtime layout that remains compatible under
  RUNTIME_FILE_TAXONOMY.md.
```

## Validation order

Validators should apply checks in this order:

```text
1. Locate optional sidecars and Markdown compatibility views.
2. Parse JSON sidecars with the Python standard library json parser or an
   equivalent dependency-free parser.
3. Validate each sidecar against its package template.
4. Parse Markdown governed fields when a compatibility view exists.
5. Compare JSON and Markdown governed fields for parity.
6. Validate the combined runtime tuple against action, transition, identity,
   and checkpoint semantics.
7. Report hard failures before warnings.
```

## Non-authority

These validation rules do not authorize writes to `project-runtime/`, do not
stage files, do not commit, do not push, and do not change ASO command
behavior. They define expected behavior for a later validator implementation.
