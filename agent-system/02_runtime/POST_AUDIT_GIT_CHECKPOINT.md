# POST_AUDIT_GIT_CHECKPOINT

## Purpose

This document defines the universal post-audit Git checkpoint gate.

The gate is executed only by the orchestrator after a required auditor result
has passed. It records accepted package or project state in Git and then routes
the runtime to the next governed task.

## Authority

The orchestrator may run Git checkpoint commands only inside this gate and only
after all preconditions pass.

Profile agents never commit or push. Task packets cannot grant commit or push
authority to profile agents.

Auditor `STATUS: pass` is necessary but not sufficient for commit or push. The
orchestrator must derive a separate `CHECKPOINT_ELIGIBILITY_STATUS` through
deterministic checkpoint preflight before staging any file.

Research dependency results follow the same audit-pass checkpoint rule. If a
research dependency task requires checkpointing, requester continuation may be
marked ready only after the independent auditor passes and this checkpoint
completes successfully.

The orchestrator must not inspect, print, copy, modify, stage, commit, or push
credentials, secret values, token values, private keys, cookies, or local
environment files.

## Required preconditions

A post-audit Git checkpoint may start only when all conditions are true:

- the immediately preceding required audit exists;
- the immediately preceding required audit returned `STATUS: pass`;
- the audited task result is formally valid;
- the audited task result is accepted by the auditor;
- no audit `fail`, `blocked`, or `gap` result exists for the same accepted
  work without a later governed correction and audit pass;
- changed files match the task packet `ALLOWED_FILE_CHANGES`;
- changed files do not match the task packet `FORBIDDEN_FILE_CHANGES`;
- changed dispatchable task packet files pass
  `TASK_PACKET_SCHEMA_VALIDATION_RULES.md`;
- changed `TASK_PROPOSAL` files pass proposal validation and remain
  non-dispatchable;
- design-audit acceptance evidence exists when the accepted result created or
  changed downstream `TASK_*.md`, `TASK_PROPOSAL*.md`, or
  `*_TASK_PACKET*.md` files;
- runtime state has no active blocker or GAP that blocks the accepted work;
- `AUDIT_STATUS` for the accepted work is `passed`;
- `CHECKPOINT_ELIGIBILITY_STATUS` is `eligible` in a bounded checkpoint
  eligibility receipt;
- checkpoint preflight has passed identity, Git target, changed file scope,
  task packet schema, runtime schema, and secret scan checks;
- working-tree validation for the task-specific invariants passes before
  staging or committing;
- syntax evidence for executable script changes is present and passing before
  staging: changed `.sh` files require `bash -n <path>` evidence, and changed
  `.py` files require `python3 -m py_compile <path>` evidence;
- `GIT_CHECKPOINT_VALIDATION_RULES.md` passes.

## Forbidden conditions

The orchestrator must not stage, commit, or push after:

- profile-agent `STATUS: pass` without the required auditor `STATUS: pass`;
- auditor `STATUS: fail`;
- auditor `STATUS: blocked`;
- auditor `STATUS: gap`;
- formally invalid profile-agent RESULT;
- formally invalid auditor RESULT;
- invalid downstream dispatchable task packet;
- missing design-audit validation evidence for changed downstream task-like
  artifacts;
- ambiguous downstream task artifact classification;
- `TASK_PROPOSAL` selected as a dispatchable task packet;
- reasoning-level dispatch mismatch where requested/configured runner reasoning
  is below the resolved required level;
- pending correction for the same work;
- unaudited research dependency output or research audit fail/blocked/gap when
  requester continuation is waiting;
- suspected secret or credential risk in changed, staged, logged, or generated
  checkpoint material;
- `SECRET_SCAN_STATUS: potential_secret_exposure`;
- missing, stale, or failed syntax evidence for changed shell or Python
  scripts;
- missing or stale checkpoint eligibility receipt;
- `CHECKPOINT_ELIGIBILITY_STATUS` other than `eligible`;
- out-of-scope changed files.

After a reasoning-level mismatch, checkpoint is forbidden. Commit is forbidden
after reasoning-level mismatch, and push is forbidden after reasoning-level
mismatch.

## Required checkpoint preflight

Before `git add`, `git commit`, or `git push`, the orchestrator must run the
checkpoint preflight defined by:

```text
agent-system/09_validators/GIT_CHECKPOINT_VALIDATION_RULES.md
agent-system/09_validators/CHANGED_FILES_SCOPE_MATRIX.md
agent-system/09_validators/TASK_PACKET_SCHEMA_VALIDATION_RULES.md
agent-system/09_validators/SECRET_SCAN_RULES.md
agent-system/scripts/checkpoint_preflight.sh
agent-system/scripts/validate_task_packet.py
```

