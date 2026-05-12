# NEXT_ACTION

## Next action

```text
ACTION_ID:
ACTION_TYPE: create_agent | route_result | update_state | wait_for_owner | correction | finalize | stop
TARGET_ROLE: designer | developer | auditor | tester | technical_writer | orchestrator | project_owner | none
TASK_ID:
TASK_PACKET:
DEPENDENCY_STATUS: ready | blocked | completed | not_applicable
BLOCKED_BY:
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
- If multiple actions are needed, each action must become a separate `NEXT_ACTION.md` update after the previous one completes.
