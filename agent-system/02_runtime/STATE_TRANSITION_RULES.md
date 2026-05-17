# STATE_TRANSITION_RULES

## Purpose

This document defines allowed transitions, forbidden transitions, terminal states, and invalid-state detection for the deterministic orchestrator runtime.

Action/state terms that can be confused during routing are defined in:

```text
agent-system/02_runtime/ACTION_STATE_SEMANTICS.md
```

Documentation-first validator checks for these rules are defined in:

```text
agent-system/09_validators/TRANSITION_VALIDATION_RULES.md
agent-system/09_validators/RUNTIME_CONSISTENCY_RULES.md
agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md
agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
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
PROJECT_STATE.PROJECT_SLUG
PROJECT_STATE.WORKSPACE_TYPE
PROJECT_STATE.WORKSPACE_IDENTITY_REF
PROJECT_STATE.REPOSITORY_LOCK_REF
PROJECT_STATE.EXPECTED_GIT_REMOTE
PROJECT_STATE.ACTUAL_GIT_REMOTE
PROJECT_STATE.EXPECTED_BRANCH
PROJECT_STATE.ACTUAL_BRANCH
PROJECT_STATE.PUSH_ALLOWED
PROJECT_STATE.IDENTITY_VALIDATION_STATUS
PROJECT_STATE.IDENTITY_VALIDATION_ERROR
PROJECT_STATE.REPOSITORY_LOCK_STATUS
PROJECT_STATE.CHECKPOINT_ELIGIBILITY
PROJECT_STATE.CHECKPOINT_BLOCKED_BY
CURRENT_GATE.GATE_TYPE
CURRENT_GATE.STATUS
CURRENT_GATE.OWNER_ROLE
CURRENT_GATE.TASK_ID
CURRENT_GATE.TASK_PACKET
CURRENT_GATE.ACTION_SEMANTIC
CURRENT_GATE.WORKSPACE_IDENTITY_STATUS
CURRENT_GATE.REPOSITORY_LOCK_STATUS
CURRENT_GATE.CHECKPOINT_ELIGIBILITY
NEXT_ACTION.ACTION_TYPE
NEXT_ACTION.TARGET_ROLE
NEXT_ACTION.TASK_ID
NEXT_ACTION.TASK_PACKET
NEXT_ACTION.DEPENDENCY_STATUS
NEXT_ACTION.ACTION_SEMANTIC
NEXT_ACTION.WORKSPACE_IDENTITY_REQUIRED
NEXT_ACTION.REPOSITORY_LOCK_REQUIRED
NEXT_ACTION.CHECKPOINT_POLICY
NEXT_ACTION.REQUESTER_RETURN_CONTEXT
GAP_REGISTER.active_gaps
TASK_REGISTRY.requester_return_metadata
PROJECT_STATE.active_blockers
PROJECT_STATE.active_branches
```

## Allowed role transitions

```text
profile_agent(pass, audit mandatory) -> auditor
requirements_analyst(pass) -> auditor when audit mandatory
designer(pass)          -> auditor
developer(pass)         -> auditor
tester(pass)            -> auditor when audit mandatory
technical_writer(pass)  -> auditor when audit mandatory
devops_setup_engineer(pass) -> auditor when audit mandatory
release_manager(pass)   -> auditor when audit mandatory
requirements_analyst(auditor pass) -> post-audit checkpoint gate, then designer or next requirements task according to NEXT_ACTION/TASK_REGISTRY
auditor(pass, design)   -> post-audit checkpoint gate, then next audited implementation/correction task
auditor(pass, research_dependency) -> post-audit checkpoint gate if required, then explicit requester continuation according to RETURN_TO_ROLE_AFTER_AUDIT_PASS and RETURN_TASK_AFTER_AUDIT_PASS
auditor(pass, impl)     -> tester if testing required, else next governed task/finalization
auditor(pass, checkpoint preflight detects audit miss) -> correction with FAILURE_TYPE audit_miss; no commit, no push, no normal next task
devops_setup_engineer(auditor pass) -> post-audit checkpoint gate, then run, launch, documentation, or correction according to gate
release_manager(auditor pass) -> post-audit checkpoint gate, then final_acceptance, handover, completed, or correction according to gate
auditor(fail)           -> correction for checked profile role; no commit, no push, no next phase
tester(pass, audit not mandatory) -> technical_writer if docs required, else orchestrator finalization
tester(fail)            -> developer correction via orchestrator
tester(blocked)         -> orchestrator routing
tester(gap)             -> orchestrator GAP routing
technical_writer(pass, audit not mandatory) -> orchestrator finalization
any_agent(blocked)      -> orchestrator routing
any_agent(gap)          -> GAP register + dependent branch blocked
```