The preflight must produce a deterministic eligibility receipt based on:

```text
agent-system/03_templates/CHECKPOINT_ELIGIBILITY_TEMPLATE.md
```

Receipt path convention:

```text
project-runtime/checkpoints/CHECKPOINT_ELIGIBILITY_<TASK_ID>_<ATTEMPT_NO>.md
```

The preflight result must set:

```text
AUDIT_STATUS: passed
CHECKPOINT_ELIGIBILITY_STATUS: eligible
CHECKPOINT_PREFLIGHT_STATUS: passed
PROJECT_CHECKPOINT_STATUS: pending
```

Any failed identity, Git target, file scope, task packet schema, runtime
schema, or secret scan check must set `CHECKPOINT_ELIGIBILITY_STATUS:
ineligible` or `blocked`, keep `PROJECT_CHECKPOINT_STATUS: blocked | failed`,
and forbid staging, commit, and push. Secret-related failures must use the
redacted class `potential_secret_exposure` and must not print secret values.

Task packet schema failures must use:

```text
invalid_task_packet_schema
```

For design outputs, the preflight must not compensate for a missing downstream
validation check in the audit. If changed downstream task artifacts were
created or modified, both the auditor acceptance and the checkpoint preflight
must agree that dispatchable packets are valid and proposals are
non-dispatchable.

When the accepted task creates new files, those untracked paths must be included
in file-scope and secret checks before staging.

## ASO-managed evidence Git policy

Stage 1 does not add `aso checkpoint commit`. Without explicit owner
acceptance for that command, checkpoint finalization uses this policy:

- commit accepted package/source changes only from task-allowed package paths;
- commit compact stable release or validation summaries under
  `agent-system/11_release/` only when the task packet owns that evidence;
- keep root-level `project-input/`, `project-runtime/`, and
  `project-archive/` ignored and untracked in the package repository;
- archive runtime receipts and artifacts locally with hashes instead of
  requiring manual `git add -f`;
- exclude owner input, local environments, caches, build output, logs that may
  contain secrets, and secret-like files from staging, stdout, and archives.

Runtime evidence under `project-runtime/` remains valid checkpoint evidence for
preflight and audit routing, but it is not automatically package commit
content. A clean package checkpoint is therefore a commit of accepted
package-owned files plus any stable release summary, with runtime evidence
referenced by path and hash in the RESULT, audit RESULT, checkpoint receipt, or
release summary.

### Runtime evidence disposition

| Evidence class | Default disposition | Examples |
|---|---|---|
| Accepted package/source changes | committed when task-allowed and audited | `README.md`, `agent-system/**`, `.gitignore` |
| Stable release/validation summary | committed when task-owned | `agent-system/11_release/**` |
| Checkpoint receipts and preflight output | archived runtime-only | `project-runtime/checkpoints/**`, `project-runtime/receipts/checkpoints/**` |
| Worker, audit, lifecycle, artifact, and report evidence | archived runtime-only | `project-runtime/results/**`, `project-runtime/agents/**`, `project-runtime/artifacts/**`, `project-runtime/reports/**` |
| Owner input, local environments, caches, build output, and secret-like files | excluded | `project-input/**`, `.venv/**`, `.tox/**`, `dist/**`, `build/**`, `.env*`, `*.pem`, `*.key`, cookies |

### Ignored-root force-add exception

Manual `git add -f` selection is forbidden. If an owner-approved task packet
explicitly requires committing a governed checkpoint file from an ignored root,
the orchestrator must create an exact force-add manifest before staging
anything.

Required force-add manifest path:

```text
project-runtime/checkpoints/FORCE_ADD_MANIFEST_<TASK_ID>_<ATTEMPT_NO>.json
```

Required pathspec path:

```text
project-runtime/checkpoints/FORCE_ADD_PATHSPEC_<TASK_ID>_<ATTEMPT_NO>.nul
```

The manifest must contain:

```text
POLICY_ID: aso_managed_checkpoint_evidence_policy_v1
TASK_ID
AUDIT_REF
CHECKPOINT_PREFLIGHT_REF
OWNER_APPROVAL_REF
COMMAND_ARGV
FORCE_ADD_PATHS
SHA256_BY_PATH
SIZE_BY_PATH
```

The only permitted force-add command shape is:

```text
git add -f --pathspec-from-file=<FORCE_ADD_PATHSPEC> --pathspec-file-nul
```

`FORCE_ADD_PATHS` must be generated from accepted checkpoint state, not from a
human-selected shell list. Each listed path must be workspace-relative, inside
the approved ignored-root evidence set, audited, secret-scanned, and covered by
the manifest hash and size fields. A checkpoint that lacks this manifest, uses
a different force-add command shape, or includes a path not listed in the
manifest is invalid and must route to correction.

