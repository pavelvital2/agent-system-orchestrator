# STATE_TRANSITION_RULES

## Purpose

This document defines allowed transitions, forbidden transitions, terminal states, and invalid-state detection for the deterministic orchestrator runtime.

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
GAP_REGISTER.active_gaps
PROJECT_STATE.active_blockers
PROJECT_STATE.active_branches
```

## Allowed role transitions

```text
designer(pass)          -> auditor
developer(pass)         -> auditor
auditor(pass, design)   -> next audited implementation/correction task
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
