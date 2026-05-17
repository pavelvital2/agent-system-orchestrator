# WORKSPACE_IDENTITY_VALIDATION_RULES

## Purpose

These documentation-level validation rules define the workspace identity gate
for v2.0.0. They are enforceable governance rules even when no executable
validator script is available in the current environment.

The gate must run before:

```text
- runtime initialization
- profile-agent dispatch
- checkpoint
- commit
- push
```

## Required inputs

```text
WORKSPACE_IDENTITY_REF
REPOSITORY_LOCK_REF
PROJECT_NAME
PROJECT_SLUG
WORKSPACE_TYPE
PROJECT_ROOT_EXPECTED
GIT_TOPLEVEL_ACTUAL
EXPECTED_REMOTE
ACTUAL_REMOTE
EXPECTED_GIT_REMOTE
ACTUAL_GIT_REMOTE
EXPECTED_BRANCH
ACTUAL_BRANCH
APPROVED_SSH_HOST_ALIASES
SSH_ALIAS_EVIDENCE
PUSH_ALLOWED
```

Missing required identity input is a hard blocker:

```text
missing_identity_manifest
```

## Canonical repository identity

Validators must compare canonical repository identity, not raw remote strings.

Canonical GitHub repository identity:

```text
github.com/<owner>/<repo>
```

Normalization rules:

```text
1. Trim surrounding whitespace.
2. Strip a trailing `.git` suffix.
3. Convert the host segment to lowercase.
4. For GitHub remotes, compare owner and repository segments by canonical
   repository identity, not by raw URL spelling.
5. Preserve the raw remote strings as evidence only.
```

Accepted equivalent raw remote forms:

```text
https://github.com/OWNER/REPO
https://github.com/OWNER/REPO.git
git@github.com:OWNER/REPO.git
git@<approved_ssh_host_alias>:OWNER/REPO.git
```

An SSH host alias is valid only when one of these is true:

```text
- the alias is explicitly listed in APPROVED_SSH_HOST_ALIASES and accepted by
  the current repository lock; or
- SSH_ALIAS_EVIDENCE proves the alias resolves to hostname github.com.
```

Evidence may include a bounded command summary such as:

```text
ssh -G <alias> -> hostname github.com
```

Do not print private keys, tokens, cookies, or secret values while collecting
alias evidence.

## Validation order

1. Verify that `WORKSPACE_IDENTITY_REF` exists or that initialization is using
   `agent-system/03_templates/WORKSPACE_IDENTITY_TEMPLATE.md`.
2. Verify all required workspace identity fields are present.
3. Verify `WORKSPACE_TYPE` is one of:
   `package_repo`, `project_workspace`, `implementation_repo`, `test_fixture`.
4. Verify `PROJECT_ROOT_EXPECTED` and `GIT_TOPLEVEL_ACTUAL` match, unless a
   governed initialization correction explicitly records why they differ.
5. Parse `EXPECTED_REMOTE` and `ACTUAL_REMOTE`.
6. Normalize both remotes to `EXPECTED_GIT_REMOTE` and `ACTUAL_GIT_REMOTE`.
7. If an SSH host alias is used, validate explicit acceptance or
   `SSH_ALIAS_EVIDENCE`.
8. Compare canonical repository identities.
9. Compare `EXPECTED_BRANCH` and `ACTUAL_BRANCH`.
10. Validate workspace type behavior.
11. Run identity leakage checks across README, runtime state, manifest, Git
    remote, Git branch, and workspace type.
12. Validate repository lock and `PUSH_ALLOWED` before any push.

## Hard blockers

```text
repository_identity_mismatch:
  EXPECTED_GIT_REMOTE and ACTUAL_GIT_REMOTE do not identify the same canonical
  repository.

repository_branch_mismatch:
  EXPECTED_BRANCH and ACTUAL_BRANCH do not match.

unapproved_ssh_host_alias:
  ACTUAL_REMOTE uses git@<alias>:OWNER/REPO.git, but the alias is not accepted
  in the repository lock and lacks evidence that it resolves to github.com.

workspace_identity_leakage:
  README, runtime state, manifest, repository lock, Git remote, Git branch, or
  workspace type identify conflicting projects or repositories.

repository_lock_missing:
  A checkpoint, commit, or push requires a repository lock, but no valid lock is
  accepted for the current workspace identity.

push_without_repository_lock:
  PUSH_ALLOWED is true without an accepted repository lock, or a push is planned
  while PUSH_ALLOWED is false.
```

## Consequences

When any hard blocker is present:

```text
- profile-agent dispatch is forbidden;
- checkpoint is forbidden;
- push is forbidden;
- commit is forbidden unless an explicit governed local-only checkpoint is
  allowed by the repository lock and active task packet;
- NEXT_ACTION must route to correction, wait_for_owner, governed update_state,
  or governed stop when stop invariants allow it.
```

## Workspace type rules

```text
package_repo:
  EXPECTED_GIT_REMOTE must identify the package repository declared by the
  owner-authorized package manifest. agent-system changes require a bounded
  package-governance task. Push requires accepted repository lock.

project_workspace:
  Runtime and project docs are governed workspace artifacts. The orchestrator
  must not infer identity from a copied `.git` directory. Push requires
  accepted repository lock.

implementation_repo:
  Implementation changes require repository and branch match for the product
  source repository. Push requires accepted repository lock.

test_fixture:
  PUSH_ALLOWED must be false. Fixture identity cannot authorize package,
  project workspace, or implementation repo checkpoint.
```

## Validation output

The identity gate must produce or preserve bounded evidence:

```text
IDENTITY_VALIDATION_STATUS: passed | failed | blocked
IDENTITY_VALIDATION_ERROR: NONE | repository_identity_mismatch | repository_branch_mismatch | workspace_identity_leakage | unapproved_ssh_host_alias | missing_identity_manifest | repository_lock_missing | push_without_repository_lock
IDENTITY_VALIDATION_EVIDENCE:
```
