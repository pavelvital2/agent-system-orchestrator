# NEXT_ACTION

## Next action

Required structured fields:

```text
ACTION_ID:
ACTION_TYPE:
TARGET_ROLE:
TASK_ID:
TASK_PACKET:
DEPENDENCY_STATUS:
BLOCKED_BY:
ACTION_SEMANTIC:
WORKSPACE_IDENTITY_REQUIRED:
REPOSITORY_LOCK_REQUIRED:
CHECKPOINT_POLICY:
CHECKPOINT_PREFLIGHT_REQUIRED:
CHECKPOINT_RECEIPT_REQUIRED:
CHECKPOINT_RECEIPT_REF:
REQUESTER_RETURN_CONTEXT:
BLOCKING_OR_RESUME_CONTEXT:
REQUIRED_UNIVERSAL_DOCS:
REQUIRED_PROJECT_DOCS:
EXPECTED_RESULT:
INSTRUCTION_FOR_ORCHESTRATOR:
```

```text
ACTION_ID:
ACTION_TYPE: create_agent | route_result | update_state | wait_for_owner | correction | finalize | stop
TARGET_ROLE: requirements_analyst | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager | orchestrator | project_owner | none
TASK_ID:
TASK_PACKET:
DEPENDENCY_STATUS: ready | blocked | completed | not_applicable
BLOCKED_BY:
ACTION_SEMANTIC: normal | wait_for_owner | pause | stop_terminal | completed_state_transition
WORKSPACE_IDENTITY_REQUIRED: yes | no
REPOSITORY_LOCK_REQUIRED: yes | no
CHECKPOINT_POLICY: forbidden | local_only | commit_and_push | no_checkpoint
CHECKPOINT_PREFLIGHT_REQUIRED: yes | no
CHECKPOINT_RECEIPT_REQUIRED: yes | no
CHECKPOINT_RECEIPT_REF:
```

`WORKSPACE_IDENTITY_REQUIRED` must be `yes` for runtime initialization,
profile-agent dispatch, checkpoint, commit, or push. It may be `no` only for a
governed correction or owner-wait action whose purpose is to create or repair
missing identity records.

`REPOSITORY_LOCK_REQUIRED` must be `yes` before commit or push. Push remains
forbidden unless the accepted repository lock sets `PUSH_ALLOWED: true`.
`CHECKPOINT_PREFLIGHT_REQUIRED: yes` is mandatory before any checkpoint, commit,
or push. `CHECKPOINT_RECEIPT_REQUIRED: yes` is mandatory when
`CHECKPOINT_POLICY` is `local_only` or `commit_and_push`; the receipt must use
`agent-system/03_templates/CHECKPOINT_ELIGIBILITY_TEMPLATE.md`.

## Requester return context

Required when routing a research dependency, accepted research return, or
requester continuation. Otherwise use `NONE`.

```text
REQUESTED_BY_ROLE:
REQUESTED_BY_TASK:
RETURN_TO_REQUESTER_AFTER_AUDIT_PASS: yes | no
RETURN_TO_ROLE_AFTER_AUDIT_PASS:
RETURN_TASK_AFTER_AUDIT_PASS:
RESEARCH_QUESTION_ID:
ACCEPTED_RESEARCH_RESULT_REF:
ACCEPTED_RESEARCH_AUDIT_REF:
```

## Blocking or resume context

Required when `DEPENDENCY_STATUS: blocked`, `ACTION_TYPE: wait_for_owner`, or `ACTION_SEMANTIC: pause`.

```text
BLOCKER_ID:
BLOCKER_TYPE: owner_decision | pause | audit_fail | gap | runtime | dependency | governance | other
BLOCKS:
RESOLUTION_PATH:
OWNER_QUESTION:
RESUME_CONDITION:
```

## REQUIRED_UNIVERSAL_DOCS

```text
- NONE
```

## REQUIRED_PROJECT_DOCS

```text
- NONE
```

## EXPECTED_RESULT

```text
- agent-system/03_templates/AGENT_RESULT_TEMPLATE.md
```

## Instruction for orchestrator

```text
One instruction only.
```

## Rules

- `NEXT_ACTION.md` must contain exactly one next action.
- It must not contain hidden subtasks.
- It must not override governance authority, state transition rules, filesystem governance, or role instructions.
- `requirements_analyst`, `designer`, `developer`, `auditor`, `tester`, `technical_writer`, `devops_setup_engineer`, and `release_manager` are profile execution roles for dispatchable agent work.
- `orchestrator`, `project_owner`, and `none` are control/routing pseudo-roles and must not be used as profile execution task types.
- `ACTION_SEMANTIC: wait_for_owner` requires `ACTION_TYPE: wait_for_owner` and `TARGET_ROLE: project_owner`.
- `ACTION_SEMANTIC: pause` is temporary and must not use `ACTION_TYPE: stop`.
- `ACTION_SEMANTIC: stop_terminal` requires `ACTION_TYPE: stop` and must not be used for temporary holds.
- `ACTION_SEMANTIC: completed_state_transition` is allowed only for governed finalization updates before terminal stop.
- Audit fail must not set `DEPENDENCY_STATUS: ready` for dependent work.
- Research dependency return must not set requester continuation ready before independent audit pass.
- Requester return routing must use explicit return metadata and must not be inferred from context.
- Workspace identity validation must pass before dispatch, checkpoint, commit,
  or push unless the action is a governed correction or owner wait for missing
  identity records.
- `CHECKPOINT_POLICY: commit_and_push` requires `REPOSITORY_LOCK_REQUIRED: yes`
  and an accepted repository lock with `PUSH_ALLOWED: true`.
- `CHECKPOINT_PREFLIGHT_REQUIRED: yes` and `CHECKPOINT_RECEIPT_REQUIRED: yes`
  are required before any local-only or commit-and-push checkpoint.
- If multiple actions are needed, each action must become a separate `NEXT_ACTION.md` update after the previous one completes.
- `orchestrator_task_packet_none_project_artifact_route_forbidden`:
  `TARGET_ROLE: orchestrator` with `TASK_PACKET: NONE` must not request
  creation of project task packets, project design artifacts, requirements
  artifacts, implementation plans, or other project-owned non-runtime files.
  Such correction routes are invalid and must be replaced by a bounded
  dispatchable task packet or explicit GAP/BLOCKED/wait_for_owner route.
