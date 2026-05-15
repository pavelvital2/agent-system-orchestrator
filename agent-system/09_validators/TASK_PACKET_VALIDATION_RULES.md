# TASK_PACKET_VALIDATION_RULES

## Purpose

This document defines documentation-first validation rules for bounded task
packets.

## Source documents

```text
agent-system/03_templates/TASK_PACKET_TEMPLATE.md
agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
agent-system/04_state/RUNTIME_STATE_SCHEMA.md
```

## Required structure

A task packet is invalid if it omits required sections from the current
`TASK_PACKET_TEMPLATE.md`.

Validators must check the current template rather than freezing a separate
schema here.

## Bounded scope checks

A task packet is invalid when:

- purpose contains multiple unrelated objectives;
- scope in contains hidden follow-up work;
- scope out is missing;
- required docs force an agent to read the whole project;
- acceptance criteria expand beyond scope in;
- expected outputs are not verifiable;
- workflow fields contradict governance.

## ACTIVE_DOC_ROOT checks

For ordinary project work:

- active task packets must be inside `ACTIVE_DOC_ROOT`;
- active project docs must be inside `ACTIVE_DOC_ROOT`;
- `project-archive/` cannot be active source-of-truth;
- deprecated or superseded docs cannot be in `REQUIRED_DOCS`;
- `NEXT_ACTION` cannot dispatch deprecated or superseded task packets.

Universal package upgrade tasks may change `agent-system/` only when a bounded
task packet explicitly authorizes that scope.

## Allowed and forbidden file checks

Every task packet must define bounded file-change authority.

Invalid conditions:

- `ALLOWED_FILE_CHANGES` is missing;
- `ALLOWED_FILE_CHANGES` is effectively unbounded;
- wildcard scope is broader than the task purpose requires;
- `FORBIDDEN_FILE_CHANGES` is missing when protected zones exist;
- allowed and forbidden patterns overlap without explicit clarification;
- protected zones are mutable without role and task authority.

Protected zones include:

```text
agent-system/
project-runtime/
project-input/
project-archive/
```

## Required docs checks

`REQUIRED_DOCS` is invalid when it includes:

- deprecated docs;
- superseded task packets;
- archive-only references for active source-of-truth;
- secrets or credential files;
- unrelated reference documents;
- entire directory trees without bounded need.

## Workflow checks

A task packet is invalid when it allows or requires:

- designer pass directly to developer;
- developer pass directly to tester or technical writer;
- audit bypass after designer or developer work;
- audit fail to normal next task;
- audit fail to Git checkpoint;
- correction without a fresh bounded task where correction is required;
- terminal completion by profile-agent RESULT alone.

## Correction task checks

Correction task packets must include:

```text
CORRECTION_OF
SOURCE_RESULT_REF
ATTEMPT_NO
FAILURE_TYPE
```

Invalid correction packets include:

- missing source result or violation reference when one exists;
- scope broader than the failed surface without designer approval;
- missing mandatory audit path;
- repeated same failure without escalation path.

## Secret-safety checks

A task packet is invalid when it asks an agent to:

- read, print, create, modify, stage, commit, or push secrets;
- include secret values in evidence;
- inspect credential files without an explicit redaction-only protocol;
- use real credentials as acceptance evidence.

Secret-related evidence must be redacted and path/class based.

## Project-agnostic checks

Universal agent-system task packets are invalid if they introduce
project-specific business terms into universal core files.
