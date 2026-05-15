# TRANSITION_VALIDATION_RULES

## Purpose

This document defines documentation-first validation rules for runtime
transitions.

The authoritative transition model is `STATE_TRANSITION_RULES.md`. This
document lists the validator checks that must catch transition violations.

## Source documents

```text
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/ACTION_STATE_SEMANTICS.md
agent-system/04_state/RUNTIME_STATE_SCHEMA.md
```

## Pre-dispatch transition checks

Before creating or routing an agent, validate:

- runtime tuple is valid;
- `NEXT_ACTION.ACTION_TYPE` is compatible with `CURRENT_PHASE`;
- `TARGET_ROLE` is compatible with `ACTION_TYPE`;
- `TASK_PACKET` is present when dispatch requires one;
- `DEPENDENCY_STATUS` is `ready` only when dependencies are actually clear;
- no active GAP or blocker blocks the target branch;
- `NEXT_ACTION` contains exactly one action.

## Post-result transition checks

After a RESULT, validate:

- RESULT status is allowed for profile agents;
- advisory next action does not override governance;
- required audit/testing/documentation gates are not skipped;
- failed, blocked, and gap results are logged before recovery routing;
- accepted state is updated only after required gates pass.

## Required catches

### Direct progress after audit fail

When an auditor returns:

```text
STATUS: fail
```

the next governed route must not be normal progress.

Forbidden next routes include:

- next implementation task;
- testing;
- documentation;
- finalization;
- completed state;
- post-audit Git checkpoint.

Allowed next routes are limited to:

- correction;
- update_state for recovery bookkeeping;
- wait_for_owner only when owner input is genuinely required.

Dependent work must have:

```text
DEPENDENCY_STATUS: blocked
```

until the correction passes its required gate.

### Multiple NEXT_ACTION entries

Transition is invalid if a single `NEXT_ACTION.md` contains more than one
action or instruction.

The orchestrator must not execute a combined instruction such as dispatch plus
checkpoint, correction plus owner wait, or finalize plus terminal stop.

### Blocked state without blocker

Transition to blocked state is invalid unless it records an active blocker,
active GAP, failed dependency, or owner-facing question.

### Branch active with BLOCKED_BY

Transition is invalid if a branch remains:

```text
STATUS: active
```

while also carrying a non-empty `BLOCKED_BY` reference.

The branch must either be active with no blocker, or blocked with `BLOCKED_BY`.

### Last accepted result fail

Transition is invalid if the orchestrator attempts to promote a failed result
into `Last accepted result`.

Only results that passed all mandatory acceptance gates may become accepted
state.

## Role transition checks

Validators must catch these forbidden transitions:

- designer pass directly to developer;
- developer pass directly to tester;
- developer pass directly to technical writer;
- tester fail to technical writer;
- tester fail to finalization;
- technical writer pass directly to completed;
- profile-agent RESULT directly setting completed;
- ordinary project task changing universal package state;
- ordinary profile agent changing runtime state.

## Action semantic checks

`wait_for_owner` is valid only with:

```text
NEXT_ACTION.ACTION_TYPE: wait_for_owner
NEXT_ACTION.TARGET_ROLE: project_owner
PROJECT_STATUS: blocked
```

and an owner-facing blocker, GAP, or question.

`pause` is valid only with blocked/correction state, an active blocker, and a
resume or correction condition.

`completed` is valid only as terminal state, not as an action shortcut.

`stop_terminal` is valid only after terminal invariants pass.

## Recovery routing

If transition validation fails, the orchestrator must not dispatch the
requested profile agent. It must enter governed recovery according to
`VIOLATION_RECOVERY.md`.
