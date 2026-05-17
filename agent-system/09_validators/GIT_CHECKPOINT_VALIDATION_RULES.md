# GIT_CHECKPOINT_VALIDATION_RULES

## Purpose

This document defines documentation-first validation rules for post-audit Git
checkpoint attempts.

Git checkpoint validation applies before staging, committing, and pushing.
It also requires committed `HEAD` validation after commit and before push. It
may be enforced by the package preflight script or by an equivalent governed
validator.

## Source documents

```text
agent-system/02_runtime/STATE_TRANSITION_RULES.md
agent-system/02_runtime/POST_AUDIT_GIT_CHECKPOINT.md
agent-system/02_runtime/ACCEPTED_STATE_LOCKING.md
agent-system/02_runtime/FILESYSTEM_GOVERNANCE.md
agent-system/03_templates/CHECKPOINT_ELIGIBILITY_TEMPLATE.md
agent-system/04_state/TASK_REGISTRY_TEMPLATE.md
agent-system/04_state/ACCEPTED_ARTIFACTS_TEMPLATE.md
agent-system/06_logs/ORCHESTRATOR_EVENTS_LOG_TEMPLATE.md
agent-system/09_validators/CHANGED_FILES_SCOPE_MATRIX.md
agent-system/09_validators/TASK_PACKET_SCHEMA_VALIDATION_RULES.md
agent-system/09_validators/SECRET_SCAN_RULES.md
agent-system/scripts/checkpoint_preflight.sh
agent-system/scripts/validate_task_packet.py
```

## Checkpoint preconditions

A Git checkpoint is valid only when all conditions are true:

- the immediately preceding required audit returned `STATUS: pass`;
- the audited task result is within scope;
- no required audit failed for the same work;
- no correction is pending for the same work;
- changed files match the task packet `ALLOWED_FILE_CHANGES`;
- no changed file matches `FORBIDDEN_FILE_CHANGES`;
- no suspected secret or credential file is staged;
- runtime state does not contain active blockers or GAPs that block the
  checkpointed work.
- accepted files can be listed without reading or printing secret values;
- working-tree validation for accepted task-specific invariants has passed.
- syntax evidence exists for executable script changes: changed `.sh` files
  have passing `bash -n <path>` evidence, and changed `.py` files have passing
  `python3 -m py_compile <path>` evidence;
- changed dispatchable task packet files pass task packet schema validation
  before staging;
- changed `TASK_PROPOSAL` files pass proposal validation and remain
  non-dispatchable before staging;
- design audit acceptance for changed downstream task-like artifacts includes
  validation evidence before checkpoint eligibility is granted;
- `CHECKPOINT_ELIGIBILITY_STATUS: eligible` is recorded separately from
  `AUDIT_STATUS`;
- `CHECKPOINT_PREFLIGHT_STATUS: passed` is recorded with a bounded preflight
  reference.
- `CHECKPOINT_PREFLIGHT_REF` identifies an executable
  `agent-system/scripts/checkpoint_preflight.sh` invocation or saved receipt;
  manual descriptions are insufficient.
- critical baseline paths are tracked, or an explicit owner policy records the
  allowed exception.
- auditor evidence contains passing `CHANGED_FILES_SCOPE_STATUS`,
  `TASK_PACKET_SCHEMA_STATUS`, `SECRET_EXPOSURE_STATUS`,
  `REPOSITORY_IDENTITY_STATUS`, `FORBIDDEN_PATH_STATUS`,
  `RUNTIME_MUTATION_STATUS`, and `REASONING_LEVEL_COMPLIANCE` where applicable.
- auditor evidence contains `SYNTAX_EVIDENCE_STATUS: passed` when executable
  shell or Python files changed, or `SYNTAX_EVIDENCE_STATUS: not_applicable`
  when no such files changed.

## Forbidden checkpoint attempts

Checkpoint is forbidden after:

