# CHECKPOINT_ELIGIBILITY

## Purpose

This template defines the deterministic receipt that separates audit pass from
checkpoint eligibility.

Auditor `STATUS: pass` is required before this receipt can be eligible, but it
does not by itself authorize `git add`, `git commit`, or `git push`.

## Receipt path

```text
project-runtime/checkpoints/CHECKPOINT_ELIGIBILITY_<TASK_ID>_<ATTEMPT_NO>.md
```

The orchestrator owns this receipt. Profile agents must not create, edit,
commit, or push checkpoint receipts.

## Required fields

```text
RECEIPT_ID:
TASK_ID:
ATTEMPT_NO:
CREATED_AT:
CREATED_BY: orchestrator
TASK_PACKET:
ACCEPTED_RESULT_REF:
AUDIT_REF:
AUDIT_STATUS: not_applicable | pending | passed | failed | blocked | gap
CHECKPOINT_POLICY: forbidden | local_only | commit_and_push | no_checkpoint
CHECKPOINT_ELIGIBILITY_STATUS: not_checked | eligible | ineligible | blocked
CHECKPOINT_PREFLIGHT_STATUS: not_run | passed | failed | blocked
CHECKPOINT_PREFLIGHT_REF:
WORKSPACE_TYPE: package_repo | project_workspace | implementation_repo | test_fixture
IDENTITY_CHECK_STATUS: not_checked | passed | failed | blocked
GIT_TARGET_CHECK_STATUS: not_checked | matched | mismatched | blocked | not_required
FILE_SCOPE_CHECK_STATUS: not_checked | passed | failed | blocked
TASK_PACKET_SCHEMA_STATUS: not_checked | passed | failed | blocked
RUNTIME_SCHEMA_STATUS: not_checked | passed | failed | blocked
SECRET_SCAN_STATUS: not_checked | passed | potential_secret_exposure | blocked
COMMIT_STATUS: not_required | not_attempted | committed | failed | blocked
COMMIT_HASH:
COMMIT_BRANCH:
PUSH_STATUS: not_required | not_attempted | pushed | failed | blocked
PUSH_REMOTE:
PUSH_BRANCH:
LAST_PUSH_TARGET_STATUS: not_checked | matched | mismatched | blocked | not_required
PROJECT_CHECKPOINT_STATUS: not_required | pending | passed | failed | blocked
ACCEPTED_FILES:
BLOCKED_BY:
FAILURE_REASON_REDACTED:
RECOVERY_ROUTE:
```

## Status rules

- `CHECKPOINT_ELIGIBILITY_STATUS: eligible` is valid only when
  `AUDIT_STATUS: passed`, all preflight checks pass, and any requested push
  target is matched.
- `CHECKPOINT_ELIGIBILITY_STATUS: ineligible` means the audit may have passed,
  but checkpoint, commit, or push is currently forbidden.
- `CHECKPOINT_ELIGIBILITY_STATUS: blocked` means recovery, owner input, or a
  governed correction is required before another checkpoint attempt.
- `SECRET_SCAN_STATUS: potential_secret_exposure` must block staging, commit,
  and push.
- `PROJECT_CHECKPOINT_STATUS: passed` is valid only after commit succeeds and
  push is either completed or not required by checkpoint policy.

## Evidence rules

Receipt evidence must identify only paths, field names, validator names,
status values, and redacted risk classes. It must not include secret values,
credential values, cookie values, private key material, or local environment
contents.