For this rule, `profile_agent` covers these profile execution roles:

```text
requirements_analyst
designer
developer
tester
technical_writer
devops_setup_engineer
release_manager
```

If `AUDIT_REQUIREMENTS` in the active task packet requires audit, no
profile-agent `STATUS: pass` may route directly to another profile role,
another lifecycle phase, terminal completion, or any Git checkpoint. It must
route to an auditor first. The post-audit Git checkpoint is allowed only after
the auditor returns `STATUS: pass`.

## Forbidden transitions

- designer pass directly to developer;
- developer pass directly to tester or technical writer;
- requirements_analyst pass directly to designer, next requirements task, or
  another phase when audit is required;
- devops_setup_engineer pass directly to run, launch, documentation, or another
  phase when audit is required;
- release_manager pass directly to final_acceptance, handover, completed, or
  another phase when audit is required;
- any profile agent pass directly to another profile role, another lifecycle
  phase, terminal completion, or Git checkpoint when audit is required;
- tester fail to technical writer/finalization;
- technical writer pass directly to completed;
- profile agent RESULT directly setting project completed;
- create_agent while runtime schema invalid;
- create_agent for task outside ACTIVE_DOC_ROOT, except the single governed
  first bootstrap task packet at
  `project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md`;
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
- audit blocked or gap routed to post-audit Git checkpoint;
- post-audit Git checkpoint before required auditor pass;
- post-audit Git checkpoint that stages files outside the audited task allowed scope;
- post-audit Git checkpoint that stages suspected secret or credential material;
- post-audit Git checkpoint after `AUDIT_FALSE_PASS_DETECTED` or unresolved
  `FAILURE_TYPE: audit_miss`;
- normal dispatch, finalize, checkpoint, commit, or push while
  `INCIDENT_RECOVERY` is active for `wrong_remote_push`,
  `wrong_branch_push`, `invalid_task_packet_commit`, `forbidden_files`,
  `secret_exposure`, `runtime_corruption`, or `audit_false_pass`;
- `TASK_PACKET: NONE` for any file-changing correction
  (`TASK_PACKET_NONE_FILE_CHANGES_FORBIDDEN`);
- post-audit Git checkpoint after reasoning-level mismatch or invalid dispatch
  where requested/configured runner reasoning is below the resolved required
  level;
- profile-agent dispatch before workspace identity validation passes;
- runtime initialization that infers identity from folder name, inherited `.git`
  metadata, or raw remote strings without a workspace identity record;
- post-audit Git checkpoint before workspace identity validation and repository
  lock validation pass;
- checkpoint, commit, or push when `repository_identity_mismatch`,
  `repository_branch_mismatch`, `workspace_identity_leakage`, or
  `unapproved_ssh_host_alias` is active;
- push when `PUSH_ALLOWED` is not true under an accepted repository lock;
- push from `WORKSPACE_TYPE: test_fixture`;
- push after commit failure or checkpoint validation failure;
- commit or push after reasoning-level mismatch or invalid dispatch where
  requested/configured runner reasoning is below the resolved required level;
- research_dependency result routed to requester continuation before independent auditor pass;
- audit fail, blocked, or gap for research_dependency routed to requester continuation;
- requester return target inferred from informal context instead of explicit return metadata;
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

## Post-audit Git checkpoint routing

When an auditor returns `STATUS: pass` for required audited work:

