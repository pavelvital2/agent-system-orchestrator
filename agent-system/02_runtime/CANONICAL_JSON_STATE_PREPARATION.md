# CANONICAL_JSON_STATE_PREPARATION

## Purpose

This document records the transition from Markdown runtime state to canonical
JSON runtime state and defines the current Runtime Schema `3.1.1` authority.

It is a specification document. It does not add daemon mode, live dispatch,
checkpoint execution, product generation, or profile-agent authority to mutate
runtime state.

Stage 2 adds package-level sidecar schemas and validation rules in:

```text
agent-system/02_runtime/CANONICAL_JSON_STATE.md
agent-system/03_templates/state/*.json
agent-system/09_validators/STATE_SIDECAR_VALIDATION_RULES.md
```

These package files define machine-verifiable sidecar shapes for current
workspace state validation. `project-runtime/state/*.json` files are canonical
for Runtime Schema `3.1.1`; Markdown files are generated compatibility views.

The generated Markdown compatibility views are:

```text
project-runtime/PROJECT_STATE.md
project-runtime/CURRENT_GATE.md
project-runtime/NEXT_ACTION.md
project-runtime/TASK_REGISTRY.md
project-runtime/ACCEPTED_ARTIFACTS.md
project-runtime/ORCHESTRATOR_EVENTS_LOG.md
project-runtime/STATUS_SUMMARY.md
```

The current authority model is:

```text
project-runtime/state/*.json         = canonical machine source of truth
project-runtime/*.md                 = generated, readable compatibility views
```

## Non-goals

This specification does not:

- use an aggregate `project-runtime/state/state.json` as the canonical source;
- require `aso render-runtime` to exist;
- replace Markdown templates or current runtime validators;
- grant profile agents authority to write runtime state;
- introduce checkpoint, dispatch, or state mutation commands.

## Migration phases

### Phase 0: historical Markdown runtime

Markdown runtime files were the operational source of truth before canonical
Runtime Schema sidecars were adopted. JSON Schema sidecars under
`agent-system/09_validators/schemas/` described equivalent object forms for
validation.

Validators may parse Markdown into structured objects for checks. If parser
support is unavailable, existing Markdown validation remains valid.

### Phase 1: normalized read model

`aso lint` and related read-only diagnostics may normalize Markdown runtime
state into an in-memory JSON object.

Requirements:

```text
- no writes to project-runtime/state/;
- no state mutation;
- no generated Markdown replacement;
- no loss of Markdown compatibility.
```

### Phase 2: canonical JSON sidecars

Accepted runtime-state tasks added canonical sidecars:

```text
project-runtime/state/PROJECT_STATE.json
project-runtime/state/TASK_REGISTRY.json
project-runtime/state/NEXT_ACTION.json
project-runtime/state/CURRENT_GATE.json
project-runtime/state/WORKSPACE_IDENTITY.json
project-runtime/state/SCHEMA_MANIFEST.json
```

At this phase, JSON sidecars are canonical. Validators must report drift between
canonical JSON and generated Markdown views instead of treating Markdown as
authoritative.

### Phase 3: governed render transition

Orchestrator-owned transactions update JSON state first, then render Markdown
compatibility views in one bounded operation.

Requirements:

```text
- profile agents still do not mutate runtime state;
- writes are orchestrator-owned only;
- Markdown views preserve all required fields from JSON;
- validators check JSON/Markdown parity before checkpoint eligibility.
```

### Phase 4: canonical JSON runtime

Canonical authority is:

```text
project-runtime/state/*.json = machine source of truth
project-runtime/*.md         = generated/readable views
```

Manual edits to generated Markdown views are not authoritative in this phase.
If Markdown and JSON conflict, validators must treat JSON as authoritative and
report the Markdown drift.

### Phase 5: mutation command layer

Mutation commands must use the same transaction rules as the orchestrator and
must never bypass governed state validation or Markdown rendering.

## Proposed future file contracts

The following files are proposed future runtime files. They are examples of the
target contract, not files that this task creates under `project-runtime/`.

### project-runtime/state/state.json

`state.json` would be a future aggregate JSON object containing a
machine-readable runtime state snapshot. It is not the current Runtime Schema
`3.1.1` source of truth.

Minimum future envelope:

