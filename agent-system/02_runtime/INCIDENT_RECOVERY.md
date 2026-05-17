# INCIDENT_RECOVERY

## Purpose

This document defines the governed `incident_recovery` protocol for material
workflow, checkpoint, repository, filesystem, secret, runtime, and audit
incidents.

Incident recovery is stricter than ordinary correction. It freezes normal
dispatch and Git checkpoint activity until the incident is classified, bounded,
corrected through authorized routes, and validated for resume.

## Incident classes

The orchestrator must classify these incident classes deterministically:

```text
wrong_remote_push
wrong_branch_push
invalid_task_packet_commit
forbidden_files
secret_exposure
runtime_corruption
audit_false_pass
```

These class names are incident identifiers, not profile-agent RESULT
`STATUS` values.

## Incident entry criteria

Enter incident recovery when any of the following is detected before, during,
or after checkpoint:

- a commit or push reached a remote other than the accepted repository lock
  target (`wrong_remote_push`);
- a commit or push reached a branch other than the accepted repository lock
  branch (`wrong_branch_push`);
- a checkpoint committed a malformed, superseded, deprecated, proposal-only, or
  otherwise invalid dispatchable task packet (`invalid_task_packet_commit`);
- a RESULT, audit pass, checkpoint, or commit includes files outside the active
  task packet allowed scope (`forbidden_files`);
- a secret, credential, token, cookie, private key, local environment value, or
  similarly sensitive artifact was read, printed, staged, committed, pushed, or
  recorded (`secret_exposure`);
- runtime files are missing, contradictory, manually corrupted, or fail schema
  or transition validation in a way that makes routing unsafe
  (`runtime_corruption`);
- checkpoint preflight or another deterministic governance check finds a
  blocker after auditor `STATUS: pass` for a check the auditor was required to
  perform (`audit_false_pass`).

## Incident freeze

When incident recovery starts, the orchestrator must set or preserve a freeze
state equivalent to:

```text
PROJECT_STATUS: blocked
CURRENT_PHASE: correction
CURRENT_GATE.STATUS: blocked
NEXT_ACTION.ACTION_TYPE: correction | wait_for_owner | update_state | stop | create_agent
```

During incident freeze:

- normal project `create_agent`, `route_result`, `finalize`, checkpoint,
  commit, and push are forbidden;
- wrong remote, wrong branch, and secret exposure incidents always block
  further push;
- dependent work remains blocked;
- checkpoint preflight cannot be retried as a bypass for the incident;
- secret values must not be printed, copied, summarized, or written into logs,
  RESULTs, task packets, or runtime files;
- owner decisions are required for remote-side remediation, history handling,
  or secret rotation when those actions are outside orchestrator authority;
- file-changing correction requires a full correction task packet, a fresh
  profile-agent context, independent audit, and checkpoint preflight before any
  later commit or push.

## Orchestrator correction boundary

The orchestrator may coordinate incident recovery only by:

- rereading runtime and governance files;
- classifying the incident without guessing business or technical intent;
- recording redacted runtime events and blocker state;
- setting `NEXT_ACTION` to a governed correction, owner wait, update_state, or
  stop route permitted by transition rules;
- selecting or routing an already-governed full bounded correction task packet,
  or requesting owner/designer creation when a required correction packet is
  missing;
- dispatching a fresh profile agent only when the correction task packet,
  filesystem governance, transition rules, and freeze rules permit it.

The orchestrator must not directly repair profile-agent artifacts. It must not
edit project docs, task packets, package docs, source code, committed content,
or profile RESULTs as a silent repair. The only direct writes available to the
orchestrator during incident recovery are governed runtime/routing metadata
updates and redacted event records.

## TASK_PACKET: NONE restriction

`TASK_PACKET_NONE_FILE_CHANGES_FORBIDDEN`

`TASK_PACKET: NONE` is allowed only for pure coordination or
orchestrator-owned runtime operations that do not change project, package,
implementation, task-packet, profile-result, or other non-runtime artifacts.

Allowed `TASK_PACKET: NONE` incident routes are limited to:

- `wait_for_owner` for an owner-facing decision or blocker;
- governed `update_state` that records runtime freeze, blocker, resume, or log
  metadata;
- governed `stop` when stop invariants permit it;
- non-dispatch `correction` routing that prepares a later full correction task
  packet without changing non-runtime files.

