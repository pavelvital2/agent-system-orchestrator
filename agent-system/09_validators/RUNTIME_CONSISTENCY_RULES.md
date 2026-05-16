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
agent-system/02_runtime/REQUESTER_RETURN_PROTOCOL.md
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
project-runtime/TASK_REGISTRY.md
project-runtime/ACCEPTED_ARTIFACTS.md
project-runtime/ORCHESTRATOR_EVENTS_LOG.md
project-runtime/STATUS_SUMMARY.md
```

If a required file is missing, the orchestrator must create it from the
matching template when governance allows it, or enter correction/wait routing.

## Tuple consistency checks

Validate the combined tuple defined in `RUNTIME_STATE_SCHEMA.md` and
`STATE_TRANSITION_RULES.md`.

The tuple is invalid when:

- a mandatory field is missing;
- a field uses a value outside the allowed set;
- `PROJECT_STATE.md` omits mandatory semantic fields `ACTION_SEMANTIC` or
  `SEMANTIC_REASON`, or their required/optional status differs between
  `PROJECT_STATE_TEMPLATE.md`, `RUNTIME_STATE_SCHEMA.md`, and
  `schemas/project_state.schema.json`;
- `CURRENT_PHASE`, `PROJECT_STATUS`, `CURRENT_GATE`, and `NEXT_ACTION` are
  semantically incompatible;
- `CURRENT_GATE.ACTION_SEMANTIC` or `NEXT_ACTION.ACTION_SEMANTIC` is missing
  from runtime tuple validation;
- requester return metadata differs between task packet, task registry, and
  `NEXT_ACTION` for a research dependency or continuation route;
- `NEXT_ACTION` contains more than one instruction;
- `TASK_ID` or `TASK_PACKET` differs between `CURRENT_GATE` and `NEXT_ACTION`
  without an explicit governed handoff;
- `TASK_PACKET` is required but set to `NONE`;
- `TASK_PACKET` points outside `ACTIVE_DOC_ROOT` without universal-governance
  authority;
- `REQUIRED_DOCS` references deprecated, superseded, or archived documents for
  active work.

## Lifecycle/runtime enum drift checks

Validators must compare lifecycle stages from `PROJECT_LIFECYCLE.md` with the
runtime phase and gate enums in `RUNTIME_STATE_SCHEMA.md`, the Markdown state
templates, and JSON schema sidecars.

Runtime state is invalid when a lifecycle stage is neither:

- accepted as a `PROJECT_STATE.CURRENT_PHASE` value; nor
- accepted as a `CURRENT_GATE.GATE_TYPE` value; nor
- explicitly documented as a deterministic alias to an accepted runtime value.

The required lifecycle stages are:

```text
bootstrap
requirements
design
audit
implementation
testing
setup
run
launch
documentation
handover
final_acceptance
```

Specialized runtime phases such as `design_audit`, `implementation_audit`,
`correction`, `blocked`, `finalization`, and `completed` may remain only if
they do not replace or hide the required lifecycle stages.

## Required catches

### Mandatory profile audit cannot be bypassed

Runtime state is invalid if the active task packet has mandatory
`AUDIT_REQUIREMENTS`, a profile execution role returned `STATUS: pass`, and the
next transition is anything other than auditor routing.

Profile execution roles for this check are:

```text
requirements_analyst
designer
developer
tester
technical_writer
devops_setup_engineer
release_manager
```

Invalid direct routes after a mandatory-audit profile pass include:

- next profile role dispatch;
- next lifecycle phase dispatch;
- terminal completion or finalization;
- post-audit Git checkpoint before auditor `STATUS: pass`;
- dependent work marked `ready` before auditor `STATUS: pass`.

If an auditor returns `STATUS: fail` for a profile task, runtime state is invalid
when it allows commit, push, normal next task dispatch, terminal completion, or
dependent work marked `ready`. The only valid recovery path is correction,
governed update_state, GAP/blocked handling, or genuine owner handling when the
full runtime tuple permits it.

### Research return cannot bypass audit

Runtime state is invalid if `TASK_KIND: research_dependency` output is routed
to requester continuation before independent auditor `STATUS: pass`.

Runtime state is also invalid if research audit `fail`, `blocked`, or `gap`
marks requester continuation `ready`, or if the return target is inferred
without explicit requester return metadata.

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