## Allowed checkpoint commands

The orchestrator may run only bounded Git commands needed for checkpointing,
for example:

```text
git status
git diff --name-only
git diff --cached --name-only
git add <accepted files only>
git commit -m <accepted task commit message>
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git push
```

After commit and before push, the orchestrator must validate the committed
`HEAD` content against the same accepted task-specific invariants that were
validated in the working tree. Push is forbidden when committed `HEAD` fails
that validation, even if the pre-commit working-tree check passed.

The orchestrator must not run commands that print secret values or inspect
credential stores.

## Required checkpoint record

Every checkpoint attempt must create or update bounded records with:

```text
TASK_ID:
AUDIT_REF:
AUDIT_STATUS:
ACCEPTED_RESULT_REF:
ACCEPTED_FILES:
CHECKPOINT_ELIGIBILITY_STATUS:
CHECKPOINT_PREFLIGHT_STATUS:
CHECKPOINT_PREFLIGHT_REF:
CHECKPOINT_RECEIPT_REF:
BRANCH:
COMMIT_STATUS:
COMMIT_HASH:
PUSH_STATUS: not_required | not_attempted | pushed | failed | blocked
PUSH_REMOTE:
PUSH_BRANCH:
LAST_PUSH_TARGET_STATUS: not_checked | matched | mismatched | blocked | not_required
PROJECT_CHECKPOINT_STATUS: not_required | pending | passed | failed | blocked
CHECKPOINT_STATUS: passed | failed | blocked
WORKING_TREE_VALIDATION_REF:
HEAD_VALIDATION_REF:
FAILURE_REASON:
RECOVERY_ROUTE:
```

For runtime schema `2.0.0` and later, `CHECKPOINT_PREFLIGHT_REF` must identify
an executable preflight invocation or saved receipt/output from
`agent-system/scripts/checkpoint_preflight.sh`. Human-only references such as
`orchestrator manual preflight <date>` are insufficient checkpoint evidence and
must block with:

```text
manual_preflight_ref_insufficient
```

Bootstrap checkpoint eligibility has an additional continuation gate.
`BOOTSTRAP_CONTINUATION_STATUS` must identify a valid downstream task packet,
explicit GAP, explicit BLOCKED route, or explicit wait_for_owner route. Missing
or invalid bootstrap continuation blocks with:

```text
bootstrap_continuation_missing
```

Successful checkpoint records must include:

- commit hash;
- branch name;
- commit status;
- push status;
- push remote and branch when push is attempted;
- last push target status;
- project checkpoint status;
- accepted files;
- accepted task id;
- audit reference;
- working-tree validation reference;
- committed `HEAD` validation reference.

Failed checkpoint records must not include secret values.

## Runtime updates after success

After a successful local-only checkpoint or commit-and-push checkpoint:

- set the task registry entry to `STATUS: checkpoint_done`;
- record `COMMIT_STATUS`, `COMMIT_HASH`, `BRANCH`, `PUSH_STATUS`,
  `PUSH_REMOTE`, `PUSH_BRANCH`, `LAST_PUSH_TARGET_STATUS`,
  `PROJECT_CHECKPOINT_STATUS`, and accepted files;
- update accepted artifact entries with the commit hash;
- append a `checkpoint` event with `STATUS: passed`;
- route only to the next task allowed by `STATE_TRANSITION_RULES.md`.

`PROJECT_CHECKPOINT_STATUS: passed` requires `COMMIT_STATUS: committed` and a
valid `PUSH_STATUS` for the checkpoint policy: `not_required` for local-only,
or `pushed` for commit-and-push.

Future `aso checkpoint` mutation behavior must follow the ordered transaction
contract in `TRANSACTIONAL_CHECKPOINT_SPEC.md`. In particular, after a passed
checkpoint, `CURRENT_GATE` must be closed, `NEXT_ACTION` must be recalculated
away from the same checkpoint, `CHECKPOINT_RECEIPT_REF` must not be `NONE`, and
post-check verification must run over the completed runtime tuple.

## Failure routing

Commit failure:

- do not push;
- log a `checkpoint` event with `STATUS: failed`;
- set `PUSH_STATUS: not_attempted`;
- route to governed correction or owner handling.

Push failure:

- keep the local commit record;
- log a `checkpoint` event with `STATUS: failed`;
- set `PUSH_STATUS: failed`;
- route to governed correction or owner handling.

Secret or credential risk:

- do not stage additional files;
- do not commit;
- do not push;
- log only a redacted secret-risk class and affected path or field;
- route to governed correction or owner handling.

Validation failure:

- do not stage additional files;
- do not commit;
- do not push;
- log validation failure without secret values;
- route according to `GIT_CHECKPOINT_VALIDATION_RULES.md`.