```json
{
  "schema_version": "1.0.0",
  "runtime_schema_version": "2.0.0",
  "state_revision": 1,
  "updated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "updated_by": "orchestrator",
  "source_event_id": "EVT-...",
  "views": {
    "PROJECT_STATE": {},
    "CURRENT_GATE": {},
    "NEXT_ACTION": {},
    "TASK_REGISTRY": {},
    "ACCEPTED_ARTIFACTS": {},
    "STATUS_SUMMARY": {}
  }
}
```

Rules:

```text
- object keys inside each view preserve the current Markdown field names unless a future migration explicitly renames them;
- required fields cannot be inferred from prose, task packets, or previous context;
- missing required fields are validation failures;
- large reports, task packet bodies, and secret values must not be embedded;
- references point to bounded files instead of copying large artifacts.
```

### project-runtime/state/events.jsonl

`events.jsonl` is append-only JSON Lines event history. Each line is one
complete JSON object.

Minimum future event envelope:

```json
{
  "event_id": "EVT-...",
  "event_time": "YYYY-MM-DDTHH:MM:SSZ",
  "event_type": "task_dispatch",
  "actor": "orchestrator",
  "task_id": "TASK_...",
  "gate_id": "GATE_...",
  "action_id": "ACTION_...",
  "status": "recorded",
  "summary": "Short material event summary.",
  "input_refs": [],
  "output_refs": [],
  "state_revision_before": 1,
  "state_revision_after": 2,
  "commit_hash": "NONE",
  "branch": "NONE",
  "push_status": "not_required",
  "failure_reason": "NONE"
}
```

Rules:

```text
- append-only; no in-place edits during normal operation;
- ordered by append sequence, with stable event IDs;
- records material routing, validation, checkpoint, lifecycle, and owner events;
- does not store secret values;
- may reference files that contain larger evidence.
```

### project-runtime/state/schema.json

`schema.json` would be the runtime-local schema used to validate a future
aggregate `state.json` for a workspace.

Rules:

```text
- uses JSON Schema Draft 2020-12;
- records or references the package schema version that produced it;
- composes existing sidecar schemas where practical;
- remains package-derived, not project-authored business documentation;
- cannot weaken mandatory governance fields defined by RUNTIME_STATE_SCHEMA.md.
```

## State render behavior

`aso state render --root .` renders reports from canonical JSON sidecars.

Without `--confirm-write`, `aso state render` is read-only except for explicit
report output to `/tmp`, `project-runtime/reports`, or
`project-runtime/rendered`. With `--confirm-write`, it writes Markdown
compatibility views from canonical `project-runtime/state/*.json` sidecars and
cannot be combined with `--out`.

`aso state render --confirm-write` must:

```text
1. read project-runtime/state/*.json sidecars;
2. validate them against package governance;
3. render generated Markdown compatibility views into project-runtime/*.md files;
4. preserve all required fields from the JSON source;
5. fail instead of inferring missing required values;
6. write generated views atomically;
7. support a check mode that reports drift without writing;
8. avoid appending events for pure render-only operations unless a future task explicitly defines render audit events.
```

Generated Markdown views include a short generated-view notice and identify the
canonical JSON sidecar source.

Render mapping:

```text
views.PROJECT_STATE        -> project-runtime/PROJECT_STATE.md
views.CURRENT_GATE         -> project-runtime/CURRENT_GATE.md
views.NEXT_ACTION          -> project-runtime/NEXT_ACTION.md
views.TASK_REGISTRY        -> project-runtime/TASK_REGISTRY.md
views.ACCEPTED_ARTIFACTS   -> project-runtime/ACCEPTED_ARTIFACTS.md
views.STATUS_SUMMARY       -> project-runtime/STATUS_SUMMARY.md
events.jsonl latest events -> project-runtime/ORCHESTRATOR_EVENTS_LOG.md or generated event summary view
```

## Validator expectations

Current validators remain Markdown-view compatible while treating required
Runtime Schema `3.1.1` JSON sidecars as canonical state.

Validators should apply checks in this order:

```text
1. Markdown parse parity with existing sidecar schemas;
2. generated Markdown parity with canonical JSON sidecars;
3. sidecar schema validity and compatibility with package schema;
4. sidecar/event consistency where event sidecars are present;
5. generated Markdown drift from canonical JSON.
```

For Runtime Schema `3.1.1`, missing required `project-runtime/state/*.json`
sidecars are missing canonical runtime state.
