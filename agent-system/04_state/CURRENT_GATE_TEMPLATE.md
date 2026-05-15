# CURRENT_GATE

## Current gate

```text
GATE_ID:
GATE_NAME:
GATE_TYPE: bootstrap | design | audit | implementation | testing | documentation | correction | finalization | terminal
STATUS: open | passed | failed | blocked | skipped
OWNER_ROLE: orchestrator | designer | developer | auditor | tester | technical_writer | project_owner
TASK_ID:
TASK_PACKET:
ACTION_SEMANTIC: normal | wait_for_owner | pause | stop_terminal | completed_state_transition
```

## Entry criteria

```text
- NONE
```

## Exit criteria

```text
- NONE
```

## Required next role

```text
designer | developer | auditor | tester | technical_writer | orchestrator | project_owner | none
```

## Gate evidence

```text
- NONE
```

## Blocking status

Required when `STATUS: blocked` or `STATUS: failed`.

```text
BLOCKER_ID:
BLOCKER_TYPE: owner_decision | pause | audit_fail | gap | runtime | dependency | governance | other
BLOCKS:
BLOCKED_BY:
RESOLUTION_PATH:
```

If the gate is not blocked or failed:

```text
NONE
```

## Notes

```text
- NONE
```
