# PROFILE_AGENT_LIFECYCLE

## Purpose

This document defines the mandatory lifecycle policy for every dispatched
profile-agent instance.

## Mandatory invariant

```text
one agent = one task = one RESULT
AGENT_LIFECYCLE_POLICY: one_agent_one_task_delete_after_result
```

Reuse is forbidden. After a profile agent returns its RESULT, the orchestrator
must close or terminate that profile-agent instance and must not send it any
new task, correction, audit follow-up, or "also fix" request.

After RESULT, the raw profile-agent context must be deleted or rendered
inaccessible for future work. If the runner or chat environment has no
physical deletion primitive, the orchestrator must record logical context
deletion through the termination event: no further messages, no reuse, and no
downstream source-of-truth status for raw context.

This policy applies to every profile execution role, including auditor agents.
Orchestrator control flow is not a profile-agent task and must not be used to
bypass this policy.

## Lifecycle states

The lifecycle for one profile-agent instance is:

```text
AGENT_INSTANCE_CREATED
AGENT_TASK_DISPATCHED
AGENT_RESULT_RECEIVED
AGENT_RESULT_VALIDATED
ARTIFACT_ACCEPTED
AGENT_INSTANCE_TERMINATED
AUDIT_ROUTE_READY
```

The forbidden state is:

```text
AGENT_REUSED_FOR_NEXT_TASK
```

Any reuse attempt is a runtime lifecycle violation. The next unit of work must
be represented by a new task packet and a new `AGENT_INSTANCE_ID`.

## Required runtime events

The canonical machine-readable lifecycle log is:

```text
project-runtime/agents/instances.jsonl
```

The orchestrator records one JSON object per event. Required events for each
profile-agent instance are:

```json
{"event":"agent_instance_created","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","role":"developer","timestamp_utc":"2026-05-17T10:00:00Z"}
{"event":"agent_task_dispatched","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","role":"developer","timestamp_utc":"2026-05-17T10:01:00Z"}
{"event":"agent_result_received","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","result_ref":"project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md","reuse_allowed":false,"timestamp_utc":"2026-05-17T10:30:00Z"}
{"event":"artifact_accepted","event_type":"ARTIFACT_ACCEPTED","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","artifact_id":"RESULT_TASK_DEMO_001_ATTEMPT_001","artifact_ref":"project-runtime/artifacts/accepted/TASK_DEMO_001/manifest.json","receipt_ref":"project-runtime/receipts/artifacts/TASK_DEMO_001/RESULT_TASK_DEMO_001_ATTEMPT_001.acceptance.json","timestamp_utc":"2026-05-17T10:30:30Z"}
{"event":"agent_instance_terminated","event_type":"AGENT_TERMINATED","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","result_ref":"project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md","artifact_ids":["RESULT_TASK_DEMO_001_ATTEMPT_001"],"artifact_receipt_refs":["project-runtime/receipts/artifacts/TASK_DEMO_001/RESULT_TASK_DEMO_001_ATTEMPT_001.acceptance.json"],"reuse_allowed":false,"timestamp_utc":"2026-05-17T10:31:00Z"}
{"event":"audit_route_ready","event_type":"AUDIT_ROUTE_READY","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","result_ref":"project-runtime/results/worker/RESULT_TASK_DEMO_001_ATTEMPT_001.md","artifact_ids":["RESULT_TASK_DEMO_001_ATTEMPT_001"],"artifact_receipt_refs":["project-runtime/receipts/artifacts/TASK_DEMO_001/RESULT_TASK_DEMO_001_ATTEMPT_001.acceptance.json"],"timestamp_utc":"2026-05-17T10:31:01Z"}
```

`agent_result_received` and `agent_instance_terminated` must record
`reuse_allowed: false`.

The mandatory completion ordering depends on result acceptance mode.

Result-only outputs:

```text
RESULT_RECEIVED -> RESULT_VALIDATED -> RESULT_ACCEPTED -> AGENT_TERMINATED -> AUDIT_ROUTE_READY
```

