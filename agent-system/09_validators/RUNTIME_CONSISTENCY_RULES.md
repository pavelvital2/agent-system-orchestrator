# RUNTIME_CONSISTENCY_RULES

## Purpose

This document defines documentation-first checks for validating runtime state
consistency across runtime files.

Runtime files can be individually well-formed and still globally invalid.
The orchestrator must validate the combined state tuple before dispatch and
after any state update.

## Source documents

```text
agent-system/04_state/RUNTIME_STATE_SCHEMA.md
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/ACTION_STATE_SEMANTICS.md
agent-system/02_runtime/VIOLATION_RECOVERY.md
```

## Required runtime files

The runtime state is invalid if any required runtime file is missing:

```text
project-runtime/PROJECT_STATE.md
project-runtime/CURRENT_GATE.md
project-runtime/NEXT_ACTION.md
project-runtime/GAP_REGISTER.md
project-runtime/AGENT_RESULTS_LOG.md
```

If a required file is missing, the orchestrator must create it from the
matching template when governance allows it, or enter correction/wait routing.

## Tuple consistency checks

Validate the combined tuple defined in `RUNTIME_STATE_SCHEMA.md` and
`STATE_TRANSITION_RULES.md`.

The tuple is invalid when:

- a mandatory field is missing;
- a field uses a value outside the allowed set;
- `CURRENT_PHASE`, `PROJECT_STATUS`, `CURRENT_GATE`, and `NEXT_ACTION` are
  semantically incompatible;
- `NEXT_ACTION` contains more than one instruction;
- `TASK_ID` or `TASK_PACKET` differs between `CURRENT_GATE` and `NEXT_ACTION`
  without an explicit governed handoff;
- `TASK_PACKET` is required but set to `NONE`;
- `TASK_PACKET` points outside `ACTIVE_DOC_ROOT` without universal-governance
  authority;
- `REQUIRED_DOCS` references deprecated, superseded, or archived documents for
  active work.

## Required catches

### Last accepted result cannot be fail

`PROJECT_STATE.md` is invalid if `Last accepted result` contains:

```text
STATUS: fail
```

Failed results are logged and routed to correction, but they are not accepted
state. The orchestrator must not use a failed result as accepted source-of-truth
for downstream work.

### Blocked project requires blocker or GAP

Runtime state is invalid if:

```text
PROJECT_STATUS: blocked
```

and all of the following are absent:

- active blocker in `PROJECT_STATE.md`;
- active GAP in `GAP_REGISTER.md`;
- owner-facing blocker or question in `NEXT_ACTION.md`.

Blocked state must explain what blocks progress.

### Blocked branch requires BLOCKED_BY

Each active branch entry with:

```text
STATUS: blocked
```

must contain a non-empty `BLOCKED_BY` reference.

### Active branch must not have BLOCKED_BY

Each branch entry with:

```text
STATUS: active
```

is invalid if `BLOCKED_BY` contains anything other than `NONE` or an empty
field.

An active branch cannot simultaneously claim to be blocked.

### Multiple NEXT_ACTION entries are invalid

`NEXT_ACTION.md` must express exactly one next action.

Invalid examples include:

- multiple `ACTION_ID` blocks;
- more than one instruction under `Instruction for orchestrator`;
- one action that combines dispatch and checkpoint;
- one action that combines owner wait and correction;
- one action that combines finalization and stop before terminal invariants are
  validated.

The orchestrator must split multi-step routing into sequential `NEXT_ACTION`
updates.

## Blocker and GAP consistency

Runtime state is invalid when:

- active GAP exists but no dependent branch is blocked;
- dependent branch is blocked but no GAP, blocker, failed audit, or unmet
  dependency explains it;
- `wait_for_owner` is used without `TARGET_ROLE: project_owner`;
- `wait_for_owner` lacks an owner-facing question, GAP, or blocker;
- `ACTION_SEMANTIC: pause` lacks an active blocker and resume or correction
  condition.

## Terminal consistency

Completion is invalid unless all terminal invariants from
`STATE_TRANSITION_RULES.md` are true.

Invalid terminal states include:

- `CURRENT_PHASE: completed` with active blockers;
- `PROJECT_STATUS: completed` with active GAPs;
- terminal gate without passed status;
- `NEXT_ACTION.ACTION_TYPE: stop` without `ACTION_SEMANTIC: stop_terminal`;
- stop used as temporary pause or owner wait.

## Secret-safety check

Runtime state must not contain credentials, tokens, cookies, private keys, or
environment secret values.

If suspected secret material is found, the orchestrator must:

- stop printing the value;
- identify only the affected path and field;
- classify the issue as a secret-safety violation;
- route to correction or owner handling according to governance.
