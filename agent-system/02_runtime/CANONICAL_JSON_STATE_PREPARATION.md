# CANONICAL_JSON_STATE_PREPARATION

## Purpose

This document prepares a future migration from Markdown runtime state to a
canonical JSON runtime state.

It is a preparation and specification document only. It does not authorize
creation of active `project-runtime/state/*` files, does not migrate current
runtime state, and does not add runtime mutation commands.

In v0, the existing Markdown runtime files remain compatible and authoritative:

```text
project-runtime/PROJECT_STATE.md
project-runtime/CURRENT_GATE.md
project-runtime/NEXT_ACTION.md
project-runtime/TASK_REGISTRY.md
project-runtime/ACCEPTED_ARTIFACTS.md
project-runtime/ORCHESTRATOR_EVENTS_LOG.md
project-runtime/STATUS_SUMMARY.md
```

The future target model is:

```text
project-runtime/state/state.json     = machine source of truth
project-runtime/state/events.jsonl   = append-only event history
project-runtime/state/schema.json    = runtime-local JSON Schema used for state validation
*.md                                 = generated, readable views
```

## Non-goals for v0

This preparation does not:

- force a workspace to create `project-runtime/state/state.json`;
- treat `project-runtime/state/state.json` as current source of truth;
- require `aso render-runtime` to exist or mutate files;
- replace Markdown templates or current runtime validators;
- grant profile agents authority to write runtime state;
- introduce checkpoint, dispatch, or state mutation commands.

## Migration phases

### Phase 0: current Markdown runtime

Markdown runtime files are the operational source of truth. JSON Schema
sidecars under `agent-system/09_validators/schemas/` describe equivalent object
forms for validation, but they do not require JSON runtime files.

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

### Phase 2: generated experimental JSON snapshot

A future accepted task may add generated experimental files:

```text
project-runtime/state/state.json
project-runtime/state/schema.json
```

At this phase, Markdown remains authoritative. `state.json` is a generated
snapshot only, and validators must report drift between Markdown and generated
JSON instead of silently choosing one.

`events.jsonl` may be introduced as a generated mirror of material
`ORCHESTRATOR_EVENTS_LOG.md` entries, but it is not authoritative until a later
canonical phase.

### Phase 3: governed dual-write transition

After read-only diagnostics and parity checks are stable, a future accepted
task may define orchestrator-owned transactions that update JSON state, append
events, and render Markdown views in one bounded operation.

Requirements:

```text
- profile agents still do not mutate runtime state;
- writes are orchestrator-owned only;
- every mutation appends exactly one material event or an explicitly linked event batch;
- Markdown views preserve all required fields from JSON;
- validators check JSON/Markdown parity before checkpoint eligibility.
```

### Phase 4: canonical JSON runtime

Only after a separate migration task is accepted may canonical authority switch:

```text
state.json     = machine source of truth
events.jsonl   = event history
*.md           = generated/readable views
```

Manual edits to generated Markdown views are not authoritative in this phase.
If Markdown and JSON conflict, validators must treat JSON as authoritative and
report the Markdown drift.

### Phase 5: mutation command layer

Future mutation commands may be added only after the canonical transition is
accepted. Mutation commands must use the same transaction rules as the
orchestrator and must never bypass event append or Markdown rendering.

## Proposed future file contracts

The following files are proposed future runtime files. They are examples of the
target contract, not files that this task creates under `project-runtime/`.

### project-runtime/state/state.json

`state.json` is a single JSON object containing the current machine-readable
runtime state.

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

`schema.json` is the runtime-local schema used to validate `state.json` for the
current workspace.

Rules:

```text
- uses JSON Schema Draft 2020-12;
- records or references the package schema version that produced it;
- composes existing sidecar schemas where practical;
- remains package-derived, not project-authored business documentation;
- cannot weaken mandatory governance fields defined by RUNTIME_STATE_SCHEMA.md.
```

## Future render-runtime behavior

`aso render-runtime --root .` is a future command. In v0 it must remain
non-required and must not be assumed by dispatch, lint, or checkpoint flow.

When implemented after canonical JSON state is accepted, `render-runtime` must:

```text
1. read project-runtime/state/state.json;
2. validate it against project-runtime/state/schema.json and package governance;
3. render generated Markdown views into the existing project-runtime/*.md files;
4. preserve all required fields from the JSON source;
5. fail instead of inferring missing required values;
6. write generated views atomically;
7. support a check mode that reports drift without writing;
8. avoid appending events for pure render-only operations unless a future task explicitly defines render audit events.
```

Generated Markdown views should include a short generated-view notice after the
canonical transition is active. Before that transition, Markdown files must not
be marked generated because they remain authoritative.

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

Current validators remain Markdown-compatible.

Future validators should add checks in this order:

```text
1. Markdown parse parity with existing sidecar schemas;
2. generated state.json parity with Markdown while Markdown is authoritative;
3. schema.json validity and compatibility with package schema;
4. state.json/event append consistency;
5. generated Markdown drift from canonical JSON after authority switches.
```

Until a future accepted task activates canonical JSON state, missing
`project-runtime/state/state.json`, `events.jsonl`, or `schema.json` must not be
treated as a runtime error.
