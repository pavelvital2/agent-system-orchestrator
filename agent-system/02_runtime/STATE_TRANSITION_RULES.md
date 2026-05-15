# STATE_TRANSITION_RULES

## Purpose

This document defines allowed transitions, forbidden transitions, terminal states, and invalid-state detection for the deterministic orchestrator runtime.

Action/state terms that can be confused during routing are defined in:

```text
agent-system/02_runtime/ACTION_STATE_SEMANTICS.md
```

## State tuple

Before dispatch, validate the combined runtime state:

```text
PROJECT_STATE.CURRENT_PHASE
PROJECT_STATE.PROJECT_STATUS
PROJECT_STATE.ACTIVE_DOC_ROOT
PROJECT_STATE.PACKAGE_VERSION
PROJECT_STATE.GOVERNANCE_RULESET_VERSION
PROJECT_STATE.RUNTIME_SCHEMA_VERSION
CURRENT_GATE.GATE_TYPE
CURRENT_GATE.STATUS
CURRENT_GATE.OWNER_ROLE
CURRENT_GATE.TASK_ID
CURRENT_GATE.TASK_PACKET
NEXT_ACTION.ACTION_TYPE
NEXT_ACTION.TARGET_ROLE
NEXT_ACTION.TASK_ID
NEXT_ACTION.TASK_PACKET
NEXT_ACTION.DEPENDENCY_STATUS
NEXT_ACTION.ACTION_SEMANTIC
GAP_REGISTER.active_gaps
PROJECT_STATE.active_blockers
PROJECT_STATE.active_branches
```

## Allowed role transitions

```text
designer(pass)          -> auditor
developer(pass)         -> auditor
auditor(pass, design)   -> post-audit checkpoint gate, then next audited implementation/correction task
auditor(pass, impl)     -> tester if testing required, else next governed task/finalization
auditor(fail)           -> correction for checked role or designer
tester(pass)            -> technical_writer if docs required, else orchestrator finalization
tester(fail)            -> developer correction via orchestrator
tester(blocked)         -> orchestrator routing
tester(gap)             -> orchestrator GAP routing
technical_writer(pass)  -> orchestrator finalization
any_agent(blocked)      -> orchestrator routing
any_agent(gap)          -> GAP register + dependent branch blocked
```

## Forbidden transitions

- designer pass directly to developer;
- developer pass directly to tester or technical writer;
- tester fail to technical writer/finalization;
- technical writer pass directly to completed;
- profile agent RESULT directly setting project completed;
- create_agent while runtime schema invalid;
- create_agent for task outside ACTIVE_DOC_ROOT;
- create_agent for deprecated/superseded task;
- dependent dispatch while active blocking GAP exists;
- use of project-archive as active source;
- ordinary project task changing agent-system;
- ordinary profile agent changing project-runtime;
- skipped gate without explicit authority and evidence;
- completed project with active gaps/blockers;
- NEXT_ACTION stop before terminal invariants pass.
- audit fail routed to normal next task, testing, documentation, finalization, or completed;
- audit fail routed to post-audit Git checkpoint;
- terminal stop used as a temporary pause or owner wait;
- `ACTION_SEMANTIC: pause` without an active blocker and resume or correction path;
- `wait_for_owner` without `TARGET_ROLE: project_owner` or an owner-facing blocker/GAP.

## Action/state semantic compatibility

```text
wait_for_owner:
  NEXT_ACTION.ACTION_TYPE: wait_for_owner
  NEXT_ACTION.TARGET_ROLE: project_owner
  PROJECT_STATUS: blocked
  Required: owner-facing question, GAP, or blocker reference

pause:
  NEXT_ACTION.ACTION_TYPE: update_state | correction
  NEXT_ACTION.ACTION_SEMANTIC: pause
  PROJECT_STATUS: blocked
  Required: active blocker reference and resume/correction condition

stop_terminal:
  NEXT_ACTION.ACTION_TYPE: stop
  NEXT_ACTION.TARGET_ROLE: none
  NEXT_ACTION.ACTION_SEMANTIC: stop_terminal
  Required: terminal stop invariants or governed unrecoverable halt

completed:
  PROJECT_STATE.CURRENT_PHASE: completed
  PROJECT_STATE.PROJECT_STATUS: completed
  CURRENT_GATE.GATE_TYPE: terminal
  CURRENT_GATE.STATUS: passed
  NEXT_ACTION.ACTION_TYPE: stop
  NEXT_ACTION.ACTION_SEMANTIC: stop_terminal
```

