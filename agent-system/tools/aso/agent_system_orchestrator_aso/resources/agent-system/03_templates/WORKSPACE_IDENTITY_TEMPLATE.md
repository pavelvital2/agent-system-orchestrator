# WORKSPACE_IDENTITY

## Purpose

This template declares the workspace/repository identity that the orchestrator
must validate before runtime initialization, profile-agent dispatch, checkpoint,
commit, or push.

The orchestrator must compare canonical repository identity, not only raw Git
remote strings. Equivalent raw remotes are acceptable only when they normalize
to the same canonical repository identity under
`agent-system/09_validators/WORKSPACE_IDENTITY_VALIDATION_RULES.md`.

## Workspace identity

```text
PROJECT_NAME:
PROJECT_SLUG:
WORKSPACE_TYPE: package_repo | project_workspace | implementation_repo | test_fixture
PROJECT_ROOT_EXPECTED:
GIT_TOPLEVEL_ACTUAL:
WORKSPACE_IDENTITY_STATUS: not_checked | passed | failed | blocked
```

## Repository identity

Raw remote fields preserve the configured values. Canonical Git remote fields
store the normalized identity used for comparison.

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

`EXPECTED_GIT_REMOTE` and `ACTUAL_GIT_REMOTE` use this canonical form:

```text
github.com/<owner>/<repo>
```

## Repository lock

```text
REPOSITORY_LOCK_REF:
REPOSITORY_LOCK_STATUS: absent | draft | accepted | revoked | blocked
PUSH_ALLOWED: false
PUSH_ALLOWED_REASON:
LOCAL_ONLY_CHECKPOINT_ALLOWED: no | yes
CHECKPOINT_ELIGIBILITY: blocked | local_only | push_allowed | not_applicable
CHECKPOINT_BLOCKED_BY:
```

`PUSH_ALLOWED` defaults to `false`. It may be `true` only after an accepted
repository lock validates the canonical repository identity, branch, workspace
type, and identity leakage checks for the current action.

## Workspace type behavior

```text
package_repo:
  The universal agent-system package repository. Package updates may change
  agent-system files only through owner-authorized package-governance tasks.
  Push remains forbidden until the repository lock is accepted.

project_workspace:
  A project orchestration workspace containing project-input, project-runtime,
  project-docs, and package instructions. It must not inherit repository
  identity from a copied package checkout. Push remains forbidden unless an
  accepted repository lock explicitly authorizes the project workspace target.

implementation_repo:
  A product/source implementation repository. Code changes must validate
  against the implementation repository identity and branch before checkpoint.
  Push remains forbidden until the repository lock is accepted.

test_fixture:
  A fixture or disposable validation workspace. PUSH_ALLOWED must remain false.
  It must not be used as an active package repo, project workspace, or
  implementation repo.
```

## Accepted equivalent remote forms

These raw remote forms are equivalent when owner/repo normalize to the same
canonical GitHub repository identity:

```text
https://github.com/OWNER/REPO
https://github.com/OWNER/REPO.git
git@github.com:OWNER/REPO.git
git@<approved_ssh_host_alias>:OWNER/REPO.git
```

An SSH host alias is approved only when either:

```text
- the alias is explicitly listed in APPROVED_SSH_HOST_ALIASES and accepted in
  the repository lock; or
- SSH_ALIAS_EVIDENCE proves that the alias resolves to hostname github.com.
```

No other raw remote form is equivalent by default.

## Identity leakage check

```text
README_IDENTITY:
RUNTIME_IDENTITY:
MANIFEST_IDENTITY:
GIT_IDENTITY:
LEAKAGE_CHECK_STATUS: not_checked | passed | failed | blocked
LEAKAGE_CONFLICTS:
```

If README, runtime state, workspace identity manifest, repository lock, Git
remote, Git branch, or workspace type identify different projects or
repositories, the orchestrator must classify the condition as
`workspace_identity_leakage` and block dispatch, checkpoint, commit, and push
until governed correction resolves the conflict.

## Required validation result

```text
IDENTITY_VALIDATION_STATUS: not_checked | passed | failed | blocked
IDENTITY_VALIDATION_ERROR: NONE | repository_identity_mismatch | repository_branch_mismatch | workspace_identity_leakage | unapproved_ssh_host_alias | missing_identity_manifest | repository_lock_missing | push_without_repository_lock
IDENTITY_VALIDATION_EVIDENCE:
VALIDATED_AT:
VALIDATED_BY: orchestrator
```
