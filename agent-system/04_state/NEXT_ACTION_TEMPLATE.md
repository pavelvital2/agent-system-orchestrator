# NEXT_ACTION

## Next action

```text
ACTION_ID:
ACTION_TYPE: create_agent | route_result | update_state | wait_for_owner | correction | finalize | stop
TARGET_ROLE: requirements_analyst | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager | orchestrator | project_owner | none
TASK_ID:
TASK_PACKET:
DEPENDENCY_STATUS: ready | blocked | completed | not_applicable
BLOCKED_BY:
ACTION_SEMANTIC: normal | wait_for_owner | pause | stop_terminal | completed_state_transition
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
- If multiple actions are needed, each action must become a separate `NEXT_ACTION.md` update after the previous one completes.