`completed` is a state, not an action. `stop_terminal` is an action semantic, not proof of completion by itself.

## Audit fail routing

When an auditor returns `STATUS: fail`:

- the checked result is not accepted;
- dependent branches must remain or become blocked;
- `NEXT_ACTION.ACTION_TYPE` must be `correction`, `update_state`, or `wait_for_owner` if owner input is genuinely required;
- `NEXT_ACTION.DEPENDENCY_STATUS` for dependent work must be `blocked`;
- normal next project task dispatch is forbidden;
- post-audit Git checkpoint is forbidden;
- correction must pass its own required audit before dependent work resumes.

## Phase/action compatibility

```text
bootstrap              -> create_agent | update_state | wait_for_owner | correction | stop
design                 -> create_agent | route_result | correction | wait_for_owner
design_audit           -> create_agent | route_result | correction
implementation         -> create_agent | route_result | correction | wait_for_owner
implementation_audit   -> create_agent | route_result | correction
testing                -> create_agent | route_result | correction | wait_for_owner
documentation          -> create_agent | route_result | correction | wait_for_owner
correction             -> update_state | correction | create_agent | wait_for_owner | stop
blocked                -> update_state | wait_for_owner | correction | stop
finalization           -> update_state | finalize | correction | stop
completed              -> stop
```

## Governed non-dispatch actions

```text
update_state:
TARGET_ROLE: orchestrator | none
TASK_PACKET: NONE unless a governed package-correction task explicitly requires one
Dispatch: must not dispatch a profile agent
Follow-up: must be followed by tuple validation
```

`TASK_PACKET: NONE` is allowed for:

- wait_for_owner;
- governed update_state;
- finalize when no task packet is required;
- stop;
- correction when routing does not dispatch a profile/package-correction agent.

## Terminal completion

Completion is valid only when:

```text
CURRENT_PHASE: completed
PROJECT_STATUS: completed
CURRENT_GATE.GATE_TYPE: terminal
CURRENT_GATE.STATUS: passed
NEXT_ACTION.ACTION_TYPE: stop
NEXT_ACTION.TARGET_ROLE: none
Active GAPs: NONE
Active blockers: NONE
Mandatory audits: passed
Mandatory testing: passed or not required by audited task packet
Mandatory documentation: completed if required
```

`NEXT_ACTION.ACTION_SEMANTIC` must be `stop_terminal` for terminal completion.

## Pause and owner wait invariants

Temporary no-dispatch conditions must remain non-terminal:

```text
pause:
  CURRENT_PHASE: blocked | correction
  PROJECT_STATUS: blocked
  CURRENT_GATE.STATUS: blocked
  NEXT_ACTION.ACTION_TYPE: update_state | correction
  NEXT_ACTION.ACTION_SEMANTIC: pause
  Active blocker: required

wait_for_owner:
  CURRENT_PHASE: blocked | correction | bootstrap
  PROJECT_STATUS: blocked
  CURRENT_GATE.STATUS: blocked
  NEXT_ACTION.ACTION_TYPE: wait_for_owner
  NEXT_ACTION.TARGET_ROLE: project_owner
  Active blocker or GAP: required
```

Neither condition may set `CURRENT_PHASE: completed`, `PROJECT_STATUS: completed`, or `CURRENT_GATE.GATE_TYPE: terminal`.

## Invalid-state detection

Enter correction if any of the following are detected:

- missing required runtime file;
- mandatory field absent;
- NEXT_ACTION contains multiple instructions;
- phase/gate/action mismatch;
- task packet absent or invalid when ACTION_TYPE requires a task packet;
- task packet outside ACTIVE_DOC_ROOT;
- task packet deprecated or superseded;
- REQUIRED_DOCS includes deprecated/archive doc;
- active gap without blocked dependent branch;
- blocked branch without BLOCKED_BY;
- skipped gate without authority/evidence;
- completed/archived status with NEXT_ACTION not stop.
- `ACTION_SEMANTIC: stop_terminal` with unresolved active blockers, active GAPs, failed required gates, or missing finalization evidence;
- `ACTION_SEMANTIC: pause` with `NEXT_ACTION.ACTION_TYPE: stop`;
- `ACTION_TYPE: wait_for_owner` with no owner-facing blocker, GAP, or question;
- auditor fail followed by `DEPENDENCY_STATUS: ready` for dependent work.
