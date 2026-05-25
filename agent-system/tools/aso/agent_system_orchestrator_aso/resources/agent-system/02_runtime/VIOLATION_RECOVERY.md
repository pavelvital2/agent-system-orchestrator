# VIOLATION_RECOVERY

## Purpose

This document defines deterministic recovery from governance, workflow,
filesystem, runtime-state, incident, GAP, blocked, and manual-intervention
failures.

## General recovery rule

When violation is detected:

```text
PROJECT_STATUS: blocked
CURRENT_PHASE: correction
NEXT_ACTION.ACTION_TYPE: correction
NEXT_ACTION.TARGET_ROLE: orchestrator
```

No new normal project agent dispatch is allowed until the state validates again.

## Violation classification

Profile-agent RESULT `STATUS` is limited to:

```text
pass
fail
blocked
gap
```

`violation` is not a valid profile-agent RESULT `STATUS`.

`violation` is an orchestrator-derived recovery/logging category for governance, workflow, filesystem, runtime-state, forbidden file change, incident recovery, audit false pass, or formally invalid RESULT handling.

When a RESULT is formally invalid, including a missing mandatory field or a `STATUS` outside the profile-agent enum, the orchestrator must not route by RESULT `STATUS`.

Before recovery/reformat routing, the orchestrator must log the invalid RESULT as an orchestrator-classified `violation` entry using the deterministic fallback from `AGENT_RESULTS_LOG_TEMPLATE.md`.

## Recovery table

| Violation | Recovery |
|---|---|
| Missing bootstrap input | `wait_for_owner`; no solution_architect dispatch. |
| Missing runtime file | Create from valid template or freeze if template missing/invalid. |
| Runtime schema violation | Enter correction; regenerate valid runtime state. |
| Schema/template mismatch | Governance freeze until package docs align. |
| Invalid transition | Enter correction; do not dispatch. |
| Forbidden file change | Log RESULT; mark workflow violation; route correction; do not accept. |
| Deprecated doc in REQUIRED_DOCS | Task packet invalid; route to solution_architect/correction. |
| Superseded task selected | Stop dispatch; route to replacing task or correction. |
| Agent RESULT format invalid | Log deterministic `violation` entry; do not route by status; request governed correction/reformat. |
| Agent STATUS gap | Register GAP; block dependent branch; route by GAP type. |
| Agent STATUS blocked | Route by blocker type; do not continue dependent branch. |
| Auditor fail | Checked result not accepted; correction to checked role/solution_architect. |
| Audit false pass after checkpoint preflight | Record `AUDIT_FALSE_PASS_DETECTED`; create correction input with `FAILURE_TYPE: audit_miss`; do not commit or push. |
| wrong_remote_push | Enter `INCIDENT_RECOVERY`; freeze normal dispatch/checkpoint/commit/push; require owner decision for remote-side remediation and full correction task packet for file changes. |
| wrong_branch_push | Enter `INCIDENT_RECOVERY`; freeze normal dispatch/checkpoint/commit/push; require owner decision for branch-side remediation and full correction task packet for file changes. |
| invalid_task_packet_commit | Enter `INCIDENT_RECOVERY`; block dispatch from the invalid packet; require validation, correction audit, and checkpoint preflight before resume. |
| forbidden_files | Enter `INCIDENT_RECOVERY`; reject acceptance; require scoped correction and independent audit before resume. |
| secret_exposure | Enter `INCIDENT_RECOVERY`; do not print secret values; block checkpoint/commit/push; require redacted recovery evidence, owner security action when applicable, secret scan, and audit before resume. |
| runtime_corruption | Enter `INCIDENT_RECOVERY`; reread runtime files; repair only governed runtime/routing metadata directly; require task packet for non-runtime file changes. |
| Tester fail | Developer correction task; audit again after developer pass. |
| Finalization invariant failure | Stay out of completed; route correction. |
| Manual intervention | Freeze; reread all files; validate state tuple; regenerate NEXT_ACTION. |

## Audit false pass recovery

An audit false pass occurs when an auditor returned `STATUS: pass`, but
checkpoint preflight or another deterministic governance check finds a blocker
that the auditor was required to validate.

The orchestrator must record a bounded event:

```text
AUDIT_FALSE_PASS_DETECTED
FAILURE_TYPE: audit_miss
```

The event must reference the checked task, checked RESULT, audit RESULT,
preflight or validator reference, blocker class, and affected paths without
printing secret values.

Recovery rules:

- do not stage additional files;
- do not commit;
- do not push;
- do not route normal dependent work as ready;
- set dependent work to blocked until correction passes;
- route to a bounded correction task with `FAILURE_TYPE: audit_miss`;
- if the correction changes files, `TASK_PACKET: NONE` is forbidden and a full
  correction task packet is required;
- the correction result must pass an independent audit and checkpoint
  eligibility preflight before commit or push can be attempted.

Audit false pass is also an `incident_recovery` class under
`INCIDENT_RECOVERY.md`.

## Incident recovery

Material incidents are governed by:

```text
agent-system/02_runtime/INCIDENT_RECOVERY.md
```

Incident classes:

```text
wrong_remote_push
wrong_branch_push
invalid_task_packet_commit
forbidden_files
secret_exposure
runtime_corruption
audit_false_pass
```

When an incident is active:

- normal dispatch, checkpoint, commit, and push are forbidden;
- `INCIDENT_RECOVERY` freeze rules apply before ordinary correction routing;
- `TASK_PACKET_NONE_FILE_CHANGES_FORBIDDEN` applies to every correction route;
- the orchestrator may update only runtime/routing metadata directly;
- profile artifacts, project docs, task packets, package docs, source files,
  committed content, and secret-containing files require a full correction
  task packet before any file-changing repair;
- resume requires the class-specific evidence, owner decisions where needed,
  independent audit for file-changing corrections, checkpoint preflight, and
  validated runtime state.

## GAP recovery

- GAP is identified by profile agent RESULT only.
- Orchestrator records GAP and blocks dependent branch.
- Owner/solution_architect answer does not automatically close GAP if source-of-truth must change.
- GAP closes only when resolution is reflected in accepted docs/tasks/runtime state.

## Blocker routing

```text
business decision missing       -> project_owner
functional ambiguity            -> project_owner or solution_architect
technical/runtime design issue  -> solution_architect
implementation defect           -> developer correction task
missing package instruction     -> project_owner or package-governance correction
missing project doc/task packet -> solution_architect
missing verified behavior       -> tester or solution_architect through orchestrator
```

## Correction task rules

- Correction is one bounded task.
- Correction uses a fresh agent.
- Correction result follows normal audit/testing/doc path.
- Correction scope must not expand beyond the failure unless solution_architect creates a new task.
- Repeated same-class failure escalates to solution_architect or owner routing.
