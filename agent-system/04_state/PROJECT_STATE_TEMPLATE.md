# PROJECT_STATE

## Project

```text
PROJECT_NAME:
PROJECT_SLUG:
PROJECT_ROOT:
TZ_PATH:
ACTIVE_DOC_ROOT:
PACKAGE_VERSION:
GOVERNANCE_RULESET_VERSION:
RUNTIME_SCHEMA_VERSION:
CURRENT_PHASE: bootstrap | requirements | design | design_audit | implementation | implementation_audit | audit | testing | setup | run | launch | documentation | handover | correction | blocked | finalization | final_acceptance | completed
PROJECT_STATUS: active | blocked | completed | archived
```

## Workspace identity

These fields are mandatory for runtime schema version `2.0.0`.

```text
WORKSPACE_TYPE: package_repo | project_workspace | implementation_repo | test_fixture
WORKSPACE_IDENTITY_REF:
REPOSITORY_LOCK_REF:
PROJECT_ROOT_EXPECTED:
GIT_TOPLEVEL_ACTUAL:
EXPECTED_REMOTE:
ACTUAL_REMOTE:
EXPECTED_GIT_REMOTE:
ACTUAL_GIT_REMOTE:
EXPECTED_BRANCH:
ACTUAL_BRANCH:
PUSH_ALLOWED: false
IDENTITY_VALIDATION_STATUS: not_checked | passed | failed | blocked
IDENTITY_VALIDATION_ERROR: NONE | repository_identity_mismatch | repository_branch_mismatch | workspace_identity_leakage | unapproved_ssh_host_alias | missing_identity_manifest | repository_lock_missing | push_without_repository_lock
IDENTITY_VALIDATION_EVIDENCE:
REPOSITORY_LOCK_STATUS: absent | draft | accepted | revoked | blocked
CHECKPOINT_ELIGIBILITY: blocked | local_only | push_allowed | not_applicable
CHECKPOINT_BLOCKED_BY:
```

`EXPECTED_GIT_REMOTE` and `ACTUAL_GIT_REMOTE` are canonical repository identity
fields. `PUSH_ALLOWED` defaults to `false` unless an accepted repository lock
authorizes push for the current workspace type, canonical repository identity,
and branch.

## Runtime semantic state

These fields are mandatory and must remain in parity with
`agent-system/04_state/RUNTIME_STATE_SCHEMA.md` and
`agent-system/09_validators/schemas/project_state.schema.json`.

```text
ACTION_SEMANTIC: normal | wait_for_owner | pause | stop_terminal | completed_state_transition
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