- `POST_AUDIT_GIT_CHECKPOINT.md` must run before normal dependent work is
  marked `ready`;
- workspace identity validation must pass before checkpoint eligibility is
  evaluated;
- repository lock validation must pass before any push is attempted;
- wrong remote or wrong branch is a hard blocker for push;
- Git checkpoint validation must pass before staging, committing, or pushing;
- only accepted files from the audited task allowed scope may be staged;
- successful checkpoint must record branch, commit hash, push status, accepted
  files, accepted result reference, and audit reference;
- task registry status may move from `audit_passed` to `checkpoint_done` only
  after commit and push succeed;
- accepted artifacts may receive a commit hash only after checkpoint success.

When auditor status is `fail`, `blocked`, or `gap`:

- post-audit Git checkpoint is forbidden;
- commit and push are forbidden;
- dependent work remains blocked;
- routing must use correction, blocked, GAP, governed update_state, or genuine
  owner handling as permitted by the full runtime tuple.

## Research dependency and requester return routing

`TASK_KIND: research_dependency` is a sequential dependency route, not a GAP,
not a BLOCKER, and not generalized DAG/parallel orchestration.

A research dependency may return to its requester only when all conditions are
true:

- the research task packet includes complete requester return metadata;
- the research executor RESULT is formally valid;
- the independent auditor returns `STATUS: pass`;
- any required post-audit Git checkpoint is complete;
- `TASK_REGISTRY` preserves `REQUESTED_BY_ROLE`, `REQUESTED_BY_TASK`,
  `RETURN_TO_REQUESTER_AFTER_AUDIT_PASS`,
  `RETURN_TO_ROLE_AFTER_AUDIT_PASS`, and
  `RETURN_TASK_AFTER_AUDIT_PASS`;
- `NEXT_ACTION` routes exactly to the recorded return role and return task.
- `NEXT_ACTION.REQUESTER_RETURN_CONTEXT` preserves the requester return
  context required for the continuation route.
- `TASK_REGISTRY.requester_return_metadata` matches the task packet return
  metadata and the requester continuation target.

If audit returns `fail`, `blocked`, or `gap`, requester continuation remains
blocked and routing must use correction, blocked/GAP handling, governed
update_state, or owner handling when genuinely required.

The orchestrator must not infer return targets from memory, conversation, or
informal notes.

When checkpoint commit fails:

- push is forbidden;
- checkpoint failure must be logged;
- routing must use governed correction or owner handling.

When checkpoint push fails:

- checkpoint failure must be logged with `PUSH_STATUS: failed`;
- the local commit hash must remain traceable if available;
- routing must use governed correction or owner handling.

When secret or credential risk is detected:

- staging, commit, and push are forbidden;
- logs and RESULT summaries must not include secret values;
- routing must use governed correction or owner handling.

When checkpoint preflight detects a blocker after auditor `STATUS: pass` for a
check the auditor was required to perform:

- record `AUDIT_FALSE_PASS_DETECTED`;
- classify the correction input as `FAILURE_TYPE: audit_miss`;
- staging, commit, and push are forbidden;
- normal dependent dispatch and requester continuation are forbidden;
- route only to governed correction, blocked/GAP handling, or genuine owner
  handling as permitted by the full runtime tuple;
- file-changing correction requires a full correction task packet and a later
  independent audit pass before checkpoint can be attempted again.

## Workspace identity and repository lock routing

Workspace identity validation is required before any dispatch, checkpoint,
commit, or push. The orchestrator must compare canonical repository identity:

```text
EXPECTED_GIT_REMOTE
ACTUAL_GIT_REMOTE
```

Raw remote strings may differ only when both normalize to the same canonical
GitHub repository identity under
`agent-system/09_validators/WORKSPACE_IDENTITY_VALIDATION_RULES.md`.

If an SSH host alias appears in `ACTUAL_REMOTE`, it is valid only when accepted
in the repository lock or when bounded evidence proves that the alias resolves
to `github.com`.

If the identity gate fails:

