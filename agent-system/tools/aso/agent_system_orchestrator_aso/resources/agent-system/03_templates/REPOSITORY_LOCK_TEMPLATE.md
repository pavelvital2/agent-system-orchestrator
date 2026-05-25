# REPOSITORY_LOCK

## Purpose

This template records the explicit repository lock that may authorize a
post-audit checkpoint to commit or push. Auditor `STATUS: pass` is necessary
for a checkpoint, but it is not sufficient to permit commit or push.

`PUSH_ALLOWED` defaults to `false`.

## Lock identity

```text
LOCK_ID:
LOCK_STATUS: absent | draft | accepted | revoked | blocked
WORKSPACE_IDENTITY_REF:
WORKSPACE_TYPE: package_repo | project_workspace | implementation_repo | test_fixture
PROJECT_NAME:
PROJECT_SLUG:
PROJECT_ROOT_EXPECTED:
GIT_TOPLEVEL_ACTUAL:
```

## Repository target

```text
EXPECTED_REMOTE:
ACTUAL_REMOTE:
EXPECTED_GIT_REMOTE:
ACTUAL_GIT_REMOTE:
EXPECTED_BRANCH:
ACTUAL_BRANCH:
APPROVED_SSH_HOST_ALIASES:
SSH_ALIAS_EVIDENCE:
```

The lock must compare `EXPECTED_GIT_REMOTE` and `ACTUAL_GIT_REMOTE` as
canonical repository identities. Raw remote strings are evidence only.

## Checkpoint policy

```text
PUSH_ALLOWED: false
LOCAL_ONLY_CHECKPOINT_ALLOWED: no | yes
CHECKPOINT_ELIGIBILITY: blocked | local_only | push_allowed | not_applicable
CHECKPOINT_POLICY: forbidden | local_only | commit_and_push | no_checkpoint
CHECKPOINT_BLOCKED_BY:
```

Push may be allowed only when all conditions are true:

```text
- LOCK_STATUS: accepted
- PUSH_ALLOWED: true
- WORKSPACE_TYPE is not test_fixture
- EXPECTED_GIT_REMOTE equals ACTUAL_GIT_REMOTE after canonicalization
- EXPECTED_BRANCH equals ACTUAL_BRANCH
- approved SSH host aliases are explicitly accepted or proven to resolve to github.com
- identity leakage check has passed
- checkpoint validation for the audited task has passed
```

If the canonical repository identity or branch does not match, push is
forbidden. Commit is also forbidden unless a governed local-only checkpoint is
explicitly allowed by this lock and by the active task packet.

## Acceptance record

```text
LOCK_ACCEPTED_BY:
LOCK_ACCEPTED_AT:
LOCK_ACCEPTANCE_REF:
VALIDATION_EVIDENCE:
LAST_VALIDATED_AT:
LAST_VALIDATION_STATUS: not_checked | passed | failed | blocked
LAST_VALIDATION_ERROR: NONE | repository_identity_mismatch | repository_branch_mismatch | workspace_identity_leakage | unapproved_ssh_host_alias | repository_lock_missing | push_without_repository_lock
```

## Revocation

```text
LOCK_REVOKED_BY:
LOCK_REVOKED_AT:
LOCK_REVOCATION_REASON:
```

When a lock is absent, draft, revoked, blocked, stale, or contradicted by
current Git/runtime evidence, `PUSH_ALLOWED` is treated as `false` regardless of
the value stored in older runtime records.