- profile-agent pass without required audit pass;
- audit fail;
- audit blocked;
- audit gap;
- invalid RESULT shape;
- invalid task packet;
- invalid downstream dispatchable task packet;
- ambiguous or unvalidated downstream task artifact created by accepted design
  output;
- `TASK_PROPOSAL` selected as a dispatchable task packet;
- invalid runtime tuple;
- direct progress after audit fail;
- unverified correction result;
- failed working-tree validation for accepted task-specific invariants;
- missing, stale, or failed syntax evidence for changed shell or Python
  scripts;
- failed committed `HEAD` validation for accepted task-specific invariants.
- `CHECKPOINT_ELIGIBILITY_STATUS` is `not_checked`, `ineligible`, or
  `blocked`;
- `SECRET_SCAN_STATUS: potential_secret_exposure`;
- missing checkpoint eligibility receipt for a local-only or commit-and-push
  checkpoint.
- manual preflight references such as `orchestrator manual preflight <date>`;
- untracked critical baseline paths without explicit policy exception;
- bootstrap results missing a valid downstream task packet, explicit GAP,
  explicit BLOCKED route, or explicit wait_for_owner route;
- unresolved `AUDIT_FALSE_PASS_DETECTED`;
- pending correction with `FAILURE_TYPE: audit_miss`.

## Required checkpoint preflight

Before staging any file, checkpoint preflight must deterministically evaluate
these checks in order:

```text
1. identity_check
2. git_target_check
3. baseline_tracking_check
4. changed_files_scope_check
5. task_packet_schema_check
6. runtime_schema_check
7. secret_scan_check
```

Preflight evidence must record these status labels:

```text
CHANGED_FILES_SCOPE_STATUS: not_checked | passed | failed | blocked
TASK_PACKET_SCHEMA_STATUS: not_checked | passed | failed | blocked | not_applicable
SECRET_EXPOSURE_STATUS: not_checked | passed | potential_secret_exposure | blocked
```

Any `failed`, `blocked`, `not_checked` after a required check, or
`potential_secret_exposure` status blocks checkpoint before `git add`.

The preflight may be implemented by:

```text
agent-system/scripts/checkpoint_preflight.sh
```

or by an equivalent governed validator that produces the same receipt fields.

The receipt must use this template:

```text
agent-system/03_templates/CHECKPOINT_ELIGIBILITY_TEMPLATE.md
```

Receipt path convention:

```text
project-runtime/checkpoints/CHECKPOINT_ELIGIBILITY_<TASK_ID>_<ATTEMPT_NO>.md
```

Checkpoint preflight passes only when all of the following are true:

- workspace identity status passed;
- canonical expected and actual Git remotes match;
- expected and actual branches match;
- actual Git remote, branch, and toplevel are read from live Git commands for
  real repository checks, not trusted from cached runtime `ACTUAL_*` fields;
- no critical baseline path is untracked without explicit owner policy;
- push target is not required, or `LAST_PUSH_TARGET_STATUS: matched`;
- changed files are allowed by task packet scope and
  `CHANGED_FILES_SCOPE_MATRIX.md`;
- newly created files intended for checkpoint are included in file-scope and
  secret checks before they are staged;
- task packet has required schema sections and is active;
- every changed downstream `# TASK PACKET` artifact has required schema
  sections before staging;
- every changed downstream `TASK_*.md` artifact is explicitly classified as a
  dispatchable `TASK_PACKET` or non-dispatchable `TASK_PROPOSAL`;
- every changed `TASK_PROPOSAL` artifact conforms to
  `TASK_PROPOSAL_TEMPLATE.md` and remains non-dispatchable;
- any task schema failure is reported as `invalid_task_packet_schema`;
- runtime schema contains mandatory checkpoint distinction fields;
- secret scan returns no `potential_secret_exposure`.
- syntax evidence for changed `.sh` and `.py` files is present and passing
  before checkpoint eligibility is granted.
- bootstrap continuation status is present and valid before a bootstrap
  checkpoint is accepted.

