# PROFILE_AGENT_LIFECYCLE

## Purpose

This document defines the mandatory lifecycle policy for every dispatched
profile-agent instance.

## Mandatory invariant

```text
one agent = one task = one RESULT
```

Reuse is forbidden. After a profile agent returns its RESULT, the orchestrator
must close or terminate that profile-agent instance and must not send it any
new task, correction, audit follow-up, or "also fix" request.

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
AGENT_INSTANCE_TERMINATED
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
{"event":"agent_result_received","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","result_ref":"project-runtime/results/RESULT_TASK_DEMO_001_ATTEMPT_001.md","reuse_allowed":false,"timestamp_utc":"2026-05-17T10:30:00Z"}
{"event":"agent_instance_terminated","agent_instance_id":"agent_TASK_DEMO_001_attempt_001","task_id":"TASK_DEMO_001","reuse_allowed":false,"timestamp_utc":"2026-05-17T10:31:00Z"}
```

`agent_result_received` and `agent_instance_terminated` must record
`reuse_allowed: false`.

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

After `AGENT_RESULT_RECEIVED`, the orchestrator must emit
`agent_instance_terminated` for the same `AGENT_INSTANCE_ID` before the task can
be treated as lifecycle-complete.

The termination event is required even when the runtime environment cannot
physically delete a chat, process, container, or session.

## Logical termination vs physical deletion

Physical deletion is environment-specific and optional. Logical termination is
mandatory and means:

- the agent receives no further messages;
- the agent is not reused for any next task;
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
