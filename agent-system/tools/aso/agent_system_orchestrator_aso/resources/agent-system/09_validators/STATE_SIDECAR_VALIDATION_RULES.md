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

Runtime State P2 adds a JSON-first Runtime Schema `3.1.0` contract at:

```text
agent-system/09_validators/schemas/runtime_state_3_1_0.contract.json
```

That contract defines the current envelope, required and optional sidecars,
allowed lifecycle/checkpoint/action/compatibility statuses, migration
compatibility rules, and fixture expectations. It is validated through Python
stdlib data checks and does not add an external `jsonschema` runtime
dependency.

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

Runtime Schema `3.1.0` additionally formalizes these package schema files:

```text
agent-system/09_validators/schemas/repository_lock.schema.json
agent-system/09_validators/schemas/checkpoint_state.schema.json
agent-system/09_validators/schemas/schema_manifest.schema.json
```

Required current P2 sidecars are:

```text
PROJECT_STATE
TASK_REGISTRY
NEXT_ACTION
CURRENT_GATE
WORKSPACE_IDENTITY
SCHEMA_MANIFEST
```

Optional current P2 sidecars are:

```text
REPOSITORY_LOCK
ACCEPTED_ARTIFACTS
CHECKPOINT_STATE
```

## Authoritative Stage 2 sidecar contract

Stage 2 sidecars use one canonical JSON shape: an envelope object with
governed lower-case fields under `content`.

```text
{
  "schema_version": "<stable package schema version>",
  "sidecar_type": "<PROJECT_STATE | CURRENT_GATE | NEXT_ACTION | TASK_REGISTRY | ACCEPTED_ARTIFACTS | WORKSPACE_IDENTITY>",
  "markdown_source": "<matching project-runtime/*.md path>",
  "state_revision": <positive integer>,
  "updated_at": "<RFC 3339 UTC timestamp>",
  "updated_by": "orchestrator",
  "content": {
    "<lower_case_field_name>": "<governed value>"
  }
}
```

The Markdown runtime templates remain the authoritative human-readable
compatibility view. They use uppercase fields so operators can review and
compare runtime state consistently. JSON sidecars do not replace that view in
Stage 2; they mirror it through the envelope and lower-case `content` model.

The JSON schemas used for sidecar validation must describe this same envelope
and lower-case `content` model. A direct JSON object that contains uppercase
Markdown fields at the sidecar root is not valid Stage 2 sidecar shape.

Field-name mapping is deterministic:

```text
PROJECT_STATE.CURRENT_PHASE -> PROJECT_STATE.content.current_phase
PROJECT_STATE.PUSH_ALLOWED -> PROJECT_STATE.content.push_allowed
CURRENT_GATE.STATUS -> CURRENT_GATE.content.status
CURRENT_GATE.CHECKPOINT_ELIGIBILITY -> CURRENT_GATE.content.checkpoint_eligibility
NEXT_ACTION.ACTION_TYPE -> NEXT_ACTION.content.action_type
NEXT_ACTION.TARGET_ROLE -> NEXT_ACTION.content.target_role
NEXT_ACTION.WORKSPACE_IDENTITY_REQUIRED -> NEXT_ACTION.content.workspace_identity_required
NEXT_ACTION.CHECKPOINT_POLICY -> NEXT_ACTION.content.checkpoint_policy
TASK_REGISTRY.STATUS -> TASK_REGISTRY.content.status
ACCEPTED_ARTIFACTS.STATUS -> ACCEPTED_ARTIFACTS.content.status
```

For all governed fields, strip the Markdown file prefix, convert the uppercase
field name to lower snake case, and place the value under `content`. List or
record sections use lower-case content names and must retain the canonical
values documented by the matching runtime template and
`agent-system/04_state/RUNTIME_STATE_SCHEMA.md`.

Boolean mapping is also deterministic:

```text
Markdown yes -> JSON true
Markdown no -> JSON false
Markdown true -> JSON true
Markdown false -> JSON false
```

If a Markdown compatibility field is governed as `yes | no` or `true | false`,
the sidecar content field must be a JSON boolean. Validators must not accept
string spellings of those booleans as governed JSON values.

Canonical enum sets for the governed sidecars are defined by the runtime
templates and `agent-system/04_state/RUNTIME_STATE_SCHEMA.md`:

```text
PROJECT_STATE: PROJECT_STATE_TEMPLATE.md and RUNTIME_STATE_SCHEMA.md PROJECT_STATE.md schema.
CURRENT_GATE: CURRENT_GATE_TEMPLATE.md and RUNTIME_STATE_SCHEMA.md CURRENT_GATE.md schema.
NEXT_ACTION: NEXT_ACTION_TEMPLATE.md and RUNTIME_STATE_SCHEMA.md NEXT_ACTION.md schema.
TASK_REGISTRY: TASK_REGISTRY_TEMPLATE.md and RUNTIME_STATE_SCHEMA.md TASK_REGISTRY.md schema.
ACCEPTED_ARTIFACTS: ACCEPTED_ARTIFACTS_TEMPLATE.md and RUNTIME_STATE_SCHEMA.md ACCEPTED_ARTIFACTS.md schema.
```

Schemas, fixtures, and validators must not permit enum values outside those
runtime templates and schema sections. In particular, these Stage 2 values are
invalid and must hard-fail if present:

```text
NEXT_ACTION.content.target_role: runtime_architect
NEXT_ACTION.content.action_semantic: dispatch
NEXT_ACTION.content.checkpoint_policy: not_required
CURRENT_GATE.content.status: active
CURRENT_GATE.content.checkpoint_eligibility: not_required
```

These exclusions do not create new valid alternatives. `runtime_architect` is
not a profile execution role or routing pseudo-role; `dispatch` is not a valid
action semantic; `not_required` is not a valid `CHECKPOINT_POLICY`; and
`active` is not a valid `CURRENT_GATE.status`.

## Hard-fail rules

A validator must fail a sidecar workspace when any rule below is violated:

```text
SIDECAR_JSON_PARSE_ERROR
  A sidecar file is not valid JSON.

SIDECAR_TOP_LEVEL_NOT_OBJECT
  The parsed sidecar root is not a JSON object.

SIDECAR_ENVELOPE_INVALID
  A sidecar does not use the required Stage 2 envelope with governed values
  under a lower-case content object, or it presents Markdown uppercase fields
  as the direct sidecar object.

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

SIDECAR_ENUM_VALUE_INVALID
  A governed content value is outside the canonical enum set documented by the
  matching runtime template and RUNTIME_STATE_SCHEMA.md.

SIDECAR_BOOLEAN_VALUE_INVALID
  A governed JSON boolean field is encoded as a string or otherwise fails the
  Markdown yes/no or true/false to JSON true/false mapping.

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

Runtime Schema `3.1.0` keeps that boundary. Legacy `2.0.0` and `3.0.0`
sidecars are compatibility inputs for diagnostics and migration planning, not
current P2 state. Validators must report `compatible_migration_available`,
`unsupported`, or `malformed` rather than silently upgrading or rewriting
workspace state.