If checkpoint preflight detects a blocker after auditor `STATUS: pass` and the
blocker belongs to changed file scope, task packet schema, repository identity,
forbidden path, runtime mutation, required evidence, secret exposure, or
reasoning-level compliance, the orchestrator must record:

```text
AUDIT_FALSE_PASS_DETECTED
FAILURE_TYPE: audit_miss
```

This condition blocks staging, commit, push, and normal next-task dispatch until
a bounded correction passes its own audit and checkpoint preflight.

## Allowed and forbidden file checks

Before staging, compare changed paths against:

```text
ALLOWED_FILE_CHANGES
FORBIDDEN_FILE_CHANGES
FILESYSTEM_GOVERNANCE
CHANGED_FILES_SCOPE_MATRIX
```

Invalid checkpoint conditions:

- path outside task packet allowed scope;
- path inside task packet forbidden scope;
- ordinary project task changed `agent-system/`;
- profile agent changed `project-runtime/`;
- auditor changed files without explicit correction authority;
- archive/deprecated source modified as active work;
- accepted artifact modified outside a governed task.

## Secret-safety checks

Before staging or committing, the orchestrator must verify that the checkpoint
does not include:

- credential files;
- token files;
- private keys;
- cookies;
- `.env` values;
- command outputs containing secret values;
- unredacted secret material in RESULT, logs, docs, or runtime state.
- HAR/devtools dumps, session material, or browser profile artifacts;
- any finding classified as `potential_secret_exposure`.

Validators must not print suspected secret values. Evidence must identify only
the path, field, or redacted class of issue.

## Commit message checks

Commit message must be consistent with the accepted task and must not include:

- secret values;
- unrelated task IDs;
- project-specific credentials or environment data;
- claims of audit pass when audit did not pass.

## Push checks

Push is valid only after the local commit is valid.

Push must not proceed when:

- checkpoint preconditions fail;
- `LAST_PUSH_TARGET_STATUS` is not `matched`;
- working tree contains out-of-scope staged changes;
- secret-safety checks fail;
- audit pass is missing;
- correction remains pending for the committed work;
- committed `HEAD` content has not been validated against the same accepted
  task-specific invariants checked before commit;
- committed `HEAD` validation fails.

## Required checkpoint outputs

Successful checkpoint validation must ensure the checkpoint records:

- accepted task id;
- accepted result reference;
- audit reference;
- audit status;
- checkpoint eligibility status;
- checkpoint preflight status and reference;
- checkpoint receipt reference;
- accepted files;
- branch;
- commit status;
- commit hash;
- push remote and branch when push is attempted;
- last push target status;
- project checkpoint status;
- working-tree validation reference;
- committed `HEAD` validation reference;
- push status.

`PUSH_STATUS: pushed` requires a valid local commit hash and a completed push.

`STATUS: checkpoint_done` in the task registry is invalid unless commit hash,
branch, commit status, push status appropriate to checkpoint policy, accepted
files, and checkpoint reference are recorded.

## Recovery

If checkpoint validation fails:

- do not stage additional files;
- do not commit;
- do not push;
- log the validation failure without secret values;
- route to correction or owner handling according to governance.

If checkpoint validation fails because of `AUDIT_FALSE_PASS_DETECTED`, the
correction input must use `FAILURE_TYPE: audit_miss`, reference the audit and
preflight evidence, and must not commit or push as part of the failed
checkpoint attempt.

If commit fails:

- do not push;
- log a checkpoint failure with `PUSH_STATUS: not_attempted`;
- route to governed correction or owner handling.

If push fails:

- keep the local commit hash traceable if available;
- log a checkpoint failure with `PUSH_STATUS: failed`;
- route to governed correction or owner handling.

If secret or credential risk is detected:

- do not stage additional files;
- do not commit;
- do not push;
- log only a redacted risk class and affected path or field;
- route to governed correction or owner handling.
