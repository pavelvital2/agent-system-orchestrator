# CURRENT_GATE

## Current gate

```text
GATE_ID:
GATE_NAME:
GATE_TYPE: bootstrap | requirements | design | audit | implementation | testing | setup | run | launch | documentation | handover | correction | finalization | final_acceptance | terminal
STATUS: open | passed | failed | blocked | skipped
OWNER_ROLE: orchestrator | requirements_analyst | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager | project_owner
TASK_ID:
TASK_PACKET:
ACTION_SEMANTIC: normal | wait_for_owner | pause | stop_terminal | completed_state_transition
WORKSPACE_IDENTITY_STATUS: not_checked | passed | failed | blocked
REPOSITORY_LOCK_STATUS: absent | draft | accepted | revoked | blocked | not_required
CHECKPOINT_ELIGIBILITY: blocked | local_only | push_allowed | not_applicable
CHECKPOINT_ELIGIBILITY_STATUS: not_checked | eligible | ineligible | blocked
PROJECT_CHECKPOINT_STATUS: not_required | pending | passed | failed | blocked
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
requirements_analyst | designer | developer | auditor | tester | technical_writer | devops_setup_engineer | release_manager | orchestrator | project_owner | none
```

Profile execution roles may own task gates. `orchestrator`, `project_owner`,
and `none` are control/routing pseudo-roles, not profile task types.

Workspace identity status, repository lock status, and checkpoint eligibility
are mandatory gate fields. A gate cannot pass checkpoint, commit, or push
eligibility while workspace identity is `not_checked`, `failed`, or `blocked`.
`CHECKPOINT_ELIGIBILITY_STATUS` must remain separate from audit status; auditor
`STATUS: pass` is a prerequisite, not a checkpoint decision.

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
