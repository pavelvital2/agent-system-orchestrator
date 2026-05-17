# VIOLATION_RECOVERY

## Purpose

This document defines deterministic recovery from governance, workflow, filesystem, runtime-state, GAP, blocked, and manual-intervention failures.

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

`violation` is an orchestrator-derived recovery/logging category for governance, workflow, filesystem, runtime-state, forbidden file change, audit false pass, or formally invalid RESULT handling.

When a RESULT is formally invalid, including a missing mandatory field or a `STATUS` outside the profile-agent enum, the orchestrator must not route by RESULT `STATUS`.

Before recovery/reformat routing, the orchestrator must log the invalid RESULT as an orchestrator-classified `violation` entry using the deterministic fallback from `AGENT_RESULTS_LOG_TEMPLATE.md`.

## Recovery table

| Violation | Recovery |
|---|---|
| Missing bootstrap input | `wait_for_owner`; no designer dispatch. |
| Missing runtime file | Create from valid template or freeze if template missing/invalid. |
| Runtime schema violation | Enter correction; regenerate valid runtime state. |
| Schema/template mismatch | Governance freeze until package docs align. |
| Invalid transition | Enter correction; do not dispatch. |
| Forbidden file change | Log RESULT; mark workflow violation; route correction; do not accept. |
| Deprecated doc in REQUIRED_DOCS | Task packet invalid; route to designer/correction. |
| Superseded task selected | Stop dispatch; route to replacing task or correction. |
| Agent RESULT format invalid | Log deterministic `violation` entry; do not route by status; request governed correction/reformat. |
| Agent STATUS gap | Register GAP; block dependent branch; route by GAP type. |
| Agent STATUS blocked | Route by blocker type; do not continue dependent branch. |
| Auditor fail | Checked result not accepted; correction to checked role/designer. |
| Audit false pass after checkpoint preflight | Record `AUDIT_FALSE_PASS_DETECTED`; create correction input with `FAILURE_TYPE: audit_miss`; do not commit or push. |
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

## GAP recovery

- GAP is identified by profile agent RESULT only.
- Orchestrator records GAP and blocks dependent branch.
- Owner/designer answer does not automatically close GAP if source-of-truth must change.
- GAP closes only when resolution is reflected in accepted docs/tasks/runtime state.

## Blocker routing

```text
business decision missing       -> project_owner
functional ambiguity            -> project_owner or designer
technical/runtime design issue  -> designer
implementation defect           -> developer correction task
missing package instruction     -> project_owner or package-governance correction
missing project doc/task packet -> designer
missing verified behavior       -> tester or designer through orchestrator
```

## Correction task rules

- Correction is one bounded task.
- Correction uses a fresh agent.
- Correction result follows normal audit/testing/doc path.
- Correction scope must not expand beyond the failure unless designer creates a new task.
- Repeated same-class failure escalates to designer or owner routing.