`TASK_PACKET: NONE` is forbidden when the correction will create, edit, delete,
restore, revert, redact, or replace files outside orchestrator-owned runtime
state. Any file-changing correction of profile artifacts, task packets,
package files, project documentation, implementation files, committed content,
or secret-containing artifacts requires a full correction task packet.

## Class-specific recovery

### wrong_remote_push

Required handling:

- freeze normal dispatch, checkpoint, commit, and push;
- record expected remote, actual remote, branch, commit hash if available, and
  affected file list without secret values;
- do not rewrite remote history or push a compensating commit without a
  separate owner-authorized recovery path;
- require owner decision for remote-side remediation when the wrong remote is
  outside the accepted repository lock;
- resume only after repository identity and repository lock validate, owner
  remediation decision is recorded, and any file-changing correction has passed
  audit and checkpoint preflight.

### wrong_branch_push

Required handling:

- freeze normal dispatch, checkpoint, commit, and push;
- record expected branch, actual branch, remote, commit hash if available, and
  affected file list without secret values;
- do not push again to the wrong branch;
- require owner decision for branch-side remediation when remote history or
  branch protection behavior is involved;
- resume only after expected branch and repository lock validate, owner
  remediation decision is recorded, and any file-changing correction has passed
  audit and checkpoint preflight.

### invalid_task_packet_commit

Required handling:

- freeze normal dispatch and checkpoint;
- mark the committed task packet as invalid for dispatch until corrected;
- block any dependent task that would use the invalid task packet;
- create a full correction task packet for any file-changing repair,
  supersession, or replacement;
- resume only after the corrected task packet passes task packet validation,
  independent audit, and checkpoint preflight.

### forbidden_files

Required handling:

- freeze normal dispatch and checkpoint;
- record the forbidden path list and the task packet allowed scope;
- reject acceptance of the affected RESULT or checkpoint;
- require a full correction task packet for removal, revert, relocation, or
  replacement of forbidden files;
- resume only after changed-file scope validation and independent audit pass.

### secret_exposure

Required handling:

- freeze normal dispatch, checkpoint, commit, and push;
- stop printing, copying, or quoting the secret value immediately;
- record only redacted references, affected paths, and validator evidence;
- require owner-controlled secret rotation or revocation when a real secret may
  have been exposed;
- require a full correction task packet for redaction or removal from files;
- resume only after redacted correction evidence, secret scan pass, independent
  audit pass, and any required owner security decision.

### runtime_corruption

Required handling:

- freeze normal dispatch and checkpoint;
- reread all runtime files and validate the full runtime tuple;
- use governed `update_state` only for orchestrator-owned runtime/routing
  metadata repair permitted by transition rules;
- require a full correction task packet when repairing package templates,
  project artifacts, task packets, or profile outputs;
- resume only after runtime schema, transition, filesystem, identity, and
  repository lock validation pass.

### audit_false_pass

Required handling:

- record `AUDIT_FALSE_PASS_DETECTED`;
- classify the correction input as `FAILURE_TYPE: audit_miss`;
- freeze normal dispatch, staging, commit, and push;
- block dependent work and requester continuation;
- require a full correction task packet for any file-changing correction;
- resume only after correction RESULT, independent audit pass, and checkpoint
  preflight validate the previously missed check.

## Resume criteria

Incident freeze exits only when all applicable criteria are satisfied:

- the incident class is recorded with redacted evidence;
- affected task, RESULT, audit, checkpoint, commit, remote, branch, and path
  references are traceable when available;
- active dependent work remains blocked until correction acceptance;
- required owner decisions are recorded for wrong remote, wrong branch, secret
  exposure, remote history, or unrecoverable state;
- file-changing corrections used full task packets and passed independent
  audit;
- checkpoint preflight passes after correction for changed-file scope, task
  packet validity, runtime schema, repository identity, branch, repository
  lock, and secret scan as applicable;
- runtime state validates under `RUNTIME_STATE_SCHEMA.md` and
  `STATE_TRANSITION_RULES.md`;
- `NEXT_ACTION` is regenerated from validated runtime files, not memory;
- no unresolved `AUDIT_FALSE_PASS_DETECTED`, `wrong_remote_push`,
  `wrong_branch_push`, `invalid_task_packet_commit`, `forbidden_files`,
  `secret_exposure`, or `runtime_corruption` blocker remains active.