```text
PROJECT_STATUS: blocked
CURRENT_PHASE: correction | blocked
CURRENT_GATE.STATUS: blocked
NEXT_ACTION.ACTION_TYPE: correction | wait_for_owner | update_state | stop
```

The following blockers must stop dependent dispatch and checkpoint:

```text
repository_identity_mismatch
repository_branch_mismatch
workspace_identity_leakage
unapproved_ssh_host_alias
repository_lock_missing
push_without_repository_lock
```

Push is allowed only when:

```text
IDENTITY_VALIDATION_STATUS: passed
REPOSITORY_LOCK_STATUS: accepted
PUSH_ALLOWED: true
CHECKPOINT_ELIGIBILITY: push_allowed
WORKSPACE_TYPE: package_repo | project_workspace | implementation_repo
```

`WORKSPACE_TYPE: test_fixture` must always keep `PUSH_ALLOWED: false`.

Commit is forbidden after wrong remote or wrong branch unless the active
repository lock and active task packet explicitly allow a governed local-only
checkpoint. That local-only exception must not push.

## Phase/action compatibility

```text
bootstrap              -> create_agent | update_state | wait_for_owner | correction | stop
requirements           -> create_agent | route_result | correction | wait_for_owner
design                 -> create_agent | route_result | correction | wait_for_owner
design_audit           -> create_agent | route_result | correction
implementation         -> create_agent | route_result | correction | wait_for_owner
implementation_audit   -> create_agent | route_result | correction
audit                  -> create_agent | route_result | correction | wait_for_owner
testing                -> create_agent | route_result | correction | wait_for_owner
setup                  -> create_agent | route_result | correction | wait_for_owner
run                    -> create_agent | route_result | correction | wait_for_owner
launch                 -> create_agent | route_result | correction | wait_for_owner
documentation          -> create_agent | route_result | correction | wait_for_owner
handover               -> create_agent | route_result | correction | wait_for_owner
correction             -> update_state | correction | create_agent | wait_for_owner | stop
blocked                -> update_state | wait_for_owner | correction | stop
finalization           -> update_state | finalize | correction | stop
final_acceptance       -> update_state | finalize | wait_for_owner | correction | stop
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

`TASK_PACKET_NONE_FILE_CHANGES_FORBIDDEN`: `TASK_PACKET: NONE` is forbidden for
file-changing corrections. It is valid only for pure coordination or
orchestrator-owned runtime operations that do not change project, package,
implementation, task-packet, profile-result, committed, or other non-runtime
artifacts. Any correction that changes non-runtime files requires a full
correction task packet.

`orchestrator_task_packet_none_project_artifact_route_forbidden`:
`ACTION_TYPE: correction`, `TARGET_ROLE: orchestrator`, and
`TASK_PACKET: NONE` must not be used when `EXPECTED_RESULT`,
`INSTRUCTION_FOR_ORCHESTRATOR`, or blocking context asks the orchestrator to
create project task packets, project design artifacts, requirements artifacts,
implementation plans, or other project-owned non-runtime files. That route is
invalid and must be blocked before dispatch/checkpoint. Project task packets
and design artifacts require a bounded profile task packet and independent
audit, or an explicit GAP/BLOCKED/wait_for_owner route.

## Incident recovery routing

Incident recovery is entered when any incident class from
`INCIDENT_RECOVERY.md` is active:

```text
wrong_remote_push
wrong_branch_push
invalid_task_packet_commit
forbidden_files
secret_exposure
runtime_corruption
audit_false_pass
```

Required incident freeze tuple:

```text
PROJECT_STATUS: blocked
CURRENT_PHASE: correction
CURRENT_GATE.STATUS: blocked
NEXT_ACTION.ACTION_TYPE: correction | wait_for_owner | update_state | stop | create_agent
```

Allowed incident recovery actions:

- governed `update_state` for runtime/routing metadata;
- `wait_for_owner` for owner decisions about wrong remote, wrong branch,
  exposed secrets, remote history, or unrecoverable state;
- `stop` only when stop invariants permit a governed halt;
- `create_agent` only for a full bounded correction task packet when file
  changes are required and governance freeze permits a correction dispatch.

Forbidden incident recovery actions:

- normal project dispatch;
- finalization or completed-state routing;
- checkpoint, commit, or push before incident resume criteria pass;
- direct orchestrator repair of project docs, task packets, package docs,
  implementation files, profile RESULTs, committed content, or secret-bearing
  files.

Resume after incident recovery requires:

- redacted incident evidence and affected references;
- repository identity, expected branch, repository lock, and push policy
  validation when Git target was involved;
- task packet validation when an invalid task packet was involved;
- changed-file scope validation when forbidden files were involved;
- secret scan pass and owner security action when secret exposure was involved;
- runtime schema and transition validation when runtime corruption was
  involved;
- `AUDIT_FALSE_PASS_DETECTED` / `FAILURE_TYPE: audit_miss` correction and
  independent audit when audit false pass was involved;
- full correction task packet, independent audit, and checkpoint preflight for
  every file-changing correction.

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
- task packet outside ACTIVE_DOC_ROOT, except the single governed first
  bootstrap task packet at
  `project-runtime/bootstrap/TASK_BOOTSTRAP_<TARGET_ROLE>_001.md`;
- task packet deprecated or superseded;
- REQUIRED_DOCS includes deprecated/archive doc;
- active gap without blocked dependent branch;
- blocked branch without BLOCKED_BY;
- skipped gate without authority/evidence;
- skipped mandatory audit after profile-agent pass;
- completed/archived status with NEXT_ACTION not stop.
- profile-agent pass followed by `DEPENDENCY_STATUS: ready` for dependent work
  before required auditor pass;
- research_dependency requester continuation marked `ready` before independent
  audit pass;
- missing or contradictory requester return metadata in task packet,
  task registry, or NEXT_ACTION;
- `ACTION_SEMANTIC: stop_terminal` with unresolved active blockers, active GAPs, failed required gates, or missing finalization evidence;
- `ACTION_SEMANTIC: pause` with `NEXT_ACTION.ACTION_TYPE: stop`;
- `ACTION_TYPE: wait_for_owner` with no owner-facing blocker, GAP, or question;
- auditor fail followed by `DEPENDENCY_STATUS: ready` for dependent work.
- checkpoint_done without commit hash, branch, push status, accepted files, or audit reference;
- checkpoint after auditor fail, blocked, gap, invalid RESULT, or pending correction;
- checkpoint, commit, or push after reasoning-level mismatch where actual
  spawned reasoning is below required;
- profile-agent dispatch, checkpoint, commit, or push before workspace identity
  validation passes;
- missing workspace identity or repository lock fields in v2.0.0 runtime state;
- `repository_identity_mismatch`;
- `repository_branch_mismatch`;
- `workspace_identity_leakage`;
- `unapproved_ssh_host_alias`;
- `PUSH_ALLOWED: true` without accepted repository lock;
- `WORKSPACE_TYPE: test_fixture` with `PUSH_ALLOWED: true`;
- checkpoint push attempted after commit failure;
- checkpoint record or event containing unredacted secret values.
- `AUDIT_FALSE_PASS_DETECTED` without blocked dependent work and a governed
  `FAILURE_TYPE: audit_miss` correction route;
- active `INCIDENT_RECOVERY` without `PROJECT_STATUS: blocked`,
  `CURRENT_PHASE: correction`, blocked dependent work, and a governed
  recovery route;
- `wrong_remote_push`, `wrong_branch_push`, `invalid_task_packet_commit`,
  `forbidden_files`, `secret_exposure`, or `runtime_corruption` followed by
  normal dispatch, finalize, checkpoint, commit, or push before incident
  resume criteria pass;
- `TASK_PACKET: NONE` paired with a correction that changes non-runtime files;

The validator layer must also catch the concrete invalid states listed in:

```text
agent-system/09_validators/RUNTIME_CONSISTENCY_RULES.md
agent-system/09_validators/TRANSITION_VALIDATION_RULES.md
```
