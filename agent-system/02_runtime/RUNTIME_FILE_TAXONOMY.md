# RUNTIME_FILE_TAXONOMY

## Purpose

This document defines the stable taxonomy for project input, stable project
documentation, and runtime execution artifacts.

The goal is to prevent runtime files from looking like duplicate project
documentation and to keep future migration work non-destructive.

## Top-level roots

The project filesystem uses these roots:

```text
project-docs     = stable documentation
project-runtime  = execution state/artifacts
project-input    = owner input/TZ/upgrade packages
project-archive  = superseded/deprecated workspace artifacts
```

These root-level directories are target-workspace roots, not active package
repository state. Root-level `project-runtime/`, `project-input/`, and
`project-archive/` are generated workspace artifacts. They are expected in
target workspaces or local orchestration sessions. They are not shipped as
active state in the package repository.

Package repository content uses package directories under `agent-system/`.
In particular:

```text
agent-system/04_state/       = package state templates
project-runtime/             = generated runtime state
agent-system/03_templates/   = package task/result templates
project-input/               = local owner input
```

The package templates define reusable shapes. The root-level workspace
directories contain local, generated, or owner-provided instance data for a
specific orchestration session.

### project-docs

`project-docs/` contains durable project documentation that remains useful
after a task attempt finishes.

Allowed content includes:

```text
- architecture documents
- accepted design documents
- stage plans
- user-facing documentation
- stable project reference material
```

`project-docs/` must not become a dump for every task packet, worker result,
audit result, checkpoint receipt, or stale runtime state record.

### project-runtime

`project-runtime/` contains execution state and operational evidence used by
the orchestrator, auditors, validators, and checkpoint flow.

Runtime artifacts include:

```text
- active runtime state
- task queues and task lifecycle records
- worker results
- audit results
- agent lifecycle events
- checkpoint receipts
- generated status, lint, archive, and smoke reports
```

Profile agents do not own `project-runtime/` writes unless a bounded task
explicitly grants a narrow universal-governance correction scope. Normal
runtime state updates remain orchestrator-owned.

### project-input

`project-input/` contains owner-supplied input and package material.

Allowed content includes:

```text
- original TZ and owner instructions
- upgrade packages
- package task packets supplied by the owner
- owner-provided source material for downstream project work
```

Agents may read `project-input/` only when the task packet or runtime handoff
explicitly lists the relevant files. Agents must not rewrite owner input unless
a separate bounded normalization or package-correction task grants that scope.

### project-archive

`project-archive/` contains superseded, deprecated, or historical workspace
artifacts that are no longer active source-of-truth for dispatch.

It is a generated target-workspace archive root. It is not package repository
active state, and package repository archival policy must be represented in
package governance files rather than by shipping active root-level archive
contents.

## Recommended project-runtime structure

New runtime-producing work should prefer this structure:

```text
project-runtime/
  tasks/
    pending/
    active/
    completed/
    superseded/

  results/
    worker/
    audit/

  agents/
    instances.jsonl

  checkpoints/

  reports/
```

Recommended meanings:

```text
project-runtime/tasks/pending     = prepared but not currently dispatched
project-runtime/tasks/active      = selected or dispatchable active task packets
project-runtime/tasks/completed   = completed task packets retained for traceability
project-runtime/tasks/superseded  = replaced task packets with supersession metadata
project-runtime/results/worker    = profile-agent RESULT records
project-runtime/results/audit     = auditor AUDIT_RESULT records
project-runtime/agents/instances.jsonl = one-task profile-agent lifecycle events
project-runtime/checkpoints       = checkpoint eligibility and checkpoint receipts
project-runtime/reports           = generated status, lint, archive, and smoke reports
```

## Naming conventions

Task packets:

```text
TASK_<ROLE>_<AREA>_<ACTION>_<NNN>.md
```

Worker results:

```text
project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_<N>.md
```

Audit results:

```text
project-runtime/results/audit/AUDIT_RESULT_<TASK_ID>_ATTEMPT_<N>.md
```

Checkpoint receipts:

