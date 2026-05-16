# PROJECT_STATE

## Project

```text
PROJECT_NAME:
PROJECT_ROOT:
TZ_PATH:
ACTIVE_DOC_ROOT:
PACKAGE_VERSION:
GOVERNANCE_RULESET_VERSION:
RUNTIME_SCHEMA_VERSION:
CURRENT_PHASE: bootstrap | requirements | design | design_audit | implementation | implementation_audit | audit | testing | setup | run | launch | documentation | handover | correction | blocked | finalization | final_acceptance | completed
PROJECT_STATUS: active | blocked | completed | archived
```

## Runtime semantic state

```text
ACTION_SEMANTIC: normal | wait_for_owner | pause | stop_terminal | completed_state
SEMANTIC_REASON:
```

## Active branches

If active branches exist:

```text
BRANCH_ID:
STATUS: active | blocked | completed | archived
CURRENT_TASK:
CURRENT_AGENT_ROLE:
DEPENDENCIES:
BLOCKED_BY: <BLOCKER_ID | GAP_ID | NONE>
```

`CURRENT_AGENT_ROLE` must be one of the profile execution roles:
`requirements_analyst`, `designer`, `developer`, `auditor`, `tester`,
`technical_writer`, `devops_setup_engineer`, or `release_manager`.

If no active branches exist:

```text
NONE
```

## Completed milestones

```text
NONE
```

## Active risks

```text
NONE
```

## Active blockers

```text
BLOCKER_ID:
BLOCKER_TYPE: owner_decision | pause | audit_fail | gap | runtime | dependency | governance | other
STATUS: active | resolving
BLOCKS:
BLOCKED_BY:
RESOLUTION_PATH:
```

If no active blockers exist:

```text
NONE
```

## Active gaps

```text
NONE
```

## Last accepted result

```text
ROLE:
TASK:
DATE:
STATUS:
RESULT_REF:
```

`ROLE` records the profile execution role that produced the accepted result.
Control pseudo-roles `orchestrator`, `project_owner`, and `none` are routing
values and must not be recorded as profile result roles.