Artifact-producing outputs:

```text
RESULT_RECEIVED -> ARTIFACT_PACKAGE_RECEIVED -> ARTIFACT_VALIDATED -> ARTIFACT_ACCEPTED -> AGENT_TERMINATED -> AUDIT_ROUTE_READY
```

The legacy compressed artifact sequence remains valid for compatibility:

```text
RESULT_RECEIVED -> ARTIFACT_ACCEPTED -> AGENT_TERMINATED -> AUDIT_ROUTE_READY
```

`ARTIFACT_ACCEPTED`, `AGENT_TERMINATED`, and `AUDIT_ROUTE_READY` events must
carry the accepted `artifact_id`, accepted artifact ref, and artifact
acceptance receipt ref. `AUDIT_ROUTE_READY` is a readiness marker only; it does
not dispatch an auditor or mutate checkpoint state.

For `RESULT_ACCEPTANCE_MODE: result_only` with
`ARTIFACT_PACKAGE_REQUIRED: false`, `RESULT_ACCEPTED` is governed result
evidence and no synthetic P5 artifact package entry is required before
termination or audit routing.

## Required RESULT fields

Every profile-agent RESULT must include the full current
`agent-system/03_templates/AGENT_RESULT_TEMPLATE.md` structure plus these
lifecycle fields:

```text
TASK_ID
AGENT_INSTANCE_ID
SUMMARY
CHANGED_FILES
COMMANDS_RUN
TESTS_RUN
RISKS
LIMITATIONS
REUSE_ALLOWED: false
AGENT_TERMINATION_REQUIRED: true
```

`STATUS` remains the canonical RESULT status field. `TASK_ID` must identify
the dispatched task and must match the task named in `TASK`.

## Termination event

After `RESULT_RECEIVED`, an artifact-producing profile-agent RESULT remains
candidate artifact package output under `project-runtime/artifacts/candidates/`.
The orchestrator must accept the governed candidate package into
`project-runtime/artifacts/accepted/`, record `ARTIFACT_ACCEPTED` with its
receipt, and only then emit `agent_instance_terminated` for the same
`AGENT_INSTANCE_ID`. A result-only RESULT is validated and accepted as RESULT
evidence directly, then the orchestrator may emit `agent_instance_terminated`
without synthetic accepted artifact package state. The task can be treated as
audit-route-ready only after the subsequent `AUDIT_ROUTE_READY` event.

Downstream context must cite accepted artifact packages or rendered views under
`project-runtime/rendered/`. Raw agent context, candidate packages, raw
artifacts, and rejected artifacts must not be treated as accepted source of
truth for the next profile-agent instance.

The termination event is required even when the runtime environment cannot
physically delete a chat, process, container, or session.

## Logical termination vs physical deletion

Physical deletion is environment-specific and optional. Logical termination is
mandatory and means:

- the agent receives no further messages;
- the agent is not reused for any next task;
- the raw agent context is deleted or treated as deleted for future work;
- the agent context is not treated as source of truth;
- only the standardized RESULT and lifecycle events remain authoritative;
- any correction, retry, audit, or next task starts with a fresh profile-agent
  instance.

If physical deletion is available, it may be used as implementation evidence.
It does not replace the required logical termination event.

## Lint rule

`aso lint` must fail when:

- a RESULT exists for an `AGENT_INSTANCE_ID` but
  `project-runtime/agents/instances.jsonl` lacks an
  `agent_instance_terminated` event for that instance;
- a RESULT has `REUSE_ALLOWED` other than `false`;
- a RESULT has `AGENT_TERMINATION_REQUIRED` other than `true`;
- an `agent_result_received` event has `reuse_allowed` other than `false`;
- one `AGENT_INSTANCE_ID` is associated with more than one task id.

These checks are implemented as read-only lifecycle lint findings in
`agent-system/tools/aso/commands/lint.py`.