```text
CHECKPOINT_<TASK_ID>.json
CHECKPOINT_<TASK_ID>.md
```

Task, result, and audit records should not share an untyped basename. Use the
`TASK_`, `RESULT_`, and `AUDIT_RESULT_` prefixes so humans and validators can
distinguish packet, worker evidence, and audit evidence at a glance.

Worker RESULT records must reference the task they executed with `TASK_ID`.
Audit RESULT records must reference the audited task with `TASK_ID` and the
audited worker result with a bounded result reference such as
`SOURCE_RESULT_REF`, `AUDITED_RESULT_REF`, `RESULT_REF`, or
`ACCEPTED_RESULT_REF`.

## Compatibility policy

Existing runtime layouts remain compatible.

The following existing paths are still valid for compatibility unless a future
bounded migration task supersedes them:

```text
project-runtime/audits/
project-runtime/bootstrap/
project-runtime/archive/
project-runtime/state/
project-runtime/PROJECT_STATE.md
project-runtime/CURRENT_GATE.md
project-runtime/NEXT_ACTION.md
project-runtime/GAP_REGISTER.md
project-runtime/TASK_REGISTRY.md
project-runtime/ACCEPTED_ARTIFACTS.md
project-runtime/AGENT_RESULTS_LOG.md
project-runtime/ORCHESTRATOR_EVENTS_LOG.md
project-runtime/STATUS_SUMMARY.md
project-runtime/WORKSPACE_IDENTITY.md
project-runtime/REPOSITORY_LOCK.md
```

`project-runtime/agent-results/` is retained only as compatibility/read-only
legacy storage for historical worker RESULT evidence. New worker RESULT files
must use `project-runtime/results/worker/RESULT_<TASK_ID>_ATTEMPT_<N>.md`.

`project-runtime/audits/` is retained only as compatibility/read-only legacy
storage for historical audit evidence. New audit RESULT files must use
`project-runtime/results/audit/AUDIT_RESULT_<TASK_ID>_ATTEMPT_<N>.md`.

`project-runtime/state/` is reserved for the future canonical JSON runtime
model documented in
`agent-system/02_runtime/CANONICAL_JSON_STATE_PREPARATION.md`.
The proposed future files are:

```text
project-runtime/state/state.json
project-runtime/state/events.jsonl
project-runtime/state/schema.json
```

They are not required by the current Markdown-compatible v0 runtime. A missing
`project-runtime/state/` directory is not a validation error until a separate
accepted migration activates canonical JSON state for the workspace.

This taxonomy is a preferred layout for new runtime artifacts, not permission
to delete, rewrite, or relocate historical execution evidence.

Validators and archive tools may read both old and canonical locations during
the migration window. They must not require historical evidence to be moved, but
they must classify new RESULT artifacts outside the canonical worker or audit
paths as non-canonical unless a bounded compatibility exception explicitly
applies.

## Future migration path

Migration to the recommended structure must be separate, audited, and
non-destructive.

A future migration task should:

```text
1. inventory existing runtime artifacts and accepted references;
2. define an explicit mapping from old paths to recommended paths;
3. update registries and accepted artifact references in one bounded change;
4. preserve historical files or add archive/supersession records before any move;
5. update validators to read both old and new paths until all references migrate;
6. record migration evidence under project-runtime/reports/ or checkpoints/;
7. run lint, archive verification, and governance smoke checks where applicable.
```

No destructive cleanup is authorized by this taxonomy task. Deletion of
historical runtime artifacts requires a dedicated archive or supersede workflow
with owner-visible evidence.

## Lint expectations

Runtime lint should detect or queue checks for:

```text
- task packet/result/audit result with the same basename and no type prefix;
- result without a referenced task;
- audit result without a referenced worker result;
- completed task still in an active folder;
- superseded task without superseded_by metadata;
- accepted artifact path missing;
- stale checkpoint_pending or audit_pending statuses after aggregate checkpoint.
```

These checks may be implemented incrementally, but their target behavior is
part of the taxonomy policy.
